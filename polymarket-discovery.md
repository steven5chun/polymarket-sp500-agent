# Polymarket S&P 500 Impact Score Pipeline

This document explains how the Polymarket S&P 500 Impact Score Agent discovers, scores, and logs prediction market contracts to track the relationship between Polymarket impact scores and S&P 500 price over time.

---

## Pipeline Overview

```text
┌──────────────────────────────────────┐
│  1. Fetch All Contracts              │  Fetch ALL active Polymarket contracts
│     (data_harvester)                 │  Filter: volume > $50K OR liquidity > $50K
│                                      │  Cache to polymarket-contracts.csv
└──────────────┬───────────────────────┘
               │ (raw contracts)
               ▼
┌──────────────────────────────────────┐
│  2. AI Impact Scorer                 │  LLM reads each contract:
│     (sector_classifier)              │  - Impact score (0-100)
│                                      │  - Direction (Bullish/Bearish/Neutral)
│                                      │  Sort top 5, calculate average
└──────────────┬───────────────────────┘
               │ (scored contracts + top 5 + avg)
               ▼
┌──────────────────────────────────────┐
│  3. Get S&P 500 Price                │  Capture real-time S&P 500 data
│     (market_data / yfinance)         │  Price, daily/weekly change
└──────────────┬───────────────────────┘
               │ (market context)
               ▼
┌──────────────────────────────────────┐
│  4. Prediction Logger                │  Save to 2 CSV files
│     (prediction_log)                 │  (predictions.csv, detail.csv)
└──────────────────────────────────────┘
```

---

## 1. Data Harvesting & Filtering

**Files:** `src/agents/data_harvester.py`, `src/agents/discovery_agent.py`

### Fetching All Contracts

The system fetches ALL active Polymarket contracts (no search query needed) using a multi-segment strategy to work around API limits:

- `fetch_all_markets()` - Fetches all active markets via multiple API segments (low-vol, high-vol, recent)
- `fetch_and_cache_contracts()` - Filters by volume > $50K OR liquidity > $50K, removes expired contracts, caches to `data/polymarket-contracts.csv`

The Discovery Agent (`src/agents/discovery_agent.py`) directly calls the data harvester and impact scorer without CrewAI orchestration.

### Contract Expiry Filtering

**File:** `src/agents/data_harvester.py` - `filter_by_expiry()`

Not all contracts returned by the Polymarket API are valid for scoring. The system filters out:

1. **Expired contracts** - Contracts where `end_date < now()`. These have already resolved and their data is stale.
2. **Not-yet-active contracts** - Contracts where `start_date > now()`. These are future events that haven't started trading yet.

**Filtering Logic:**
```python
def filter_by_expiry(markets: list[dict]) -> list[dict]:
    now = datetime.now(timezone.utc)
    filtered = []
    
    for market in markets:
        end_date_str = market.get("endDate") or market.get("endDateIso")
        start_date_str = market.get("startDate") or market.get("startDateIso")
        
        if not end_date_str:
            filtered.append(market)
            continue
        
        end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
        
        if end_date < now:
            continue
        
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
            if start_date > now:
                continue
        
        filtered.append(market)
    
    return filtered
```

---

## 2. AI Impact Scoring

**File:** `src/agents/sector_classifier.py`

### Overview

Instead of classifying contracts into sectors, the LLM directly scores each contract's potential **impact on the S&P 500** (magnitude) and **direction** (bullish/bearish/neutral).

### Step 1: Filter Irrelevant Contracts

Pattern-based filtering removes obviously irrelevant contracts before LLM processing:
- Sports scores and betting (exact score, O/U, spread, vs.)
- Entertainment awards (Oscar, Emmy, Grammy, Tony)
- Personal events (dating, marriage, babies)

### Step 2: LLM Impact Scoring

Contracts are sent to the LLM in batches of 10. For each contract, the LLM receives:
- `question`: The contract question text
- `description`: The contract description (truncated to 300 chars)
- `yes_price`: The current market probability (0.0 to 1.0)
- `volume`: Trading volume

The LLM returns two values per contract:

**1. Impact Score (0-100):** Magnitude of potential S&P 500 impact
- 0 = No impact (niche topic, small market)
- 25 = Low impact (minor economic indicator, small policy change)
- 50 = Moderate impact (sector-specific news, medium policy)
- 75 = High impact (major economic data, significant policy, geopolitical event)
- 100 = Extremely high impact (Fed decision, recession, major war, financial crisis)

**2. Direction:** Bullish / Bearish / Neutral for S&P 500

The LLM considers the `yes_price` when determining direction:

**For BAD EVENT contracts** (recession, war, crisis, unemployment):
- Low yes_price = bad event UNLIKELY = BULLISH for S&P 500
- High yes_price = bad event LIKELY = BEARISH for S&P 500

**For GOOD EVENT contracts** (peace deal, rate cut, growth, IPO):
- High yes_price = good event LIKELY = BULLISH for S&P 500
- Low yes_price = good event UNLIKELY = BEARISH for S&P 500

**Examples:**
- "Will recession happen?" at 7.5% yes → recession unlikely → BULLISH, impact: 85
- "Will Fed cut rates?" at 80% yes → rate cut likely → BULLISH, impact: 90
- "Will war escalate?" at 60% yes → war likely → BEARISH, impact: 80
- "Will Bitcoin hit $150K?" at 2.3% yes → unlikely → BEARISH, impact: 15
- "OpenAI IPO above $1T?" at 72.5% yes → likely → BULLISH, impact: 25

