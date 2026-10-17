import json
from typing import Any

from src.agents.data_filter import fetch_and_cache_contracts
from src.agents.data_transformation import score_contracts


def run_discovery() -> dict[str, Any]:
    """Fetch all Polymarket contracts and score them for S&P 500 impact.
    
    Returns:
        Dict containing:
        - all_scored_contracts: All contracts with impact_score and direction
        - total_contracts: Total number of scored contracts
        - market_prediction: Predicted market direction with confidence
    """
    print("Fetching all contracts and scoring for S&P 500 impact...")
    
    all_contracts = fetch_and_cache_contracts(min_volume=50000)
    print(f"Fetched {len(all_contracts)} contracts")
    
    print("Scoring contracts for S&P 500 impact...")
    scoring_result = score_contracts(all_contracts)
    
    return {
        "all_scored_contracts": scoring_result.get("all_scored_contracts", []),
        "total_contracts": len(scoring_result.get("all_scored_contracts", [])),
        "market_prediction": scoring_result.get("market_prediction", {}),
    }
