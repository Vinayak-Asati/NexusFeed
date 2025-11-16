from typing import Sequence

from .base_exchange import BaseExchange


class BinanceSpot(BaseExchange):
    def __init__(self, symbols: Sequence[str]):
        super().__init__("binance", symbols=symbols)