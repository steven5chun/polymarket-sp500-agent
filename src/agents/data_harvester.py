import os
import json
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

GAMMA_API_URL = os.getenv("GAMMA_API_URL", "https://gamma-api.polymarket.com")
CLOB_API_URL = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")
MIN_LIQUIDITY_USD = int(os.getenv("MIN_LIQUIDITY_USD", "10000"))

SECTOR_KEYWORDS = {
    "economic_growth": [
        "gdp", "recession", "unemployment", "jobs", "employment",
        "economic growth", "inflation", "deflation", "consumer spending",
        "retail sales", "manufacturing", "pmi", "industrial production",
        "housing starts", "construction", "business investment",
        "nonfarm", "payroll", "economic",
    ],
    "monetary_policy": [
        "fed", "federal reserve", "interest rate", "rate cut", "rate hike",
        "monetary policy", "powell", "fomc", "quantitative easing", "qe",
        "quantitative tightening", "qt", "inflation target", "dollar",
        "currency", "central bank", "treasury yield", "bond yield",
    ],
    "geopolitical_conflict": [
        "war", "conflict", "military", "invasion", "attack", "missile",
        "nuclear", "ukraine", "russia", "middle east", "israel", "palestine",
        "iran", "china taiwan", "north korea", "ceasefire", "peace deal",
        "sanctions", "nato",
    ],
    "us_political_stability": [
        "trump", "biden", "election", "president", "congress", "senate",
        "house", "democrat", "republican", "government shutdown",
        "debt ceiling", "impeachment", "supreme court", "legislation",
        "bill", "vote", "poll", "approval rating",
    ],
    "energy_commodities": [
        "oil", "crude", "brent", "wti", "gas", "energy", "opec",
        "commodity", "gold", "silver", "copper", "steel", "agriculture",
        "wheat", "corn", "soybean", "food prices", "petroleum",
    ],
    "stock_prediction": [
        "market cap", "bitcoin", "btc", "ethereum", "eth", "crypto",
        "stock price", "share price", "ipo", "public offering",
        "hit $", "reach $", "above $", "over $",
        "tesla", "apple", "microsoft", "nvidia", "amazon", "google",
        "sp500", "s&p 500", "nasdaq", "dow jones",
    ],
    "financial_system": [
        "bank", "banking", "credit", "debt", "default", "bond", "treasury",
        "yield", "spread", "liquidity", "financial crisis", "bankruptcy",
        "systemic risk", "contagion",
    ],
    "technology_cyber": [
        "cyber", "hack", "data breach", "ransomware", "tech", "ai",
        "artificial intelligence", "semiconductor", "chip", "cyberattack",
        "infrastructure attack", "power grid", "internet outage",
    ],
    "public_health": [
        "pandemic", "virus", "covid", "outbreak", "epidemic", "health",
        "disease", "vaccine", "lockdown", "quarantine", "who", "cdc",
    ],
    "trade_regulatory": [
        "tariff", "trade war", "sanctions", "embargo", "import", "export",
        "customs", "trade deal", "us china", "regulation", "antitrust",
        "monopoly", "sec", "compliance",
    ],
}

BAD_EVENT_KEYWORDS = [
    "recession", "default", "crisis", "invasion", "war", "attack",
    "shutdown", "impeach", "bankruptcy", "pandemic", "hurricane",
    "disaster", "hack", "cyberattack", "outbreak", "unemployment reach",
    "inflation reach", "hit $", "crash", "collapse", "fail", "out",
    "win the", "nomination", "presidential",
]

GOOD_EVENT_KEYWORDS = [
    "growth", "rate cut", "ceasefire", "peace", "bipartisan", "passed",
    "innovation", "containment", "vaccine", "trade deal", "deregulation",
    "beat", "exceed", "greater than", "above", "best performance",
    "reach", "between", "or higher", "or lower", "or greater",
]


