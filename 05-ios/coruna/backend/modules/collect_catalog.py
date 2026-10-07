"""
Supported collect asset types — catalog drives UI, RPC scan, and C2 dispatch.
"""

from __future__ import annotations

from typing import Any

COLLECT_ASSETS: list[dict[str, Any]] = [
    {
        "id": "ETH_USDC",
        "chain": "ETH",
        "token": "USDC",
        "label": "ETH · USDC",
        "dest_key": "eth_usdc",
        "wallet_key": "eth_address",
        "balance_key": "eth_usdc",
        "rpc": "eth_rpc",
        "contract_key": "eth_usdc_contract",
        "decimals": 6,
    },
    {
        "id": "ETH_USDT",
        "chain": "ETH",
        "token": "USDT",
        "label": "ETH · USDT",
        "dest_key": "eth_usdt",
        "wallet_key": "eth_address",
        "balance_key": "eth_usdt",
        "rpc": "eth_rpc",
        "contract": "0xdAC17F958D2ee523a2206206994597C13D832831",
        "decimals": 6,
    },
    {
        "id": "ETH_NATIVE",
        "chain": "ETH",
        "token": "ETH",
        "label": "ETH · 原生 ETH",
        "dest_key": "eth_native",
        "wallet_key": "eth_address",
        "balance_key": "eth_native",
        "rpc": "eth_rpc",
        "contract": "",
        "decimals": 18,
        "native": True,
    },
    {
        "id": "TRX_USDT",
        "chain": "TRX",
        "token": "USDT",
        "label": "TRX · USDT",
        "dest_key": "trx_usdt",
        "wallet_key": "trx_address",
        "balance_key": "trx_usdt",
        "rpc": "trx_rpc",
        "contract_key": "trx_usdt_contract",
        "decimals": 6,
    },
    {
        "id": "TRX_NATIVE",
        "chain": "TRX",
        "token": "TRX",
        "label": "TRX · 原生 TRX",
        "dest_key": "trx_native",
        "wallet_key": "trx_address",
        "balance_key": "trx_native",
        "rpc": "trx_rpc",
        "contract": "",
        "decimals": 6,
        "native": True,
    },
    {
        "id": "BTC",
        "chain": "BTC",
        "token": "BTC",
        "label": "BTC",
        "dest_key": "btc",
        "wallet_key": "btc_address",
        "balance_key": "btc",
        "rpc": "btc_api",
        "contract": "",
        "decimals": 8,
        "native": True,
    },
    {
        "id": "BSC_USDT",
        "chain": "BSC",
        "token": "USDT",
        "label": "BSC · USDT",
        "dest_key": "bsc_usdt",
        "wallet_key": "bsc_address",
        "balance_key": "bsc_usdt",
        "rpc": "bsc_rpc",
        "contract": "0x55d398326f99059fF775485246999027B3197955",
        "decimals": 18,
    },
    {
        "id": "BSC_BNB",
        "chain": "BSC",
        "token": "BNB",
        "label": "BSC · 原生 BNB",
        "dest_key": "bsc_native",
        "wallet_key": "bsc_address",
        "balance_key": "bsc_native",
        "rpc": "bsc_rpc",
        "contract": "",
        "decimals": 18,
        "native": True,
    },
    {
        "id": "SOL_USDT",
        "chain": "SOL",
        "token": "USDT",
        "label": "SOL · USDT",
        "dest_key": "sol_usdt",
        "wallet_key": "sol_address",
        "balance_key": "sol_usdt",
        "rpc": "sol_rpc",
        "contract": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
        "decimals": 6,
    },
    {
        "id": "SOL_NATIVE",
        "chain": "SOL",
        "token": "SOL",
        "label": "SOL · 原生 SOL",
        "dest_key": "sol_native",
        "wallet_key": "sol_address",
        "balance_key": "sol_native",
        "rpc": "sol_rpc",
        "contract": "",
        "decimals": 9,
        "native": True,
    },
]

COLLECT_DEST_KEYS = [a["dest_key"] for a in COLLECT_ASSETS]
WALLET_KEYS = list(dict.fromkeys(a["wallet_key"] for a in COLLECT_ASSETS))
BALANCE_KEYS = [a["balance_key"] for a in COLLECT_ASSETS]

NATIVE_USD_RATES: dict[str, float] = {
    "ETH": 3500.0,
    "TRX": 0.12,
    "BTC": 65000.0,
    "BNB": 600.0,
    "SOL": 150.0,
}

RPC_FORM_FIELDS: list[dict[str, str]] = [
    {"key": "eth_rpc", "label": "ETH JSON-RPC", "placeholder": "https://eth-mainnet.g.alchemy.com/v2/..."},
    {"key": "eth_usdc_contract", "label": "USDC 合约 (ETH)", "placeholder": "0xA0b8..."},
    {"key": "trx_rpc", "label": "TRON API / RPC", "placeholder": "https://api.trongrid.io"},
    {"key": "trx_usdt_contract", "label": "USDT 合约 (TRX)", "placeholder": "TR7NHq..."},
    {"key": "btc_api", "label": "BTC API", "placeholder": "https://blockstream.info/api"},
    {"key": "bsc_rpc", "label": "BSC JSON-RPC", "placeholder": "https://bsc-dataseed.binance.org"},
    {"key": "sol_rpc", "label": "Solana JSON-RPC", "placeholder": "https://api.mainnet-beta.solana.com"},
]


def asset_usd_value(asset: dict[str, Any], balance: float) -> float:
    token = asset.get("token", "")
    if token in ("USDC", "USDT"):
        return float(balance)
    if asset.get("native"):
        return float(balance) * NATIVE_USD_RATES.get(token, 0.0)
    return float(balance)


def compute_row_total_usd(row: dict[str, Any]) -> float:
    total = 0.0
    for asset in COLLECT_ASSETS:
        bal = float(row.get(asset["balance_key"], 0) or 0)
        total += asset_usd_value(asset, bal)
    return round(total, 2)
