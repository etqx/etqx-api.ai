from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Directory with capability .txt files
    capabilities_dir: Path = Field(
        default=Path("data/prompts/capabilities"),
        validation_alias="ETQX_CAPABILITIES_DIR",
    )
    # Directory with protocol .txt files
    protocols_dir: Path = Field(
        default=Path("data/prompts/protocols"),
        validation_alias="ETQX_PROTOCOLS_DIR",
    )
    # CORS origins (comma-separated). "*" for dev.
    cors_origins: str = Field(default="*", validation_alias="ETQX_CORS_ORIGINS")

    # Public base URL for constructing results links
    public_base: str = Field(default="http://localhost:8000", validation_alias="ETQX_PUBLIC_BASE")

    # Default payoff parameters (R, P, T, S)
    payoff_r: float = Field(default=3.0, validation_alias="ETQX_PAYOFF_R")
    payoff_p: float = Field(default=1.0, validation_alias="ETQX_PAYOFF_P")
    payoff_t: float = Field(default=5.0, validation_alias="ETQX_PAYOFF_T")
    payoff_s: float = Field(default=0.0, validation_alias="ETQX_PAYOFF_S")

    model_config = SettingsConfigDict(env_prefix="ETQX_", extra="ignore")


settings = Settings()
