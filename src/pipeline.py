import json
import sys
import os
import argparse
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from src.agents.discovery_agent import run_discovery
from src.prediction_log import log_prediction, get_prediction_count
from src.market_data import get_realtime_sp500_data, format_market_snapshot


BANNER = """
============================================================
  Polymarket S&P 500 Impact Score Agent
  Track prediction market impact vs S&P 500 price
============================================================
"""


def run_pipeline(log: bool = True) -> dict:
    print(f"\n[1/3] Fetching and scoring Polymarket contracts for S&P 500 impact...")
    discovery_data = run_discovery()
    contract_count = discovery_data.get("total_contracts", 0)
    avg_impact = discovery_data.get("avg_impact_score", 0.0)
    top_contracts = discovery_data.get("top_contracts", [])
    print(f"       Scored {contract_count} contracts. Average impact (top 5): {avg_impact}")

    print(f"\n[2/3] Getting current S&P 500 price...")
    market_context = get_realtime_sp500_data()
    print(f"       {format_market_snapshot(market_context)}")

    if log and contract_count > 0:
        print(f"\n[3/3] Logging prediction...")
        log_prediction(
            avg_impact_score=avg_impact,
            top_contracts=top_contracts,
            market_context=market_context,
            contracts_data=discovery_data.get("all_scored_contracts", []),
        )
        total_logged = get_prediction_count()
        print(f"       Prediction logged (total: {total_logged})")

    return {
        "avg_impact_score": avg_impact,
        "top_contracts": top_contracts,
        "market_snapshot": market_context,
        "total_contracts": contract_count,
    }


def format_top_contracts(top_contracts: list) -> str:
    if not top_contracts:
        return "No top contracts available."
    
    lines = []
    for i, contract in enumerate(top_contracts, 1):
        impact = contract.get("impact_score", 0)
        direction = contract.get("direction", "Neutral")
        question = contract.get("question", "")[:70]
        lines.append(f"  {i}. [{impact:3d}] {direction:<10} | {question}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Polymarket S&P 500 Impact Score Agent"
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Don't log this prediction"
    )
    
    args = parser.parse_args()
    
    print(BANNER)
    print("\nFetching all Polymarket contracts and scoring for S&P 500 impact...")
    print("-" * 60)

    try:
        result = run_pipeline(log=not args.no_log)
        
        print("\n" + "=" * 60)
        print("  IMPACT SCORE REPORT")
        print("=" * 60)
        
        market_snapshot = result.get("market_snapshot", {})
        if market_snapshot:
            print("\nS&P 500 Market Data:")
            print(f"  {format_market_snapshot(market_snapshot)}")
        
        print(f"\nAverage Impact Score (Top 5): {result.get('avg_impact_score', 0)}")
        
        print("\n" + "-" * 60)
        print("  TOP 5 HIGHEST IMPACT CONTRACTS")
        print("-" * 60)
        print(format_top_contracts(result.get("top_contracts", [])))
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\nPipeline error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
