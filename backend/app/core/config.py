import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MONGO_URI: str
    MONGO_DB_NAME: str
    LOGGER: int = 20
    MISTRAL_API_KEY: str = "your-key-here"
    MISTRAL_MODEL: str = "mistral-tiny"

    model_config = SettingsConfigDict(
        # Look for .env in the current folder OR the parent folder
        env_file=(".env", "../.env"), 
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()