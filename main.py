"""Main entry point for NexusFeed application."""

import argparse
import asyncio
import importlib
import logging
from datetime import datetime, timezone
from typing import Sequence, Optional
from urllib.parse import unquote

import ccxt
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
import sys
from pathlib import Path
import random

# Ensure src/ is on sys.path for local development
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import Config, EXCHANGES, ENABLED_EXCHANGES, REFRESH_INTERVAL
from helpers.logger import setup_logger
from helpers.saver import DataSaver, normalize_ticker
from helpers.gomarket_api import (
    get_symbols_for_exchange,
    get_all_instrument_types_for_exchange,
    API_EXCHANGE_INSTRUMENT_MAP,
    GOMARKET_API_SYMBOL_ROUTES,
)
from nexusfeed.services.feed_manager import FeedManager
from nexusfeed.storage.repo import Repo
from exchanges.loader import get_exchange
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from nexusfeed.storage.models import OrderbookSnapshot
from nexusfeed.storage.redis_cache import get_snapshot as redis_get_snapshot
from nexusfeed.publisher.websocket_pub import WebSocketPublisher
from fastapi import WebSocket
from nexusfeed.services.replay_service import (
    create_session,
    get_session,
    remove_session,
    stream_replay,
)
from nexusfeed.connectors.binance import BinanceOrderBookConnector
import time
from fastapi import Response
from nexusfeed.utils.metrics import latest_metrics, metrics_content_type

app = FastAPI(title="NexusFeed API", version="0.1.0")

