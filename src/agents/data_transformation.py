"""
Impact scorer using pure LLM.

LLM reads question + description + yes_price
and determines: impact_score (0-100) and direction (Bullish/Bearish/Neutral).
"""

import re
import json
from typing import Any

from src.llm import get_llm_object
from src.agents.data_filter import filter_by_consent


SENSITIVE_PATTERNS = [
    r"\b(trump|biden|harris|obama|clinton|bush)\b",
    r"\b(xi jinping|putin|kim jong|netanyahu|abbas)\b",
    r"\b(democrat|republican|democratic party|gop)\b",
    r"\b(impeach|indict|arrest|prison|jail)\b",
    r"\b(assassination|killed|murder|death)\b",
    r"\b(nuclear war|nuclear attack|nuclear strike)\b",
]


def sanitize_text(text: str) -> str:
    sanitized = text
    for pattern in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)
    return sanitized


def classify_economic_financial_with_llm(contracts: list[dict], batch_size: int = 10) -> list[dict]:
    """Use LLM to classify which contracts are purely economic/financial.
    
    Args:
        contracts: List of contract dicts
        batch_size: Number of contracts per LLM call (default: 10)
    
    Returns:
        List of contracts classified as economic/financial
    """
    llm = get_llm_object()
    economic_contracts = []
    
    for i in range(0, len(contracts), batch_size):
        batch = contracts[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(contracts) + batch_size - 1) // batch_size
        
        print(f"  Classifying batch {batch_num}/{total_batches} ({len(batch)} contracts)...")
        
        contract_texts = []
        for idx, contract in enumerate(batch):
            question = contract.get("question", "")
            description = contract.get("description", "")[:200]
            contract_texts.append(f"[{idx}] {question}\n    {description}")
        
        contracts_str = "\n\n".join(contract_texts)
        
        prompt = f"""You are filtering prediction market contracts to identify ONLY those that are purely economic or financial in nature.

Economic/Financial contracts include:
- Macroeconomic indicators (GDP, unemployment, inflation, PMI, retail sales, housing)
- Monetary policy (Fed, Bank of England, ECB, interest rates, quantitative easing)
- Currency markets (EUR/USD, forex, exchange rates)
- Bond markets (yield curve, credit spreads, treasury yields)
- Trade indicators (trade balance, tariffs, imports/exports)
- Housing market (home prices, mortgage rates)
- Broad market indices (S&P 500, Nasdaq, Dow Jones)
- Major commodities (oil, gold, silver, copper, agriculture)

NOT economic/financial (exclude these):
- Cryptocurrency price targets (Bitcoin, Ethereum, etc.)
- Individual company events (IPOs, M&A, CEO changes, market cap)
- Political events (elections, impeachment, legislation)
- War/geopolitical conflicts (military strikes, invasions, sanctions)
- Sports, entertainment, personal events
- Technology/product launches (unless purely economic indicator)

Examples:
- "Will US unemployment reach 6.0%?" → YES (economic indicator)
- "Will federal funds rate be 2.25%?" → YES (monetary policy)
- "Will WTI Crude Oil hit $65?" → YES (commodity)
- "Will Bitcoin reach $95,000?" → NO (cryptocurrency)
- "OpenAI IPO above $1T?" → NO (company-specific)
- "Stripe acquire PayPal?" → NO (company M&A)
- "Will recession happen?" → YES (macroeconomic)

For each contract, answer YES if it's purely economic/financial, NO otherwise.

Contracts to classify:
{contracts_str}

Return a JSON object mapping each index to YES or NO:
{{"0": "YES", "1": "NO", "2": "YES"}}

Return ONLY the JSON object."""

        try:
            response = llm.invoke(prompt)
            content = response.content.strip()
            
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
                classifications = json.loads(json_str)
                
                for idx_str, classification in classifications.items():
                    idx = int(idx_str)
                    if 0 <= idx < len(batch):
                        if classification.upper() == "YES":
                            economic_contracts.append(batch[idx])
        except Exception as e:
            print(f"    Warning: Classification failed ({e}), skipping batch")
    
    print(f"\n  Classification complete: {len(economic_contracts)} / {len(contracts)} are economic/financial")
    return economic_contracts


