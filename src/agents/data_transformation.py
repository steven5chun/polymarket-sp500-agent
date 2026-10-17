"""
Impact scorer using pure LLM.

LLM reads question + description + yes_price
and determines: impact_score (0-100) and direction (Bullish/Bearish/Neutral).
"""

import re
import json
from typing import Any

from src.llm import get_llm_object


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

CRITICAL: Consider the yes_price when determining DIRECTION:

For BAD EVENT contracts (recession, war, crisis, unemployment, inflation spike):
  - Low yes_price = bad event UNLIKELY = BULLISH for S&P 500
  - High yes_price = bad event LIKELY = BEARISH for S&P 500

For GOOD EVENT contracts (peace deal, rate cut, growth, IPO, price target):
  - High yes_price = good event LIKELY = BULLISH for S&P 500
  - Low yes_price = good event UNLIKELY = BEARISH for S&P 500

Examples:
- "Will recession happen?" at 7.5% yes → recession unlikely → BULLISH, impact: 85 (recession is high impact)
- "Will Fed cut rates?" at 80% yes → rate cut likely → BULLISH, impact: 90 (Fed decisions are very high impact)
- "Will war escalate?" at 60% yes → war likely → BEARISH, impact: 80 (geopolitical conflict is high impact)
- "Will Bitcoin hit $150K?" at 2.3% yes → unlikely → BEARISH, impact: 15 (crypto has limited S&P impact)
- "OpenAI IPO above $1T?" at 72.5% yes → likely → BULLISH, impact: 25 (tech IPO is moderate impact)

Contracts to analyze:
{contracts_str}

Return a JSON object mapping each contract index to its analysis:
{{"0": {{"impact_score": 85, "direction": "Bullish"}}, "1": {{"impact_score": 15, "direction": "Bearish"}}}}

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
                        scored_contracts.append(contract)
            else:
                print(f"    Warning: Could not parse LLM response, skipping batch")
        
        except Exception as e:
            print(f"    Warning: Batch scoring failed ({e}), skipping batch")
    
    print(f"\n  Scoring complete:")
    print(f"    Total contracts scored: {len(scored_contracts)} / {len(contracts)}")
    
    return scored_contracts


def get_top_impact_contracts(scored_contracts: list[dict], top_n: int = 5) -> list[dict]:
    """Get the top N contracts by impact score.
    
    Args:
        scored_contracts: List of contracts with impact_score
        top_n: Number of top contracts to return
    
    Returns:
        List of top N contracts sorted by impact_score (descending)
    """
    sorted_contracts = sorted(scored_contracts, key=lambda c: c.get("impact_score", 0), reverse=True)
    return sorted_contracts[:top_n]


def calculate_average_impact_score(contracts: list[dict]) -> float:
    """Calculate the average impact score of a list of contracts.
    
    Args:
        contracts: List of contracts with impact_score
    
    Returns:
        Average impact score (0-100)
    """
    if not contracts:
        return 0.0
    total = sum(c.get("impact_score", 0) for c in contracts)
    return round(total / len(contracts), 2)


def score_contracts(contracts: list[dict]) -> dict[str, Any]:
    """Main entry point: Score contracts for S&P 500 impact.
    
    1. Filter out obviously irrelevant contracts (sports, entertainment, etc.)
    2. LLM scores remaining contracts for impact (0-100) and direction
    3. Sort by impact score and get top 5
    4. Calculate average of top 5
    
    Args:
        contracts: List of contract dicts to score
    
    Returns:
        Dict containing:
        - all_scored_contracts: All contracts with impact_score and direction
        - top_contracts: Top 5 contracts by impact score
        - avg_impact_score: Average impact score of top 5
    """
    relevant_contracts = filter_irrelevant_contracts(contracts)
    
    if not relevant_contracts:
        print("  No relevant contracts after filtering")
        return {
            "all_scored_contracts": [],
            "top_contracts": [],
            "avg_impact_score": 0.0,
        }
    
    print(f"  Using LLM to score {len(relevant_contracts)} relevant contracts...")
    try:
        scored_contracts = score_contracts_with_llm(relevant_contracts, batch_size=10)
        top_contracts = get_top_impact_contracts(scored_contracts, top_n=5)
        avg_impact_score = calculate_average_impact_score(top_contracts)
        
        print(f"\n  Top 5 impact contracts:")
        for i, contract in enumerate(top_contracts, 1):
            print(f"    {i}. [{contract.get('impact_score')}] {contract.get('direction')} - {contract.get('question', '')[:60]}...")
        print(f"\n  Average impact score (top 5): {avg_impact_score}")
        
        return {
            "all_scored_contracts": scored_contracts,
            "top_contracts": top_contracts,
            "avg_impact_score": avg_impact_score,
        }
    except Exception as e:
        print(f"  Warning: LLM scoring failed ({e})")
        return {
            "all_scored_contracts": [],
            "top_contracts": [],
            "avg_impact_score": 0.0,
        }
