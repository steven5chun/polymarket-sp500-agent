"""
Quant scorer - aggregates LLM-provided sentiment scores per sector.

No keyword-based sentiment logic. Each contract already has sentiment_score
and signal from the LLM classifier. This module aggregates them.
"""

import json
import math
from typing import Any

from crewai import Agent, Task, Crew

from src.llm import get_llm
from src.sectors import SECTORS, get_sector


def compute_volume_weight(volume: float) -> float:
    if volume <= 0:
        return 0.0
    return min(1.0, math.log10(volume + 1) / 8.0)


def compute_prob_deviation(price: float) -> float:
    return abs(price - 0.5) * 2.0


def compute_stress_coefficient(contracts: list[dict]) -> float:
    """Compute stress coefficient based on volume and probability deviation.
    
    High volume + strong consensus (price far from 0.5) = high stress.
    This measures how much the market is pricing in, regardless of direction.
    """
    if not contracts:
        return 0.0

    scores = []
    for c in contracts:
        vol = float(c.get("volume", 0))
        price = float(c.get("yes_price", 0.5))
        vol_weight = compute_volume_weight(vol)
        prob_dev = compute_prob_deviation(price)
        stress = vol_weight * prob_dev
        scores.append(stress)

    if not scores:
        return 0.0
    return round(min(1.0, sum(scores) / len(scores) * 1.5), 4)


def compute_sector_sentiment(sector_id: str, contracts: list[dict]) -> dict[str, Any]:
    """Compute sector sentiment by aggregating LLM-provided sentiment scores.
    
    Each contract already has sentiment_score and signal from the LLM classifier.
    We aggregate these using volume-weighted averaging.
    """
    sector = get_sector(sector_id)
    if not sector or not contracts:
        return {}

    # Volume-weighted average of LLM-provided sentiment scores
    total_volume = sum(c.get("volume", 0) for c in contracts)
    if total_volume > 0:
        weighted_sentiment = sum(
            c.get("sentiment_score", 0.5) * c.get("volume", 0)
            for c in contracts
        ) / total_volume
    else:
        weighted_sentiment = sum(c.get("sentiment_score", 0.5) for c in contracts) / len(contracts)

    # Count signals from LLM
    bullish = sum(1 for c in contracts if c.get("signal") == "Bullish")
    bearish = sum(1 for c in contracts if c.get("signal") == "Bearish")
    neutral = sum(1 for c in contracts if c.get("signal") == "Neutral")

    # Determine overall sector signal
    if bullish > bearish and bullish > neutral:
        signal = "Bullish"
    elif bearish > bullish and bearish > neutral:
        signal = "Bearish"
    else:
        signal = "Neutral"

    stress = compute_stress_coefficient(contracts)

    return {
        "sector_id": sector_id,
        "sector_name": sector.name,
        "spx_weight": sector.spx_weight,
        "sentiment_score": round(weighted_sentiment, 4),
        "stress_coefficient": stress,
        "signal": signal,
        "contract_count": len(contracts),
        "total_volume": total_volume,
        "avg_implied_prob": round(sum(c.get("yes_price", 0.5) for c in contracts) / len(contracts), 4),
        "bullish_count": bullish,
        "bearish_count": bearish,
        "neutral_count": neutral,
        "top_contracts": [
            {
                "id": c.get("id"),
                "question": c.get("question")[:80],
                "volume": c.get("volume"),
                "yes_price": c.get("yes_price"),
                "sentiment_score": c.get("sentiment_score", 0.5),
                "signal": c.get("signal", "Neutral"),
            }
            for c in sorted(contracts, key=lambda x: x.get("volume", 0), reverse=True)[:3]
        ],
    }


def compute_all_sector_sentiments(
    grouped_contracts: dict[str, list[dict]]
) -> dict[str, dict[str, Any]]:
    sector_sentiments = {}
    
    for sector_id, contracts in grouped_contracts.items():
        if sector_id == "unknown" or not contracts:
            continue
        sentiment = compute_sector_sentiment(sector_id, contracts)
        if sentiment:
            sector_sentiments[sector_id] = sentiment
    
    return sector_sentiments