def score_contracts_with_llm(contracts: list[dict], batch_size: int = 10) -> list[dict]:
    """Score contracts for S&P 500 impact using LLM.
    
    For each contract, LLM determines:
    1. impact_score (0-100): Magnitude of potential S&P 500 impact
       - 0 = no impact on S&P 500
       - 100 = extremely high impact on S&P 500
    2. direction: Bullish / Bearish / Neutral for S&P 500
    
    The LLM receives question, description, AND yes_price to make this determination.
    
    Args:
        contracts: List of contract dicts to score
        batch_size: Number of contracts to process per LLM call
    
    Returns:
        List of contracts with impact_score and direction added
    """
    llm = get_llm_object()
    scored_contracts = []
    
    for i in range(0, len(contracts), batch_size):
        batch = contracts[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(contracts) + batch_size - 1) // batch_size
        
        print(f"  Scoring batch {batch_num}/{total_batches} ({len(batch)} contracts)...")
        
        contract_texts = []
        for idx, contract in enumerate(batch):
            question = sanitize_text(contract.get("question", ""))
            description = sanitize_text(contract.get("description", ""))[:300]
            yes_price = contract.get("yes_price", 0.5)
            volume = contract.get("volume", 0)
            contract_texts.append(
                f"[{idx}] Question: {question}\n"
                f"    Description: {description}\n"
                f"    Yes Price: {yes_price} ({yes_price*100:.1f}% probability)\n"
                f"    Volume: ${volume:,.0f}"
            )
        
        contracts_str = "\n\n".join(contract_texts)
        
        prompt = f"""You are analyzing prediction market contracts to determine their IMPACT on the S&P 500 stock market.

For each contract, determine:
1. IMPACT SCORE (0-100): How much could this contract's outcome impact the S&P 500?
   - 0 = No impact on S&P 500 (niche topic, small market)
   - 25 = Low impact (minor economic indicator, small policy change)
   - 50 = Moderate impact (sector-specific news, medium policy)
   - 75 = High impact (major economic data, significant policy, geopolitical event)
   - 100 = Extremely high impact (Fed decision, recession, major war, financial crisis)

2. DIRECTION: If this contract resolves YES, would it be Bullish, Bearish, or Neutral for S&P 500?
   - "Bullish" = Good for S&P 500 (growth, peace, rate cuts, stability)
   - "Bearish" = Bad for S&P 500 (recession, war, rate hikes, crisis)
   - "Neutral" = Mixed or unclear impact

3. REASON: Provide a 1-sentence explanation of why this contract's outcome would be Bullish/Bearish/Neutral for S&P 500.

CRITICAL: Consider the yes_price when determining DIRECTION:

For BAD EVENT contracts (recession, war, crisis, unemployment, inflation spike):
  - Low yes_price = bad event UNLIKELY = BULLISH for S&P 500
  - High yes_price = bad event LIKELY = BEARISH for S&P 500

For GOOD EVENT contracts (peace deal, rate cut, growth, IPO, price target):
  - High yes_price = good event LIKELY = BULLISH for S&P 500
  - Low yes_price = good event UNLIKELY = BEARISH for S&P 500

Examples:
- "Will recession happen?" at 7.5% yes → recession unlikely → BULLISH, impact: 85, reason: "Low recession probability signals economic stability and continued corporate earnings growth"
- "Will Fed cut rates?" at 80% yes → rate cut likely → BULLISH, impact: 90, reason: "Fed rate cuts lower borrowing costs for corporations, boosting profit margins and equity valuations"
- "Will war escalate?" at 60% yes → war likely → BEARISH, impact: 80, reason: "Geopolitical conflict increases market uncertainty and disrupts global supply chains"
- "Will Bitcoin hit $150K?" at 2.3% yes → unlikely → BEARISH, impact: 15, reason: "Crypto market has limited direct impact on traditional equity valuations"
- "OpenAI IPO above $1T?" at 72.5% yes → likely → BULLISH, impact: 25, reason: "Major tech IPOs boost market sentiment and innovation sector valuations"

Contracts to analyze:
{contracts_str}

Return a JSON object mapping each contract index to its analysis:
{{"0": {{"impact_score": 85, "direction": "Bullish", "reason": "Low recession probability signals economic stability and continued corporate earnings growth"}}, "1": {{"impact_score": 15, "direction": "Bearish", "reason": "Crypto market has limited direct impact on traditional equity valuations"}}}}

Return ONLY the JSON object."""

        try:
            response = llm.invoke(prompt)
            content = response.content.strip()
            
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
                classifications = json.loads(json_str)
                
                for idx_str, classification in classifications.items():
                    idx = int(idx_str)
                    if 0 <= idx < len(batch):
                        contract = batch[idx].copy()
                        contract["impact_score"] = int(classification.get("impact_score", 0))
                        contract["direction"] = classification.get("direction", "Neutral")
                        contract["reason"] = classification.get("reason", "")
                        scored_contracts.append(contract)
            else:
                print(f"    Warning: Could not parse LLM response, skipping batch")
        
        except Exception as e:
            print(f"    Warning: Batch scoring failed ({e}), skipping batch")
    
    print(f"\n  Scoring complete:")
    print(f"    Total contracts scored: {len(scored_contracts)} / {len(contracts)}")
    
    return scored_contracts


