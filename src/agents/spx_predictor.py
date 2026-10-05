import json
from typing import Any

from crewai import Agent, Task, Crew

from src.llm import get_llm
from src.sectors import get_sector


def determine_direction(aggregate: dict, sector_sentiments: dict) -> str:
    score = float(aggregate.get("sentiment_score", 0.5))
    stress = float(aggregate.get("stress_coefficient", 0.0))

    bullish_sectors = sum(
        1 for s in sector_sentiments.values()
        if s.get("signal") == "Bullish"
    )
    bearish_sectors = sum(
        1 for s in sector_sentiments.values()
        if s.get("signal") == "Bearish"
    )

    # High stress reduces confidence but doesn't override direction
    # Adjust effective sentiment based on stress
    effective_score = score
    if stress >= 0.7:
        # High stress: pull sentiment toward neutral (0.5)
        effective_score = 0.5 + (score - 0.5) * 0.5
    elif stress >= 0.5:
        # Medium stress: slight pull toward neutral
        effective_score = 0.5 + (score - 0.5) * 0.7

    if effective_score > 0.6 and bullish_sectors >= bearish_sectors:
        return "Bullish"
    elif effective_score < 0.4 and bearish_sectors >= bullish_sectors:
        return "Bearish"
    elif effective_score > 0.55:
        return "Slightly Bullish"
    elif effective_score < 0.45:
        return "Slightly Bearish"
    else:
        return "Neutral"


def determine_confidence(aggregate: dict, sector_sentiments: dict) -> str:
    stress = float(aggregate.get("stress_coefficient", 0.0))
    count = int(aggregate.get("contract_count", 0))
    score = float(aggregate.get("sentiment_score", 0.5))
    sector_count = int(aggregate.get("sector_count", 0))

    high_impact_sectors = sum(
        1 for s in sector_sentiments.values()
        if s.get("spx_weight", 0) >= 0.85 and s.get("signal") in ["Bullish", "Bearish"]
    )

    # High stress reduces confidence
    stress_penalty = 0
    if stress >= 0.7:
        stress_penalty = 2
    elif stress >= 0.5:
        stress_penalty = 1

    if (count >= 5 and stress < 0.5 and (score > 0.65 or score < 0.35)) or \
       (sector_count >= 3 and high_impact_sectors >= 2 and stress < 0.5):
        return "High" if stress_penalty == 0 else "Medium"
    elif count >= 3 and stress < 0.7:
        return "Medium" if stress_penalty == 0 else "Low"
    else:
        return "Low"


def build_sector_breakdown(sector_sentiments: dict) -> dict[str, Any]:
    breakdown = {}
    
    for sector_id, sentiment in sector_sentiments.items():
        sector = get_sector(sector_id)
        if not sector:
            continue
        
        breakdown[sector_id] = {
            "name": sector.name,
            "sentiment_score": sentiment.get("sentiment_score", 0.5),
            "stress_coefficient": sentiment.get("stress_coefficient", 0.0),
            "signal": sentiment.get("signal", "Neutral"),
            "contract_count": sentiment.get("contract_count", 0),
            "total_volume": sentiment.get("total_volume", 0),
            "spx_weight": sentiment.get("spx_weight", 0.5),
            "key_risk_factors": sentiment.get("key_risk_factors", []),
            "top_contracts": sentiment.get("top_contracts", []),
        }
    
    return breakdown


def build_predictor_agent() -> Agent:
    return Agent(
        role="S&P 500 Tactical Director",
        goal=(
            "Generate a structured market report with directional prediction, "
            "confidence level, and detailed sector-by-sector rationale for the S&P 500 "
            "over a 7-day horizon based on Polymarket sentiment data."
        ),
        backstory=(
            "You are a seasoned macro strategist and portfolio manager with deep "
            "expertise in translating prediction market signals into actionable "
            "equity market forecasts. You synthesize sector-level sentiment vectors, "
            "stress coefficients, and contract-level data into clear, structured reports "
            "that institutional traders can act on. You identify which sectors are "
            "driving the overall market outlook."
        ),
        verbose=True,
        allow_delegation=False,
        llm=get_llm(),
    )


def build_predictor_task(
    agent: Agent,
    discovery_data: dict,
    quant_data: dict,
    sector_breakdown: dict,
) -> Task:
    quant_json = json.dumps({
        "aggregate": quant_data.get("aggregate", {}),
        "dominant_sectors": quant_data.get("dominant_sectors", []),
        "overall_risk_assessment": quant_data.get("overall_risk_assessment", ""),
    }, indent=2)
    
    breakdown_json = json.dumps(sector_breakdown, indent=2)

    return Task(
        description=(
            "Generate the final S&P 500 prediction report with sector breakdown.\n\n"
            f"Quantitative Analysis:\n{quant_json}\n\n"
            f"Sector Breakdown:\n{breakdown_json}\n\n"
            "Steps:\n"
            "1. Analyze the aggregate sentiment and stress levels.\n"
            "2. Review each sector's contribution to the overall outlook.\n"
            "3. Identify which sectors are driving the market direction.\n"
            "4. Determine the 7-day directional outlook for $SPX.\n"
            "5. Assign a confidence level (High/Medium/Low).\n"
            "6. Write a detailed rationale connecting sector signals to the forecast.\n"
            "7. Identify the market regime.\n\n"
            "Return your prediction as a JSON object with this schema:\n"
            "{\n"
            '  "market_regime": "<description of current macro regime>",\n'
            '  "sentiment_score": <0.0 to 1.0>,\n'
            '  "sp500_direction_7d": "<Bullish|Slightly Bullish|Neutral|Slightly Bearish|Bearish>",\n'
            '  "rationale": "<detailed multi-sentence explanation>",\n'
            '  "confidence_level": "<High|Medium|Low>",\n'
            '  "driving_sectors": ["<sector1>", "<sector2>"],\n'
            '  "risk_factors": ["<factor1>", "<factor2>"]\n'
            "}\n"
        ),
        expected_output="A JSON object containing the final S&P 500 prediction report with sector analysis.",
        agent=agent,
    )


def run_prediction(
    discovery_data: dict,
    quant_data: dict,
) -> dict[str, Any]:
    sector_sentiments = quant_data.get("sector_sentiments", {})
    aggregate = quant_data.get("aggregate", {})
    
    direction = determine_direction(aggregate, sector_sentiments)
    confidence = determine_confidence(aggregate, sector_sentiments)
    sector_breakdown = build_sector_breakdown(sector_sentiments)

    agent = build_predictor_agent()
    task = build_predictor_task(agent, discovery_data, quant_data, sector_breakdown)
    crew = Crew(
        agents=[agent],
        tasks=[task],
        verbose=True,
    )
    
    try:
        result = crew.kickoff()
        raw = str(result)
        
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            prediction = json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError):
            prediction = {
                "market_regime": discovery_data.get("market_regime", "Unknown"),
                "rationale": raw[:500],
            }
    except Exception as e:
        print(f"LLM prediction failed: {e}")
        prediction = {
            "market_regime": discovery_data.get("market_regime", "Unknown"),
            "rationale": "LLM prediction unavailable",
        }

    prediction.setdefault("sentiment_score", aggregate.get("sentiment_score", 0.5))
    prediction.setdefault("sp500_direction_7d", direction)
    prediction.setdefault("confidence_level", confidence)
    prediction["sector_breakdown"] = sector_breakdown
    prediction["aggregate_metrics"] = aggregate
    prediction["dominant_sectors"] = quant_data.get("dominant_sectors", [])

    return prediction
