from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]  # если config.py лежит в app/
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    DB_USER: str
    DB_PASS: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    SECRET_KEY: str
    REDIS_URL: str

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def secret_key(self) -> str:
        return self.SECRET_KEY


settings = Settings()
