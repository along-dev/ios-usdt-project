# -*- coding: utf-8 -*-
"""wallet-sweeper：本地钱包多链余额测绘与归集工具。

模块划分：
  derive  —— BIP39/BIP32 派生 + EVM/TRON/BTC/Solana 地址生成
  loader  —— 目录递归扫描 / 文件 / 命令行 三种输入入口
  chains  —— 多链 RPC 余额查询（EVM×6 / TRON / BTC / Solana）
  sweep   —— 归集签名与广播（默认 dry-run）
  btc_tx  —— BTC 交易构造与 BIP143 签名
  cli     —— scan / sweep 分离的命令行入口
"""

__version__ = "1.0.0"
__all__ = ["derive", "loader", "chains", "sweep", "btc_tx", "cli"]
