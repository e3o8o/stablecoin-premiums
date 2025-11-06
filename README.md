# stablecoin-premiums

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Utilities to fetch P2P stablecoin quotes and FX rates, then compute premiums/spreads across fiat markets. Built for research, monitoring, and comparative analysis of stablecoins (default: USDT; and extendable to other assets) in local markets versus reference FX rates.

## Installation

### From Source
```bash
git clone https://github.com/e3o8o/stablecoin-premiums.git
cd stablecoin-premiums
pip install -e .
```

### Development Installation
```bash
pip install -e ".[dev,notebooks]"
```

> Status: Initial public scaffold (sanitized). Contributions are welcome.

---

## Features

- Fetch P2P quotes (BUY/SELL) from Binance (public C2C endpoint)
- Fetch FX mid-rates from XE (or plug alternative FX providers)
- Compute:
  - Stablecoin sell premium vs. FX bid
  - Stablecoin buy premium vs. FX ask
  - Buy–sell spread
- CLI to run one-shot checks
- Notebook-friendly design (for exploration and dashboards)
- Environment-based configuration (no secrets committed)

---

## Repository Layout

```
stablecoin-premiums/
├── .env.example          # sample env vars (copy to .env and fill)
├── .gitignore
├── requirements.txt
├── README.md
├── setup.py              # package installation
├── pyproject.toml        # modern Python packaging
├── src/
│   └── stablecoin_premiums/
│       ├── __init__.py
│       ├── config.py         # reads env vars
│       ├── compute.py        # premium/spread math
│       ├── cli.py            # simple command-line entrypoint
│       └── clients/
│           ├── binance.py      # P2P quotes (public)
│           ├── xe.py           # FX mid-rates (auth)
│           ├── eldorado.py     # optional (stub; adapt if you have access)
│           └── coinapi.py      # optional (stub; adapt if you have access)
├── notebooks/
│   ├── 01_fetch_premiums.ipynb
│   └── 02_batch_premiums_export.ipynb
├── tests/                # unit tests
│   ├── conftest.py
│   └── test_compute.py
└── data/                 # (gitignored; for your own outputs/exports)
```

---

## Quickstart

### 1) Create and activate a virtual environment

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1
```

### 2) Install the package

```bash
pip install -e .
```

### 3) Set environment variables (required for FX rates)

Copy the sample file and fill in your XE API credentials:

```bash
cp .env.example .env
```

Edit `.env` and set your credentials (never commit this!):

- `XE_API_ACCOUNT_ID`, `XE_API_KEY`: From your [XE account](https://www.xe.com/account/developer/api-keys) (required for FX rates)
- `COINAPI_KEY` (optional): For alternative price lookups
- `ELDORADO_API_BASE_URL` (optional): If you have access
- Timeouts/retry settings: `REQUEST_TIMEOUT`, `MAX_RETRIES`, `RETRY_SLEEP`
- Defaults: `DEFAULT_ASSET`, `REF_FIAT`, `DEFAULT_FIATS`

### 4) Run a quick check (CLI)

```bash
stablecoin-premiums
```

By default, it queries USDT in MXN vs USD mid-rate. To query different markets:

```bash
# Single fiat
stablecoin-premiums --fiats BRL

# Multiple fiats
stablecoin-premiums --fiats MXN,BRL,ARS

# Different asset and reference fiat
stablecoin-premiums --fiats EUR --asset USDC --ref-fiat USD

# CSV output
stablecoin-premiums --output csv

# Pretty JSON
stablecoin-premiums --output json --pretty
```

Example output (JSON):

```json
[
  {
    "fiat": "MXN",
    "asset": "USDT",
    "ref_fiat": "USD",
    "sell_rate": 18.95,
    "buy_rate": 18.70,
    "fx": {"bid": 17.12, "ask": 17.12},
    "stablecoin_sell_premium": 10.69,
    "stablecoin_buy_premium": 9.25,
    "stablecoin_buy_sell_spread": -1.32,
    "status": "ok"
  }
]
```

**Note**: Values above are illustrative; your output depends on live market conditions and available ads.

---

## Usage Patterns

### A) Programmatic Usage

Import and compose the clients + compute functions:

```python
from stablecoin_premiums.clients.binance import average_price
from stablecoin_premiums.clients.xe import fetch_fx_rate
from stablecoin_premiums.compute import compute_premiums

fiat = "BRL"
asset = "USDT"
ref_fiat = "USD"

buy = average_price(fiat, asset, "BUY")
sell = average_price(fiat, asset, "SELL")
fx = fetch_fx_rate(fiat, ref_fiat)

if buy and sell and fx:
    result = compute_premiums(sell, buy, fx["bid"], fx["ask"])
    print({
        "fiat": fiat,
        "asset": asset,
        "sell_rate": sell,
        "buy_rate": buy,
        "fx": fx,
        **result.to_dict()
    })
else:
    print("Insufficient data for computation")
```

### B) Jupyter Notebooks

Two example notebooks are included:

1. **`notebooks/01_fetch_premiums.ipynb`** - Quick start with basic usage
2. **`notebooks/02_batch_premiums_export.ipynb`** - Batch processing and export

Load environment variables in notebooks:
```python
from dotenv import load_dotenv
load_dotenv()  # Loads from .env file
```

---

## Testing

Run the test suite:

```bash
pytest tests/
```

Or with coverage:

```bash
pytest tests/ --cov=stablecoin_premiums --cov-report=html
```

## Configuration & Providers

### Data Providers

- **Binance P2P**
  Public C2C endpoint used for USDT quotes. Code filters and averages top ads under basic validity checks. You can enhance:
  - Payment method filters (`payTypes`)
  - Country filters
  - Ad validation rules (min/max trade amounts, KYC level, etc.)

- **XE FX**
  Uses authenticated endpoint to fetch mid rate, exposed as `bid/ask` parity (mid as both). Requires XE API credentials.

- **CoinAPI** (optional)
  Alternative FX provider - requires API key.

- **Eldorado** (optional)
  Stub implementation - adapt if you have access.

### Adding New Providers

Add new providers under `src/stablecoin_premiums/clients/` following the existing patterns:

1. Implement client functions with proper error handling
2. Read configuration from environment variables
3. Return `None` on failure (don't raise exceptions)
4. Add to imports in `__init__.py` if appropriate

---

## Design Principles

- **No secrets in code**: All credentials are read from environment variables
- **Defensive programming**: Functions return `None` on failure rather than raising exceptions
- **Extensibility**: Add new providers under `src/stablecoin_premiums/clients/`
- **Data hygiene**: `data/` directory is gitignored for local outputs
- **Type safety**: Comprehensive type hints throughout the codebase
- **Documentation**: Inline docstrings and examples for all public functions

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Troubleshooting

- **"Insufficient data" output**
  - P2P response may lack valid ads (filters too strict, market low liquidity)
  - Try increasing `rows` or relaxing validity checks in `binance.py`
  - Use `--min-valid-ads` flag to require minimum number of valid ads

- **XE returns `None`**
  - Check your `XE_API_ACCOUNT_ID` and `XE_API_KEY`
  - Verify account status and rate limits
  - Network timeouts—tune `REQUEST_TIMEOUT`, `MAX_RETRIES`, `RETRY_SLEEP`

- **Rate limits / HTTP errors**
  - Respect provider Terms of Service
  - Add exponential backoff if running frequent queries
  - Consider implementing request caching for repeated queries

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Binance for P2P data access
- XE.com for FX rate API
- Contributors and users of this package

MIT
