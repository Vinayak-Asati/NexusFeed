"""GoMarket API utility for fetching exchange symbols."""

import asyncio
from typing import Optional, List, Dict, Any
import aiohttp

API_URL = "https://gomarket-api.goquant.io"

API_EXCHANGE_INSTRUMENT_MAP: dict = {
    "okx": ["spot", "margin", "swap", "futures", "option"],
    "deribit": ["future", "future_combo", "option", "option_combo", "spot"],
    "bybit": ["spot", "linear", "inverse", "option"],
    "binance": ["spot", "usdm_futures", "coinm_futures", "option"],
    "cryptocom": ["ccy_pair", "perpetual_swap", "future"],
    "kraken": ["spot", "futures"],
    "kucoin": ["spot", "margin", "futures"],
    "bitstamp": ["spot"],
    "bitmex": ["all"],
    "coinbase_intl": ["all"],
    "coinbase": ["spot"],
    "mexc": ["spot", "futures"],
    "gemini": ["all"],
    "htx": ["spot"],
    "bitfinex": ["all"],
    "hyperliquid": ["spot", "perpetual"],
    "blofin": ["all"],
    "gateio": ["spot", "futures"],
    "bitget": ["spot", "futures"],
    "bitso": ["spot"],
}

GOMARKET_API_EXCHANGE_MISSING_INSTRUMENT_MAP: dict = {
    "okx": {
        "perpetual": "swap",
        "linear": "swap",
        "usdm_futures": "swap",
        "all": "swap",
    },
    "bybit": {
        "perpetual": "linear",
        "swap": "linear",
        "usdm_futures": "linear",
        "all": "linear",
    },
    "hyperliquid": {
        "margin": "spot",
        "swap": "perpetual",
        "all": "perpetual",
        "linear": "perpetual",
        "usdm_futures": "perpetual",
    },
    "blofin": {
        "perpetual": "all",
        "swap": "all",
        "spot": "all",
        "linear": "all",
        "usdm_futures": "all",
    },
    "bitmex": {
        "perpetual": "all",
        "swap": "all",
        "spot": "all",
        "linear": "all",
        "usdm_futures": "all",
    },
    "kucoin": {
        "perpetual": "futures",
        "swap": "futures",
        "all": "futures",
        "linear": "futures",
        "usdm_futures": "futures",
    },
    "binance": {
        "perpetual": "usdm_futures",
        "swap": "usdm_futures",
        "spot": "spot",
        "linear": "usdm_futures",
        "all": "usdm_futures",
    },
    "gateio": {
        "perpetual": "futures",
        "swap": "futures",
        "all": "futures",
        "linear": "futures",
        "usdm_futures": "futures",
    },
    "bitget": {
        "perpetual": "futures",
        "swap": "futures",
        "all": "futures",
        "linear": "futures",
        "usdm_futures": "futures",
    },
}

GOMARKET_API_SYMBOL_ROUTES: dict = {
    "kucoinspot": "kucoin",
    "kucoinfutures": "kucoin",
    "kucoinmargin": "kucoin",
    "binancespot": "binance",
    "binance_spot": "binance",
    "binanceoptions": "binance",
    "binancecoinm": "binance",
    "binance_coinm": "binance",
    "binanceusdm": "binance",
    "binance_usdm": "binance",
    "mexcspot": "mexc",
    "mexcfutures": "mexc",
    "krakenspot": "kraken",
    "kraken_spot": "kraken",
    "krakenfutures": "kraken",
    "kraken_futures": "kraken",
    "kucoin_spot": "kucoin",
    "kucoin_futures": "kucoin",
}

BASE_SYM_MAPPING_PREP: dict = {
    "kucoin": {
        "BTC": "XBT",
    },
    "hyperliquid": {
        "XBT": "BTC",
    },
    "binance": {
        "XBT": "BTC",
    },
    "bybit": {
        "XBT": "BTC",
    },
    "blofin": {
        "XBT": "BTC",
    },
    "okx": {
        "XBT": "BTC",
    },
}


def get_instrument_type_for_exchange(
    exchange_name: str,
    instrument_type: str,
) -> Optional[str]:
    """Map instrument type to gomarket API format."""
    target_instrument_type = ""

    if exchange_name in API_EXCHANGE_INSTRUMENT_MAP:
        if instrument_type in API_EXCHANGE_INSTRUMENT_MAP[exchange_name]:
            target_instrument_type = instrument_type
        elif (
            exchange_name in GOMARKET_API_EXCHANGE_MISSING_INSTRUMENT_MAP
            and instrument_type
            in GOMARKET_API_EXCHANGE_MISSING_INSTRUMENT_MAP[exchange_name]
        ):
            target_instrument_type = GOMARKET_API_EXCHANGE_MISSING_INSTRUMENT_MAP[
                exchange_name
            ][instrument_type]

    return target_instrument_type