def fetch_all_markets(max_markets: int = 10000) -> list[dict]:
    """Fetch all active markets from Polymarket using multi-segment strategy.

    The Polymarket Gamma API has an offset limit of ~2,100 markets. To access
    more markets, we use different order parameters to access different segments:
    1. Low-volume markets (order by volume ascending)
    2. High-volume markets (order by volume descending)
    3. Recent markets (order by createdAt descending)
    
    Results are deduplicated by market ID.
    
    Args:
        max_markets: Maximum number of markets to fetch per segment (default: 10000)
    
    Returns:
        List of unique market dicts
    """
    all_markets = {}  # Use dict to deduplicate by market ID
    page_size = 100
    max_offset = 2100  # API offset limit
    
    # Segment 1: Low-volume markets (order by volume ascending)
    print("    Fetching low-volume markets...")
    params = {"closed": "false", "limit": page_size, "order": "volume", "ascending": True}
    offset = 0
    while offset < min(max_markets, max_offset):
        params["offset"] = offset
        try:
            response = requests.get(f"{GAMMA_API_URL}/markets", params=params, timeout=15)
            response.raise_for_status()
            markets = response.json()
            if not markets or not isinstance(markets, list):
                break
            markets = [m for m in markets if isinstance(m, dict)]
            if not markets:
                break
            for m in markets:
                all_markets[m['id']] = m
            if len(markets) < page_size:
                break
            offset += page_size
        except Exception as e:
            print(f"    Error fetching low-volume markets at offset {offset}: {e}")
            break
    
    print(f"    Low-volume: {len(all_markets)} markets")
    
    # Segment 2: High-volume markets (order by volume descending)
    print("    Fetching high-volume markets...")
    params = {"closed": "false", "limit": page_size, "order": "volume", "ascending": False}
    offset = 0
    segment2_start = len(all_markets)
    while offset < min(max_markets, max_offset):
        params["offset"] = offset
        try:
            response = requests.get(f"{GAMMA_API_URL}/markets", params=params, timeout=15)
            response.raise_for_status()
            markets = response.json()
            if not markets or not isinstance(markets, list):
                break
            markets = [m for m in markets if isinstance(m, dict)]
            if not markets:
                break
            new_count = 0
            for m in markets:
                if m['id'] not in all_markets:
                    all_markets[m['id']] = m
                    new_count += 1
            if len(markets) < page_size:
                break
            offset += page_size
        except Exception as e:
            print(f"    Error fetching high-volume markets at offset {offset}: {e}")
            break
    
    print(f"    High-volume: +{len(all_markets) - segment2_start} new markets")
    
    # Segment 3: Recent markets (order by createdAt descending)
    print("    Fetching recent markets...")
    params = {"closed": "false", "limit": page_size, "order": "createdAt", "ascending": False}
    offset = 0
    segment3_start = len(all_markets)
    while offset < min(max_markets, max_offset):
        params["offset"] = offset
        try:
            response = requests.get(f"{GAMMA_API_URL}/markets", params=params, timeout=15)
            response.raise_for_status()
            markets = response.json()
            if not markets or not isinstance(markets, list):
                break
            markets = [m for m in markets if isinstance(m, dict)]
            if not markets:
                break
            new_count = 0
            for m in markets:
                if m['id'] not in all_markets:
                    all_markets[m['id']] = m
                    new_count += 1
            if len(markets) < page_size:
                break
            offset += page_size
        except Exception as e:
            print(f"    Error fetching recent markets at offset {offset}: {e}")
            break
    
    print(f"    Recent: +{len(all_markets) - segment3_start} new markets")
    
    result = list(all_markets.values())
    print(f"    Total unique markets: {len(result)}")
    
    return result


def score_relevance(market: dict, query: str) -> int:
    """Score how relevant a market is to the user's query.

    Returns the number of keyword matches across the market's question
    and description. A score of 0 means the contract is unrelated.
    """
    text = f"{market.get('question', '')} {market.get('description', '')}".lower()
    query_words = [w for w in query.lower().split() if len(w) >= 3]

    score = 0
    for word in query_words:
        if word in text:
            score += 1

    for sector_id, keywords in SECTOR_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                for qw in query_words:
                    if qw in kw or kw in qw:
                        score += 2

    return score


def filter_by_relevance(markets: list[dict], query: str, min_score: int = 1) -> list[dict]:
    """Filter markets to only include those relevant to the query."""
    scored = []
    for market in markets:
        score = score_relevance(market, query)
        if score >= min_score:
            market["_relevance_score"] = score
            scored.append(market)

    scored.sort(key=lambda m: (-m["_relevance_score"], -float(m.get("volume", 0) or 0)))
    return scored


