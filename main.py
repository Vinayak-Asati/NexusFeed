"""Main entry point for NexusFeed application."""

import argparse
import asyncio
import importlib
import logging
from datetime import datetime, timezone
from typing import Sequence, Optional
from urllib.parse import unquote

import ccxt
from fastapi import FastAPI
import sys
from pathlib import Path

# Ensure src/ is on sys.path for local development
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import Config
from helpers.logger import setup_logger
from helpers.saver import DataSaver, normalize_ticker
from nexusfeed.services.feed_manager import FeedManager
from nexusfeed.storage.repo import Repo
from nexusfeed.services.simulated_connector import SimulatedConnector

app = FastAPI(title="NexusFeed API", version="0.1.0")

# Global state for exchanges and tasks
exchanges_list: list = []
fetch_tasks: list = []
logger_instance: logging.Logger = None
saver_instance: DataSaver = None
feed_manager_instance: FeedManager = None
repo_instance: Repo = None


def initialize() -> logging.Logger:
    """Initializes the application (directories, logger, etc.)."""
    Config.ensure_directories()

    logger = setup_logger(
        name="nexusfeed",
        log_file=None,  # Do not write logs to any file
        level=getattr(logging, Config.LOG_LEVEL),
    )

    logger.info("NexusFeed application starting...")
    logger.info("Data directory: %s", Config.DATA_DIR)
    logger.info("NexusFeed application initialized.")
    return logger