# Mount static files directory (frontend folder)
FRONTEND_DIR = BASE_DIR / "frontend"
FRONTEND_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Global state for exchanges and tasks
exchanges_list: list = []
fetch_tasks: list = []
logger_instance: logging.Logger = None
saver_instance: DataSaver = None
feed_manager_instance: FeedManager = None
repo_instance: Repo = None
publisher_instance: WebSocketPublisher = None
binance_obc: BinanceOrderBookConnector = None


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
        interval = REFRESH_INTERVAL
    
    if not exchange.symbols:
        logger.warning("Exchange %s has no symbols configured.", exchange.exchange_name)
        return

    failure_counts = {}
    backoffs = {}
    async def _apply_backoff(key: tuple, base_rand: bool = False) -> float:
        prev = backoffs.get(key, 0.0)
        base = random.uniform(3.0, 10.0) if base_rand else 3.0
        nxt = base if prev == 0 else min(prev * 2, 60.0)
        backoffs[key] = nxt
        return nxt
    async def _reset(key: tuple):
        if failure_counts.get(key):
            failure_counts[key] = 0
            backoffs[key] = 0.0
    async def _inc_fail(key: tuple) -> int:
        cnt = failure_counts.get(key, 0) + 1
        failure_counts[key] = cnt
        return cnt
    async def _fetch_ticker(symbol: str):
        key = ("ticker", symbol)
        try:
            ticker = await asyncio.to_thread(exchange.get_ticker, symbol)
            price = ticker.get("last") or ticker.get("close")
            logger.info(
                "[%s] %s price: %s",
                exchange.exchange_name.upper(),
                symbol,
                price,
            )
            ticker_data = dict(ticker)
            ticker_data["symbol"] = symbol
            if "timestamp" not in ticker_data and "datetime" not in ticker_data:
                ticker_data["timestamp"] = datetime.now(timezone.utc).isoformat()
            normalized_data = normalize_ticker(ticker_data, exchange.exchange_name)
            await asyncio.to_thread(
                saver.save_csv,
                normalized_data,
                f"{exchange.exchange_name}_ticker",
            )
            await _reset(key)
        except (ccxt.RateLimitExceeded, ccxt.DDoSProtection, ccxt.ExchangeNotAvailable) as exc:
            cnt = await _inc_fail(key)
            msg = "%s fetching %s on %s: %s" % (
                exc.__class__.__name__,
                symbol,
                exchange.exchange_name,
                str(exc),
            )
            if cnt == 1:
                logger.warning(msg)
            else:
                logger.error(msg)
            await asyncio.sleep(await _apply_backoff(key, base_rand=True))
        except ccxt.NetworkError as exc:
            cnt = await _inc_fail(key)
            msg = "NetworkError fetching %s on %s: %s" % (
                symbol,
                exchange.exchange_name,
                str(exc),
            )
            if cnt == 1:
                logger.warning(msg)
            else:
                logger.error(msg)
            await asyncio.sleep(await _apply_backoff(key))
        except ccxt.ExchangeError as exc:
            cnt = await _inc_fail(key)
            msg = "ExchangeError fetching %s on %s: %s" % (
                symbol,
                exchange.exchange_name,
                str(exc),
            )
            if cnt == 1:
                logger.warning(msg)
            else:
                logger.error(msg)
            await asyncio.sleep(await _apply_backoff(key))
        except Exception as exc:
            cnt = await _inc_fail(key)
            msg = "Unexpected error fetching %s on %s: %s" % (
                symbol,
                exchange.exchange_name,
                str(exc),
            )
            if cnt == 1:
                logger.warning(msg)
            else:
                logger.error(msg)
            await asyncio.sleep(await _apply_backoff(key))
    async def _fetch_book(symbol: str):
        key = ("book", symbol)
        try:
            _ = await asyncio.to_thread(exchange.get_orderbook, symbol)
            await _reset(key)
        except (ccxt.RateLimitExceeded, ccxt.DDoSProtection, ccxt.ExchangeNotAvailable) as exc:
            cnt = await _inc_fail(key)
            msg = "%s fetching book %s on %s: %s" % (
                exc.__class__.__name__,
                symbol,
                exchange.exchange_name,
                str(exc),
            )
            if cnt == 1:
                logger.warning(msg)
            else:
                logger.error(msg)
            await asyncio.sleep(await _apply_backoff(key, base_rand=True))
        except ccxt.NetworkError as exc:
            cnt = await _inc_fail(key)
            msg = "NetworkError fetching book %s on %s: %s" % (
                symbol,
                exchange.exchange_name,
                str(exc),
            )
            if cnt == 1:
                logger.warning(msg)
            else:
                logger.error(msg)
            await asyncio.sleep(await _apply_backoff(key))
        except ccxt.ExchangeError as exc:
            cnt = await _inc_fail(key)
            msg = "ExchangeError fetching book %s on %s: %s" % (
                symbol,
                exchange.exchange_name,
                str(exc),
            )
            if cnt == 1:
                logger.warning(msg)
            else:
                logger.error(msg)
            await asyncio.sleep(await _apply_backoff(key))
        except Exception as exc:
            cnt = await _inc_fail(key)
            msg = "Unexpected error fetching book %s on %s: %s" % (
                symbol,
                exchange.exchange_name,
                str(exc),
            )
            if cnt == 1:
                logger.warning(msg)
            else:
                logger.error(msg)
            await asyncio.sleep(await _apply_backoff(key))
    async def _fetch_trades(symbol: str):
        key = ("trades", symbol)
        try:
            _ = await asyncio.to_thread(exchange.get_trades, symbol)
            await _reset(key)
        except (ccxt.RateLimitExceeded, ccxt.DDoSProtection, ccxt.ExchangeNotAvailable) as exc:
            cnt = await _inc_fail(key)
            msg = "%s fetching trades %s on %s: %s" % (
                exc.__class__.__name__,
                symbol,
                exchange.exchange_name,
                str(exc),
            )
            if cnt == 1:
                logger.warning(msg)
            else:
                logger.error(msg)
            await asyncio.sleep(await _apply_backoff(key, base_rand=True))
        except ccxt.NetworkError as exc:
            cnt = await _inc_fail(key)
            msg = "NetworkError fetching trades %s on %s: %s" % (
                symbol,
                exchange.exchange_name,
                str(exc),
            )
            if cnt == 1:
                logger.warning(msg)
            else:
                logger.error(msg)
            await asyncio.sleep(await _apply_backoff(key))
        except ccxt.ExchangeError as exc:
            cnt = await _inc_fail(key)
            msg = "ExchangeError fetching trades %s on %s: %s" % (
                symbol,
                exchange.exchange_name,
                str(exc),
            )
            if cnt == 1:
                logger.warning(msg)
            else:
                logger.error(msg)
            await asyncio.sleep(await _apply_backoff(key))
        except Exception as exc:
            cnt = await _inc_fail(key)
            msg = "Unexpected error fetching trades %s on %s: %s" % (
                symbol,
                exchange.exchange_name,
                str(exc),
            )
            if cnt == 1:
                logger.warning(msg)
            else:
                logger.error(msg)
            await asyncio.sleep(await _apply_backoff(key))
    while True:
        tasks = []
        for symbol in exchange.symbols:
            tasks.append(asyncio.create_task(_fetch_ticker(symbol)))
            tasks.append(asyncio.create_task(_fetch_book(symbol)))
            tasks.append(asyncio.create_task(_fetch_trades(symbol)))
        if tasks:
            try:
                await asyncio.gather(*tasks)
            except Exception:
                pass
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
    global logger_instance
    exchanges = []
    log_warning = logger_instance.warning if logger_instance else print
    log_exception = logger_instance.exception if logger_instance else print
    enabled = list(ENABLED_EXCHANGES) if ENABLED_EXCHANGES else []
    for exchange_name in enabled:
        try:
            ex = get_exchange(
                exchange_name,
                [],
                sandbox=Config.SANDBOX_MODE,
                **Config.get_exchange_credentials(exchange_name),
            )
            markets = ex.get_markets()
            all_symbols = [s for s in markets.keys() if "/" in s]
            if not all_symbols:
                continue
            k = min(3, len(all_symbols))
            selected = random.sample(all_symbols, k)
            ex.symbols = selected
            exchanges.append(ex)
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
    global logger_instance, saver_instance, exchanges_list, repo_instance, feed_manager_instance, publisher_instance, binance_obc
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
    if not publisher_instance:
        publisher_instance = WebSocketPublisher()
        await publisher_instance.start()
    if not feed_manager_instance:
        feed_manager_instance = FeedManager(repo_instance, publisher=publisher_instance)
        for exch in exchanges_list:
            feed_manager_instance.register(exch)
        asyncio.create_task(feed_manager_instance.start_all())
    # Initialize Binance order book connector using ccxt snapshot fetcher
    if not binance_obc:
        bin_ex = next((e for e in exchanges_list if getattr(e, "exchange_name", "").lower() == "binance"), None)
        def snapshot_fetcher(symbol: str):
            ob = bin_ex.get_orderbook(symbol, limit=50) if bin_ex else {"bids": [], "asks": []}
            return {
                "lastUpdateId": int(time.time() * 1000),
                "bids": ob.get("bids", []),
                "asks": ob.get("asks", []),
            }
        binance_obc = BinanceOrderBookConnector(snapshot_fetcher=snapshot_fetcher)


