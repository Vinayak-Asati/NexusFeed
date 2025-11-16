from typing import Sequence

from .base_exchange import BaseExchange


class KrakenFutures(BaseExchange):
    def __init__(self, symbols: Sequence[str]):
        super().__init__("krakenfutures", symbols=symbols)