from typing import Sequence

from .base_exchange import BaseExchange


class Bitget(BaseExchange):
    def __init__(self, symbols: Sequence[str]):
        super().__init__("bitget", symbols=symbols)