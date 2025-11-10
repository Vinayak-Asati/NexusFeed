"""Binance exchange connector."""

from .base_exchange import BaseExchange
from typing import Optional


class BinanceExchange(BaseExchange):
    """Binance exchange connector."""
    
    def __init__(self, api_key: Optional[str] = None, 
                 api_secret: Optional[str] = None, sandbox: bool = False):
        """Initialize Binance exchange connector."""
        super().__init__('binance', api_key, api_secret, sandbox)