def compute_aggregate_sentiment(
    sector_sentiments: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    if not sector_sentiments:
        return {
            "sentiment_score": 0.5,
            "stress_coefficient": 0.0,
            "contract_count": 0,
            "total_volume": 0,
            "sector_count": 0,
        }
    
    total_weight = 0
    weighted_sentiment = 0
    weighted_stress = 0
    total_contracts = 0
    total_volume = 0
    
    for sector_id, sentiment in sector_sentiments.items():
        weight = sentiment.get("spx_weight", 0.5)
        total_weight += weight
        weighted_sentiment += sentiment["sentiment_score"] * weight
        weighted_stress += sentiment["stress_coefficient"] * weight
        total_contracts += sentiment["contract_count"]
        total_volume += sentiment["total_volume"]
    
    if total_weight > 0:
        avg_sentiment = weighted_sentiment / total_weight
        avg_stress = weighted_stress / total_weight
    else:
        avg_sentiment = 0.5
        avg_stress = 0
    
    return {
        "sentiment_score": round(avg_sentiment, 4),
        "stress_coefficient": round(avg_stress, 4),
        "contract_count": total_contracts,
        "total_volume": total_volume,
        "sector_count": len(sector_sentiments),
    }


def build_quant_agent() -> Agent:
    return Agent(
        role="Neural Sentiment Scoring Agent",
        goal=(
            "Analyze sector-level sentiment data from Polymarket contracts to identify "
            "key risk factors and determine which sectors are driving the S&P 500 outlook."
        ),
        backstory=(
            "You are a quantitative analyst specializing in prediction market "
            "microstructure. You analyze sector-level sentiment vectors and stress "
            "coefficients to identify key risk factors and market drivers."
        ),
        verbose=True,
        allow_delegation=False,
        llm=get_llm(),
    )


def build_quant_task(agent: Agent, discovery_data: dict, grouped_contracts: dict) -> Task:
    sector_summary = {}
    for sector_id, contracts in grouped_contracts.items():
        if sector_id == "unknown" or not contracts:
            continue
        sector = get_sector(sector_id)
        sector_summary[sector_id] = {
            "name": sector.name if sector else sector_id,
            "contract_count": len(contracts),
            "total_volume": sum(c.get("volume", 0) for c in contracts),
            "avg_sentiment_score": round(
                sum(c.get("sentiment_score", 0.5) for c in contracts) / len(contracts), 4
            ),
            "sample_contracts": [
                f"{c.get('question', '')[:50]} (yes: {c.get('yes_price', 0)}, sentiment: {c.get('sentiment_score', 0.5)})"
                for c in contracts[:3]
            ],
        }
    
    summary_json = json.dumps(sector_summary, indent=2)
    
    return Task(
        description=(
            f"Analyze the following Polymarket contract data grouped by sector:\n\n"
            f"Market Regime: {discovery_data.get('market_regime', 'Unknown')}\n\n"
            f"Sector Summary:\n{summary_json}\n\n"
            "Steps:\n"
            "1. Analyze each sector's sentiment and stress levels.\n"
            "2. Identify key risk factors for each sector.\n"
            "3. Determine which sectors are driving the overall market outlook.\n"
            "4. Return a structured JSON analysis.\n\n"
            "Return your analysis as a JSON object with this schema:\n"
            "{\n"
            '  "sector_analysis": {\n'
            '    "<sector_id>": {\n'
            '      "key_risk_factors": ["<factor1>", "<factor2>"],\n'
            '      "market_impact": "<high|medium|low>"\n'
            "    }\n"
            "  },\n"
            '  "dominant_sectors": ["<sector1>", "<sector2>"],\n'
            '  "overall_risk_assessment": "<brief assessment>"\n'
            "}\n"
        ),
        expected_output="A JSON object containing sector-level analysis and risk assessment.",
        agent=agent,
    )


def run_quant_scoring(discovery_data: dict, grouped_contracts: dict = None) -> dict[str, Any]:
    if grouped_contracts is None:
        from src.agents.sector_classifier import classify_contracts_hybrid
        contracts = discovery_data.get("all_contracts", [])
        grouped_contracts = classify_contracts_hybrid(contracts)
    
    sector_sentiments = compute_all_sector_sentiments(grouped_contracts)
    aggregate = compute_aggregate_sentiment(sector_sentiments)
    
    agent = build_quant_agent()
    task = build_quant_task(agent, discovery_data, grouped_contracts)
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
            llm_analysis = json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError):
            llm_analysis = {"overall_risk_assessment": raw[:200]}
    except Exception as e:
        print(f"LLM analysis failed: {e}")
        llm_analysis = {"overall_risk_assessment": "LLM analysis unavailable"}
    
    for sector_id, sentiment in sector_sentiments.items():
        if sector_id in llm_analysis.get("sector_analysis", {}):
            sector_analysis = llm_analysis["sector_analysis"][sector_id]
            sentiment["key_risk_factors"] = sector_analysis.get("key_risk_factors", [])
            sentiment["market_impact"] = sector_analysis.get("market_impact", "medium")
    
    return {
        "sector_sentiments": sector_sentiments,
        "aggregate": aggregate,
        "dominant_sectors": llm_analysis.get("dominant_sectors", []),
        "overall_risk_assessment": llm_analysis.get("overall_risk_assessment", ""),
    }
