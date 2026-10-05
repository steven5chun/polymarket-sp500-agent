import json
import sys
import os
import argparse
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from src.agents.discovery_agent import run_discovery
from src.agents.quant_scorer import run_quant_scoring
from src.agents.spx_predictor import run_prediction
from src.prediction_log import log_prediction, get_prediction_count
from src.market_data import get_realtime_sp500_data, format_market_snapshot


BANNER = """
============================================================
  Polymarket Macro Sentiment S&P 500 Predictor AI Agent
  Sector-Based Analysis (All Contracts)
============================================================
"""


def run_pipeline(log: bool = True) -> dict:
    # Capture market snapshot before running prediction
    print("\n[0/4] Capturing market snapshot...")
    market_context = get_realtime_sp500_data()
    print(f"       {format_market_snapshot(market_context)}")

    print(f"\n[1/4] Discovery Agent: Fetching and classifying all Polymarket contracts...")
    discovery_data = run_discovery()
    contract_count = len(discovery_data.get("all_contracts", []))
    sector_count = len(discovery_data.get("sector_summary", {}))
    print(f"       Found {contract_count} contracts across {sector_count} sectors.")

    print(f"\n[2/4] Quant Agent: Scoring sector sentiment vectors...")
    grouped_contracts = discovery_data.get("grouped_contracts", {})
    quant_data = run_quant_scoring(discovery_data, grouped_contracts)
    sentiment_score = quant_data.get("aggregate", {}).get("sentiment_score", "N/A")
    stress = quant_data.get("aggregate", {}).get("stress_coefficient", "N/A")
    print(f"       Aggregate Sentiment: {sentiment_score} | Stress: {stress}")

    print(f"\n[3/4] Predictor Agent: Generating S&P 500 forecast...")
    prediction = run_prediction(discovery_data, quant_data)
    direction = prediction.get("sp500_direction_7d", "Unknown")
    confidence = prediction.get("confidence_level", "Unknown")
    print(f"       Direction: {direction} | Confidence: {confidence}")

    if log and direction != "Unknown":
        # Flatten grouped contracts into a list with sector assignments
        contracts_data = []
        for sector_id, sector_contracts in grouped_contracts.items():
            for contract in sector_contracts:
                contract_with_sector = contract.copy()
                contract_with_sector["sector"] = sector_id
                contracts_data.append(contract_with_sector)
        
        log_prediction(
            direction=direction,
            confidence=confidence,
            sentiment_score=float(sentiment_score) if sentiment_score != "N/A" else 0.5,
            stress_coefficient=float(stress) if stress != "N/A" else 0.0,
            sector_breakdown=prediction.get("sector_breakdown", {}),
            market_context=market_context,
            market_regime=prediction.get("market_regime"),
            driving_sectors=prediction.get("driving_sectors", []),
            rationale=prediction.get("rationale"),
            contracts_data=contracts_data,
        )
        total_logged = get_prediction_count()
        print(f"\n       Prediction logged (total: {total_logged})")

    # Include market context in result
    prediction["market_snapshot"] = market_context
    return prediction


def format_sector_breakdown(sector_breakdown: dict) -> str:
    if not sector_breakdown:
        return "No sector data available."
    
    lines = []
    for sector_id, data in sorted(
        sector_breakdown.items(),
        key=lambda x: x[1].get("spx_weight", 0),
        reverse=True
    ):
        name = data.get("name", sector_id)
        sentiment = data.get("sentiment_score", 0.5)
        signal = data.get("signal", "Neutral")
        count = data.get("contract_count", 0)
        weight = data.get("spx_weight", 0.5)
        
        sentiment_bar = "█" * int(sentiment * 10) + "░" * (10 - int(sentiment * 10))
        
        lines.append(
            f"  {name:<25} | {sentiment_bar} {sentiment:.2f} | {signal:<10} | "
            f"Contracts: {count} | Weight: {weight:.2f}"
        )
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Polymarket S&P 500 Prediction Pipeline - Fetches all contracts and classifies via AI"
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Don't log this prediction"
    )
    
    args = parser.parse_args()
    
    print(BANNER)
    print("\nFetching all Polymarket contracts and classifying via AI agent...")
    print("-" * 60)

    try:
        result = run_pipeline(log=not args.no_log)
        
        print("\n" + "=" * 60)
        print("  FINAL PREDICTION REPORT")
        print("=" * 60)
        
        # Display market context
        market_snapshot = result.get("market_snapshot", {})
        if market_snapshot:
            print("\nMarket Context at Prediction:")
            print(f"  {format_market_snapshot(market_snapshot)}")
        
        print(f"\nMarket Regime: {result.get('market_regime', 'Unknown')}")
        print(f"S&P 500 Direction (7d): {result.get('sp500_direction_7d', 'Unknown')}")
        print(f"Confidence Level: {result.get('confidence_level', 'Unknown')}")
        print(f"Aggregate Sentiment: {result.get('sentiment_score', 'N/A')}")
        
        print("\n" + "-" * 60)
        print("  SECTOR BREAKDOWN")
        print("-" * 60)
        sector_breakdown = result.get("sector_breakdown", {})
        print(format_sector_breakdown(sector_breakdown))
        
        print("\n" + "-" * 60)
        print("  DRIVING SECTORS")
        print("-" * 60)
        driving = result.get("driving_sectors", [])
        if driving:
            for sector in driving:
                print(f"  - {sector}")
        else:
            print("  No dominant sectors identified.")
        
        print("\n" + "-" * 60)
        print("  RATIONALE")
        print("-" * 60)
        print(result.get("rationale", "No rationale available."))
        
        print("\n" + "=" * 60)
        print("  FULL JSON OUTPUT")
        print("=" * 60)
        print(json.dumps(result, indent=2))
        print("=" * 60)
        
    except Exception as e:
        print(f"\nPipeline error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
