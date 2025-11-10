"""Coinbase exchange connector."""

from .base_exchange import BaseExchange
from typing import Optional


class CoinbaseExchange(BaseExchange):
    """Coinbase exchange connector."""
    
    def __init__(self, api_key: Optional[str] = None, 
                 api_secret: Optional[str] = None, sandbox: bool = False):
        """Initialize Coinbase exchange connector."""
        super().__init__('coinbase', api_key, api_secret, sandbox)

