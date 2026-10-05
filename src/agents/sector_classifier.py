"""
Sector classifier using pure LLM.

No keyword matching. LLM reads question + description + yes_price
and determines: sector, sentiment_score, signal.
"""

import re
import json
from typing import Any

from src.llm import get_llm_object
from src.sectors import SECTORS, get_sector


SENSITIVE_PATTERNS = [
    r"\b(trump|biden|harris|obama|clinton|bush)\b",
    r"\b(xi jinping|putin|kim jong|netanyahu|abbas)\b",
    r"\b(democrat|republican|democratic party|gop)\b",
    r"\b(impeach|indict|arrest|prison|jail)\b",
    r"\b(assassination|killed|murder|death)\b",
    r"\b(nuclear war|nuclear attack|nuclear strike)\b",
]

IRRELEVANT_PATTERNS = [
    r"\b(exact score|o/u|over/under|spread|vs\.?|versus)\b",
    r"\b(will.*win the.*final|championship|super bowl|world series|nba|nfl|mlb|nhl)\b",
    r"\b(will.*win.*oscar|emmy|grammy|tony|award)\b",
    r"\b(will.*movie|film|album|song|book)\b.*\b(top|grossing|best)\b",
    r"\b(will.*date|marry|divorce|engage)\b",
    r"\b(will.*have.*baby|pregnant|give birth)\b",
]


def sanitize_text(text: str) -> str:
    sanitized = text
    for pattern in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)
    return sanitized


def is_irrelevant_contract(contract: dict) -> bool:
    """Check if a contract is clearly irrelevant to S&P 500 prediction."""
    question = contract.get("question", "").lower()
    description = contract.get("description", "").lower()
    text = f"{question} {description}"
    
    for pattern in IRRELEVANT_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    
    return False


def filter_irrelevant_contracts(contracts: list[dict]) -> list[dict]:
    """Filter out contracts that are clearly irrelevant to S&P 500 prediction."""
    relevant = []
    filtered_count = 0
    
    for contract in contracts:
        if is_irrelevant_contract(contract):
            filtered_count += 1
        else:
            relevant.append(contract)
    
    if filtered_count > 0:
        print(f"  Filtered out {filtered_count} irrelevant contracts (sports, entertainment, etc.)")
    
    return relevant