### Step 3: Sort Top 5 & Calculate Average

After all contracts are scored:
1. Sort all contracts by `impact_score` in descending order
2. Select the top 5 highest-impact contracts
3. Calculate the average impact score of the top 5

```python
top_contracts = sorted(scored_contracts, key=lambda c: c["impact_score"], reverse=True)[:5]
avg_impact_score = sum(c["impact_score"] for c in top_contracts) / len(top_contracts)
```

### Content Sanitization

Before any contract text reaches the LLM, regex patterns redact:
- Political figure names (Trump, Biden, Xi Jinping, etc.)
- Political party names (Democrat, Republican, etc.)
- Violent event terms (assassination, murder, etc.)
- Nuclear threat terms

This prevents Qwen's content moderation from blocking legitimate financial analysis.

---

## 3. S&P 500 Price Capture

**File:** `src/market_data.py`

The system captures real-time S&P 500 data using `yfinance`:

| Field | Description |
|-------|-------------|
| `sp500_price` | Current S&P 500 price |
| `sp500_daily_change_pct` | Daily change % |
| `sp500_weekly_change_pct` | 7-day change % |
| `market_status` | open / closed / pre-market / after-hours |

This data is captured at prediction time and logged alongside the impact score, enabling trend analysis over time.

---

## 4. Prediction Logging

**File:** `src/prediction_log.py`

### predictions.csv

One row per prediction run. Designed for plotting impact score vs S&P 500 price over time.

| Column | Description |
|--------|-------------|
| `prediction_id` | Unique ID (e.g., `pred_20261015_123`) |
| `timestamp` | When prediction was made |
| `avg_impact_score` | Average impact score of top 5 contracts (0-100) |
| `top1_question` | Highest impact contract question |
| `top1_impact_score` | Its impact score (0-100) |
| `top1_direction` | Bullish / Bearish / Neutral |
| `top2_question` / `top2_impact_score` / `top2_direction` | 2nd highest |
| `top3_question` / `top3_impact_score` / `top3_direction` | 3rd highest |
| `top4_question` / `top4_impact_score` / `top4_direction` | 4th highest |
| `top5_question` / `top5_impact_score` / `top5_direction` | 5th highest |
| `sp500_price` | S&P 500 price at prediction time |
| `sp500_daily_change_pct` | S&P 500 daily change % |
| `sp500_weekly_change_pct` | S&P 500 7-day change % |

### detail.csv

One row per Polymarket contract. Contains each contract's impact score and direction.

| Column | Description |
|--------|-------------|
| `prediction_id` | Links to predictions.csv |
| `timestamp` | When prediction was made |
| `contract_id` | Polymarket market ID |
| `contract_question` | The contract question text |
| `contract_volume` | Trading volume in USD |
| `contract_yes_price` | Implied probability (0.0 to 1.0) |
| `impact_score` | LLM-determined S&P 500 impact (0-100) |
| `direction` | Bullish / Bearish / Neutral |

---

## Data Flow Summary

```text
Polymarket Gamma API
    │
    │  fetch_all_markets()
    │  filter_by_volume_or_liquidity(>= $50k)
    │  filter_by_expiry(remove expired/not-yet-active)
    │  cache to polymarket-contracts.csv
    │
    ▼
Raw Contracts (list of dicts)
    │
    │  filter_irrelevant_contracts()
    │  - Remove sports, entertainment, personal events
    │
    ▼
Relevant Contracts
    │
    │  score_contracts_with_llm()
    │  - LLM determines impact_score (0-100) and direction for each contract
    │  - Content sanitization applied before LLM call
    │
    ▼
Scored Contracts (list of dicts with impact_score + direction)
    │
    │  get_top_impact_contracts(top_n=5)
    │  - Sort by impact_score descending
    │  - Select top 5
    │
    │  calculate_average_impact_score(top_5)
    │  - avg = sum(scores) / 5
    │
    ▼
Top 5 Contracts + Average Impact Score
    │
    │  get_realtime_sp500_data()
    │  - Capture S&P 500 price, daily/weekly change
    │
    ▼
Market Context
    │
    │  log_prediction()
    │  - Save to 2 CSV files (predictions.csv, detail.csv)
    │
    ▼
Logged Prediction (predictions.csv + detail.csv)
```

---

## Daily Workflow

```bash
# Run prediction (fetches all contracts, scores impact, logs)
python -m scripts.run_daily_predictions

# Or run manually
python -m src.pipeline

# Run without logging
python -m src.pipeline --no-log
```

---

## File Reference

| File | Purpose |
|------|---------|
| `src/agents/data_harvester.py` | Polymarket Gamma/CLOB REST API client with expiry filtering |
| `src/agents/discovery_agent.py` | Fetches all contracts and calls impact scorer |
| `src/agents/sector_classifier.py` | LLM impact scoring (0-100) + direction (Bullish/Bearish/Neutral) |
| `src/llm.py` | Unified LLM provider factory (OpenAI/Qwen/Ollama) |
| `src/market_data.py` | Real-time S&P 500 data fetcher via yfinance |
| `src/pipeline.py` | Main orchestration entry point |
| `src/prediction_log.py` | Prediction logging to 2 CSV files |
| `scripts/run_daily_predictions.py` | Run daily predictions |
| `scripts/regenerate_detail_csv.py` | Regenerate detail.csv from cached contracts |
