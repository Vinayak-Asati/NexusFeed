from typing import Sequence

from .base_exchange import BaseExchange


class KucoinSpot(BaseExchange):
    def __init__(self, symbols: Sequence[str]):
        super().__init__("kucoin", symbols=symbols)