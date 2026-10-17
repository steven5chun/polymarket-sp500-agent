# Polymarket S&P 500 Indicator Pipeline

This document explains how the Polymarket S&P 500 Indicator discovers, filters, scores, and logs prediction market contracts to forecast S&P 500 direction using leading indicators from prediction markets.

---

## Pipeline Overview

```text
┌──────────────────────────────────────┐
│  1. Fetch All Contracts              │  Fetch ALL active Polymarket contracts
│     (data_filter)                    │  Filter: volume > $50K OR liquidity > $50K
│                                      │  Cache to polymarket-contracts.csv
└──────────────┬───────────────────────┘
               │ (raw contracts)
               ▼
┌──────────────────────────────────────┐
│  2. Consensus Filter                 │  Filter contracts where market has
│     (data_filter)                    │  reached majority consensus:
│                                      │  - yes_price > 70% (strong YES) OR
│                                      │  - yes_price < 30% (strong NO)
└──────────────┬───────────────────────┘
               │ (consensus contracts)
               ▼
┌──────────────────────────────────────┐
│  3. LLM Classification               │  LLM classifies each contract:
│     (data_transformation)            │  - Is this economic/financial? (YES/NO)
│                                      │  - Only YES contracts proceed
└──────────────┬───────────────────────┘
               │ (economic/financial contracts)
               ▼
┌──────────────────────────────────────┐
│  4. LLM Impact Scoring               │  LLM scores each contract:
│     (data_transformation)            │  - Impact score (0-100)
│                                      │  - Direction (Bullish/Bearish/Neutral)
│                                      │  - Reason (1-sentence explanation)
└──────────────┬───────────────────────┘
               │ (scored contracts + prediction)
               ▼
┌──────────────────────────────────────┐
│  5. Get S&P 500 Price                │  Capture real-time S&P 500 data
│     (market_data / yfinance)         │  Price, daily/weekly change
└──────────────┬───────────────────────┘
               │ (market context)
               ▼
┌──────────────────────────────────────┐
│  6. Prediction Logger                │  Save to 2 CSV files
│     (prediction_log)                 │  (predictions.csv, detail.csv)
└──────────────────────────────────────┘
```

---

## 1. Data Filtering

**Files:** `src/agents/data_filter.py`, `src/agents/discovery_agent.py`

### Fetching All Contracts

The system fetches ALL active Polymarket contracts (no search query needed) using a multi-segment strategy to work around API limits:

- `fetch_all_markets()` - Fetches all active markets via multiple API segments (low-vol, high-vol, recent)
- `fetch_and_cache_contracts()` - Filters by volume > $50K OR liquidity > $50K, removes expired contracts, caches to `data/polymarket-contracts.csv`

The Discovery Agent (`src/agents/discovery_agent.py`) directly calls the data harvester and impact scorer without CrewAI orchestration.

### Contract Expiry Filtering

**File:** `src/agents/data_filter.py` - `filter_by_expiry()`

Not all contracts returned by the Polymarket API are valid for scoring. The system filters out:

1. **Expired contracts** - Contracts where `end_date < now()`. These have already resolved and their data is stale.
2. **Not-yet-active contracts** - Contracts where `start_date > now()`. These are future events that haven't started trading yet.

**Filtering Logic:**
```python
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
```

---

## 2. Consensus Filtering

**File:** `src/agents/data_filter.py` - `filter_by_consent()`

After filtering by expiry, the system applies a consent filter to keep only contracts where the market has reached majority consensus.

### Filtering Logic

Keep contracts where:
- `yes_price > CONSENT_YES_HIGH` (default: 0.70) - strong YES consensus
- OR `yes_price < CONSENT_YES_LOW` (default: 0.30) - strong NO consensus

Remove contracts where:
- `CONSENT_YES_LOW <= yes_price <= CONSENT_YES_HIGH` - market uncertain

### Why This Matters

- **Leading indicators need strong signals** - Contracts with extreme yes_price values represent market consensus
- **Reduces noise** - Uncertain contracts (30-70% yes_price) add confusion without clear directional signal
- **Reduces LLM API calls** - Fewer contracts to process = lower cost
- **Improves prediction accuracy** - Focus on contracts where market has strong opinion

### Configuration

Consent thresholds are configurable via environment variables:
- `CONSENT_YES_HIGH` - Upper threshold (default: 0.70)
- `CONSENT_YES_LOW` - Lower threshold (default: 0.30)

---

## 3. AI Impact Scoring

**File:** `src/agents/data_transformation.py`

### Overview

The system uses a two-step LLM process:
1. **Classification** - LLM identifies which contracts are purely economic/financial
2. **Scoring** - LLM scores each economic/financial contract for impact on S&P 500 (magnitude), direction (bullish/bearish/neutral), and provides reasoning

### Step 1: LLM Classification (Economic/Financial Filter)

