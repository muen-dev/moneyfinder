import os

# Never load real keys from .env.local or touch AWS during tests.
os.environ["COMPANY_ENV_FILE"] = "/nonexistent/.env.local"
os.environ["COMPANY_RESEARCH_LLM"] = "0"
for name in ("TAVILY_API_KEY", "FIRECRAWL_API_KEY", "NIMBLE_API_KEY"):
    os.environ.pop(name, None)
