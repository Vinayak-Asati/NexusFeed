import time


class SimulatedConnector:
    def __init__(self, exchange_name: str = "sim", symbols=None):
        self.exchange_name = exchange_name
        self.symbols = symbols or ["BTC/USDT"]
        self._tid = 0

    def get_trades(self, symbol: str, limit: int = 5):
        out = []
        now = int(time.time() * 1000)
        for i in range(limit):
            self._tid += 1
            out.append(
                {
                    "id": str(self._tid),
                    "timestamp": now,
                    "symbol": symbol,
                    "price": 35000.0 + (self._tid % 50),
                    "amount": 0.01 + (i * 0.001),
                    "side": "buy" if (self._tid % 2 == 0) else "sell",
                }
            )
        return out

    def get_orderbook(self, symbol: str, limit: int = 5):
        now = int(time.time() * 1000)
        bids = [[35000.0 - i, 0.1 + i * 0.01] for i in range(limit)]
        asks = [[35000.5 + i, 0.1 + i * 0.01] for i in range(limit)]
        return {
            "symbol": symbol,
            "nonce": self._tid,
            "bids": bids,
            "asks": asks,
            "timestamp": now,
        }