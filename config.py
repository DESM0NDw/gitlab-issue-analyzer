from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gitlab_url: str = "https://gitlab.com"
    gitlab_token: str
    gitlab_project_id: str  # comma-separated for multiple projects

    @property
    def project_ids(self) -> list[str]:
        return [x.strip() for x in self.gitlab_project_id.split(",") if x.strip()]

    llm_provider: str = "groq"
    groq_api_key: str = ""
    openai_api_key: str = ""
    mistral_api_key: str = ""

    max_issues: int = 100
    closed_issues_days: int = 90
    api_rate_limit: float = 0.5  # Sekunden zwischen API-Calls

    duplicate_high_threshold: float = 0.90
    duplicate_medium_threshold: float = 0.75

    business_context: str = ""
    cache_path: str = "/data/embeddings.pkl"

    class Config:
        env_file = ".env"


settings = Settings()

LLM_CONFIG = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-8b-instant",
        "api_key_field": "groq_api_key",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "api_key_field": "openai_api_key",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "model": "mistral-small-latest",
        "api_key_field": "mistral_api_key",
    },
}
