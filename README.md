# Polymarket Macro Sentiment S&P 500 Predictor AI Agent

An autonomous multi-agent framework that fetches all active Polymarket contracts, classifies them into 10 macro sectors via AI, and predicts short-term directional movement for the **S&P 500 ($SPX)**.

---

## Overview

This project leverages the **"Wisdom of the Crowds"** by tracking [prediction markets](./prediction-market.md) where capital allocators back their economic perspectives with real money. The system:

1. Fetches **all active Polymarket contracts** (volume > $50K)
2. Caches contracts to `data/polymarket-contracts.csv` (refreshed daily)
3. AI agent classifies each contract into one of 10 macro sectors
4. Contracts not fitting any sector are discarded
5. Computes sector-level sentiment vectors
6. Generates a 7-day directional S&P 500 forecast
7. Logs predictions across 3 CSV files

### Architecture

```text
┌──────────────────────────────────────┐
│  0. Market Snapshot                  │  Capture real-time S&P 500 data
│     (yfinance)                       │  Price, daily/weekly change, 50d MA
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  1. Fetch All Contracts              │  Fetch ALL active Polymarket contracts
│     (data_harvester)                 │  Filter: volume > $50K, not expired
│                                      │  Cache to polymarket-contracts.csv
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  2. AI Sector Classifier             │  LLM classifies each contract
│     (sector_classifier)              │  into 10 sectors. Contracts not
│                                      │  fitting any sector are discarded.
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  3. Quant Scorer                     │  Aggregates LLM-provided sentiment
│     (Pure LLM)                       │  scores + stress coefficients
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  4. S&P 500 Predictor                │  Directional forecast +
│     (Deterministic + LLM)            │  sector breakdown + rationale
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  5. Log to 3 CSV Files               │
│     predictions.csv  - overall + S&P │
│     sectors.csv      - sector scores │
│     detail.csv       - each contract │
└──────────────────────────────────────┘
```

---

## Features

- **Full Market Coverage** - Fetches ALL active Polymarket contracts (no search query needed), ensuring no relevant signal is missed
- **Daily Contract Cache** - Contracts cached to `data/polymarket-contracts.csv`, refreshed once per day to avoid redundant API calls
- **Pure LLM Classification & Sentiment** - LLM reads question + description + yes_price to determine sector, sentiment score, and signal for each contract
- **Sector-Based Analysis** - Each sector weighted by historical S&P 500 impact
- **Liquidity Filtering** - Only contracts with volume > $50K are considered
- **Contract Expiry Filtering** - Removes expired and not-yet-active contracts
- **Multi-LLM Support** - Configurable backend: OpenAI, Qwen (Alibaba Cloud), or Ollama (local)
- **Real-Time Market Context** - Captures S&P 500 price, daily/weekly changes, and 50-day MA with each prediction
- **3-File CSV Logging** - Clean separation: predictions, sectors, and contract details
- **Zero-Account Data** - Polymarket API requires no authentication

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

No query needed - the system fetches ALL Polymarket contracts and classifies them via AI.