**File:** `src/agents/data_transformation.py` - `classify_economic_financial_with_llm()`

Instead of keyword-based filtering, the system uses LLM to classify which contracts are purely economic/financial.

**Process:**
1. Contracts are sent to LLM in batches of 10
2. For each contract, LLM answers YES or NO: "Is this purely economic/financial?"
3. Only YES contracts proceed to scoring

**Included (YES):**
- Macroeconomic indicators (GDP, unemployment, inflation, PMI, retail sales, housing)
- Monetary policy (Fed, Bank of England, ECB, interest rates, quantitative easing)
- Currency markets (EUR/USD, forex, exchange rates)
- Bond markets (yield curve, credit spreads, treasury yields)
- Trade indicators (trade balance, tariffs, imports/exports)
- Housing market (home prices, mortgage rates)
- Broad market indices (S&P 500, Nasdaq, Dow Jones)
- Major commodities (oil, gold, silver, copper, agriculture)

**Excluded (NO):**
- Cryptocurrency price targets (Bitcoin, Ethereum, etc.)
- Individual company events (IPOs, M&A, CEO changes, market cap)
- Political events (elections, impeachment, legislation)
- War/geopolitical conflicts (military strikes, invasions, sanctions)
- Sports, entertainment, personal events
- Technology/product launches (unless purely economic indicator)

**Examples:**
- "Will US unemployment reach 6.0%?" → YES (economic indicator)
- "Will federal funds rate be 2.25%?" → YES (monetary policy)
- "Will WTI Crude Oil hit $65?" → YES (commodity)
- "Will Bitcoin reach $95,000?" → NO (cryptocurrency)
- "OpenAI IPO above $1T?" → NO (company-specific)
- "Stripe acquire PayPal?" → NO (company M&A)
- "Will recession happen?" → YES (macroeconomic)

**Benefits:**
- More accurate than keyword filtering
- Understands context and edge cases
- No manual keyword maintenance required

### Step 2: LLM Impact Scoring

Contracts are sent to the LLM in batches of 10. For each contract, the LLM receives:
- `question`: The contract question text
- `description`: The contract description (truncated to 300 chars)
- `yes_price`: The current market probability (0.0 to 1.0)
- `volume`: Trading volume

The LLM returns three values per contract:

#### 1. Impact Score (0-100): Magnitude of potential S&P 500 impact

The LLM assigns each contract an `impact_score` based on how much the contract's outcome could move the S&P 500:

| Score | Meaning | Example |
|-------|---------|---------|
| 0 | No impact | Niche topic, tiny market |
| 25 | Low impact | Minor economic indicator, small policy |
| 50 | Moderate impact | Sector-specific news, medium policy |
| 75 | High impact | Major economic data, significant policy |
| 100 | Extremely high impact | Fed decision, recession, financial crisis |

The LLM considers:
- **Economic significance** (Fed rates, unemployment, GDP = high impact)
- **Market size** (broad indices vs. niche sectors)
- **Policy importance** (major regulations vs. minor changes)

**Note:** Impact score is subjective LLM judgment, not a mathematical formula.

#### 2. Direction: Bullish / Bearish / Neutral for S&P 500

The LLM classifies each contract based on whether the outcome would be good or bad for S&P 500, considering the `yes_price` (market probability):

**For BAD EVENT contracts** (recession, crisis, unemployment):
- Low yes_price = bad event UNLIKELY = **BULLISH** for S&P 500
- High yes_price = bad event LIKELY = **BEARISH** for S&P 500

**For GOOD EVENT contracts** (rate cut, growth, IPO):
- High yes_price = good event LIKELY = **BULLISH** for S&P 500
- Low yes_price = good event UNLIKELY = **BEARISH** for S&P 500

**Examples:**
- "Will recession happen?" at 7.5% yes → recession unlikely → **BULLISH**, impact: 85
- "Will Fed cut rates?" at 80% yes → rate cut likely → **BULLISH**, impact: 90
- "Will Bitcoin hit $150K?" at 2.3% yes → unlikely → **BEARISH**, impact: 15

#### 3. Reason: 1-sentence explanation

The LLM provides a brief explanation of why the contract is bullish/bearish/neutral for S&P 500.

**Examples:**
- "Low recession probability signals economic stability and continued corporate earnings growth"
- "Fed rate cuts lower borrowing costs for corporations, boosting profit margins and equity valuations"
- "Crypto market has limited direct impact on traditional equity valuations"

### Step 3: Predict Market Direction

The system aggregates all contracts to predict overall market direction using **impact-weighted directional sentiment**:

#### Calculation Logic

