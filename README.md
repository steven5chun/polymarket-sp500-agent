# Polymarket S&P 500 Indicator

A leading indicator that uses Polymarket prediction markets to forecast S&P 500 direction. The system fetches economic/financial contracts with majority consensus, uses LLM to score their S&P 500 impact, and predicts market direction with confidence levels.

---

## Overview

This project leverages the **"Wisdom of the Crowds"** by tracking [prediction markets](prediction-markets.md) where capital allocators back their economic perspectives with real money. The system:

1. Fetches **all active Polymarket contracts** (volume > $50K OR liquidity > $50K)
2. Filters by **consensus** - keeps only contracts where market has reached majority consensus (yes_price > 70% OR yes_price < 30%)
3. Caches contracts to `data/polymarket-contracts.csv` (refreshed daily)
4. LLM classifies contracts as **economic/financial** (excludes crypto, company events, politics, geopolitics)
5. LLM scores each contract's **impact on S&P 500** (0-100) and **direction** (Bullish/Bearish/Neutral)
6. Predicts **overall market direction** with confidence percentage
7. Captures the **current S&P 500 price**
8. Logs predictions to CSV files for trend analysis

---

## Takeaway

- **Data Preprocessing is Critical**: Raw Polymarket data contains multiple contract types and noise. You must filter, clean, and transform this data before feeding it into a Large Language Model (LLM) to ensure the output is accurate and meaningful.

- **Leverage LLM Text Strengths**: LLMs excel at text-based tasks. Use your model specifically for classification, summarization, and text-similarity analysis within your project.

- **Optimize via Prompt Engineering**: The quality of your LLM output depends heavily on your prompt. Always include few-shot examples (clear input-output pairs) in your prompts to guide the LLM toward your desired format and logic.

---

### Architecture

```text
┌──────────────────────────────────────┐
│  1. Fetch All Contracts              │  Fetch ALL active Polymarket contracts
│     (data_filter)                    │  Filter: volume > $50K OR liquidity > $50K
│                                      │  Cache to polymarket-contracts.csv
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  2. Consensus Filter                 │  Filter by market consensus:
│     (data_filter)                    │  - yes_price > 70% (strong YES) OR
│                                      │  - yes_price < 30% (strong NO)
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  3. LLM Classification               │  LLM classifies each contract:
│     (data_transformation)            │  - Is this economic/financial? (YES/NO)
│                                      │  - Only YES contracts proceed
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  4. LLM Impact Scoring               │  LLM scores each contract:
│     (data_transformation)            │  - Impact score (0-100)
│                                      │  - Direction (Bullish/Bearish/Neutral)
│                                      │  - Reason (1-sentence explanation)
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  5. Get S&P 500 Price                │  Capture real-time S&P 500 data
│     (market_data / yfinance)         │  Price, daily/weekly change
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  6. Log to CSV Files                 │
│     predictions.csv - prediction +   │
│                       S&P data       │
│     detail.csv      - each contract  │
└──────────────────────────────────────┘
```

---

## Features

- **Full Market Coverage** - Fetches ALL active Polymarket contracts (no search query needed), ensuring no relevant signal is missed
- **Consensus Filtering** - Filters contracts where market has reached majority consensus (yes_price > 70% OR yes_price < 30%), reducing noise from uncertain markets
- **LLM-Based Economic Filtering** - LLM classifies each contract as economic/financial (YES/NO), excluding crypto, company events, politics, and geopolitics
- **Daily Contract Cache** - Contracts cached to `data/polymarket-contracts.csv`, refreshed once per day to avoid redundant API calls
- **LLM Impact Scoring** - LLM reads each contract's question + description and scores S&P 500 impact magnitude (0-100), direction (Bullish/Bearish/Neutral), and provides reasoning
- **Market Direction Prediction** - Aggregates all contracts to predict overall market direction with confidence percentage
- **Volume/Liquidity Filtering** - Only contracts with volume > $50K OR liquidity > $50K are considered
- **Contract Expiry Filtering** - Removes expired and not-yet-active contracts
- **Multi-LLM Support** - Configurable backend: OpenAI, Qwen (Alibaba Cloud), or Ollama (local)
- **Real-Time Market Context** - Captures S&P 500 price and daily/weekly changes with each prediction
- **Trend Tracking** - CSV output designed for plotting impact score vs S&P 500 price over time
- **Zero-Account Data** - Polymarket API requires no authentication

