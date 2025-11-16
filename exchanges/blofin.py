from typing import Sequence

from .base_exchange import BaseExchange


class Blofin(BaseExchange):
    def __init__(self, symbols: Sequence[str]):
        super().__init__("blofin", symbols=symbols)