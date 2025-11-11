"""Generic wrapper for ccxt exchanges."""

import ccxt
from typing import Dict, Any, Optional, Sequence


class BaseExchange:
    """Base class for exchange connectors using ccxt."""
    
    def __init__(
        self,
        exchange_name: str,
        symbols: Optional[Sequence[str]] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        sandbox: bool = False,
    ):
        """
        Initialize exchange connector.
        
        Args:
            exchange_name: Name of the exchange (e.g., 'binance', 'okx')
            api_key: API key for authenticated requests
            api_secret: API secret for authenticated requests
            sandbox: Whether to use sandbox/testnet mode
        """
        self.exchange_name = exchange_name
        self.symbols = list(symbols) if symbols is not None else []
        self.sandbox = sandbox
        
        # Initialize ccxt exchange
        exchange_class = getattr(ccxt, exchange_name)
        config = {
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': sandbox,
            'enableRateLimit': True,
        }
        self.exchange = exchange_class(config)
    
    def get_markets(self) -> Dict[str, Any]:
        """Fetch available markets."""
        return self.exchange.load_markets()
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch ticker data for a symbol."""
        return self.exchange.fetch_ticker(symbol)
    
    def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """Fetch order book for a symbol."""
        return self.exchange.fetch_order_book(symbol, limit)
    
    def get_trades(self, symbol: str, limit: int = 50) -> list:
        """Fetch recent trades for a symbol."""
        return self.exchange.fetch_trades(symbol, limit=limit)

