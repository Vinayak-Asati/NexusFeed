from typing import Sequence

from .base_exchange import BaseExchange


class BinanceUsdm(BaseExchange):
    def __init__(self, symbols: Sequence[str]):
        super().__init__("binanceusdm", symbols=symbols)