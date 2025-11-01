from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Directory with capability .txt files
    capabilities_dir: Path = Field(
        default=Path("data/prompts/capabilities"),
        validation_alias="ETQX_CAPABILITIES_DIR",
    )
    # CORS origins (comma-separated). "*" for dev.
    cors_origins: str = Field(default="*", validation_alias="ETQX_CORS_ORIGINS")

    model_config = SettingsConfigDict(env_prefix="ETQX_", extra="ignore")


settings = Settings()