---

## How Scoring & Prediction Works

### Contract Filtering (LLM-Based)

The system uses **LLM-based classification** to identify ONLY pure economic/financial contracts:

**Included:**
- Macroeconomic indicators (GDP, unemployment, inflation, PMI, retail sales)
- Monetary policy (Fed, Bank of England, ECB, interest rates, quantitative easing)
- Currency markets (EUR/USD, GBP/USD, forex, exchange rates)
- Bond markets (yield curve, credit spreads, treasury yields)
- Trade indicators (trade balance, tariffs, imports/exports)
- Housing market (home prices, mortgage rates, housing starts)
- Broad market indices (S&P 500, Nasdaq, Dow Jones)
- Major commodities (oil, gold, silver, copper, agriculture)

**Excluded:**
- Cryptocurrency price targets (Bitcoin, Ethereum, etc.)
- Individual company events (IPOs, M&A, CEO changes, market cap)
- Political events (elections, impeachment, legislation)
- War/geopolitical conflicts (military strikes, invasions, sanctions)
- Sports, entertainment, personal events

The LLM classifies each contract as economic/financial (YES/NO) before scoring.

### Impact Score Calculation (0-100)

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

### Direction Determination (Bullish/Bearish/Neutral)

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

### Market Direction Prediction

The system aggregates all contracts to predict overall market direction using **impact-weighted directional sentiment**:

1. **Sum impact scores by direction:**
   - `bullish_impact_sum` = sum of impact scores from all Bullish contracts
   - `bearish_impact_sum` = sum of impact scores from all Bearish contracts
   - `neutral_impact_sum` = sum of impact scores from all Neutral contracts (excluded from direction calculation)

2. **Determine predicted direction:**
   - If `bullish_impact_sum > bearish_impact_sum` → **Bullish**
   - If `bearish_impact_sum > bullish_impact_sum` → **Bearish**
   - If equal → **Neutral**

3. **Calculate confidence percentage:**
   ```
   confidence = max(bullish, bearish) / (bullish + bearish) * 100
   ```

**Example:**
- Bullish Impact: 185 (9 contracts)
- Bearish Impact: 310 (13 contracts)
- Neutral Impact: 150 (45 contracts)
- Directional Sum: 185 + 310 = 495
- Predicted Direction: **Bearish** (310 > 185)
- Confidence: 310 / 495 × 100 = **62.6%**

**Interpretation:**
- Higher confidence (>70%) = stronger consensus among directional contracts
- Lower confidence (<55%) = mixed signals
- Neutral contracts are excluded because they don't signal a directional bias

---

## Setup

### Prerequisites

- Python 3.10+
- Node.js v18+ (optional, for MCP server)

### 1. Clone and Install

```bash
git clone https://github.com/steven5chun/polymarket-sp500-agent
cd polymarket-sp500-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure LLM Provider

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# Choose one: "openai", "qwen", or "ollama"
LLM_PROVIDER=qwen

# For Qwen (Alibaba Cloud Token Plan)
QWEN_API_KEY=sk-your-qwen-key-here
QWEN_MODEL=qwen3.7-plus
QWEN_API_BASE=https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1

# For OpenAI
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL=gpt-4o

# For Ollama (local, no API key needed)
OLLAMA_MODEL=llama3
OLLAMA_BASE_URL=http://localhost:11434
```

### 3. (Optional) MCP Server

```bash
git clone https://github.com/JamesANZ/prediction-market-mcp
cd prediction-market-mcp && npm install && npm run build
```

---

## Usage

### Run a Prediction

No query needed - the system fetches ALL Polymarket contracts and scores them via AI.

```bash
source .venv/bin/activate

# Run prediction (fetches all contracts, scores impact, logs)
python -m src.pipeline

# Run without logging the prediction
python -m src.pipeline --no-log
```

### Daily Prediction Runner

```bash
# Run daily prediction with full output
python -m scripts.run_daily_predictions

# Run quietly
python -m scripts.run_daily_predictions --quiet
```

### CLI Reference

| Command | Description |
|---------|-------------|
| `python -m src.pipeline` | Run prediction (all contracts, score impact) |
| `python -m src.pipeline --no-log` | Run prediction without logging |
| `python -m scripts.run_daily_predictions` | Run daily prediction |

---

