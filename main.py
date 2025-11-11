"""Main entry point for NexusFeed application."""

import asyncio
import logging
from datetime import datetime
from typing import Sequence, Optional
from urllib.parse import unquote

import ccxt
from fastapi import FastAPI

from config import Config
from exchanges import BinanceExchange, DeribitExchange, OKXExchange, BybitExchange
from helpers.logger import setup_logger
from helpers.saver import DataSaver

app = FastAPI(title="NexusFeed API", version="0.1.0")

# Global state for exchanges and tasks
exchanges_list: list = []
fetch_tasks: list = []
logger_instance: logging.Logger = None
saver_instance: DataSaver = None


def initialize() -> logging.Logger:
    """Initializes the application (directories, logger, etc.)."""
    Config.ensure_directories()

    logger = setup_logger(
        name="nexusfeed",
        log_file=Config.LOG_FILE,
        level=getattr(logging, Config.LOG_LEVEL),
    )

    logger.info("NexusFeed application starting...")
    logger.info("Data directory: %s", Config.DATA_DIR)
    logger.info("Logs directory: %s", Config.LOGS_DIR)
    logger.info("NexusFeed application initialized.")
    return logger


async def fetch_loop(
    exchange,
    saver: DataSaver,
    logger: logging.Logger,
    interval: int = 5,
) -> None:
    """Continuously fetch ticker data for all symbols on an exchange."""
    if not exchange.symbols:
        logger.warning("Exchange %s has no symbols configured.", exchange.exchange_name)
        return

    while True:
        for symbol in exchange.symbols:
            try:
                ticker = await asyncio.to_thread(exchange.get_ticker, symbol)
                price = ticker.get("last") or ticker.get("close")
                logger.info(
                    "[%s] %s price: %s",
                    exchange.exchange_name.upper(),
                    symbol,
                    price,
                )

                record = {
                    "timestamp": ticker.get("datetime") or datetime.utcnow().isoformat(),
                    "exchange": exchange.exchange_name,
                    "symbol": symbol,
                    "price": price,
                }
                await asyncio.to_thread(
                    saver.save_csv,
                    record,
                    f"{exchange.exchange_name}_ticker",
                )
            except ccxt.NetworkError as exc:
                logger.warning(
                    "Network error fetching %s on %s: %s. Retrying in 1 second...",
                    symbol,
                    exchange.exchange_name,
                    exc,
                )
                await asyncio.sleep(1)
            except ccxt.ExchangeError as exc:
                logger.warning(
                    "Exchange error fetching %s on %s: %s. Retrying in 1 second...",
                    symbol,
                    exchange.exchange_name,
                    exc,
                )
                await asyncio.sleep(1)
            except Exception as exc:
                logger.exception(
                    "Unexpected error fetching data for %s on %s: %s",
                    symbol,
                    exchange.exchange_name,
                    exc,
                )
        await asyncio.sleep(interval)


def normalize_symbol(symbol: str) -> str:
    """
    Normalize symbol format.
    Converts BTCUSDT -> BTC/USDT, handles URL decoding, etc.
    """
    # URL decode if needed
    symbol = unquote(symbol)
    
    # If symbol doesn't have a slash, try to add one
    # Common patterns: BTCUSDT -> BTC/USDT, BTCUSD -> BTC/USD
    if '/' not in symbol:
        # Try common quote currencies
        quote_currencies = ['USDT', 'USD', 'EUR', 'GBP', 'BTC', 'ETH', 'USDC']
        for quote in quote_currencies:
            if symbol.endswith(quote) and len(symbol) > len(quote):
                base = symbol[:-len(quote)]
                return f"{base}/{quote}"
    
    return symbol


def get_exchanges() -> Sequence:
    """Get configured exchanges."""
    return [
        BinanceExchange(
            symbols=["BTC/USDT", "ETH/USDT"],
            sandbox=Config.SANDBOX_MODE,
            **Config.get_exchange_credentials("binance"),
        ),
        DeribitExchange(
            symbols=["BTC/USDT", "ETH/USDT"],
            sandbox=Config.SANDBOX_MODE,
            **Config.get_exchange_credentials("deribit"),
        ),
        # OKXExchange(
        #     symbols=["BTC/USDT", "ETH/USDT"],
        #     sandbox=Config.SANDBOX_MODE,
        #     **Config.get_exchange_credentials("okx"),
        # ),
        # BybitExchange(
        #     symbols=["BTC/USDT", "ETH/USDT"],
        #     sandbox=Config.SANDBOX_MODE,
        #     **Config.get_exchange_credentials("bybit"),
        # ),
    ]


async def main() -> None:
    """Run concurrent fetch loops for the configured exchanges."""
    global logger_instance, saver_instance, exchanges_list, fetch_tasks
    
    logger_instance = initialize()
    saver_instance = DataSaver(base_path=str(Config.RAW_DATA_DIR))
    exchanges_list = get_exchanges()

    fetch_tasks = [
        asyncio.create_task(fetch_loop(exchange, saver_instance, logger_instance))
        for exchange in exchanges_list
    ]

    try:
        await asyncio.gather(*fetch_tasks)
    except asyncio.CancelledError:
        logger_instance.info("Fetch loops cancelled.")
        raise


