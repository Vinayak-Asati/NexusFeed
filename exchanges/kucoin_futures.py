from typing import Optional, Sequence

from .base_exchange import BaseExchange


class KucoinFutures(BaseExchange):
    def __init__(
        self,
        symbols: Sequence[str],
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        sandbox: bool = False,
    ):
        super().__init__(
            "kucoinfutures",
            symbols=symbols,
            api_key=api_key,
            api_secret=api_secret,
            sandbox=sandbox,
        )