async def get_symbols_for_exchange(
    exchange_name: str,
    instrument_type: str = "spot",
) -> List[Dict[str, Any]]:
    """
    Fetch all symbols for a given exchange and instrument type from gomarket API.
    
    Args:
        exchange_name: Name of the exchange (e.g., 'binance', 'okx', 'bybit')
        instrument_type: Type of instrument (e.g., 'spot', 'futures', 'swap')
    
    Returns:
        List of symbol dictionaries with 'name', 'base', 'quote' fields
    """
    try:
        final_exchange_name = exchange_name.lower()

        # Map exchange name to gomarket API format
        if exchange_name in GOMARKET_API_SYMBOL_ROUTES:
            final_exchange_name = GOMARKET_API_SYMBOL_ROUTES[exchange_name]

        # Map instrument type to gomarket API format
        mapped_instrument_type = get_instrument_type_for_exchange(
            final_exchange_name, instrument_type
        )
        
        if not mapped_instrument_type:
            # Try default instrument types
            if final_exchange_name in API_EXCHANGE_INSTRUMENT_MAP:
                mapped_instrument_type = API_EXCHANGE_INSTRUMENT_MAP[final_exchange_name][0]
            else:
                mapped_instrument_type = "spot"  # Default fallback

        api_url = (
            f"{API_URL}/api/symbols/{final_exchange_name}/{mapped_instrument_type}"
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                response.raise_for_status()
                data = await response.json()
                symbols = data.get("symbols", [])
                return symbols
    except aiohttp.ClientError as e:
        raise Exception(f"Network error fetching symbols for {exchange_name}: {e}")
    except Exception as e:
        raise Exception(f"Error fetching symbols for {exchange_name} - {instrument_type}: {e}")


async def get_all_instrument_types_for_exchange(
    exchange_name: str,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch all symbols for all instrument types available for an exchange.
    
    Args:
        exchange_name: Name of the exchange
    
    Returns:
        Dictionary mapping instrument_type -> list of symbols
    """
    final_exchange_name = exchange_name.lower()
    
    # Map exchange name to gomarket API format
    if exchange_name in GOMARKET_API_SYMBOL_ROUTES:
        final_exchange_name = GOMARKET_API_SYMBOL_ROUTES[exchange_name]
    
    # Get available instrument types for this exchange
    instrument_types = API_EXCHANGE_INSTRUMENT_MAP.get(
        final_exchange_name, ["spot"]
    )
    
    result = {}
    
    for inst_type in instrument_types:
        try:
            symbols = await get_symbols_for_exchange(exchange_name, inst_type)
            result[inst_type] = symbols
        except Exception as e:
            # If one instrument type fails, continue with others
            result[inst_type] = []
            print(f"Warning: Failed to fetch {inst_type} for {exchange_name}: {e}")
    
    return result


async def get_native_symbol_for_exchange(
    exchange_name: str,
    base_instrument: str,
    quote_instrument: str,
    instrument_type: str,
) -> Optional[str]:
    """
    Get the native symbol name for an exchange given base/quote instruments.
    
    Args:
        exchange_name: Name of the exchange
        base_instrument: Base currency (e.g., 'BTC')
        quote_instrument: Quote currency (e.g., 'USDT')
        instrument_type: Type of instrument (e.g., 'spot')
    
    Returns:
        Native symbol name or None if not found
    """
    try:
        if not instrument_type:
            return None

        final_exchange_name = exchange_name.lower()

        if exchange_name in GOMARKET_API_SYMBOL_ROUTES:
            final_exchange_name = GOMARKET_API_SYMBOL_ROUTES[exchange_name]

        if instrument_type.lower() != "spot":
            if final_exchange_name in BASE_SYM_MAPPING_PREP:
                if base_instrument.upper() in BASE_SYM_MAPPING_PREP[final_exchange_name]:
                    base_instrument = BASE_SYM_MAPPING_PREP[final_exchange_name][
                        base_instrument.upper()
                    ]

        instrument_type = get_instrument_type_for_exchange(
            final_exchange_name, instrument_type
        )

        api_url = (
            f"{API_URL}/api/symbols/{final_exchange_name}/{instrument_type}"
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                response.raise_for_status()
                data = await response.json()
                symbols = data.get("symbols", [])
                base_upper = base_instrument.upper()
                quote_upper = quote_instrument.upper()
                
                for symbol in symbols:
                    if (
                        symbol.get("base", "").upper() == base_upper
                        and symbol.get("quote", "").upper() == quote_upper
                    ):
                        return symbol.get("name")

                # Try USDC if USDT not found
                if quote_instrument.upper() == "USDT":
                    for symbol in symbols:
                        if (
                            symbol.get("base", "").upper() == base_upper
                            and symbol.get("quote", "").upper() == "USDC"
                        ):
                            return symbol.get("name")

                # Try USDT if USDC not found
                if quote_instrument.upper() == "USDC":
                    for symbol in symbols:
                        if (
                            symbol.get("base", "").upper() == base_upper
                            and symbol.get("quote", "").upper() == "USDT"
                        ):
                            return symbol.get("name")

                # Try ETH/UETH mapping
                if base_instrument.upper() == "ETH":
                    for symbol in symbols:
                        if (
                            symbol.get("base", "").upper() == "UETH"
                            and symbol.get("quote", "").upper() == quote_upper
                        ):
                            return symbol.get("name")

                if base_instrument.upper() == "UETH":
                    for symbol in symbols:
                        if (
                            symbol.get("base", "").upper() == "ETH"
                            and symbol.get("quote", "").upper() == quote_upper
                        ):
                            return symbol.get("name")
        return None
    except Exception as e:
        print(f"Error fetching symbols for {exchange_name} - {instrument_type}: {e}")
        return None

