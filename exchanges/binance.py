"""Binance exchange connector."""

from typing import Optional, Sequence

from .base_exchange import BaseExchange


class Binance(BaseExchange):
    """Binance exchange connector."""

    def __init__(
        self,
        symbols: Sequence[str],
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        sandbox: bool = False,
    ):
        """Initialize Binance exchange connector."""
        super().__init__(
            "binance",
            symbols=symbols,
            api_key=api_key,
            api_secret=api_secret,
            sandbox=sandbox,
        )

