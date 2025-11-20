from datetime import datetime, timezone


def _iso(dt):
    if isinstance(dt, (int, float)):
        return datetime.fromtimestamp(dt / 1000 if dt > 1e12 else dt, tz=timezone.utc).isoformat()
    if isinstance(dt, str):
        try:
            # assume already iso or parseable
            return datetime.fromisoformat(dt.replace("Z", "+00:00")).isoformat()
        except Exception:
            return dt
    if isinstance(dt, datetime):
        return dt.astimezone(timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def normalize_trade(raw: dict, source: str) -> dict:
    symbol = raw.get("symbol") or raw.get("instrument") or raw.get("pair")
    trade_id = raw.get("id") or raw.get("trade_id") or raw.get("tid")
    price = raw.get("price")
    size = raw.get("amount") or raw.get("qty") or raw.get("size")
    side = raw.get("side")
    ts = raw.get("timestamp") or raw.get("datetime")

    if isinstance(ts, str) and ts.endswith("Z"):
        timestamp = _iso(ts)
    else:
        timestamp = _iso(ts)

    return {
        "source": source,
        "instrument": symbol,
        "trade_id": str(trade_id) if trade_id is not None else None,
        "price": float(price) if price is not None else None,
        "size": float(size) if size is not None else None,
        "side": side,
        "timestamp": timestamp,
    }


def normalize_book(raw: dict, source: str) -> dict:
    symbol = raw.get("symbol") or raw.get("instrument") or raw.get("pair")
    sequence = raw.get("nonce") or raw.get("sequence") or raw.get("seq")

    bids = raw.get("bids") or []
    asks = raw.get("asks") or []

    def _levels(levels):
        out = []
        for lvl in levels:
            if isinstance(lvl, (list, tuple)):
                price = float(lvl[0])
                size = float(lvl[1])
                out.append([price, size])
            elif isinstance(lvl, dict):
                price = float(lvl.get("price"))
                size = float(lvl.get("amount") or lvl.get("size") or lvl.get("qty"))
                out.append([price, size])
        return out

    ts = raw.get("timestamp") or raw.get("datetime")
    timestamp = _iso(ts)

    return {
        "source": source,
        "instrument": symbol,
        "sequence": sequence,
        "bids": _levels(bids),
        "asks": _levels(asks),
        "timestamp": timestamp,
    }