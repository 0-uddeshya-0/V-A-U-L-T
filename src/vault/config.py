from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="VAULT_", extra="ignore")

    llm_provider: str = "openai/gpt-4o-mini"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "vault-dev-password"
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "vault-pipeline"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    grounding_min_score: float = 0.75
    comprehension_min_score: float = 0.70
    cors_origins: str = "*"
    instagram_cookies_from_browser: str | None = None


settings = Settings()
