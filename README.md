# Polymarket S&P 500 Impact Score Agent

An autonomous framework that fetches all active Polymarket contracts, uses LLM to score each contract's potential impact on S&P 500 movement, and tracks the relationship between prediction market impact scores and S&P 500 price over time.

---

## Overview

This project leverages the **"Wisdom of the Crowds"** by tracking [prediction markets](prediction-markets.md) where capital allocators back their economic perspectives with real money. The system:

1. Fetches **all active Polymarket contracts** (volume > $50K OR liquidity > $50K)
2. Caches contracts to `data/polymarket-contracts.csv` (refreshed daily)
3. LLM scores each contract's **impact on S&P 500** (0-100) and **direction** (Bullish/Bearish/Neutral)
4. Sorts contracts by impact score and selects the **top 5 highest impact** contracts
5. Calculates the **average impact score** of the top 5
6. Captures the **current S&P 500 price**
7. Logs predictions to CSV files for trend analysis

### Architecture

```text
┌──────────────────────────────────────┐
│  1. Fetch All Contracts              │  Fetch ALL active Polymarket contracts
│     (data_harvester)                 │  Filter: volume > $50K OR liquidity > $50K
│                                      │  Cache to polymarket-contracts.csv
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  2. AI Impact Scorer                 │  LLM reads each contract and scores:
│     (sector_classifier)              │  - Impact score (0-100)
│                                      │  - Direction (Bullish/Bearish/Neutral)
│                                      │  Sort top 5, calculate average
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  3. Get S&P 500 Price                │  Capture real-time S&P 500 data
│     (market_data / yfinance)         │  Price, daily/weekly change
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  4. Log to CSV Files                 │
│     predictions.csv - avg score +    │
│                       top 5 + S&P    │
│     detail.csv      - each contract  │
└──────────────────────────────────────┘
```

---

## Features

- **Full Market Coverage** - Fetches ALL active Polymarket contracts (no search query needed), ensuring no relevant signal is missed
- **Daily Contract Cache** - Contracts cached to `data/polymarket-contracts.csv`, refreshed once per day to avoid redundant API calls
- **LLM Impact Scoring** - LLM reads each contract's question + description and scores S&P 500 impact magnitude (0-100) and direction (Bullish/Bearish/Neutral)
- **Top 5 Focus** - Identifies the 5 highest-impact contracts and calculates their average score
- **Volume/Liquidity Filtering** - Only contracts with volume > $50K OR liquidity > $50K are considered
- **Contract Expiry Filtering** - Removes expired and not-yet-active contracts
- **Multi-LLM Support** - Configurable backend: OpenAI, Qwen (Alibaba Cloud), or Ollama (local)
- **Real-Time Market Context** - Captures S&P 500 price and daily/weekly changes with each prediction
- **Trend Tracking** - CSV output designed for plotting impact score vs S&P 500 price over time
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
4. **LLM Impact Scoring** - LLM determines impact score (0-100) and direction (Bullish/Bearish/Neutral) for each contract
5. **Sort & Average** - Sort by impact score, select top 5, calculate average
6. **Get S&P 500 Price** - Capture current S&P 500 price and changes
7. **Log** - Save to 2 CSV files (predictions, detail)

---

## Output: 2 CSV Files

All logs are stored in `data/` as CSV files. No `query` column - the system processes all contracts.

### 1. `data/predictions.csv` - Overall Predictions

One row per prediction run. Contains average impact score, top 5 contracts, and S&P 500 data.

| Column | Description |
|--------|-------------|
| `prediction_id` | Unique ID (e.g., `pred_20261004_339`) |
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

### 2. `data/detail.csv` - Individual Contract Details

One row per Polymarket contract. Contains impact score and direction.

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
│   ├── predictions.csv                 # Average impact score + top 5 + S&P 500 data
│   └── detail.csv                      # Individual contract impact scores
├── scripts/
│   ├── run_daily_predictions.py        # Run daily prediction
│   └── regenerate_detail_csv.py        # Regenerate detail.csv from cache
├── src/
│   ├── agents/
│   │   ├── data_harvester.py           # Polymarket API client + caching
│   │   ├── discovery_agent.py          # Fetches all contracts
│   │   └── sector_classifier.py        # LLM impact scoring (0-100) + direction
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