@app.on_event("startup")
async def startup_event():
    """Initialize exchanges when FastAPI app starts."""
    global logger_instance, saver_instance, exchanges_list
    if not logger_instance:
        logger_instance = initialize()
    if not saver_instance:
        saver_instance = DataSaver(base_path=str(Config.RAW_DATA_DIR))
    if not exchanges_list:
        exchanges_list = get_exchanges()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "debug": Config.DEBUG,
        "sandbox": Config.SANDBOX_MODE,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {"name": "NexusFeed", "message": "Welcome to NexusFeed API"}


@app.get("/api/exchanges")
async def list_exchanges():
    """List all configured exchanges and their symbols."""
    global exchanges_list
    if not exchanges_list:
        exchanges_list = get_exchanges()
    
    return {
        "exchanges": [
            {
                "name": exchange.exchange_name,
                "symbols": exchange.symbols,
                "sandbox": exchange.sandbox,
            }
            for exchange in exchanges_list
        ]
    }


@app.get("/api/exchanges/status")
async def get_exchanges_status():
    """Get status of all configured exchanges."""
    global exchanges_list
    if not exchanges_list:
        exchanges_list = get_exchanges()
    
    status_list = []
    for exchange in exchanges_list:
        # Try to fetch markets to check if exchange is accessible
        is_accessible = False
        error = None
        try:
            await asyncio.to_thread(exchange.get_markets)
            is_accessible = True
        except Exception as e:
            error = str(e)
        
        status_list.append({
            "name": exchange.exchange_name,
            "symbols": exchange.symbols,
            "symbol_count": len(exchange.symbols),
            "sandbox": exchange.sandbox,
            "accessible": is_accessible,
            "error": error,
        })
    
    return {
        "exchanges": status_list,
        "total_exchanges": len(status_list),
    }


@app.get("/api/exchanges/{exchange_name}/ticker/{symbol:path}")
async def fetch_ticker(exchange_name: str, symbol: str):
    """
    Manually fetch ticker data for a specific exchange and symbol.
    
    Args:
        exchange_name: Name of the exchange (binance, deribit, okx, bybit)
        symbol: Trading pair symbol (e.g., BTC/USDT or BTCUSDT) - can be in path or query parameter
    """
    global exchanges_list, saver_instance
    if not exchanges_list:
        exchanges_list = get_exchanges()
    
    # Find the exchange
    exchange = None
    for exch in exchanges_list:
        if exch.exchange_name.lower() == exchange_name.lower():
            exchange = exch
            break
    
    if not exchange:
        return {
            "error": f"Exchange '{exchange_name}' not found",
            "available_exchanges": [e.exchange_name for e in exchanges_list]
        }
    
    # Normalize the symbol (e.g., BTCUSDT -> BTC/USDT)
    normalized_symbol = normalize_symbol(symbol)
    
    # Try to find matching symbol (try normalized first, then original)
    matched_symbol = None
    if normalized_symbol in exchange.symbols:
        matched_symbol = normalized_symbol
    elif symbol in exchange.symbols:
        matched_symbol = symbol
    else:
        # Try case-insensitive match
        symbol_lower = normalized_symbol.upper()
        for configured_symbol in exchange.symbols:
            if configured_symbol.upper() == symbol_lower:
                matched_symbol = configured_symbol
                break
    
    if not matched_symbol:
        return {
            "error": f"Symbol '{symbol}' (normalized: '{normalized_symbol}') not configured for {exchange_name}",
            "available_symbols": exchange.symbols,
            "received_symbol": symbol,
            "normalized_symbol": normalized_symbol
        }
    
    # Use the matched symbol for the API call
    symbol = matched_symbol
    
    try:
        ticker = await asyncio.to_thread(exchange.get_ticker, symbol)
        price = ticker.get("last") or ticker.get("close")
        
        # Save the data if saver is available
        if saver_instance:
            record = {
                "timestamp": ticker.get("datetime") or datetime.utcnow().isoformat(),
                "exchange": exchange.exchange_name,
                "symbol": symbol,
                "price": price,
            }
            await asyncio.to_thread(
                saver_instance.save_json,
                record,
                f"{exchange.exchange_name}_ticker",
            )
        
        return {
            "exchange": exchange.exchange_name,
            "symbol": symbol,
            "price": price,
            "ticker": ticker,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except ccxt.NetworkError as exc:
        return {
            "error": "Network error",
            "message": str(exc),
            "exchange": exchange_name,
            "symbol": symbol,
        }
    except ccxt.ExchangeError as exc:
        return {
            "error": "Exchange error",
            "message": str(exc),
            "exchange": exchange_name,
            "symbol": symbol,
        }
    except Exception as exc:
        return {
            "error": "Unexpected error",
            "message": str(exc),
            "exchange": exchange_name,
            "symbol": symbol,
        }


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass