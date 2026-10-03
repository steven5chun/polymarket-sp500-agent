# 📈 Polymarket Macro Sentiment S&P 500 Predictor AI Agent

An autonomous multi-agent framework utilizing the **Model Context Protocol (MCP)** to dynamically search, filter, and ingest real-money crowd probabilities from Polymarket (via the Gamma & CLOB APIs) to predict short-term directional movement regimes for the **S&P 500 (\$SPX)**.

---

## 🚀 Overview

Traditional stock market indicators are backward-looking or heavily reliant on laggy retail media feeds. This project leverages the **"Wisdom of the Crowds"** by tracking multi-billion-dollar prediction markets where capital allocators back their economic perspectives with real money. 

By utilizing a dedicated discovery agent, this pipeline can search for *any* dynamic user item, asset, or breaking news catalyst (e.g., "Middle East conflicts," "oil prices," or "Federal Reserve rate hikes"), filter them for financial relevance, and pass them into quantitative text-based feature vectors to predict near-term stock trends.

### 🧠 Core Architecture

The system operates using an advanced multi-agent design powered by **CrewAI** / **LangGraph** paired with a dedicated MCP server bridge:

```text
┌─────────────────────────────────┐
│   SPX Impact Discovery Agent    │ <-- Dynamically searches Polymarket contracts for ANY
│ (Search & Relevance Discovery)  │     breaking target item or market-moving keyword.
└────────────────┬────────────────┘
                 │ (Filtered Relevant Contracts Data)
                 ▼
┌─────────────────────────────────┐
│     Polymarket Ingestion        │ <-- Queries open public API endpoints 
│         (Data Agent)            │     (Zero authorization tokens required)
└────────────────┬────────────────┘
                 │ (Raw Implied Event Odds Data)
                 ▼
┌─────────────────────────────────┐
│    Neural Sentiment Scoring     │ <-- Normalizes macro trends into a unified
│        (Quant Agent)            │     Stress & Sentiment Coefficient [0.0 - 1.0]
└────────────────┬────────────────┘
                 │ (Clean Sentiment Vector)
                 ▼
┌─────────────────────────────────┐
│     S&P 500 Tactical Director   │ ──> Generates structural market text reports,
│       (Predictor Agent)         │     direction alerts, and confidence matrices.
└─────────────────────────────────┘
```

---

## 🛠 Features

- **Dynamic Contract Discovery:** An autonomous agent that searches any input item or asset keyword to find related sentiment pools across Polymarket.
- **Zero-Account Ingestion:** Programmatic read-access to real-time Polymarket data requiring no authentication keys or crypto wallet handshakes.
- **MCP Native Bridge:** Utilizes the open-source Model Context Protocol (`prediction-market-mcp`) to enable seamless tool-calling interfaces for LLM execution loops.
- **Liquidity Hardened Filtering:** Built-in safeguards that discard noisy, low-volume event brackets (sub-\$50k) to neutralize whale market manipulation.
- **100% Open Source Ready:** Fully compatible with local LLM pipelines like **Ollama (Llama 3, Mistral)** to keep the entire engine private and zero-cost.

---

## 🗂 Project Structure

```text
├── config/
│   └── mcp.json             # Configurations to bind the server to your local LLM framework
├── src/
│   ├── agents/
│   │   ├── discovery_agent.py# Dynamic query scanner & relevance assessment engine
│   │   ├── data_harvester.py # Code interface handling public REST extraction logic
│   │   ├── quant_scorer.py   # Processes data and weights underlying event curves
│   │   └── spx_predictor.py  # Calculates directional S&P 500 alpha
│   └── pipeline.py           # Core execution loop orchestrating agent network tasks
├── requirements.txt         # Dependencies manifest
└── README.md                # Project documentation (this file)
```

---

## ⚙️ Quick Start Installation

### Prerequisites
- Python 3.10+
- Node.js v18+ (for running the underlying MCP data tool server)

### 1. Set Up the Local Python Environment
Clone this project directory and install the necessary modular packages:
```bash
git clone https://github.com/steven5chun/polymarket-sp500-agent
cd polymarket-sp500-agent
pip install -r requirements.txt
```

### 2. Connect the open-source MCP Server
Initialize the native prediction market data context protocol module inside your local directory:
```bash
git clone https://github.com/JamesANZ/prediction-market-mcp
cd prediction-market-mcp
npm install
npm run build
```

### 3. Run the Execution Pipeline
Return to the parent application folder and kick off your autonomous forecast engine:
```bash
python src/pipeline.py
```

---

## 📊 Sample Agent Output Matrix

Upon pipeline execution, the network returns strict structured textual data schemas for your financial models:

```json
{
  "market_regime": "Geopolitical Volatility Risk",
  "sentiment_score": 0.28,
  "sp500_direction_7d": "Bearish",
  "rationale": "The Discovery Agent isolated a sudden 400% surge in volume on the Polymarket contract 'Will Brent crude exceed \$95 before next Friday?', with implied odds climbing from 15% to 64%. The Quant Agent mapped this into a global supply shock vector. The Predictor Agent forecasts severe valuation contraction across consumer-discretionary sectors inside the S&P 500 over a 7-day horizon.",
  "confidence_level": "High"
}
```

---

## ⚠️ Disclaimer

*This repository is intended strictly for educational, open-source, and research purposes. Prediction market data represents speculative human probabilities and should never be viewed as definitive financial or professional investment advice. Past accuracy does not predict future performance parameters.*

