import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Storage mode: "mongodb" or "local"
    STORAGE_MODE: str = "local"
    
    # MongoDB Configuration (only needed if STORAGE_MODE=mongodb)
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "travel_agent_db"
    
    LOGGER: int = 20
    
    # LLM Provider Selection
    LLM_PROVIDER: str = "mistral"  # Options: mistral, openai, anthropic, groq
    
    # Mistral Configuration
    MISTRAL_API_KEY: str = "your-key-here"
    MISTRAL_MODEL: str = "mistral-tiny"
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = "your-key-here"
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    
    # Anthropic Configuration
    ANTHROPIC_API_KEY: str = "your-key-here"
    ANTHROPIC_MODEL: str = "claude-3-haiku-20240307"
    
    # Groq Configuration
    GROQ_API_KEY: str = "your-key-here"
    GROQ_MODEL: str = "llama3-8b-8192"

    model_config = SettingsConfigDict(
        # Look for .env in the current folder OR the parent folder
        env_file=(".env", "../.env"), 
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()