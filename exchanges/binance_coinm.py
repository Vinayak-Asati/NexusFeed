from typing import Sequence

from .base_exchange import BaseExchange


class BinanceCoinm(BaseExchange):
    def __init__(self, symbols: Sequence[str]):
        super().__init__("binancecoinm", symbols=symbols)