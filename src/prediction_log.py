"""
Prediction logging module.

Saves each prediction run to two CSV files:
- data/predictions.csv: Average impact score, top 5 contracts, and S&P 500 data
- data/detail.csv: Individual Polymarket contracts with impact scores
"""

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def get_data_dir() -> Path:
    """Get the data directory path."""
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


def get_predictions_csv() -> Path:
    """Get the path to the predictions CSV file."""
    return get_data_dir() / "predictions.csv"


def get_detail_csv() -> Path:
    """Get the path to the detail CSV file."""
    return get_data_dir() / "detail.csv"


def generate_prediction_id(timestamp: str) -> str:
    """
    Generate a unique prediction ID.
    
    Format: pred_YYYYMMDD_XXX
    """
    date_str = timestamp[:10].replace("-", "")
    ts_hash = abs(hash(timestamp)) % 1000
    return f"pred_{date_str}_{ts_hash:03d}"


def get_predictions_headers() -> list:
    """Get the standard predictions CSV headers."""
    headers = [
        "prediction_id",
        "timestamp",
        "avg_impact_score",
    ]
    for i in range(1, 6):
        headers.extend([
            f"top{i}_question",
            f"top{i}_impact_score",
            f"top{i}_direction",
        ])
    headers.extend([
        "sp500_price",
        "sp500_daily_change_pct",
        "sp500_weekly_change_pct",
    ])
    return headers


def get_detail_headers() -> list:
    """Get the detail CSV headers."""
    return [
        "prediction_id",
        "timestamp",
        "contract_id",
        "contract_question",
        "contract_volume",
        "contract_yes_price",
        "impact_score",
        "direction",
    ]


def init_csv_files():
    """Initialize CSV files with headers if they don't exist."""
    predictions_csv = get_predictions_csv()
    detail_csv = get_detail_csv()
    
    if not predictions_csv.exists():
        with open(predictions_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(get_predictions_headers())
    
    if not detail_csv.exists():
        with open(detail_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(get_detail_headers())


def log_prediction(
    avg_impact_score: float,
    top_contracts: list,
    market_context: dict,
    timestamp: str = None,
    contracts_data: list = None,
) -> dict:
    """
    Log a prediction to CSV files.
    
    Args:
        avg_impact_score: Average impact score of top 5 contracts (0-100)
        top_contracts: List of top 5 contracts with impact_score and direction
        market_context: Market snapshot data from get_realtime_sp500_data()
        timestamp: Optional custom timestamp (ISO format). If None, uses current time.
        contracts_data: List of contract dicts with impact_score and direction
    
    Returns:
        The logged prediction dict
    """
    init_csv_files()
    
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    prediction_id = generate_prediction_id(ts)
    
    prediction_row = {
        "prediction_id": prediction_id,
        "timestamp": ts,
        "avg_impact_score": avg_impact_score,
    }
    
    for i in range(1, 6):
        if i <= len(top_contracts):
            contract = top_contracts[i - 1]
            prediction_row[f"top{i}_question"] = contract.get("question", "")
            prediction_row[f"top{i}_impact_score"] = contract.get("impact_score", 0)
            prediction_row[f"top{i}_direction"] = contract.get("direction", "Neutral")
        else:
            prediction_row[f"top{i}_question"] = ""
            prediction_row[f"top{i}_impact_score"] = ""
            prediction_row[f"top{i}_direction"] = ""
    
    prediction_row["sp500_price"] = market_context.get("sp500_price", 0)
    prediction_row["sp500_daily_change_pct"] = market_context.get("sp500_daily_change_pct", 0)
    prediction_row["sp500_weekly_change_pct"] = market_context.get("sp500_weekly_change_pct", 0)
    
    predictions_csv = get_predictions_csv()
    with open(predictions_csv, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=get_predictions_headers())
        writer.writerow(prediction_row)
    
    if contracts_data:
        detail_csv = get_detail_csv()
        with open(detail_csv, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=get_detail_headers())
            for contract in contracts_data:
                detail_row = {
                    "prediction_id": prediction_id,
                    "timestamp": ts,
                    "contract_id": contract.get("id", ""),
                    "contract_question": contract.get("question", ""),
                    "contract_volume": contract.get("volume", 0),
                    "contract_yes_price": contract.get("yes_price", 0),
                    "impact_score": contract.get("impact_score", 0),
                    "direction": contract.get("direction", "Neutral"),
                }
                writer.writerow(detail_row)
    
    return prediction_row


def load_predictions(days: int = None) -> list[dict]:
    """
    Load predictions from the predictions CSV file.
    
    Args:
        days: If specified, only load predictions from the last N days
    
    Returns:
        List of prediction dicts
    """
    predictions_csv = get_predictions_csv()
    
    if not predictions_csv.exists():
        return []
    
    predictions = []
    with open(predictions_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if days is not None:
                cutoff = datetime.now(timezone.utc).timestamp() - (days * 24 * 60 * 60)
                pred_ts = datetime.fromisoformat(row["timestamp"]).timestamp()
                if pred_ts < cutoff:
                    continue
            
            predictions.append(row)
    
    return predictions


def load_detail(prediction_id: str = None) -> list[dict]:
    """
    Load contract details from the detail CSV file.
    
    Args:
        prediction_id: If specified, only load details for this prediction
    
    Returns:
        List of detail dicts
    """
    detail_csv = get_detail_csv()
    
    if not detail_csv.exists():
        return []
    
    details = []
    with open(detail_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if prediction_id is not None and row.get("prediction_id") != prediction_id:
                continue
            details.append(row)
    
    return details


def get_prediction_count() -> int:
    """
    Get the number of logged predictions.
    
    Returns:
        int: Number of predictions
    """
    predictions_csv = get_predictions_csv()
    if not predictions_csv.exists():
        return 0
    with open(predictions_csv, "r") as f:
        return sum(1 for _ in f) - 1


def get_prediction_by_id(prediction_id: str) -> Optional[dict]:
    """Get a specific prediction by ID."""
    predictions = load_predictions()
    for pred in predictions:
        if pred.get("prediction_id") == prediction_id:
            return pred
    return None
