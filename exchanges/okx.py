"""OKX exchange connector."""

from typing import Optional, Sequence

from .base_exchange import BaseExchange


class OkxExchange(BaseExchange):
    """OKX exchange connector."""

    def __init__(
        self,
        symbols: Sequence[str],
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        sandbox: bool = False,
    ):
        """Initialize OKX exchange connector."""
        super().__init__(
            "okx",
            symbols=symbols,
            api_key=api_key,
            api_secret=api_secret,
            sandbox=sandbox,
        )