def predict_market_direction(scored_contracts: list[dict]) -> dict[str, Any]:
    """Predict overall market direction based on impact-weighted directional sentiment.
    
    Args:
        scored_contracts: List of contracts with impact_score and direction
    
    Returns:
        Dict containing:
        - predicted_direction: Bullish / Bearish / Neutral
        - confidence_pct: 0-100% confidence in prediction
        - bullish_impact_sum: Total impact of bullish contracts
        - bearish_impact_sum: Total impact of bearish contracts
        - neutral_impact_sum: Total impact of neutral contracts
        - total_contracts_scored: Number of contracts analyzed
    """
    bullish = [c for c in scored_contracts if c.get("direction") == "Bullish"]
    bearish = [c for c in scored_contracts if c.get("direction") == "Bearish"]
    neutral = [c for c in scored_contracts if c.get("direction") == "Neutral"]
    
    bull_sum = sum(c.get("impact_score", 0) for c in bullish)
    bear_sum = sum(c.get("impact_score", 0) for c in bearish)
    neut_sum = sum(c.get("impact_score", 0) for c in neutral)
    
    directional_sum = bull_sum + bear_sum
    if directional_sum == 0:
        return {
            "predicted_direction": "Neutral",
            "confidence_pct": 0.0,
            "bullish_impact_sum": bull_sum,
            "bearish_impact_sum": bear_sum,
            "neutral_impact_sum": neut_sum,
            "total_contracts_scored": len(scored_contracts),
        }
    
    if bull_sum > bear_sum:
        direction = "Bullish"
        confidence = bull_sum / directional_sum * 100
    elif bear_sum > bull_sum:
        direction = "Bearish"
        confidence = bear_sum / directional_sum * 100
    else:
        direction = "Neutral"
        confidence = 50.0
    
    return {
        "predicted_direction": direction,
        "confidence_pct": round(confidence, 1),
        "bullish_impact_sum": bull_sum,
        "bearish_impact_sum": bear_sum,
        "neutral_impact_sum": neut_sum,
        "total_contracts_scored": len(scored_contracts),
    }


def score_contracts(contracts: list[dict]) -> dict[str, Any]:
    """Main entry point: Score contracts for S&P 500 impact.
    
    1. Filter by consensus (majority consensus)
    2. LLM classifies which contracts are economic/financial
    3. LLM scores remaining contracts for impact (0-100) and direction
    4. Predict market direction
    
    Args:
        contracts: List of contract dicts to score
    
    Returns:
        Dict containing:
        - all_scored_contracts: All contracts with impact_score and direction
        - market_prediction: Market direction prediction with confidence
    """
    print(f"  Filtering {len(contracts)} contracts by consensus (majority consensus)...")
    consensus_contracts = filter_by_consent(contracts)
    print(f"  After consensus filter: {len(consensus_contracts)} contracts")
    
    if not consensus_contracts:
        print("  No contracts after consensus filter")
        return {
            "all_scored_contracts": [],
            "market_prediction": {
                "predicted_direction": "Neutral",
                "confidence_pct": 0.0,
                "bullish_impact_sum": 0,
                "bearish_impact_sum": 0,
                "neutral_impact_sum": 0,
                "total_contracts_scored": 0,
            },
        }
    
    print(f"  Using LLM to classify {len(consensus_contracts)} contracts as economic/financial...")
    economic_contracts = classify_economic_financial_with_llm(consensus_contracts, batch_size=10)
    
    if not economic_contracts:
        print("  No economic/financial contracts after classification")
        return {
            "all_scored_contracts": [],
            "market_prediction": {
                "predicted_direction": "Neutral",
                "confidence_pct": 0.0,
                "bullish_impact_sum": 0,
                "bearish_impact_sum": 0,
                "neutral_impact_sum": 0,
                "total_contracts_scored": 0,
            },
        }
    
    print(f"  Scoring {len(economic_contracts)} economic/financial contracts...")
    try:
        scored_contracts = score_contracts_with_llm(economic_contracts, batch_size=10)
        
        market_prediction = predict_market_direction(scored_contracts)
        print(f"\n  Market Direction Prediction:")
        print(f"    Predicted Direction: {market_prediction['predicted_direction']}")
        print(f"    Confidence: {market_prediction['confidence_pct']}%")
        print(f"    Bullish Impact: {market_prediction['bullish_impact_sum']} | Bearish Impact: {market_prediction['bearish_impact_sum']} | Neutral Impact: {market_prediction['neutral_impact_sum']}")
        
        return {
            "all_scored_contracts": scored_contracts,
            "market_prediction": market_prediction,
        }
    except Exception as e:
        print(f"  Warning: LLM scoring failed ({e})")
        return {
            "all_scored_contracts": [],
            "market_prediction": {
                "predicted_direction": "Neutral",
                "confidence_pct": 0.0,
                "bullish_impact_sum": 0,
                "bearish_impact_sum": 0,
                "neutral_impact_sum": 0,
                "total_contracts_scored": 0,
            },
        }
