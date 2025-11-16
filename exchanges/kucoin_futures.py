from typing import Sequence

from .base_exchange import BaseExchange


class KucoinFutures(BaseExchange):
    def __init__(self, symbols: Sequence[str]):
        super().__init__("kucoinfutures", symbols=symbols)