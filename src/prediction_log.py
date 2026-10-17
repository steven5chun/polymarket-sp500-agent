"""
Prediction logging module.

Saves each prediction run to two CSV files:
- data/predictions.csv: Market direction prediction and S&P 500 data
- data/detail.csv: Individual Polymarket contracts with impact scores
"""

import csv
from datetime import datetime, timezone
from pathlib import Path


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
    return [
        "prediction_id",
        "timestamp",
        "predicted_direction",
        "confidence_pct",
        "bullish_impact_sum",
        "bearish_impact_sum",
        "neutral_impact_sum",
        "total_contracts_scored",
        "sp500_price",
        "sp500_daily_change_pct",
        "sp500_weekly_change_pct",
    ]


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
        "reason",
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
    market_context: dict,
    timestamp: str = None,
    contracts_data: list = None,
    market_prediction: dict = None,
) -> dict:
    """
    Log a prediction to CSV files.
    
    Args:
        market_context: Market snapshot data from get_realtime_sp500_data()
        timestamp: Optional custom timestamp (ISO format). If None, uses current time.
        contracts_data: List of contract dicts with impact_score and direction
        market_prediction: Dict with predicted_direction, confidence_pct, and breakdown sums
    
    Returns:
        The logged prediction dict
    """
    init_csv_files()
    
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    prediction_id = generate_prediction_id(ts)
    
    prediction_row = {
        "prediction_id": prediction_id,
        "timestamp": ts,
    }
    
    if market_prediction:
        prediction_row["predicted_direction"] = market_prediction.get("predicted_direction", "Neutral")
        prediction_row["confidence_pct"] = market_prediction.get("confidence_pct", 0.0)
        prediction_row["bullish_impact_sum"] = market_prediction.get("bullish_impact_sum", 0)
        prediction_row["bearish_impact_sum"] = market_prediction.get("bearish_impact_sum", 0)
        prediction_row["neutral_impact_sum"] = market_prediction.get("neutral_impact_sum", 0)
        prediction_row["total_contracts_scored"] = market_prediction.get("total_contracts_scored", 0)
    else:
        prediction_row["predicted_direction"] = ""
        prediction_row["confidence_pct"] = ""
        prediction_row["bullish_impact_sum"] = ""
        prediction_row["bearish_impact_sum"] = ""
        prediction_row["neutral_impact_sum"] = ""
        prediction_row["total_contracts_scored"] = ""
    
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
                    "reason": contract.get("reason", ""),
                }
                writer.writerow(detail_row)
    
    return prediction_row


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