@app.on_event("shutdown")
async def shutdown_event():
    global feed_manager_instance
    if feed_manager_instance:
        await feed_manager_instance.stop_all()
    if publisher_instance:
        await publisher_instance.stop()


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
    """Root endpoint - redirects to web interface."""
    from fastapi.responses import FileResponse
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"name": "NexusFeed", "message": "Welcome to NexusFeed API", "docs": "/docs"}


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


@app.get("/api/v1/exchanges/configured")
async def list_configured_exchanges():
    """
    List only exchanges that are configured in the project (from exchanges folder).
    Returns only exchanges that have integration files.
    """
    try:
        from exchanges.loader import EXCHANGE_CLASS_MAP
        
        # Get only configured exchanges from EXCHANGE_CLASS_MAP
        configured_exchanges = sorted(list(EXCHANGE_CLASS_MAP.keys()))
        
        return {
            "total_exchanges": len(configured_exchanges),
            "exchanges": configured_exchanges,
            "message": "These are the exchanges with integration in this project"
        }
    except Exception as e:
        return {
            "error": "Failed to list configured exchanges",
            "message": str(e)
        }


@app.get("/api/v1/exchanges/available")
async def list_available_exchanges():
    """
    List all available exchanges from CCXT.
    Returns a list of exchange names that can be used with NexusFeed.
    """
    try:
        # Get all exchange names from CCXT
        all_exchanges = ccxt.exchanges
        
        # Get exchanges that are configured in the system
        configured_exchanges = list(EXCHANGES.keys())
        
        # Get exchanges that are supported by gomarket API
        gomarket_exchanges = list(API_EXCHANGE_INSTRUMENT_MAP.keys())
        gomarket_exchanges.extend(GOMARKET_API_SYMBOL_ROUTES.keys())
        
        return {
            "total_exchanges": len(all_exchanges),
            "available_exchanges": sorted(all_exchanges),
            "configured_exchanges": configured_exchanges,
            "gomarket_supported": sorted(set(gomarket_exchanges)),
            "message": "Use /api/v1/exchanges/{exchange_name}/symbols to get symbols for an exchange"
        }
    except Exception as e:
        return {
            "error": "Failed to list exchanges",
            "message": str(e)
        }


