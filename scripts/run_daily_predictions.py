#!/usr/bin/env python3
"""
Daily prediction runner for forward testing.

Fetches all Polymarket contracts, classifies them via AI, and logs predictions.
Can be run manually or scheduled via cron/launchd.

Usage:
    python -m scripts.run_daily_predictions
    python -m scripts.run_daily_predictions --quiet
"""

import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline import run_pipeline
from src.prediction_log import get_prediction_count
from src.market_data import get_realtime_sp500_data, format_market_snapshot


def run_daily_prediction(verbose: bool = True) -> dict:
    """
    Run a single daily prediction by fetching all contracts and classifying them.
    
    Args:
        verbose: Whether to print detailed output
    
    Returns:
        dict with summary of prediction
    """
    start_time = datetime.now(timezone.utc)
    initial_count = get_prediction_count()
    
    if verbose:
        print("=" * 70)
        print("DAILY PREDICTION RUNNER")
        print("=" * 70)
        print(f"\nStart Time: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print()
        
        # Show current market context
        market_data = get_realtime_sp500_data()
        print("Market Context:")
        print(f"  {format_market_snapshot(market_data)}")
        print()
        print("-" * 70)
    
    result = None
    error = None
    
    try:
        if verbose:
            print("\nFetching all Polymarket contracts and classifying via AI...")
            print("-" * 70)
        
        result = run_pipeline(log=True)
        
        if verbose:
            print(f"\n✓ Prediction logged successfully")
            print(f"  Direction: {result.get('sp500_direction_7d')}")
            print(f"  Confidence: {result.get('confidence_level')}")
            print(f"  Sentiment: {result.get('sentiment_score')}")
    
    except Exception as e:
        error = str(e)
        if verbose:
            print(f"\n✗ Error: {e}")
    
    # Summary
    final_count = get_prediction_count()
    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()
    
    summary = {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": round(duration, 2),
        "successful": result is not None,
        "predictions_before": initial_count,
        "predictions_after": final_count,
        "predictions_logged": final_count - initial_count,
    }
    
    if result:
        summary["direction"] = result.get("sp500_direction_7d")
        summary["confidence"] = result.get("confidence_level")
        summary["sentiment_score"] = result.get("sentiment_score")
    
    if error:
        summary["error"] = error
    
    if verbose:
        print()
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Duration: {duration:.1f} seconds")
        print(f"Successful: {result is not None}")
        print(f"Predictions logged: {final_count - initial_count}")
        print(f"Total predictions in log: {final_count}")
        
        if error:
            print(f"\nError: {error}")
    
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Run daily prediction by fetching all Polymarket contracts"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed output"
    )
    
    args = parser.parse_args()
    
    # Run prediction
    summary = run_daily_prediction(verbose=not args.quiet)
    
    # Exit with error code if prediction failed
    if not summary["successful"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
