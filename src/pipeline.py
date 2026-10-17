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
  Polymarket S&P 500 Indicator
  Leading indicator using prediction markets to forecast S&P 500
============================================================
"""


def run_pipeline(log: bool = True) -> dict:
    print(f"\n[1/3] Fetching and scoring Polymarket contracts for S&P 500 impact...")
    discovery_data = run_discovery()
    contract_count = discovery_data.get("total_contracts", 0)
    market_prediction = discovery_data.get("market_prediction", {})
    print(f"       Scored {contract_count} contracts.")

    print(f"\n[2/3] Getting current S&P 500 price...")
    market_context = get_realtime_sp500_data()
    print(f"       {format_market_snapshot(market_context)}")

    if log and contract_count > 0:
        print(f"\n[3/3] Logging prediction...")
        log_prediction(
            market_context=market_context,
            contracts_data=discovery_data.get("all_scored_contracts", []),
            market_prediction=market_prediction,
        )
        total_logged = get_prediction_count()
        print(f"       Prediction logged (total: {total_logged})")

    return {
        "market_snapshot": market_context,
        "total_contracts": contract_count,
        "market_prediction": market_prediction,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Polymarket S&P 500 Indicator"
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
        print("  MARKET DIRECTION REPORT")
        print("=" * 60)
        
        market_prediction = result.get("market_prediction", {})
        if market_prediction:
            print("\nMarket Direction Prediction:")
            print(f"  Predicted Direction: {market_prediction.get('predicted_direction', 'N/A')}")
            print(f"  Confidence: {market_prediction.get('confidence_pct', 0)}%")
            print(f"  Bullish Impact: {market_prediction.get('bullish_impact_sum', 0)} | Bearish Impact: {market_prediction.get('bearish_impact_sum', 0)} | Neutral Impact: {market_prediction.get('neutral_impact_sum', 0)}")
            print(f"  Contracts Analyzed: {market_prediction.get('total_contracts_scored', 0)}")
        
        market_snapshot = result.get("market_snapshot", {})
        if market_snapshot:
            print("\nS&P 500 Market Data:")
            print(f"  {format_market_snapshot(market_snapshot)}")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\nPipeline error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
