import json
from typing import Any

from crewai import Agent, Task, Crew
from crewai.tools import tool

from src.agents.data_harvester import fetch_and_cache_contracts
from src.agents.sector_classifier import classify_contracts_hybrid, get_sector_summary
from src.llm import get_llm


@tool("fetch_all_contracts")
def fetch_all_contracts_tool() -> str:
    """Fetch all active Polymarket contracts with volume > $50K.
    
    This tool retrieves all active markets from Polymarket with volume > $50K.
    Uses cached data if available from today, otherwise fetches fresh data.
    Returns contract data including volume, prices, and liquidity.
    """
    contracts = fetch_and_cache_contracts(min_volume=50000)
    return json.dumps(contracts, indent=2)


def build_discovery_agent() -> Agent:
    return Agent(
        role="Polymarket Contract Classifier",
        goal=(
            "Fetch all active Polymarket contracts and classify each one into the most "
            "relevant sector for S&P 500 impact analysis."
        ),
        backstory=(
            "You are a senior macro-strategy analyst specializing in prediction market "
            "intelligence. You excel at categorizing prediction market contracts into "
            "meaningful sectors that impact the S&P 500. You analyze contract questions "
            "and descriptions to determine which macroeconomic or geopolitical sector "
            "each contract belongs to."
        ),
        verbose=True,
        allow_delegation=False,
        tools=[fetch_all_contracts_tool],
        llm=get_llm(),
    )


def build_discovery_task(agent: Agent) -> Task:
    return Task(
        description=(
            "Fetch all active Polymarket contracts and classify each one into a sector.\n\n"
            "Steps:\n"
            "1. Use the fetch_all_contracts tool to retrieve all active contracts.\n"
            "2. For each contract, analyze the question and description.\n"
            "3. Classify each contract into one of these sectors:\n"
            "   - economic_growth\n"
            "   - monetary_policy\n"
            "   - geopolitical_conflict\n"
            "   - us_political_stability\n"
            "   - energy_commodities\n"
            "   - stock_prediction\n"
            "   - financial_system\n"
            "   - technology_cyber\n"
            "   - public_health\n"
            "   - trade_regulatory\n"
            "4. Return a structured JSON summary of the classification results.\n\n"
            "Return your findings as a JSON object with this schema:\n"
            "{\n"
            '  "total_contracts": <number>,\n'
            '  "classified_contracts": [\n'
            "    {\n"
            '      "id": "<market id>",\n'
            '      "question": "<market question>",\n'
            '      "volume": <volume>,\n'
            '      "yes_price": <implied probability>,\n'
            '      "sector": "<sector_id>",\n'
            '      "classification_rationale": "<brief reason for sector assignment>"\n'
            "    }\n"
            "  ],\n"
            '  "market_regime": "<brief description of overall market conditions>",\n'
            '  "summary": "<2-3 sentence overview of contract distribution>"\n'
            "}\n"
        ),
        expected_output="A JSON object containing all contracts with their sector classifications.",
        agent=agent,
    )


def run_discovery() -> dict[str, Any]:
    """Fetch all Polymarket contracts and classify them into sectors.
    
    This function bypasses the CrewAI agent to avoid LLM quota issues.
    It directly fetches contracts and uses hybrid classification.
    
    Returns:
        Dict containing:
        - all_contracts: List of all contracts with sector assignments
        - grouped_contracts: Dict mapping sector_id to list of contracts
        - sector_summary: Summary statistics per sector
        - market_regime: Description of market conditions
        - summary: Overview of classification results
    """
    print("Fetching all contracts and classifying...")
    
    # Fetch all contracts
    all_contracts = fetch_and_cache_contracts(min_volume=50000)
    print(f"Fetched {len(all_contracts)} contracts")
    
    # Classify using pure LLM method
    print("Classifying contracts...")
    grouped_contracts = classify_contracts_hybrid(all_contracts)
    
    # Build contracts list with sector assignments
    contracts = []
    for sector_id, sector_contracts in grouped_contracts.items():
        for contract in sector_contracts:
            contracts.append({
                "id": contract.get("id"),
                "question": contract.get("question"),
                "volume": contract.get("volume"),
                "yes_price": contract.get("yes_price"),
                "sector": sector_id,
                "classification_rationale": "Classified by hybrid method",
            })
    
    # Generate sector summary
    sector_summary = get_sector_summary(grouped_contracts)
    
    # Build discovery data
    discovery_data = {
        "classified_contracts": contracts,
        "total_contracts": len(contracts),
        "all_contracts": contracts,
        "grouped_contracts": grouped_contracts,
        "sector_summary": sector_summary,
        "market_regime": "Multi-Sector Analysis",
        "summary": f"Classified {len(contracts)} contracts into {len([s for s in grouped_contracts.values() if s])} sectors",
    }
    
    return discovery_data