```bash
source .venv/bin/activate

# Run prediction (fetches all contracts, classifies, predicts)
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
| `python -m src.pipeline` | Run prediction (all contracts) |
| `python -m src.pipeline --no-log` | Run prediction without logging |
| `python -m scripts.run_daily_predictions` | Run daily prediction |

---

## Data Flow

### How It Works

1. **Fetch All Contracts** - Polymarket Gamma API returns all active markets
2. **Filter** - Keep only contracts with volume > $50K and valid (non-expired) dates
3. **Cache** - Save to `data/polymarket-contracts.csv` (reused for same-day runs)
4. **Pure LLM Classification** - LLM determines sector, sentiment_score (0.0-1.0), and signal for each contract
5. **Discard Unmatched** - Contracts not fitting any sector are removed
6. **Score** - Aggregate LLM-provided sentiment scores per sector using volume-weighted averaging
7. **Predict** - Generate 7-day S&P 500 directional forecast
8. **Log** - Save to 3 CSV files (predictions, sectors, detail)

---

## Output: 3 CSV Files

All logs are stored in `data/` as CSV files. No `query` column - the system processes all contracts.

### 1. `data/predictions.csv` - Overall Predictions

One row per prediction run. Contains overall prediction, all 10 sector scores, and real-time S&P 500 data.

| Column | Description |
|--------|-------------|
| `prediction_id` | Unique ID (e.g., `pred_20261004_339`) |
| `timestamp` | When prediction was made |
| `direction` | Bullish / Bearish / Neutral |
| `confidence` | High / Medium / Low |
| `sentiment_score` | Aggregate sentiment (0.0 to 1.0) |
| `stress_coefficient` | Aggregate stress (0.0 to 1.0) |
| `market_regime` | LLM-described market regime |
| `driving_sectors` | Comma-separated sector IDs |
| `sp500_price` | S&P 500 price at prediction time |
| `sp500_daily_change_pct` | S&P 500 daily change % |
| `sp500_weekly_change_pct` | S&P 500 7-day change % |
| `sp500_distance_from_50d_ma_pct` | Distance from 50-day MA % |
| `{sector}_score` | Sentiment score per sector (10 columns) |

### 2. `data/sectors.csv` - Sector-Level Aggregations

One row per sector per prediction. Contains sector total scores.

| Column | Description |
|--------|-------------|
| `prediction_id` | Links to predictions.csv |
| `timestamp` | When prediction was made |
| `sector_id` | Sector identifier (e.g., `economic_growth`) |
| `sector_name` | Human-readable name |
| `sentiment_score` | Sector sentiment (0.0 to 1.0) |
| `stress_coefficient` | Sector stress (0.0 to 1.0) |
| `signal` | Bullish / Bearish / Neutral |
| `contract_count` | Number of contracts in sector |
| `total_volume` | Total contract volume in USD |
| `spx_weight` | Sector weight in aggregate (0.0 to 1.0) |

### 3. `data/detail.csv` - Individual Contract Details

One row per Polymarket contract. Contains classification and scores.

| Column | Description |
|--------|-------------|
| `prediction_id` | Links to predictions.csv |
| `timestamp` | When prediction was made |
| `contract_id` | Polymarket market ID |
| `contract_question` | The contract question text |
| `contract_volume` | Trading volume in USD |
| `contract_yes_price` | Implied probability (0.0 to 1.0) |
| `contract_sentiment_score` | LLM-determined sentiment (0.0 to 1.0) |
| `contract_signal` | Bullish / Bearish / Neutral |
| `sector_id` | Which sector this contract belongs to |
| `sector_sentiment_score` | Sentiment of the assigned sector |
| `sector_signal` | Signal of the assigned sector |

### 4. `data/polymarket-contracts.csv` - Contract Cache

All active Polymarket contracts with volume > $50K. Overwritten daily.

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

## Sector Taxonomy

| Sector | Weight | Description |
|--------|--------|-------------|
| Economic Growth | 1.00 | GDP, employment, recession, economic indicators |
| Monetary Policy | 0.95 | Fed decisions, interest rates, inflation, FOMC |
| Financial System | 0.95 | Banking stability, credit markets, financial crises |
| Geopolitical Conflict | 0.90 | Wars, military conflicts, sanctions, international tensions |
| US Political Stability | 0.85 | Government dysfunction, elections, policy uncertainty |
| Energy & Commodities | 0.80 | Oil, gas, commodities, supply chains |
| Trade & Regulatory | 0.80 | Tariffs, trade wars, regulation, antitrust |
| Public Health | 0.75 | Pandemics, health crises, disease outbreaks |
| Technology & Cyber | 0.70 | Cyberattacks, tech infrastructure, AI developments |
| Stock Prediction | 0.65 | Stock/crypto price predictions, market confidence indicators |

Weights reflect each sector's historical correlation with S&P 500 directional movement. Contracts that don't fit any sector are discarded. See [polymarket-discovery.md](polymarket-discovery.md) for detailed weight methodology.

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
│   ├── predictions.csv                 # Overall predictions with S&P 500 data
│   ├── sectors.csv                     # Sector-level aggregations
│   └── detail.csv                      # Individual contract details
├── scripts/
│   └── run_daily_predictions.py        # Run daily prediction
├── src/
│   ├── agents/
│   │   ├── data_harvester.py           # Polymarket API client + caching
│   │   ├── discovery_agent.py          # CrewAI agent (fetches all, no query)
│   │   ├── sector_classifier.py        # AI sector classification
│   │   ├── quant_scorer.py             # Sector-level sentiment scoring
│   │   └── spx_predictor.py            # Directional prediction + rationale
│   ├── sectors.py                      # 10-sector taxonomy + weights
│   ├── llm.py                          # LLM provider factory
│   ├── market_data.py                  # Real-time S&P 500 data fetcher
│   ├── prediction_log.py               # CSV logging (3 files)
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
