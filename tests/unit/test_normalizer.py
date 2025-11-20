import pytest

from nexusfeed.normalizer import normalize_trade, normalize_book


def test_normalize_trade_ccxt_like():
    raw = {
        "id": "12345",
        "timestamp": 1609459200000,  # 2021-01-01T00:00:00Z in ms
        "datetime": "2021-01-01T00:00:00.000Z",
        "symbol": "BTC/USDT",
        "price": 34000.5,
        "amount": 0.01,
        "side": "buy",
    }

    out = normalize_trade(raw, source="binance")

    assert out["source"] == "binance"
    assert out["instrument"] == "BTC/USDT"
    assert out["trade_id"] == "12345"
    assert out["price"] == 34000.5
    assert out["size"] == 0.01
    assert out["side"] == "buy"
    assert out["timestamp"].startswith("2021-01-01T00:00:00")


def test_normalize_book_ccxt_like():
    raw = {
        "symbol": "ETH/USDT",
        "nonce": 987654321,
        "bids": [[2000.0, 1.5], [1999.5, 2.0]],
        "asks": [[2000.5, 1.0], [2001.0, 0.8]],
        "timestamp": 1609459200000,
    }

    out = normalize_book(raw, source="deribit")

    assert out["source"] == "deribit"
    assert out["instrument"] == "ETH/USDT"
    assert out["sequence"] == 987654321
    assert out["bids"] == [[2000.0, 1.5], [1999.5, 2.0]]
    assert out["asks"] == [[2000.5, 1.0], [2001.0, 0.8]]
    assert out["timestamp"].startswith("2021-01-01T00:00:00")