@app.get("/api/v1/exchanges/{exchange_name}/instrument-types")
async def get_exchange_instrument_types(exchange_name: str):
    """
    Get available instrument types for a specific exchange.
    
    Args:
        exchange_name: Name of the exchange (e.g., 'binance', 'binance_spot', 'binance_usdm')
    
    Returns:
        List of available instrument types for this exchange
    """
    try:
        final_exchange_name = exchange_name.lower()
        
        # Handle exchange name variations (e.g., binance_spot -> binance)
        # Map exchange name to gomarket API format
        if exchange_name in GOMARKET_API_SYMBOL_ROUTES:
            final_exchange_name = GOMARKET_API_SYMBOL_ROUTES[exchange_name]
        elif "_" in final_exchange_name:
            # Try to extract base exchange name (e.g., binance_spot -> binance)
            base_name = final_exchange_name.split("_")[0]
            if base_name in API_EXCHANGE_INSTRUMENT_MAP:
                final_exchange_name = base_name
        
        # Get available instrument types for this exchange
        instrument_types = API_EXCHANGE_INSTRUMENT_MAP.get(
            final_exchange_name, ["spot"]
        )
        
        # If exchange name has a specific type (e.g., binance_spot), filter to that type
        if "_" in exchange_name.lower():
            parts = exchange_name.lower().split("_")
            if len(parts) > 1:
                specific_type = parts[1]
                # Map common variations
                type_mapping = {
                    "spot": "spot",
                    "usdm": "usdm_futures",
                    "coinm": "coinm_futures",
                    "futures": "futures",
                    "margin": "margin",
                }
                mapped_type = type_mapping.get(specific_type, specific_type)
                if mapped_type in instrument_types:
                    instrument_types = [mapped_type]
        
        # Create user-friendly labels
        type_labels = {
            "spot": "Spot",
            "futures": "Futures",
            "future": "Futures",
            "swap": "Perpetual Swap",
            "perpetual": "Perpetual",
            "linear": "Linear Futures",
            "inverse": "Inverse Futures",
            "margin": "Margin",
            "option": "Options",
            "option_combo": "Option Combo",
            "future_combo": "Future Combo",
            "usdm_futures": "USD-M Futures",
            "coinm_futures": "Coin-M Futures",
            "ccy_pair": "Currency Pair",
            "perpetual_swap": "Perpetual Swap",
            "all": "All Types"
        }
        
        return {
            "exchange": exchange_name,
            "instrument_types": [
                {
                    "value": inst_type,
                    "label": type_labels.get(inst_type, inst_type.replace("_", " ").title())
                }
                for inst_type in instrument_types
            ]
        }
    except Exception as e:
        return {
            "error": f"Failed to fetch instrument types for {exchange_name}",
            "message": str(e),
            "exchange": exchange_name
        }


