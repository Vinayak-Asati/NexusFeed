from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

messages_received_total = Counter(
    "messages_received_total",
    "Total normalized messages received",
    ["type"],
)

trades_ingested_total = Counter(
    "trades_ingested_total",
    "Total trades ingested into storage",
)

connector_restarts_total = Counter(
    "connector_restarts_total",
    "Total connector restarts/resyncs",
    ["connector"],
)

db_write_latency_seconds = Histogram(
    "db_write_latency_seconds",
    "Database write latency in seconds",
    ["operation"],
)

def latest_metrics():
    return generate_latest()

def metrics_content_type():
    return CONTENT_TYPE_LATEST