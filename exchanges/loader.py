from typing import Sequence

from .base_exchange import BaseExchange
from .binance_spot import BinanceSpot
from .binance_usdm import BinanceUsdm
from .binance_coinm import BinanceCoinm
from .bitfinex import Bitfinex
from .bitget import Bitget
from .bitmex import Bitmex
from .bitso import Bitso
from .bitstamp import Bitstamp
from .blofin import Blofin
from .bybit import Bybit
from .cryptocom import Cryptocom
from .deribit import Deribit
from .gateio import Gateio
from .gemini import Gemini
from .kraken_spot import KrakenSpot
from .kraken_futures import KrakenFutures
from .kucoin_spot import KucoinSpot
from .kucoin_futures import KucoinFutures
from .okx import Okx


EXCHANGE_CLASS_MAP = {
    "binance_spot": BinanceSpot,
    "binance_usdm": BinanceUsdm,
    "binance_coinm": BinanceCoinm,
    "bitfinex": Bitfinex,
    "bitget": Bitget,
    "bitmex": Bitmex,
    "bitso": Bitso,
    "bitstamp": Bitstamp,
    "blofin": Blofin,
    "bybit": Bybit,
    "cryptocom": Cryptocom,
    "deribit": Deribit,
    "gateio": Gateio,
    "gemini": Gemini,
    "kraken_spot": KrakenSpot,
    "kraken_futures": KrakenFutures,
    "kucoin_spot": KucoinSpot,
    "kucoin_futures": KucoinFutures,
    "okx": Okx,
}


def get_exchange(name: str, symbols: Sequence[str], **kwargs) -> BaseExchange:
    key = name.lower().replace("-", "_")
    cls = EXCHANGE_CLASS_MAP.get(key)
    if not cls:
        raise ValueError(f"Unsupported exchange: {name}")
    return cls(symbols=symbols, **kwargs)