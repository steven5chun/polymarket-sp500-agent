"""
Prediction logging module.

Saves each prediction run to three CSV files:
- data/detail.csv: Individual Polymarket contracts with classification and scores
- data/sectors.csv: Sector-level aggregations with total scores
- data/predictions.csv: Overall predictions with sector scores and S&P 500 data
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


def get_sectors_csv() -> Path:
    """Get the path to the sectors CSV file."""
    return get_data_dir() / "sectors.csv"


def get_detail_csv() -> Path:
    """Get the path to the detail CSV file."""
    return get_data_dir() / "detail.csv"


def generate_prediction_id(timestamp: str) -> str:
    """
    Generate a unique prediction ID.
    
    Format: pred_YYYYMMDD_XXX
    """
    date_str = timestamp[:10].replace("-", "")
    # Use timestamp hash for uniqueness
    ts_hash = abs(hash(timestamp)) % 1000
    return f"pred_{date_str}_{ts_hash:03d}"


def get_predictions_headers() -> list:
    """Get the standard predictions CSV headers."""
    return [
        "prediction_id",
        "timestamp",
        "direction",
        "confidence",
        "sentiment_score",
        "stress_coefficient",
        "market_regime",
        "driving_sectors",
        "sp500_price",
        "sp500_daily_change_pct",
        "sp500_weekly_change_pct",
        "sp500_distance_from_50d_ma_pct",
        # Sector total scores
        "economic_growth_score",
        "monetary_policy_score",
        "financial_system_score",
        "geopolitical_conflict_score",
        "us_political_stability_score",
        "energy_commodities_score",
        "trade_regulatory_score",
        "public_health_score",
        "technology_cyber_score",
        "stock_prediction_score",
    ]


def get_sectors_headers() -> list:
    """Get the sectors CSV headers."""
    return [
        "prediction_id",
        "timestamp",
        "sector_id",
        "sector_name",
        "sentiment_score",
        "stress_coefficient",
        "signal",
        "contract_count",
        "total_volume",
        "spx_weight",
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
        "contract_sentiment_score",
        "contract_signal",
        "sector_id",
        "sector_sentiment_score",
        "sector_signal",
    ]


def init_csv_files():
    """Initialize CSV files with headers if they don't exist."""
    predictions_csv = get_predictions_csv()
    sectors_csv = get_sectors_csv()
    detail_csv = get_detail_csv()
    
    if not predictions_csv.exists():
        with open(predictions_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(get_predictions_headers())
    
    if not sectors_csv.exists():
        with open(sectors_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(get_sectors_headers())
    
    if not detail_csv.exists():
        with open(detail_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(get_detail_headers())


def log_prediction(
    direction: str,
    confidence: str,
    sentiment_score: float,
    stress_coefficient: float,
    sector_breakdown: dict,
    market_context: dict,
    market_regime: str = None,
    driving_sectors: list = None,
    rationale: str = None,
    timestamp: str = None,
    contracts_data: list = None,
) -> dict:
    """
    Log a prediction to three CSV files.
    
    Args:
        direction: Predicted direction (Bullish/Bearish/Neutral)
        confidence: Confidence level (High/Medium/Low)
        sentiment_score: Aggregate sentiment score (0-1)
        stress_coefficient: Aggregate stress coefficient (0-1)
        sector_breakdown: Dict of sector sentiments
        market_context: Market snapshot data from get_realtime_sp500_data()
        market_regime: Description of market regime
        driving_sectors: List of driving sector IDs
        rationale: Prediction rationale
        timestamp: Optional custom timestamp (ISO format). If None, uses current time.
        contracts_data: List of contract dicts with classification info
    
    Returns:
        The logged prediction dict
    """
    init_csv_files()
    
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    prediction_id = generate_prediction_id(ts)
    
    # Build prediction row
    prediction_row = {
        "prediction_id": prediction_id,
        "timestamp": ts,
        "direction": direction,
        "confidence": confidence,
        "sentiment_score": sentiment_score,
        "stress_coefficient": stress_coefficient,
        "market_regime": market_regime or "",
        "driving_sectors": ",".join(driving_sectors or []),
        "sp500_price": market_context.get("sp500_price", 0),
        "sp500_daily_change_pct": market_context.get("sp500_daily_change_pct", 0),
        "sp500_weekly_change_pct": market_context.get("sp500_weekly_change_pct", 0),
        "sp500_distance_from_50d_ma_pct": market_context.get("sp500_distance_from_50d_ma_pct", 0),
    }
    
    # Add sector total scores
    sector_ids = [
        "economic_growth",
        "monetary_policy",
        "financial_system",
        "geopolitical_conflict",
        "us_political_stability",
        "energy_commodities",
        "trade_regulatory",
        "public_health",
        "technology_cyber",
        "stock_prediction",
    ]
    
    for sector_id in sector_ids:
        sector_data = sector_breakdown.get(sector_id, {})
        prediction_row[f"{sector_id}_score"] = sector_data.get("sentiment_score", "")
    
    # Write to predictions.csv
    predictions_csv = get_predictions_csv()
    with open(predictions_csv, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=get_predictions_headers())
        writer.writerow(prediction_row)
    
    # Write sector aggregations to sectors.csv
    sectors_csv = get_sectors_csv()
    with open(sectors_csv, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=get_sectors_headers())
        for sector_id in sector_ids:
            sector_data = sector_breakdown.get(sector_id, {})
            if sector_data:  # Only write if sector has data
                sector_row = {
                    "prediction_id": prediction_id,
                    "timestamp": ts,
                    "sector_id": sector_id,
                    "sector_name": sector_data.get("sector_name", sector_id),
                    "sentiment_score": sector_data.get("sentiment_score", ""),
                    "stress_coefficient": sector_data.get("stress_coefficient", ""),
                    "signal": sector_data.get("signal", ""),
                    "contract_count": sector_data.get("contract_count", 0),
                    "total_volume": sector_data.get("total_volume", 0),
                    "spx_weight": sector_data.get("spx_weight", ""),
                }
                writer.writerow(sector_row)
    
    # Write contract details to detail.csv
    if contracts_data:
        detail_csv = get_detail_csv()
        with open(detail_csv, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=get_detail_headers())
            for contract in contracts_data:
                sector_id = contract.get("sector", "unknown")
                sector_data = sector_breakdown.get(sector_id, {})
                
                detail_row = {
                    "prediction_id": prediction_id,
                    "timestamp": ts,
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
            # Filter by days
            if days is not None:
                cutoff = datetime.now(timezone.utc).timestamp() - (days * 24 * 60 * 60)
                pred_ts = datetime.fromisoformat(row["timestamp"]).timestamp()
                if pred_ts < cutoff:
                    continue
            
            predictions.append(row)
    
    return predictions


def load_sectors(prediction_id: str = None) -> list[dict]:
    """
    Load sector data from the sectors CSV file.
    
    Args:
        prediction_id: If specified, only load sectors for this prediction
    
    Returns:
        List of sector dicts
    """
    sectors_csv = get_sectors_csv()
    
    if not sectors_csv.exists():
        return []
    
    sectors = []
    with open(sectors_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if prediction_id is not None and row.get("prediction_id") != prediction_id:
                continue
            sectors.append(row)
    
    return sectors


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
        return sum(1 for _ in f) - 1  # Subtract header row


def get_prediction_by_id(prediction_id: str) -> Optional[dict]:
    """Get a specific prediction by ID."""
    predictions = load_predictions()
    for pred in predictions:
        if pred.get("prediction_id") == prediction_id:
            return pred
    return None