@app.get("/api/v1/exchanges/{exchange_name}/symbols")
async def get_exchange_symbols(
    exchange_name: str,
    instrument_type: Optional[str] = Query("spot", description="Type of instrument (spot, futures, swap, etc.)"),
    all_types: bool = Query(False, description="If true, return symbols for all instrument types")
):
    """
    Get all symbols for a specific exchange using the gomarket API.
    
    Args:
        exchange_name: Name of the exchange (e.g., 'binance', 'okx', 'bybit')
        instrument_type: Type of instrument (e.g., 'spot', 'futures', 'swap'). Default: 'spot'
        all_types: If True, return symbols for all instrument types. Default: False
    
    Returns:
        List of symbols with their details (name, base, quote, etc.)
    """
    try:
        if all_types:
            # Get symbols for all instrument types
            result = await get_all_instrument_types_for_exchange(exchange_name)
            total_symbols = sum(len(symbols) for symbols in result.values())
            return {
                "exchange": exchange_name,
                "total_symbols": total_symbols,
                "instrument_types": {
                    inst_type: {
                        "count": len(symbols),
                        "symbols": symbols
                    }
                    for inst_type, symbols in result.items()
                }
            }
        else:
            # Get symbols for specific instrument type
            symbols = await get_symbols_for_exchange(exchange_name, instrument_type)
            return {
                "exchange": exchange_name,
                "instrument_type": instrument_type,
                "total_symbols": len(symbols),
                "symbols": symbols
            }
    except Exception as e:
        return {
            "error": f"Failed to fetch symbols for {exchange_name}",
            "message": str(e),
            "exchange": exchange_name,
            "instrument_type": instrument_type
        }


@app.get("/api/v1/exchanges/{exchange_name}/symbols/ccxt")
async def get_exchange_symbols_ccxt(exchange_name: str):
    """
    Get all symbols for a specific exchange using CCXT directly.
    This is an alternative to the gomarket API endpoint.
    
    Args:
        exchange_name: Name of the exchange (e.g., 'binance', 'okx', 'bybit')
    
    Returns:
        List of all available symbols from CCXT for this exchange
    """
    try:
        # Try to initialize the exchange
        exchange = get_exchange(
            exchange_name,
            [],
            sandbox=Config.SANDBOX_MODE,
            **Config.get_exchange_credentials(exchange_name),
        )
        
        # Load markets
        markets = await asyncio.to_thread(exchange.get_markets)
        
        # Extract symbols
        symbols = [symbol for symbol in markets.keys() if "/" in symbol]
        
        # Get market details
        market_details = []
        for symbol in symbols:
            market = markets.get(symbol, {})
            market_details.append({
                "symbol": symbol,
                "base": market.get("base"),
                "quote": market.get("quote"),
                "active": market.get("active", True),
                "type": market.get("type", "spot"),
                "spot": market.get("spot", False),
                "margin": market.get("margin", False),
                "swap": market.get("swap", False),
                "future": market.get("future", False),
                "option": market.get("option", False),
            })
        
        return {
            "exchange": exchange_name,
            "total_symbols": len(symbols),
            "symbols": sorted(symbols),
            "market_details": market_details
        }
    except ValueError as e:
        return {
            "error": f"Exchange '{exchange_name}' not supported",
            "message": str(e),
            "available_exchanges": list(EXCHANGES.keys())
        }
    except Exception as e:
        return {
            "error": f"Failed to fetch symbols for {exchange_name}",
            "message": str(e),
            "exchange": exchange_name
        }


