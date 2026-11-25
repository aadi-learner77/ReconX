from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "ReconX AI"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = "postgresql+psycopg://reconx:reconx_local_dev@localhost:5432/reconx"

    jwt_secret: str = "CHANGE_ME_LOCAL_DEV_SECRET_AT_LEAST_32_CHARS"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    login_rate_limit_max_attempts: int = 10
    login_rate_limit_window_seconds: int = 60

    storage_root: str = "./storage"
    max_upload_size_mb: int = 15

    worker_enabled: bool = True
    worker_poll_interval_seconds: float = 1.0
    job_max_attempts: int = 3

    llm_provider: str = "mock"
    llm_timeout_seconds: int = 20
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    feature_evidence_graph: bool = True
    feature_finance_copilot: bool = True
    feature_anomaly_ml: bool = True
    feature_cash_view: bool = True
    feature_report_exports: bool = True

    seed_org_name: str = "Acme Manufacturing India Pvt Ltd"
    seed_default_password: str = "ReconXDemo#2026!"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