1. **Sum impact scores by direction:**
   ```python
   bullish = [c for c in scored_contracts if c.get("direction") == "Bullish"]
   bearish = [c for c in scored_contracts if c.get("direction") == "Bearish"]
   neutral = [c for c in scored_contracts if c.get("direction") == "Neutral"]
   
   bullish_impact_sum = sum(c.get("impact_score", 0) for c in bullish)
   bearish_impact_sum = sum(c.get("impact_score", 0) for c in bearish)
   neutral_impact_sum = sum(c.get("impact_score", 0) for c in neutral)
   ```

2. **Determine predicted direction:**
   ```python
   directional_sum = bullish_impact_sum + bearish_impact_sum
   
   if bullish_impact_sum > bearish_impact_sum:
       predicted_direction = "Bullish"
   elif bearish_impact_sum > bullish_impact_sum:
       predicted_direction = "Bearish"
   else:
       predicted_direction = "Neutral"
   ```

3. **Calculate confidence percentage:**
   ```python
   confidence_pct = max(bullish_impact_sum, bearish_impact_sum) / directional_sum * 100
   ```

#### Example Calculation

Given:
- Bullish Impact: 185 (9 contracts)
- Bearish Impact: 310 (13 contracts)
- Neutral Impact: 150 (45 contracts)

Calculation:
```
directional_sum = 185 + 310 = 495
predicted_direction = "Bearish" (310 > 185)
confidence_pct = 310 / 495 × 100 = 62.6%
```

#### Interpretation

- **Higher confidence (>70%)** = stronger consensus among directional contracts
- **Lower confidence (<55%)** = mixed signals, uncertain market direction
- **Neutral contracts are excluded** from directional calculation because they don't signal a directional bias (benefit some sectors but hurt others, or have mixed/unclear impact)

#### Why This Approach?

- **Impact-weighted**: A contract with impact 90 counts more than a contract with impact 10
- **Directional focus**: Only bullish and bearish contracts contribute to the prediction
- **Confidence metric**: Shows how strong the consensus is, not just the direction

---

## 4. S&P 500 Price Capture

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

## 5. Prediction Logging

**File:** `src/prediction_log.py`

### predictions.csv

One row per prediction run. Designed for plotting market direction prediction vs S&P 500 price over time.

| Column | Description |
|--------|-------------|
| `prediction_id` | Unique ID (e.g., `pred_20261015_123`) |
| `timestamp` | When prediction was made |
| `predicted_direction` | Overall market prediction: Bullish / Bearish / Neutral |
| `confidence_pct` | Confidence in prediction (0-100%) |
| `bullish_impact_sum` | Total impact score of all bullish contracts |
| `bearish_impact_sum` | Total impact score of all bearish contracts |
| `neutral_impact_sum` | Total impact score of all neutral contracts |
| `total_contracts_scored` | Number of contracts analyzed |
| `sp500_price` | S&P 500 price at prediction time |
| `sp500_daily_change_pct` | S&P 500 daily change % |
| `sp500_weekly_change_pct` | S&P 500 7-day change % |

### detail.csv

One row per Polymarket contract. Contains each contract's impact score, direction, and reasoning.

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
| `reason` | 1-sentence explanation of why this contract is bullish/bearish/neutral |

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
    │  filter_by_consent()
    │  - Keep contracts where yes_price > 70% OR yes_price < 30%
    │  - Remove uncertain contracts (30% <= yes_price <= 70%)
    │
    ▼
Consensus Contracts
    │
    │  classify_economic_financial_with_llm()
    │  - LLM classifies each contract as YES/NO (economic/financial?)
    │  - Only YES contracts proceed to scoring
    │
    ▼
Economic/Financial Contracts
    │
    │  score_contracts_with_llm()
    │  - LLM determines impact_score (0-100), direction, and reason
    │  - Content sanitization applied before LLM call
    │
    ▼
Scored Contracts (list of dicts with impact_score + direction + reason)
    │
    │  predict_market_direction(scored_contracts)
    │  - Sum impact by direction (bullish/bearish/neutral)
    │  - Determine predicted_direction (highest directional sum)
    │  - Calculate confidence_pct = max(bull, bear) / (bull + bear) * 100
    │
    ▼
Market Direction Prediction
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
| `src/agents/data_filter.py` | Polymarket API client with filtering (liquidity, expiry, consensus) |
| `src/agents/discovery_agent.py` | Fetches all contracts and calls impact scorer |
| `src/agents/data_transformation.py` | LLM classification (economic/financial?) + impact scoring (0-100) + direction + reason |
| `src/llm.py` | Unified LLM provider factory (OpenAI/Qwen/Ollama) |
| `src/market_data.py` | Real-time S&P 500 data fetcher via yfinance |
| `src/pipeline.py` | Main orchestration entry point |
| `src/prediction_log.py` | Prediction logging to 2 CSV files |
| `scripts/run_daily_predictions.py` | Run daily predictions |
| `scripts/regenerate_detail_csv.py` | Regenerate detail.csv from cached contracts |