async def fetch_loop(
    exchange,
    saver: DataSaver,
    logger: logging.Logger,
    interval: int = None,
) -> None:
    """Continuously fetch ticker data for all symbols on an exchange."""
    if interval is None:
        interval = Config.REFRESH_INTERVAL
    
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

                # Prepare ticker data with symbol and timestamp
                ticker_data = dict(ticker)
                ticker_data["symbol"] = symbol
                if "timestamp" not in ticker_data and "datetime" not in ticker_data:
                    ticker_data["timestamp"] = datetime.now(timezone.utc).isoformat()
                
                # Normalize ticker data before saving
                normalized_data = normalize_ticker(ticker_data, exchange.exchange_name)
                
                await asyncio.to_thread(
                    saver.save_csv,
                    normalized_data,
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
    """
    Dynamically load and instantiate exchanges from Config.EXCHANGES.
    
    Returns:
        List of exchange instances
    """
    global logger_instance
    exchanges = []
    
    # Use logger if available, otherwise use print for errors
    log_warning = logger_instance.warning if logger_instance else print
    log_exception = logger_instance.exception if logger_instance else print
    
    for exchange_name, symbols in Config.EXCHANGES.items():
        try:
            # Get the class name
            class_name = f"{exchange_name.capitalize()}Exchange"
            
            # Dynamically import the exchange module
            module = importlib.import_module(f"exchanges.{exchange_name}")
            
            # Get the exchange class
            exchange_class = getattr(module, class_name)
            
            # Instantiate the exchange
            exchange = exchange_class(
                symbols=symbols,
                sandbox=Config.SANDBOX_MODE,
                **Config.get_exchange_credentials(exchange_name),
            )
            
            exchanges.append(exchange)
        except ImportError as e:
            log_warning(f"Failed to import exchange '{exchange_name}': {e}")
        except AttributeError as e:
            log_warning(f"Exchange class '{class_name}' not found for '{exchange_name}': {e}")
        except Exception as e:
            log_exception(f"Failed to initialize exchange '{exchange_name}': {e}")
    
    return exchanges


async def fetch_once() -> None:
    """Fetch ticker data once for all symbols on all exchanges and exit."""
    global logger_instance, saver_instance, exchanges_list
    
    logger_instance = initialize()
    saver_instance = DataSaver(base_path=str(Config.RAW_DATA_DIR))
    
    # Clear existing data before starting new session
    deleted_count = saver_instance.clear_data()
    if deleted_count > 0:
        logger_instance.info("Cleared %d existing data files from previous session.", deleted_count)
    
    exchanges_list = get_exchanges()
    
    if not exchanges_list:
        logger_instance.warning("No exchanges configured.")
        return
    
    logger_instance.info("Fetching ticker data once for all symbols...")
    
    # Fetch all symbols from all exchanges concurrently
    tasks = []
    for exchange in exchanges_list:
        if not exchange.symbols:
            logger_instance.warning("Exchange %s has no symbols configured.", exchange.exchange_name)
            continue
        
        for symbol in exchange.symbols:
            async def fetch_single_ticker(exch, sym):
                try:
                    ticker = await asyncio.to_thread(exch.get_ticker, sym)
                    price = ticker.get("last") or ticker.get("close")
                    logger_instance.info(
                        "[%s] %s price: %s",
                        exch.exchange_name.upper(),
                        sym,
                        price,
                    )
                    
                    # Prepare ticker data with symbol and timestamp
                    ticker_data = dict(ticker)
                    ticker_data["symbol"] = sym
                    if "timestamp" not in ticker_data and "datetime" not in ticker_data:
                        ticker_data["timestamp"] = datetime.now(timezone.utc).isoformat()
                    
                    # Normalize ticker data before saving
                    normalized_data = normalize_ticker(ticker_data, exch.exchange_name)
                    
                    await asyncio.to_thread(
                        saver_instance.save_csv,
                        normalized_data,
                        f"{exch.exchange_name}_ticker",
                    )
                except ccxt.NetworkError as exc:
                    logger_instance.warning(
                        "Network error fetching %s on %s: %s",
                        sym,
                        exch.exchange_name,
                        exc,
                    )
                except ccxt.ExchangeError as exc:
                    logger_instance.warning(
                        "Exchange error fetching %s on %s: %s",
                        sym,
                        exch.exchange_name,
                        exc,
                    )
                except Exception as exc:
                    logger_instance.exception(
                        "Unexpected error fetching data for %s on %s: %s",
                        sym,
                        exch.exchange_name,
                        exc,
                    )
            
            tasks.append(asyncio.create_task(fetch_single_ticker(exchange, symbol)))
    
    # Wait for all fetches to complete
    await asyncio.gather(*tasks)
    logger_instance.info("Completed one-time fetch for all symbols.")


async def main(once: bool = False) -> None:
    """
    Run concurrent fetch loops for the configured exchanges.
    
    Args:
        once: If True, fetch each symbol once and exit. If False, run continuously.
    """
    if once:
        await fetch_once()
        return
    
    global logger_instance, saver_instance, exchanges_list, fetch_tasks
    
    logger_instance = initialize()
    saver_instance = DataSaver(base_path=str(Config.RAW_DATA_DIR))
    
    # Clear existing data before starting new session
    deleted_count = saver_instance.clear_data()
    if deleted_count > 0:
        logger_instance.info("Cleared %d existing data files from previous session.", deleted_count)
    
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
    global logger_instance, saver_instance, exchanges_list, repo_instance, feed_manager_instance
    if not logger_instance:
        logger_instance = initialize()
    if not saver_instance:
        saver_instance = DataSaver(base_path=str(Config.RAW_DATA_DIR))
        # Clear existing data before starting new session
        deleted_count = saver_instance.clear_data()
        if deleted_count > 0 and logger_instance:
            logger_instance.info("Cleared %d existing data files from previous session.", deleted_count)
    if not exchanges_list:
        exchanges_list = get_exchanges()
    if not repo_instance:
        repo_instance = Repo()
    if not feed_manager_instance:
        feed_manager_instance = FeedManager(repo_instance)
        for exch in exchanges_list:
            feed_manager_instance.register(exch)
        # Register a simulated connector for quick validation
        feed_manager_instance.register(SimulatedConnector(exchange_name="sim", symbols=["BTC/USDT"]))
        asyncio.create_task(feed_manager_instance.start_all())


@app.on_event("shutdown")
async def shutdown_event():
    global feed_manager_instance
    if feed_manager_instance:
        await feed_manager_instance.stop_all()


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
            # Prepare ticker data with symbol and timestamp
            ticker_data = dict(ticker)
            ticker_data["symbol"] = symbol
            if "timestamp" not in ticker_data and "datetime" not in ticker_data:
                ticker_data["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            # Normalize ticker data before saving
            normalized_data = normalize_ticker(ticker_data, exchange.exchange_name)
            
            await asyncio.to_thread(
                saver_instance.save_json,
                normalized_data,
                f"{exchange.exchange_name}_ticker",
            )
        
        return {
            "exchange": exchange.exchange_name,
            "symbol": symbol,
            "price": price,
            "ticker": ticker,
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
    parser = argparse.ArgumentParser(
        description="NexusFeed: Market Data Aggregator & Normalizer"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Fetch ticker data once for all symbols and exit (useful for debugging)",
    )
    
    args = parser.parse_args()
    
    try:
        asyncio.run(main(once=args.once))
    except KeyboardInterrupt:
        pass