def search_markets(query: str, limit: int = 20) -> list[dict]:
    """Search Polymarket markets by fetching all and filtering client-side."""
    all_markets = fetch_all_markets()
    relevant = filter_by_relevance(all_markets, query)
    return relevant[:limit]


def search_events(query: str, limit: int = 10) -> list[dict]:
    params = {
        "closed": "false",
        "limit": limit,
        "tag": query,
    }
    response = requests.get(f"{GAMMA_API_URL}/events", params=params, timeout=15)
    if response.status_code == 200:
        return response.json()
    params.pop("tag")
    params["_q"] = query
    response = requests.get(f"{GAMMA_API_URL}/events", params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def get_market(market_id: str) -> dict:
    response = requests.get(f"{GAMMA_API_URL}/markets/{market_id}", timeout=15)
    response.raise_for_status()
    return response.json()


def get_orderbook(token_id: str) -> dict:
    params = {"token_id": token_id}
    response = requests.get(f"{CLOB_API_URL}/book", params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def get_midpoint(token_id: str) -> Optional[float]:
    try:
        params = {"token_id": token_id}
        response = requests.get(f"{CLOB_API_URL}/midpoint", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data.get("mid", 0))
    except Exception:
        return None


def get_price(token_id: str) -> Optional[float]:
    try:
        params = {"token_id": token_id}
        response = requests.get(f"{CLOB_API_URL}/price", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data.get("price", 0))
    except Exception:
        return None


def filter_by_liquidity(markets: list[dict], min_volume: int = MIN_LIQUIDITY_USD) -> list[dict]:
    filtered = []
    for market in markets:
        volume = float(market.get("volume", 0) or 0)
        liquidity = float(market.get("liquidity", 0) or 0)
        if volume >= min_volume or liquidity >= min_volume:
            filtered.append(market)
    return filtered


def filter_by_expiry(markets: list[dict]) -> list[dict]:
    """Filter out expired or not-yet-active contracts.

    Removes contracts where:
    - end_date < now() (already expired/resolved)
    - start_date > now() (not yet active)
    """
    now = datetime.now(timezone.utc)
    filtered = []

    for market in markets:
        end_date_str = market.get("endDate") or market.get("endDateIso")
        start_date_str = market.get("startDate") or market.get("startDateIso")

        if not end_date_str:
            filtered.append(market)
            continue

        try:
            end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))

            if end_date < now:
                continue

            if start_date_str:
                start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
                if start_date > now:
                    continue

            filtered.append(market)
        except (ValueError, AttributeError):
            filtered.append(market)

    return filtered


def extract_market_features(market: dict) -> dict:
    tokens = market.get("clobTokenIds") or market.get("clob_token_ids") or ""
    if isinstance(tokens, str):
        token_list = [t.strip() for t in tokens.split(",") if t.strip()]
    elif isinstance(tokens, list):
        token_list = tokens
    else:
        token_list = []

    outcome_prices = market.get("outcomePrices") or market.get("outcome_prices") or "[]"
    if isinstance(outcome_prices, str):
        try:
            outcome_prices = json.loads(outcome_prices)
        except Exception:
            outcome_prices = []

    outcomes = market.get("outcomes") or "[]"
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except Exception:
            outcomes = []

    yes_price = float(outcome_prices[0]) if len(outcome_prices) > 0 else 0.5
    no_price = float(outcome_prices[1]) if len(outcome_prices) > 1 else 0.5

    midpoint = None
    if token_list:
        midpoint = get_midpoint(token_list[0])

    return {
        "id": market.get("id", ""),
        "question": market.get("question", ""),
        "description": market.get("description", "")[:500],
        "slug": market.get("slug", ""),
        "volume": float(market.get("volume", 0) or 0),
        "liquidity": float(market.get("liquidity", 0) or 0),
        "start_date": market.get("startDate", ""),
        "end_date": market.get("endDate", ""),
        "yes_price": yes_price,
        "no_price": no_price,
        "midpoint": midpoint,
        "outcomes": outcomes,
        "outcome_prices": outcome_prices,
        "token_ids": token_list,
        "active": market.get("active", True),
        "_relevance_score": market.get("_relevance_score", 0),
    }


