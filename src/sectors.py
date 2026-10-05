"""
Sector definitions for S&P 500 prediction.

Each sector has an ID, name, and S&P 500 weight reflecting its historical
correlation with S&P 500 directional movement.
"""

from dataclasses import dataclass


@dataclass
class Sector:
    id: str
    name: str
    spx_weight: float


SECTORS = {
    "economic_growth": Sector(
        id="economic_growth",
        name="Economic Growth",
        spx_weight=1.0,
    ),
    "monetary_policy": Sector(
        id="monetary_policy",
        name="Monetary Policy",
        spx_weight=0.95,
    ),
    "financial_system": Sector(
        id="financial_system",
        name="Financial System",
        spx_weight=0.95,
    ),
    "geopolitical_conflict": Sector(
        id="geopolitical_conflict",
        name="Geopolitical Conflict",
        spx_weight=0.9,
    ),
    "us_political_stability": Sector(
        id="us_political_stability",
        name="US Political Stability",
        spx_weight=0.85,
    ),
    "energy_commodities": Sector(
        id="energy_commodities",
        name="Energy & Commodities",
        spx_weight=0.8,
    ),
    "trade_regulatory": Sector(
        id="trade_regulatory",
        name="Trade & Regulatory",
        spx_weight=0.8,
    ),
    "public_health": Sector(
        id="public_health",
        name="Public Health",
        spx_weight=0.75,
    ),
    "technology_cyber": Sector(
        id="technology_cyber",
        name="Technology & Cyber",
        spx_weight=0.7,
    ),
    "stock_prediction": Sector(
        id="stock_prediction",
        name="Stock Prediction",
        spx_weight=0.65,
    ),
}


def get_sector(sector_id: str) -> Sector | None:
    return SECTORS.get(sector_id)


def get_all_sectors() -> dict[str, Sector]:
    return SECTORS


def get_sector_names() -> list[str]:
    return [sector.name for sector in SECTORS.values()]


def get_sector_ids() -> list[str]:
    return list(SECTORS.keys())
