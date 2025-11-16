from typing import Sequence

from .base_exchange import BaseExchange


class Bitstamp(BaseExchange):
    def __init__(self, symbols: Sequence[str]):
        super().__init__("bitstamp", symbols=symbols)