def harvest_contracts(query: str, limit: int = 20) -> list[dict]:
    markets = search_markets(query, limit=limit * 3)
    filtered = filter_by_relevance(markets, query)
    filtered = filter_by_liquidity(filtered)
    filtered = filter_by_expiry(filtered)

    features = []
    for market in filtered[:limit]:
        try:
            feature = extract_market_features(market)
            features.append(feature)
        except Exception:
            continue

    return features


def fetch_all_active_contracts(min_volume: int = MIN_LIQUIDITY_USD) -> list[dict]:
    """Fetch all active Polymarket contracts, filtered by liquidity and expiry.
    
    This function:
    1. Fetches all active markets from Polymarket (no search query)
    2. Filters by minimum volume/liquidity
    3. Filters out expired contracts
    4. Extracts features for each contract
    
    Returns:
        List of contract dicts ready for AI classification
    """
    print(f"Fetching all active markets from Polymarket...")
    all_markets = fetch_all_markets()
    print(f"  Found {len(all_markets)} total markets")
    
    # Filter by liquidity
    filtered = filter_by_liquidity(all_markets, min_volume)
    print(f"  After liquidity filter (>={min_volume}): {len(filtered)} markets")
    
    # Filter by expiry
    filtered = filter_by_expiry(filtered)
    print(f"  After expiry filter: {len(filtered)} markets")
    
    # Extract features
    features = []
    for market in filtered:
        try:
            feature = extract_market_features(market)
            features.append(feature)
        except Exception:
            continue
    
    print(f"  Extracted features for {len(features)} contracts")
    return features


def get_contracts_cache_path() -> Path:
    """Get the path to the contracts cache file."""
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "polymarket-contracts.csv"


def fetch_and_cache_contracts(min_volume: int = 50000) -> list[dict]:
    """Fetch all contracts with volume > $50K and cache to CSV file.
    
    If today's cache file exists, use it instead of fetching again.
    Otherwise, fetch fresh data and save to cache.
    
    Args:
        min_volume: Minimum volume threshold (default: $50,000)
    
    Returns:
        List of contract dicts
    """
    import csv
    
    cache_path = get_contracts_cache_path()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Check if cache exists and is from today
    if cache_path.exists():
        try:
            with open(cache_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                cache_date = None
                contracts = []
                
                for row in reader:
                    if cache_date is None:
                        cache_date = row.get('cache_date', '')
                    # Remove cache_date and cache_timestamp from contract data
                    contract = {k: v for k, v in row.items() if k not in ['cache_date', 'cache_timestamp']}
                    # Convert numeric fields back to proper types
                    if 'volume' in contract:
                        contract['volume'] = float(contract['volume'])
                    if 'liquidity' in contract:
                        contract['liquidity'] = float(contract['liquidity'])
                    if 'yes_price' in contract:
                        contract['yes_price'] = float(contract['yes_price'])
                    if 'no_price' in contract:
                        contract['no_price'] = float(contract['no_price'])
                    if '_relevance_score' in contract:
                        contract['_relevance_score'] = int(contract['_relevance_score'])
                    contracts.append(contract)
            
            if cache_date == today:
                print(f"Using cached contracts from {cache_date}")
                print(f"  Loaded {len(contracts)} contracts from cache")
                return contracts
            else:
                print(f"Cache is from {cache_date}, fetching fresh data...")
        except Exception as e:
            print(f"Error reading cache: {e}, fetching fresh data...")
    
    # Fetch fresh data
    contracts = fetch_all_active_contracts(min_volume=min_volume)
    
    # Save to CSV cache
    if contracts:
        try:
            # Get all field names from the first contract
            fieldnames = list(contracts[0].keys())
            # Add cache metadata fields
            fieldnames = ['cache_date', 'cache_timestamp'] + fieldnames
            
            with open(cache_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for contract in contracts:
                    # Add cache metadata to each row
                    row = {
                        'cache_date': today,
                        'cache_timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    row.update(contract)
                    writer.writerow(row)
            
            print(f"  Cached {len(contracts)} contracts to {cache_path}")
        except Exception as e:
            print(f"  Warning: Could not save cache: {e}")
    
    return contracts
