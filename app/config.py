from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str
    model_name: str = "claude-haiku-4-5-20251001"
    chroma_path: str = "./chroma_db"
    scraper_headless: bool = True
    scraper_timeout: int = 30
    max_reviews_per_product: int = 50


settings = Settings()
