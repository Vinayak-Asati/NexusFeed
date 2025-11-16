from typing import Sequence

from .base_exchange import BaseExchange


class KrakenSpot(BaseExchange):
    def __init__(self, symbols: Sequence[str]):
        super().__init__("kraken", symbols=symbols)