def classify_contracts_with_llm(contracts: list[dict], batch_size: int = 10) -> dict[str, list[dict]]:
    """Classify contracts and determine sentiment using LLM only.
    
    For each contract, LLM determines:
    1. Which sector it belongs to
    2. Sentiment score (0.0 = very bearish for S&P 500, 1.0 = very bullish)
    3. Signal (Bullish / Bearish / Neutral)
    
    The LLM receives question, description, AND yes_price to make this determination.
    
    Args:
        contracts: List of contract dicts to classify
        batch_size: Number of contracts to process per LLM call
    
    Returns:
        Dict mapping sector_id to list of contracts in that sector
    """
    llm = get_llm_object()
    grouped = {sector_id: [] for sector_id in SECTORS.keys()}
    
    sector_list = "\n".join([f"- {sid}: {sector.name}" for sid, sector in SECTORS.items()])
    
    for i in range(0, len(contracts), batch_size):
        batch = contracts[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(contracts) + batch_size - 1) // batch_size
        
        print(f"  Classifying batch {batch_num}/{total_batches} ({len(batch)} contracts)...")
        
        contract_texts = []
        for idx, contract in enumerate(batch):
            question = sanitize_text(contract.get("question", ""))
            description = sanitize_text(contract.get("description", ""))[:300]
            yes_price = contract.get("yes_price", 0.5)
            contract_texts.append(
                f"[{idx}] Question: {question}\n"
                f"    Description: {description}\n"
                f"    Yes Price: {yes_price} ({yes_price*100:.1f}% probability)"
            )
        
        contracts_str = "\n\n".join(contract_texts)
        
        prompt = f"""You are analyzing prediction market contracts to determine their impact on the S&P 500 stock market.

For each contract, determine:
1. SECTOR: Which sector does this contract belong to?
2. SENTIMENT SCORE: How does this contract's outcome affect S&P 500?
   - 0.0 = very bearish for S&P 500
   - 0.5 = neutral
   - 1.0 = very bullish for S&P 500
3. SIGNAL: "Bullish" (score > 0.6), "Bearish" (score < 0.4), or "Neutral" (0.4-0.6)

CRITICAL: Think about the DIRECTION of impact based on the yes_price:

For BAD EVENT contracts (recession, war, crisis, unemployment, inflation spike):
  - Low yes_price = bad event UNLIKELY = BULLISH for S&P 500 (score near 1.0)
  - High yes_price = bad event LIKELY = BEARISH for S&P 500 (score near 0.0)

For GOOD EVENT contracts (peace deal, rate cut, growth, IPO, price target):
  - High yes_price = good event LIKELY = BULLISH for S&P 500 (score near 1.0)
  - Low yes_price = good event UNLIKELY = BEARISH for S&P 500 (score near 0.0)

Examples:
- "Will recession happen?" at 7.5% yes → recession unlikely → BULLISH → score: 0.9
- "Will Fed cut rates?" at 80% yes → rate cut likely → BULLISH → score: 0.8
- "Will war escalate?" at 60% yes → war likely → BEARISH → score: 0.4
- "Leaders meet for peace?" at 10% yes → peace unlikely → BEARISH → score: 0.1
- "Will Bitcoin hit $150K?" at 2.3% yes → unlikely → BEARISH → score: 0.1
- "OpenAI IPO above $1T?" at 72.5% yes → likely → BULLISH → score: 0.8

Available sectors:
{sector_list}

Contracts to analyze:
{contracts_str}

Return a JSON object mapping each contract index to its analysis:
{{"0": {{"sector": "economic_growth", "sentiment_score": 0.9, "signal": "Bullish"}}, "1": {{"sector": "geopolitical_conflict", "sentiment_score": 0.1, "signal": "Bearish"}}}}

Use "unknown" for sector if the contract doesn't fit any sector or doesn't impact S&P 500.
Return ONLY the JSON object."""

        try:
            response = llm.invoke(prompt)
            content = response.content.strip()
            
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
                classifications = json.loads(json_str)
                
                unknown_count = 0
                for idx_str, classification in classifications.items():
                    idx = int(idx_str)
                    if 0 <= idx < len(batch):
                        contract = batch[idx]
                        sector_id = classification.get("sector", "unknown")
                        
                        contract["sector"] = sector_id
                        contract["sentiment_score"] = float(classification.get("sentiment_score", 0.5))
                        contract["signal"] = classification.get("signal", "Neutral")
                        
                        if sector_id in SECTORS:
                            grouped[sector_id].append(contract)
                        else:
                            unknown_count += 1
                
                if unknown_count > 0:
                    print(f"    Filtered out {unknown_count} irrelevant contracts")
            else:
                print(f"    Warning: Could not parse LLM response, skipping batch")
        
        except Exception as e:
            print(f"    Warning: Batch classification failed ({e}), skipping batch")
    
    total_classified = sum(len(c) for c in grouped.values())
    print(f"\n  Classification complete:")
    print(f"    Total contracts classified: {total_classified} / {len(contracts)}")
    for sector_id, sector_contracts in grouped.items():
        if sector_contracts:
            sector_name = SECTORS[sector_id].name
            avg_sentiment = sum(c.get("sentiment_score", 0.5) for c in sector_contracts) / len(sector_contracts)
            print(f"    {sector_name}: {len(sector_contracts)} contracts (avg sentiment: {avg_sentiment:.2f})")
    
    return grouped


def classify_contracts_hybrid(contracts: list[dict]) -> dict[str, list[dict]]:
    """Classify contracts using pure LLM approach.
    
    1. Filter out obviously irrelevant contracts (sports, entertainment, etc.)
    2. LLM classifies remaining contracts into sectors AND determines sentiment
    
    Args:
        contracts: List of contract dicts to classify
    
    Returns:
        Dict mapping sector_id to list of contracts in that sector
    """
    relevant_contracts = filter_irrelevant_contracts(contracts)
    
    if not relevant_contracts:
        print("  No relevant contracts after filtering")
        return {sector_id: [] for sector_id in SECTORS.keys()}
    
    print(f"  Using LLM to classify {len(relevant_contracts)} relevant contracts...")
    try:
        grouped = classify_contracts_with_llm(relevant_contracts, batch_size=10)
        return grouped
    except Exception as e:
        print(f"  Warning: LLM classification failed ({e})")
        return {sector_id: [] for sector_id in SECTORS.keys()}


def get_sector_summary(grouped_contracts: dict[str, list[dict]]) -> dict[str, Any]:
    summary = {}
    
    for sector_id, contracts in grouped_contracts.items():
        if sector_id == "unknown" or not contracts:
            continue
        
        sector = get_sector(sector_id)
        if not sector:
            continue
        
        summary[sector_id] = {
            "name": sector.name,
            "contract_count": len(contracts),
            "total_volume": sum(c.get("volume", 0) for c in contracts),
            "avg_sentiment_score": sum(c.get("sentiment_score", 0.5) for c in contracts) / len(contracts),
            "contracts": [
                {
                    "id": c.get("id"),
                    "question": c.get("question"),
                    "volume": c.get("volume"),
                    "yes_price": c.get("yes_price"),
                    "sentiment_score": c.get("sentiment_score", 0.5),
                    "signal": c.get("signal", "Neutral"),
                }
                for c in contracts[:5]
            ],
        }
    
    return summary
