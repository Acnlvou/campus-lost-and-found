from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CAMPUS_",
        extra="ignore",
    )

    app_name: str = "Campus Lost and Found API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/runtime/campus_lost_and_found.db"
    frontend_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
