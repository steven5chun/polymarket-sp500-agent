"""
Regenerate detail.csv using the new pure LLM logic.
"""

import csv
from datetime import datetime, timezone
from pathlib import Path

from src.agents.sector_classifier import classify_contracts_hybrid
from src.agents.quant_scorer import compute_all_sector_sentiments
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
    
    print(f"\nClassifying {len(contracts)} contracts with pure LLM...")
    grouped_contracts = classify_contracts_hybrid(contracts)
    
    print(f"\nComputing sector sentiments...")
    sector_sentiments = compute_all_sector_sentiments(grouped_contracts)
    
    timestamp = datetime.now(timezone.utc).isoformat()
    prediction_id = generate_prediction_id(timestamp)
    
    detail_csv = get_detail_csv()
    print(f"\nWriting to {detail_csv}...")
    
    with open(detail_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=get_detail_headers())
        writer.writeheader()
        
        for sector_id, sector_contracts in grouped_contracts.items():
            if sector_id == "unknown" or not sector_contracts:
                continue
            
            sector_data = sector_sentiments.get(sector_id, {})
            
            for contract in sector_contracts:
                detail_row = {
                    "prediction_id": prediction_id,
                    "timestamp": timestamp,
                    "contract_id": contract.get("id", ""),
                    "contract_question": contract.get("question", ""),
                    "contract_volume": contract.get("volume", 0),
                    "contract_yes_price": contract.get("yes_price", 0),
                    "contract_sentiment_score": contract.get("sentiment_score", 0.5),
                    "contract_signal": contract.get("signal", "Neutral"),
                    "sector_id": sector_id,
                    "sector_sentiment_score": sector_data.get("sentiment_score", ""),
                    "sector_signal": sector_data.get("signal", ""),
                }
                writer.writerow(detail_row)
    
    total_written = sum(len(c) for c in grouped_contracts.values())
    print(f"\nDone! Wrote {total_written} contracts to {detail_csv}")
    print(f"Prediction ID: {prediction_id}")


if __name__ == "__main__":
    main()
