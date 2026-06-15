from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    APP_NAME: str = "Buyside API"
    APP_ENV: str = "local"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/buyside"
    )
    DATABASE_ECHO: bool = True


settings = Settings()
