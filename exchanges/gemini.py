from typing import Sequence

from .base_exchange import BaseExchange


class Gemini(BaseExchange):
    def __init__(self, symbols: Sequence[str]):
        super().__init__("gemini", symbols=symbols)