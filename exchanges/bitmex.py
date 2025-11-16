from typing import Sequence

from .base_exchange import BaseExchange


class Bitmex(BaseExchange):
    def __init__(self, symbols: Sequence[str]):
        super().__init__("bitmex", symbols=symbols)