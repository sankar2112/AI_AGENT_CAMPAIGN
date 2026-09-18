from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/bfsi_campaigns"
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "amazon.nova-lite-v1:0"
    bedrock_max_tokens: int = 700
    bedrock_temperature: float = 0.6
    allow_mock_llm: bool = True
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
