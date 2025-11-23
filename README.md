# NexusFeed: Market Data Aggregator & Normalizer
[Live Demo](https://nexusfeed.onrender.com)

## Overview

**NexusFeed** is a real-time cryptocurrency market data aggregator that collects, normalizes, and stores ticker data from multiple exchanges. The system connects to various exchange APIs concurrently, fetches market data at configurable intervals, and saves the data in standardized CSV and JSON formats.

### Purpose

- **Aggregate** real-time market data from multiple cryptocurrency exchanges (Binance, Deribit, Bybit, OKX, etc.)
- **Normalize** exchange-specific data formats into a unified schema
- **Store** historical ticker data in CSV and JSON formats for analysis
- **Provide** a REST API for querying exchange status and fetching ticker data
- **Enable** debugging and testing with a one-time fetch mode

## Folder Structure

```
NexusFeed/
├── main.py                  # Application entrypoint with CLI and async fetch loops
├── config.py                # Configuration settings (exchanges, intervals, paths)
├── pyproject.toml           # Poetry dependencies and project metadata
├── poetry.lock              # Locked dependency versions
├── README.md                # This file
├── .gitignore               # Git ignore patterns
├── exchanges/               # Exchange connector modules
│   ├── __init__.py
│   ├── base_exchange.py     # Base exchange class using ccxt
│   ├── binance.py           # Binance exchange connector
│   ├── deribit.py           # Deribit exchange connector
│   ├── bybit.py             # Bybit exchange connector
│   └── okx.py               # OKX exchange connector
├── helpers/                 # Utility modules
│   ├── __init__.py
│   ├── logger.py            # Centralized logging setup
│   └── saver.py             # Data persistence utilities (CSV/JSON)
└── data/                    # Data storage directory
    ├── raw/                 # Raw ticker data (CSV/JSON files)
    └── logs/                # Application logs (if enabled)
```

## Installation

### Prerequisites

- Python 3.10 or higher
- Poetry (recommended) or pip

### Using Poetry (Recommended)

1. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd NexusFeed
   ```

3. **Install dependencies**:
   ```bash
   poetry install
   ```

4. **Activate the Poetry shell**:
   ```bash
   poetry shell
   ```

### Using pip

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd NexusFeed
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   (Note: If `requirements.txt` doesn't exist, install from `pyproject.toml` or manually install: `pip install fastapi uvicorn ccxt pandas`)

## Usage

### Continuous Mode (Default)

Run the application to continuously fetch ticker data from all configured exchanges:

```bash
# Using Python directly
python3 main.py

# Using Poetry
poetry run python main.py

# Or if using Poetry scripts
poetry run nexusfeed
```

The application will:
- Clear existing data files in `data/raw/`
- Start fetching ticker data for all configured symbols
- Save data to CSV files (`{exchange}_ticker.csv`)
- Run indefinitely until interrupted (Ctrl+C)

### One-Time Fetch Mode (Debugging)

Use the `--once` flag to fetch ticker data once for all symbols and exit:

```bash
# Using Python directly
python3 main.py --once

# Using Poetry
poetry run python main.py --once
```

This mode is useful for:
- Testing exchange connections
- Debugging data fetching issues
- Quick data snapshots
- Verifying configuration

### Running as FastAPI Server

The application also includes a FastAPI server with REST endpoints:

```bash
# Start the server
uvicorn main:app --reload

# Or with Poetry
poetry run uvicorn main:app --reload
```

Access the API at `http://localhost:8000`:
- API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`
- List Exchanges: `http://localhost:8000/api/exchanges`
- Exchange Status: `http://localhost:8000/api/exchanges/status`
- Fetch Ticker: `http://localhost:8000/api/exchanges/{exchange_name}/ticker/{symbol}`

## Configuration

Configuration is managed in `config.py`. Key settings include:

### Exchange Configuration

Edit `Config.EXCHANGES` to configure which exchanges and symbols to monitor:

```python
EXCHANGES: dict = {
    "binance": ["BTC/USDT", "ETH/USDT"],
    "deribit": ["BTC/USDT", "ETH/USDT"],
    "bybit": ["BTC/USDT", "ETH/USDT"],
    "okx": ["BTC/USDT", "ETH/USDT"],  # Comment out to disable
}
```

### Refresh Interval

Set the data fetching interval (in seconds) via `Config.REFRESH_INTERVAL`:

```python
REFRESH_INTERVAL: int = int(os.getenv("REFRESH_INTERVAL", "5"))  # Default: 5 seconds
```

Or set via environment variable:
```bash
export REFRESH_INTERVAL=10  # Fetch every 10 seconds
```

### Environment Variables

Configure the application using environment variables:

#### Exchange API Credentials (Optional)
Only needed for authenticated endpoints:
```bash
export BINANCE_API_KEY="your_api_key"
export BINANCE_API_SECRET="your_api_secret"
export DERIBIT_API_KEY="your_api_key"
export DERIBIT_API_SECRET="your_api_secret"
# ... similar for other exchanges
```

#### Application Settings
```bash
# Logging
export LOG_LEVEL="INFO"  # Options: DEBUG, INFO, WARNING, ERROR

# Sandbox/Test Mode
export SANDBOX_MODE="true"  # Use exchange sandbox/testnet

# Debug Mode
export DEBUG="true"

# Refresh Interval
export REFRESH_INTERVAL="5"  # Seconds between fetches
```

#### Database & Redis (Future Use)
```bash
export DATABASE_URL="sqlite:///data/nexusfeed.db"
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export REDIS_DB="0"
```

### Configuration File Structure

```python
class Config:
    # Base paths
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"
    RAW_DATA_DIR = DATA_DIR / "raw"
    LOGS_DIR = DATA_DIR / "logs"
    
    # Refresh interval (seconds)
    REFRESH_INTERVAL: int = 5
    
    # Exchange configuration
    EXCHANGES: dict = {
        "binance": ["BTC/USDT", "ETH/USDT"],
        # ... more exchanges
    }
    
    # Application settings
    DEBUG: bool = False
    SANDBOX_MODE: bool = False
    LOG_LEVEL: str = "INFO"
```

## Data Output

### CSV Files

Ticker data is saved to CSV files in `data/raw/` with the naming pattern:
- `{exchange_name}_ticker.csv`

**Example: `binance_ticker.csv`**
```csv
timestamp,exchange,symbol,price
2024-01-15T10:30:00.000Z,binance,BTC/USDT,42500.50
2024-01-15T10:30:05.000Z,binance,ETH/USDT,2650.75
2024-01-15T10:30:10.000Z,binance,BTC/USDT,42510.25
```

**CSV Format:**
- **timestamp**: ISO 8601 UTC timestamp
- **exchange**: Exchange name (e.g., "binance", "deribit")
- **symbol**: Trading pair (e.g., "BTC/USDT")
- **price**: Last traded price

### JSON Files

When using the REST API endpoint `/api/exchanges/{exchange_name}/ticker/{symbol}`, data is also saved to JSON files:
- `{exchange_name}_ticker.json`

**Example: `binance_ticker.json`**
```json
[
  {
    "timestamp": "2024-01-15T10:30:00.000Z",
    "exchange": "binance",
    "symbol": "BTC/USDT",
    "price": "42500.50"
  },
  {
    "timestamp": "2024-01-15T10:30:05.000Z",
    "exchange": "binance",
    "symbol": "ETH/USDT",
    "price": "2650.75"
  }
]
```

**JSON Format:**
- Array of objects, each containing:
  - `timestamp`: ISO 8601 UTC timestamp
  - `exchange`: Exchange name
  - `symbol`: Trading pair
  - `price`: Last traded price

### Data Management

- **Automatic Cleanup**: On startup, all existing CSV and JSON files in `data/raw/` are automatically cleared to start a fresh session
- **Append Mode**: New data is appended to existing files during the session
- **File Location**: All data files are stored in `data/raw/` directory

## API Endpoints

### REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root endpoint - serves web interface |
| GET | `/health` | Health check endpoint |
| GET | `/api/exchanges` | List all configured exchanges |
| GET | `/api/exchanges/status` | Get status and connectivity for all exchanges |
| GET | `/api/exchanges/{exchange_name}/ticker/{symbol}` | Fetch ticker data for a specific exchange and symbol |
| GET | `/api/v1/exchanges/available` | List all available exchanges from CCXT |
| GET | `/api/v1/exchanges/{exchange_name}/symbols` | Get all symbols for an exchange using gomarket API |
| GET | `/api/v1/exchanges/{exchange_name}/symbols/ccxt` | Get all symbols for an exchange using CCXT directly |

### Web Interface

NexusFeed includes a modern web interface accessible at the root URL (`/`). The interface allows you to:
- Browse all available exchanges from CCXT
- Select an exchange to view its symbols
- Filter symbols by instrument type (spot, futures, swap, etc.)
- View all symbol types for an exchange at once

### New Features

#### Exchange Symbol Browser

The new symbol browser endpoints use the **gomarket API** to fetch comprehensive symbol lists for any exchange:

1. **List Available Exchanges**: `/api/v1/exchanges/available`
   - Returns all exchanges supported by CCXT
   - Shows which exchanges are configured in NexusFeed
   - Indicates which exchanges are supported by gomarket API

2. **Get Exchange Symbols**: `/api/v1/exchanges/{exchange_name}/symbols`
   - Fetches symbols using the gomarket API
   - Supports filtering by instrument type (spot, futures, swap, etc.)
   - Can return all instrument types with `?all_types=true`
   - Example: `/api/v1/exchanges/binance/symbols?instrument_type=spot`

3. **Get Exchange Symbols (CCXT)**: `/api/v1/exchanges/{exchange_name}/symbols/ccxt`
   - Alternative endpoint that uses CCXT directly
   - Returns detailed market information for each symbol
   - Useful for getting real-time market data structure

### Example API Requests

```bash
# List all exchanges
curl http://localhost:8000/api/exchanges

# Get exchange status
curl http://localhost:8000/api/exchanges/status

# List all available exchanges from CCXT
curl http://localhost:8000/api/v1/exchanges/available

# Get all spot symbols for Binance using gomarket API
curl http://localhost:8000/api/v1/exchanges/binance/symbols?instrument_type=spot

# Get all symbol types for Bybit
curl http://localhost:8000/api/v1/exchanges/bybit/symbols?all_types=true

# Get symbols for OKX using CCXT directly
curl http://localhost:8000/api/v1/exchanges/okx/symbols/ccxt

# Fetch ticker for Binance BTC/USDT
curl http://localhost:8000/api/exchanges/binance/ticker/BTC/USDT

# Or using symbol without slash
curl http://localhost:8000/api/exchanges/binance/ticker/BTCUSDT
```

## Development

### Running Tests
```bash
poetry run pytest
```

### Code Formatting
```bash
poetry run black .
```

### Linting
```bash
poetry run flake8
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed (`poetry install` or `pip install -r requirements.txt`)

2. **Exchange Connection Errors**: 
   - Check internet connectivity
   - Verify exchange names in `Config.EXCHANGES` match available exchange modules
   - Some exchanges may require API credentials even for public endpoints

3. **Data Not Saving**: 
   - Check that `data/raw/` directory exists and is writable
   - Verify file permissions

4. **Rate Limiting**: 
   - Increase `REFRESH_INTERVAL` if hitting exchange rate limits
   - Some exchanges have strict rate limits on public endpoints

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]
