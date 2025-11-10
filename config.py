"""Configuration settings for NexusFeed."""

import os
from typing import Optional
from pathlib import Path


class Config:
    """Application configuration."""
    
    # Base paths
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"
    RAW_DATA_DIR = DATA_DIR / "raw"
    LOGS_DIR = DATA_DIR / "logs"
    
    # Exchange API credentials (load from environment variables)
    BINANCE_API_KEY: Optional[str] = os.getenv("BINANCE_API_KEY")
    BINANCE_API_SECRET: Optional[str] = os.getenv("BINANCE_API_SECRET")
    
    COINBASE_API_KEY: Optional[str] = os.getenv("COINBASE_API_KEY")
    COINBASE_API_SECRET: Optional[str] = os.getenv("COINBASE_API_SECRET")
    
    KRAKEN_API_KEY: Optional[str] = os.getenv("KRAKEN_API_KEY")
    KRAKEN_API_SECRET: Optional[str] = os.getenv("KRAKEN_API_SECRET")
    
    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/nexusfeed.db")
    
    # Redis configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = str(LOGS_DIR / "nexusfeed.log")
    
    # Application settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    SANDBOX_MODE: bool = os.getenv("SANDBOX_MODE", "False").lower() == "true"
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist."""
        cls.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)

