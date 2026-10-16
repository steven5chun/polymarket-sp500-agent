import json
from typing import Any

from src.agents.data_harvester import fetch_and_cache_contracts
from src.agents.sector_classifier import score_contracts


def run_discovery() -> dict[str, Any]:
    """Fetch all Polymarket contracts and score them for S&P 500 impact.
    
    Returns:
        Dict containing:
        - all_scored_contracts: All contracts with impact_score and direction
        - top_contracts: Top 5 contracts by impact score
        - avg_impact_score: Average impact score of top 5
        - total_contracts: Total number of scored contracts
    """
    print("Fetching all contracts and scoring for S&P 500 impact...")
    
    all_contracts = fetch_and_cache_contracts(min_volume=50000)
    print(f"Fetched {len(all_contracts)} contracts")
    
    print("Scoring contracts for S&P 500 impact...")
    scoring_result = score_contracts(all_contracts)
    
    return {
        "all_scored_contracts": scoring_result.get("all_scored_contracts", []),
        "top_contracts": scoring_result.get("top_contracts", []),
        "avg_impact_score": scoring_result.get("avg_impact_score", 0.0),
        "total_contracts": len(scoring_result.get("all_scored_contracts", [])),
    }
