import os


def get_llm():
    """Get LLM identifier string for CrewAI agents."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()

    if provider == "ollama":
        model = os.getenv("OLLAMA_MODEL", "llama3")
        return f"ollama/{model}"

    if provider == "qwen":
        api_key = os.getenv("QWEN_API_KEY", "")
        model = os.getenv("QWEN_MODEL", "qwen-plus")
        api_base = os.getenv(
            "QWEN_API_BASE",
            "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
        )
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["OPENAI_API_BASE"] = api_base
        return f"openai/{model}"

    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    return f"openai/{model}"


def get_llm_object():
    """Get actual LangChain LLM object for direct invocation."""
    from langchain_openai import ChatOpenAI
    
    provider = os.getenv("LLM_PROVIDER", "openai").lower()

    if provider == "ollama":
        from langchain_community.llms import Ollama
        return Ollama(
            model=os.getenv("OLLAMA_MODEL", "llama3"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )

    if provider == "qwen":
        api_key = os.getenv("QWEN_API_KEY", "")
        model = os.getenv("QWEN_MODEL", "qwen-plus")
        api_base = os.getenv(
            "QWEN_API_BASE",
            "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
        )
        return ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base=api_base,
            temperature=0.1,
        )

    # Default to OpenAI
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    return ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        temperature=0.1,
    )
