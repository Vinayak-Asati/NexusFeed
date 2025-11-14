from nexusfeed.connectors.binance import BinanceOrderBookConnector


def test_binance_resync_on_gap():
    snapshot_calls = []

    def fetcher(symbol: str):
        snapshot_calls.append(symbol)
        return {
            "lastUpdateId": 100,
            "bids": [[35000.0, 1.0]],
            "asks": [[35010.0, 1.0]],
        }

    conn = BinanceOrderBookConnector(snapshot_fetcher=fetcher)

    # first delta arrives before snapshot init -> connector will fetch snapshot
    applied = conn.process_depth_delta("BTC/USDT", {"U": 90, "u": 95, "b": [[34999.0, 0.5]], "a": []})
    assert not applied
    assert snapshot_calls == ["BTC/USDT"]

    # normal sequential delta: U == last+1 or enveloping last+1
    applied = conn.process_depth_delta("BTC/USDT", {"U": 101, "u": 101, "b": [[35001.0, 0.3]], "a": []})
    assert applied
    book = conn.get_book("BTC/USDT")
    assert book["sequence"] == 101

    # gap/out-of-order: U far ahead of last+1 -> resync
    applied = conn.process_depth_delta("BTC/USDT", {"U": 200, "u": 200, "b": [[35002.0, 0.2]], "a": []})
    assert not applied
    assert snapshot_calls == ["BTC/USDT", "BTC/USDT"]