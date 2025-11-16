from typing import Sequence

from .base_exchange import BaseExchange


class Cryptocom(BaseExchange):
    def __init__(self, symbols: Sequence[str]):
        super().__init__("cryptocom", symbols=symbols)