@app.get("/api/v1/exchanges/{exchange_name}/market-data/{symbol:path}")
async def get_market_data(exchange_name: str, symbol: str):
    """
    Get comprehensive market data for a specific exchange and symbol.
    Returns ticker, orderbook, recent trades, and market information.
    
    Args:
        exchange_name: Name of the exchange (e.g., 'binance', 'okx', 'bybit')
        symbol: Trading pair symbol (e.g., BTC/USDT or BTCUSDT)
    
    Returns:
        Complete market data including ticker, orderbook, trades, and market info
    """
    try:
        # Initialize the exchange
        exchange = get_exchange(
            exchange_name,
            [],
            sandbox=Config.SANDBOX_MODE,
            **Config.get_exchange_credentials(exchange_name),
        )
        
        # Normalize the symbol
        normalized_symbol = normalize_symbol(symbol)
        
        # Load markets to get market info
        markets = await asyncio.to_thread(exchange.get_markets)
        market_info = markets.get(normalized_symbol, {})
        
        # Fetch all market data concurrently
        ticker_task = asyncio.to_thread(exchange.get_ticker, normalized_symbol)
        orderbook_task = asyncio.to_thread(exchange.get_orderbook, normalized_symbol, 20)
        trades_task = asyncio.to_thread(exchange.get_trades, normalized_symbol, 20)
        
        ticker, orderbook, trades = await asyncio.gather(
            ticker_task,
            orderbook_task,
            trades_task,
            return_exceptions=True
        )
        
        # Handle errors for each data type
        ticker_data = ticker if not isinstance(ticker, Exception) else None
        orderbook_data = orderbook if not isinstance(orderbook, Exception) else None
        trades_data = trades if not isinstance(trades, Exception) else None
        
        # Prepare response
        response = {
            "exchange": exchange_name,
            "symbol": normalized_symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "market_info": {
                "base": market_info.get("base"),
                "quote": market_info.get("quote"),
                "active": market_info.get("active", True),
                "type": market_info.get("type", "spot"),
                "spot": market_info.get("spot", False),
                "margin": market_info.get("margin", False),
                "swap": market_info.get("swap", False),
                "future": market_info.get("future", False),
                "option": market_info.get("option", False),
                "precision": {
                    "amount": market_info.get("precision", {}).get("amount"),
                    "price": market_info.get("precision", {}).get("price"),
                },
                "limits": {
                    "amount": market_info.get("limits", {}).get("amount", {}),
                    "price": market_info.get("limits", {}).get("price", {}),
                    "cost": market_info.get("limits", {}).get("cost", {}),
                },
            },
            "ticker": None,
            "orderbook": None,
            "trades": None,
            "errors": {}
        }
        
        # Add ticker data
        if ticker_data:
            response["ticker"] = {
                "symbol": ticker_data.get("symbol"),
                "last": ticker_data.get("last"),
                "bid": ticker_data.get("bid"),
                "ask": ticker_data.get("ask"),
                "high": ticker_data.get("high"),
                "low": ticker_data.get("low"),
                "open": ticker_data.get("open"),
                "close": ticker_data.get("close"),
                "volume": ticker_data.get("volume"),
                "quoteVolume": ticker_data.get("quoteVolume"),
                "change": ticker_data.get("change"),
                "percentage": ticker_data.get("percentage"),
                "vwap": ticker_data.get("vwap"),
                "timestamp": ticker_data.get("timestamp"),
                "datetime": ticker_data.get("datetime"),
            }
        else:
            response["errors"]["ticker"] = str(ticker) if isinstance(ticker, Exception) else "Failed to fetch"
        
        # Add orderbook data
        if orderbook_data:
            response["orderbook"] = {
                "symbol": orderbook_data.get("symbol"),
                "bids": orderbook_data.get("bids", [])[:10],  # Top 10 bids
                "asks": orderbook_data.get("asks", [])[:10],  # Top 10 asks
                "timestamp": orderbook_data.get("timestamp"),
                "datetime": orderbook_data.get("datetime"),
                "nonce": orderbook_data.get("nonce"),
            }
        else:
            response["errors"]["orderbook"] = str(orderbook) if isinstance(orderbook, Exception) else "Failed to fetch"
        
        # Add trades data
        if trades_data:
            response["trades"] = [
                {
                    "id": trade.get("id"),
                    "timestamp": trade.get("timestamp"),
                    "datetime": trade.get("datetime"),
                    "symbol": trade.get("symbol"),
                    "type": trade.get("type"),
                    "side": trade.get("side"),
                    "price": trade.get("price"),
                    "amount": trade.get("amount"),
                    "cost": trade.get("cost"),
                }
                for trade in (trades_data[:20] if isinstance(trades_data, list) else [])
            ]
        else:
            response["errors"]["trades"] = str(trades) if isinstance(trades, Exception) else "Failed to fetch"
        
        return response
        
    except ValueError as e:
        return {
            "error": f"Exchange '{exchange_name}' not supported",
            "message": str(e),
            "available_exchanges": list(EXCHANGES.keys())
        }
    except Exception as e:
        return {
            "error": f"Failed to fetch market data for {exchange_name}/{symbol}",
            "message": str(e),
            "exchange": exchange_name,
            "symbol": symbol
        }


