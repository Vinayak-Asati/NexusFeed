Canonical schemas

Trade
- source: string
- instrument: string
- trade_id: string
- price: float
- size: float
- side: string  # buy|sell
- timestamp: string  # ISO8601

OrderBook
- source: string
- instrument: string
- sequence: int | string
- bids: list[list[float]]  # [[price, size], ...]
- asks: list[list[float]]  # [[price, size], ...]
- timestamp: string  # ISO8601