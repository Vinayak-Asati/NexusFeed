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
    
    # Generic exchange API credentials loader (from environment variables)
    @staticmethod
    def get_exchange_credentials(exchange_name: str) -> dict:
        """
        Get API credentials for a given exchange from environment variables.
        Looks for environment variables in the form:
        - {EXCHANGE_NAME}_API_KEY
        - {EXCHANGE_NAME}_API_SECRET
        """
        env_prefix = exchange_name.upper()
        return {
            "api_key": os.getenv(f"{env_prefix}_API_KEY"),
            "api_secret": os.getenv(f"{env_prefix}_API_SECRET"),
        }
    
    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/nexusfeed.db")
    
    # Redis configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    
    # Application settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    SANDBOX_MODE: bool = os.getenv("SANDBOX_MODE", "False").lower() == "true"
    
    # Refresh interval for fetching ticker data (in seconds)
    REFRESH_INTERVAL: int = int(os.getenv("REFRESH_INTERVAL", "5"))
    
    # Exchange configuration: exchange name -> list of symbols
    ENABLED_EXCHANGES: list = [
        "binance_spot",
        "bybit",
        "deribit",
        # "kraken_spot",
        "kraken_futures",
        # "kucoin_spot",
        # "kucoin_futures",
        # "okx",
        "gateio",
        "gemini",
        # "cryptocom",
        "blofin",
        # "bitfinex",
        "bitget",
        # "bitmex",
        "bitso",
        # "bitstamp",
        "binance_usdm",
        "binance_coinm",
    ]

    EXCHANGES: dict = {
        "binance_spot": ["BTC/USDT", "ETH/USDT"],
        "binance_usdm": ["BTC/USDT", "ETH/USDT"],
        "binance_coinm": ["BTC/USD", "ETH/USD"],
        "bitfinex": ["BTC/USD", "ETH/USD"],
        "bitget": ["BTC/USDT", "ETH/USDT"],
        "bitmex": ["BTC/USD", "ETH/USD"],
        "bitso": ["BTC/USD", "ETH/USD"],
        "bitstamp": ["BTC/USD", "ETH/USD"],
        "blofin": ["BTC/USDT", "ETH/USDT"],
        "bybit": ["BTC/USDT", "ETH/USDT"],
        "cryptocom": ["BTC/USDT", "ETH/USDT"],
        "deribit": ["BTC/USD", "ETH/USD"],
        "gateio": ["BTC/USDT", "ETH/USDT"],
        "gemini": ["BTC/USD", "ETH/USD"],
        "kraken_spot": ["BTC/USD", "ETH/USD"],
        "kraken_futures": ["BTC/USD", "ETH/USD"],
        "kucoin_spot": ["BTC/USDT", "ETH/USDT"],
        "kucoin_futures": ["BTC/USDT", "ETH/USDT"],
        "okx": ["BTC/USDT", "ETH/USDT"],
    }
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist."""
        cls.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

EXCHANGES = Config.EXCHANGES
ENABLED_EXCHANGES = Config.ENABLED_EXCHANGES
REFRESH_INTERVAL = Config.REFRESH_INTERVAL

