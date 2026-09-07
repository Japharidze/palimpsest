def build_llm(provider: str, model: str, api_key: str | None = None):
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model)
    if provider == "anthropic":
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, api_key=api_key, temperature=0)
    raise ValueError(f"unknown provider {provider!r}")
