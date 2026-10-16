"""
Regenerate detail.csv using the impact scoring logic.
"""

import csv
from datetime import datetime, timezone
from pathlib import Path

from src.agents.sector_classifier import score_contracts
from src.prediction_log import get_detail_csv, get_detail_headers, generate_prediction_id


def load_contracts_from_cache() -> list[dict]:
    cache_csv = Path(__file__).parent.parent / "data" / "polymarket-contracts.csv"
    
    if not cache_csv.exists():
        print("No polymarket-contracts.csv found")
        return []
    
    contracts = []
    with open(cache_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            contract = {
                "id": row.get("id", ""),
                "question": row.get("question", ""),
                "description": row.get("description", ""),
                "volume": float(row.get("volume", 0) or 0),
                "liquidity": float(row.get("liquidity", 0) or 0),
                "yes_price": float(row.get("yes_price", 0.5) or 0.5),
                "start_date": row.get("start_date", ""),
                "end_date": row.get("end_date", ""),
            }
            contracts.append(contract)
    
    print(f"Loaded {len(contracts)} contracts from cache")
    return contracts


def main():
    print("Loading contracts from cache...")
    contracts = load_contracts_from_cache()
    
    if not contracts:
        print("No contracts to process")
        return
    
    print(f"\nScoring {len(contracts)} contracts for S&P 500 impact...")
    scoring_result = score_contracts(contracts)
    scored_contracts = scoring_result.get("all_scored_contracts", [])
    
    timestamp = datetime.now(timezone.utc).isoformat()
    prediction_id = generate_prediction_id(timestamp)
    
    detail_csv = get_detail_csv()
    print(f"\nWriting to {detail_csv}...")
    
    with open(detail_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=get_detail_headers())
        writer.writeheader()
        
        for contract in scored_contracts:
            detail_row = {
                "prediction_id": prediction_id,
                "timestamp": timestamp,
                "contract_id": contract.get("id", ""),
                "contract_question": contract.get("question", ""),
                "contract_volume": contract.get("volume", 0),
                "contract_yes_price": contract.get("yes_price", 0),
                "impact_score": contract.get("impact_score", 0),
                "direction": contract.get("direction", "Neutral"),
            }
            writer.writerow(detail_row)
    
    print(f"\nDone! Wrote {len(scored_contracts)} contracts to {detail_csv}")
    print(f"Prediction ID: {prediction_id}")


if __name__ == "__main__":
    main()