## Data Flow

### How It Works

1. **Fetch All Contracts** - Polymarket Gamma API returns all active markets
2. **Filter** - Keep only contracts with volume > $50K OR liquidity > $50K and valid (non-expired) dates
3. **Cache** - Save to `data/polymarket-contracts.csv` (reused for same-day runs)
4. **Consensus Filter** - Keep only contracts where market has reached majority consensus (yes_price > 70% OR yes_price < 30%)
5. **LLM Classification** - LLM classifies each contract as economic/financial (YES/NO), filtering out crypto, company events, politics, and geopolitics
6. **LLM Impact Scoring** - LLM determines impact score (0-100), direction (Bullish/Bearish/Neutral), and reason for each economic/financial contract
7. **Market Direction Prediction** - Aggregates all contracts to predict overall market direction with confidence percentage
8. **Get S&P 500 Price** - Capture current S&P 500 price and changes
9. **Log** - Save to 2 CSV files (predictions, detail)

---

## Output: 2 CSV Files

All logs are stored in `data/` as CSV files. No `query` column - the system processes all contracts.

### 1. `data/predictions.csv` - Overall Predictions

One row per prediction run. Contains market direction prediction and S&P 500 data.

| Column | Description |
|--------|-------------|
| `prediction_id` | Unique ID (e.g., `pred_20261004_339`) |
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

### 2. `data/detail.csv` - Individual Contract Details

One row per Polymarket contract. Contains impact score, direction, and reasoning.

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

### 3. `data/polymarket-contracts.csv` - Contract Cache

All active Polymarket contracts with volume > $50K OR liquidity > $50K. Overwritten daily.

| Column | Description |
|--------|-------------|
| `cache_date` | Date when cache was created |
| `cache_timestamp` | Exact timestamp of cache creation |
| `id` | Polymarket market ID |
| `question` | Contract question |
| `description` | Contract description |
| `volume` | Trading volume |
| `liquidity` | Current liquidity |
| `yes_price` | Current yes price |
| `start_date` | Contract start date |
| `end_date` | Contract end date |

---

## LLM Provider Options

| Provider | Models | API Key | Cost | Notes |
|----------|--------|---------|------|-------|
| **OpenAI** | gpt-4o, gpt-4o-mini | Required | Paid | No content filter issues |
| **Qwen** | qwen3.7-plus, qwen-plus, qwen-max | Required | Paid | May block political content |
| **Ollama** | llama3, mistral, etc. | Not needed | Free | Local, private, no filters |

### Qwen Content Filter Note

Qwen's API has content moderation that may block political/geopolitical content common in Polymarket contracts. The system includes content sanitization, but some contracts may still trigger filters. If you encounter errors, switch to OpenAI or Ollama.

---

## Project Structure

```text
├── config/
│   └── mcp.json                        # MCP server binding configuration
├── data/
│   ├── polymarket-contracts.csv        # Daily contract cache (overwritten daily)
│   ├── predictions.csv                 # Market direction prediction + S&P 500 data
│   └── detail.csv                      # Individual contract impact scores
├── scripts/
│   ├── run_daily_predictions.py        # Run daily prediction
│   └── regenerate_detail_csv.py        # Regenerate detail.csv from cache
├── src/
│   ├── agents/
│   │   ├── data_filter.py              # Polymarket API client + filtering
│   │   ├── data_transformation.py      # LLM classification + impact scoring
│   │   └── discovery_agent.py          # Fetches all contracts
│   ├── llm.py                          # LLM provider factory
│   ├── market_data.py                  # Real-time S&P 500 data fetcher
│   ├── prediction_log.py               # CSV logging (2 files)
│   └── pipeline.py                     # Main entry point
├── .env.example                        # Environment variable template
├── requirements.txt                    # Python dependencies
├── polymarket-discovery.md             # Detailed agent/scoring documentation
└── README.md                           # This file
```

---

## Documentation

| File | Purpose |
|------|---------|
| [README.md](README.md) | Setup, usage, data flow, CSV format |
| [polymarket-discovery.md](polymarket-discovery.md) | Agent details, sector weights, scoring formulas |



---

## Disclaimer

*This repository is intended strictly for educational, open-source, and research purposes. Prediction market data represents speculative human probabilities and should never be viewed as definitive financial or professional investment advice. Past accuracy does not predict future performance parameters.*
