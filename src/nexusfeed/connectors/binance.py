import logging
from typing import Callable, Dict, List, Optional


log = logging.getLogger("nexusfeed")


class BinanceOrderBookConnector:
    def __init__(self, snapshot_fetcher: Callable[[str], dict]):
        self.snapshot_fetcher = snapshot_fetcher
        self.state: Dict[str, Dict] = {}

    def _ensure_state(self, symbol: str):
        if symbol not in self.state:
            self.state[symbol] = {
                "last_update_id": None,
                "bids": {},
                "asks": {},
            }

    def fetch_snapshot(self, symbol: str) -> None:
        snap = self.snapshot_fetcher(symbol)
        self._ensure_state(symbol)
        s = self.state[symbol]
        s["last_update_id"] = snap.get("lastUpdateId")
        s["bids"] = {float(p): float(q) for p, q in snap.get("bids", [])}
        s["asks"] = {float(p): float(q) for p, q in snap.get("asks", [])}
        log.info("binance_resync", extra={"symbol": symbol, "sequence": s["last_update_id"]})

    def _apply_levels(self, book: Dict[float, float], levels: List[List[float]]):
        for price, qty in levels:
            price = float(price)
            qty = float(qty)
            if qty == 0.0:
                book.pop(price, None)
            else:
                book[price] = qty

    def process_depth_delta(self, symbol: str, delta: dict) -> bool:
        self._ensure_state(symbol)
        s = self.state[symbol]
        U = delta.get("U")
        u = delta.get("u")
        bids = delta.get("b", [])
        asks = delta.get("a", [])

        if s["last_update_id"] is None:
            self.fetch_snapshot(symbol)
            # ignore any deltas with u <= snapshot
            if u is not None and u <= s["last_update_id"]:
                return False

        last = s["last_update_id"] or 0

        if U is None or u is None:
            log.warning("binance_missing_sequence", extra={"symbol": symbol})
            self.fetch_snapshot(symbol)
            return False

        # normal case: next delta should start at last+1
        if U == last + 1 or (U <= last + 1 <= u):
            self._apply_levels(s["bids"], bids)
            self._apply_levels(s["asks"], asks)
            s["last_update_id"] = u
            return True

        # out-of-order or gap detected -> resync
        log.warning(
            "binance_sequence_gap",
            extra={"symbol": symbol, "last": last, "U": U, "u": u},
        )
        self.fetch_snapshot(symbol)
        return False

    def get_book(self, symbol: str) -> dict:
        self._ensure_state(symbol)
        s = self.state[symbol]
        bids = sorted([[p, q] for p, q in s["bids"].items()], key=lambda x: -x[0])
        asks = sorted([[p, q] for p, q in s["asks"].items()], key=lambda x: x[0])
        return {
            "instrument": symbol,
            "sequence": s["last_update_id"],
            "bids": bids,
            "asks": asks,
        }

__all__ = ["BinanceOrderBookConnector"]