@app.get("/api/v1/book")
async def get_book(instrument: str):
    snap = await redis_get_snapshot(instrument)
    if snap:
        return snap
    async with AsyncSession(repo_instance.engine) as session:
        res = await session.exec(
            select(OrderbookSnapshot).where(OrderbookSnapshot.instrument == instrument)
        )
        obj = res.first()
        if obj:
            return {
                "source": obj.source,
                "instrument": obj.instrument,
                "sequence": obj.sequence,
                "bids": obj.bids,
                "asks": obj.asks,
                "timestamp": obj.ts.isoformat(),
            }
    return {"error": "snapshot_not_found", "instrument": instrument}


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
@app.websocket("/ws/feeds")
async def ws_feeds(ws: WebSocket):
    await ws.accept()
    await publisher_instance.register(ws)
    try:
        while True:
            msg = await ws.receive_json()
            act = msg.get("action")
            instr = msg.get("instrument")
            if act == "subscribe" and instr:
                await publisher_instance.subscribe(ws, instr)
            elif act == "unsubscribe" and instr:
                await publisher_instance.unsubscribe(ws, instr)
    except Exception:
        pass
    finally:
        await publisher_instance.unregister(ws)


@app.post("/api/v1/binance/depth")
async def post_binance_depth(payload: dict):
    symbol = payload.get("instrument") or payload.get("symbol")
    delta = {
        "U": payload.get("U"),
        "u": payload.get("u"),
        "b": payload.get("b", []),
        "a": payload.get("a", []),
    }
    applied = binance_obc.process_depth_delta(symbol, delta)
    book = binance_obc.get_book(symbol)
    # persist and publish
    await feed_manager_instance.ingest_book({
        "symbol": symbol,
        "nonce": book.get("sequence"),
        "bids": book.get("bids"),
        "asks": book.get("asks"),
        "timestamp": int(time.time() * 1000),
    }, source="binance")
    return {"applied": applied, "sequence": book.get("sequence")}


@app.get("/api/v1/binance/book")
async def get_binance_book(instrument: str):
    return binance_obc.get_book(instrument)


@app.post("/api/v1/replay")
async def start_replay(payload: dict):
    instrument = payload.get("instrument")
    from_ts = payload.get("from_ts")
    to_ts = payload.get("to_ts")
    speed = float(payload.get("speed", 1.0))
    sid = create_session(instrument, from_ts, to_ts, speed)
    return {"session_id": sid, "ws_url": f"/ws/replay/{sid}"}


@app.websocket("/ws/replay/{sid}")
async def ws_replay(ws: WebSocket, sid: str):
    await ws.accept()
    sess = get_session(sid)
    if not sess:
        await ws.send_json({"error": "invalid_session"})
        await ws.close()
        return
    try:
        async with AsyncSession(repo_instance.engine) as dbs:
            await stream_replay(
                dbs,
                ws,
                sess["instrument"],
                sess["from_ts"],
                sess["to_ts"],
                sess["speed"],
            )
    except Exception as e:
        try:
            await ws.send_json({"error": str(e)})
        except Exception:
            pass
    finally:
        remove_session(sid)


@app.get("/metrics")
async def metrics():
    data = latest_metrics()
    return Response(content=data, media_type=metrics_content_type())