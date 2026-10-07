# -*- coding: utf-8 -*-
"""密钥 A（32B AES）—— **载荷自身密钥** 的唯一存放处（T92 收口）。

★ 该密钥属于 `assets/0gvw74arcr5sml` 载荷**自身**（见 `bdecrypt.py` 头注所引 bytecode 片段）
  ⇒ ⛔ **不宜简单脱敏**：改了 ⇒ 载荷**解不开**。
★ `bdecrypt.py` / `bstage.py` / `bstage2.py` / `bstage3.py` 一律<引用>本模块，⛔ 不再各自复制字面量。
★ 如需轮换 ⇒ 等于**重建载荷** ⇒ **待 Owner**（T92 卡不做）。

★ 可用环境变量 `PAYLOAD_AES_KEY_HEX` 覆盖（默认即下方常量，保证工具开箱即用）。
"""
import os

KEY_HEX = os.environ.get("PAYLOAD_AES_KEY_HEX", "3e88e24cb730e0f1367a7d5f76d9427661e6c7fdc952c3e4d8f6d403b8585b7a")
