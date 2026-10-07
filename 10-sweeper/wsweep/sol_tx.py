# -*- coding: utf-8 -*-
"""Solana 交易构造与签名（不依赖 solders / solana-py）。

为什么手写：solders 是 Rust 扩展，本环境无法安装；但 Solana 的
交易格式本身并不复杂，用已有依赖（nacl + base58）即可完整实现：

  1. 交易消息序列化（legacy v0 message）
     - 头部：required_signatures / read-only signed / read-only unsigned
     - 账户地址表（32 字节 pubkey 列表，签名者在前）
     - recent_blockhash（32 字节）
     - 指令数组：program_id_index + account_indices + data
  2. compact-u16（shortvec）编码，用于数组长度
  3. ed25519 签名（nacl.signing）
  4. Base58 编码后提交 sendTransaction

覆盖的指令
  - System Program (1111...): Transfer  转账 SOL
  - SPL Token Program: TransferChecked  转账 SPL 代币（含 USDT/USDC）
  - Associated Token Account (ATA) 地址推导
"""
from __future__ import annotations

import base58
from nacl.signing import SigningKey

from . import chains as C

# 程序 ID
SYSTEM_PROGRAM = "11111111111111111111111111111111"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
ATA_PROGRAM = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
SYSVAR_RENT = "SysvarRent111111111111111111111111111111111"

LAMPORTS_PER_SOL = 1_000_000_000
# System Program 指令索引
IX_TRANSFER = 2
# SPL Token 指令索引
IX_TRANSFER_CHECKED = 12
IX_CREATE_IDEMPOTENT_ATA = 1


# --------------------------------------------------------------------------
# 基础编码
# --------------------------------------------------------------------------
def shortvec(n: int) -> bytes:
    """Solana compact-u16 编码。"""
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n == 0:
            out.append(b)
            break
        out.append(b | 0x80)
    return bytes(out)


def pk_bytes(addr: str) -> bytes:
    """Base58 地址 -> 32 字节 pubkey。"""
    raw = base58.b58decode(addr)
    if len(raw) != 32:
        raise ValueError(f"Solana 地址应为 32 字节，实际 {len(raw)}: {addr[:16]}")
    return raw


def pk_str(raw: bytes) -> str:
    return base58.b58encode(raw).decode()


def pubkey_from_seed(seed32: bytes) -> bytes:
    """从 32 字节 seed 推导 ed25519 公钥。"""
    return bytes(SigningKey(seed32[:32]).verify_key)


# --------------------------------------------------------------------------
# ATA（Associated Token Account）推导
# --------------------------------------------------------------------------
def find_ata(owner: str, mint: str) -> tuple:
    """推导 owner 对 mint 的关联代币账户地址。

    使用 PDA：seeds = [owner, token_program, mint]，program = ATA program。
    """
    seeds = [pk_bytes(owner), pk_bytes(TOKEN_PROGRAM), pk_bytes(mint)]
    program = pk_bytes(ATA_PROGRAM)
    for bump in range(255, -1, -1):
        addr = _create_program_address(seeds + [bytes([bump])], program)
        if addr is not None:
            return pk_str(addr), bump
    raise RuntimeError("无法推导 ATA 地址")


def _create_program_address(seeds: list, program_id: bytes) -> bytes:
    """create_program_address：sha256(seeds || program_id || "ProgramDerivedAddress")。"""
    import hashlib
    data = b"".join(seeds) + program_id + b"ProgramDerivedAddress"
    h = hashlib.sha256(data).digest()
    # 若结果为合法 ed25519 曲线点则该地址无效（需继续换 bump）
    if _is_on_curve(h):
        return None
    return h


def _is_on_curve(pubkey: bytes) -> bool:
    """判断 32 字节是否落在 ed25519 曲线上（用于 PDA 校验）。

    ed25519: -x^2 + y^2 = 1 + d*x^2*y^2  (mod p)
    压缩点为 (y, sign(x))，检查 y 是否使右侧为二次剩余。
    """
    if len(pubkey) != 32:
        return False
    p = 2 ** 255 - 19
    d = (-121665 * pow(121666, p - 2, p)) % p
    y = int.from_bytes(pubkey, "little")
    y &= (1 << 255) - 1
    if y >= p:
        return False
    y2 = (y * y) % p
    u = (y2 - 1) % p
    v = (d * y2 + 1) % p
    # x^2 = u / v 必须为二次剩余
    if v == 0:
        return False
    x2 = (u * pow(v, p - 2, p)) % p
    # 欧拉判别法
    return pow(x2, (p - 1) // 2, p) == 1


# --------------------------------------------------------------------------
# 指令构造
# --------------------------------------------------------------------------
class Ix:
    __slots__ = ("program", "accounts", "data")

    def __init__(self, program: str, accounts: list, data: bytes):
        self.program = program
        self.accounts = accounts   # [(pubkey_str, is_signer, is_writable), ...]
        self.data = data


def ix_transfer_sol(frm: str, to: str, lamports: int) -> Ix:
    """System Program Transfer。data = u32 索引(2) + u64 lamports。"""
    data = IX_TRANSFER.to_bytes(4, "little") + lamports.to_bytes(8, "little")
    return Ix(SYSTEM_PROGRAM, [(frm, True, True), (to, False, True)], data)


def ix_create_ata_idempotent(payer: str, owner: str, mint: str, ata: str) -> Ix:
    """创建关联代币账户（幂等，已存在则跳过）。"""
    return Ix(
        ATA_PROGRAM,
        [(payer, True, True), (ata, False, True), (owner, False, False),
         (mint, False, False), (SYSTEM_PROGRAM, False, False),
         (TOKEN_PROGRAM, False, False)],
        bytes([IX_CREATE_IDEMPOTENT_ATA]),
    )


def ix_transfer_checked(source: str, mint: str, dest: str, owner: str,
                        amount: int, decimals: int) -> Ix:
    """SPL Token TransferChecked。

    data = u8(12) + u64 amount + u8 decimals
    账户顺序：source, mint, dest, owner(+signer)
    """
    data = (bytes([IX_TRANSFER_CHECKED])
            + amount.to_bytes(8, "little")
            + bytes([decimals]))
    return Ix(
        TOKEN_PROGRAM,
        [(source, False, True), (mint, False, False),
         (dest, False, True), (owner, True, False)],
        data,
    )


# --------------------------------------------------------------------------
# 消息与交易序列化
# --------------------------------------------------------------------------
def compile_message(instructions: list, payer: str, recent_blockhash: str) -> bytes:
    """把指令编译成 legacy 交易消息（不含签名）。

    账户表排序规则（Solana 要求）：
      1. 签名者 + 可写  （payer 必须在第 0 位）
      2. 签名者 + 只读
      3. 非签名者 + 可写
      4. 非签名者 + 只读
    每组内部必须保持「首次出现顺序」，不能重排 —— 否则链上会报
    "Transaction failed to sanitize accounts offsets correctly"。
    """
    # --- 按首次出现顺序收集账户元数据 ---
    order = []          # 保持首次出现顺序的 pubkey 列表
    meta = {}           # pubkey_str -> [is_signer, is_writable]

    def touch(key: str, signer: bool, writable: bool):
        if key not in meta:
            meta[key] = [False, False]
            order.append(key)
        meta[key][0] = meta[key][0] or signer
        meta[key][1] = meta[key][1] or writable

    # payer 永远最先（第 0 位必须是付款方）
    touch(payer, True, True)

    for ix in instructions:
        touch(ix.program, False, False)
        for (key, signer, writable) in ix.accounts:
            touch(key, signer, writable)

    # --- 分组，但组内保持首次出现顺序 ---
    signers_w, signers_r, unsigned_w, unsigned_r = [], [], [], []
    for k in order:
        sg, wr = meta[k]
        if sg and wr:
            signers_w.append(k)
        elif sg and not wr:
            signers_r.append(k)
        elif not sg and wr:
            unsigned_w.append(k)
        else:
            unsigned_r.append(k)

    # payer 强制置于签名者可写组的第一位
    if payer in signers_w:
        signers_w.remove(payer)
    signers_w.insert(0, payer)

    ordered = signers_w + signers_r + unsigned_w + unsigned_r
    index = {k: i for i, k in enumerate(ordered)}

    header = bytes([
        len(signers_w) + len(signers_r),   # num_required_signatures
        len(signers_r),                    # num_readonly_signed_accounts
        len(unsigned_r),                   # num_readonly_unsigned_accounts
    ])

    # --- 账户表 ---
    acct_table = shortvec(len(ordered)) + b"".join(pk_bytes(k) for k in ordered)

    # --- blockhash ---
    bh = pk_bytes(recent_blockhash)

    # --- 指令 ---
    ix_bytes = bytearray()
    ix_bytes += shortvec(len(instructions))
    for ix in instructions:
        keys = [index[a[0]] for a in ix.accounts]
        ix_bytes += bytes([index[ix.program]])
        ix_bytes += shortvec(len(keys)) + bytes(keys)
        ix_bytes += shortvec(len(ix.data)) + ix.data

    return header + acct_table + bh + ix_bytes


def build_signed_tx(instructions: list, payer: str, seed32: bytes,
                    recent_blockhash: str) -> tuple:
    """构造并签名交易，返回 (raw_tx_bytes, base64, tx_signature_b58)。"""
    msg = compile_message(instructions, payer, recent_blockhash)
    sk = SigningKey(seed32[:32])
    sig = sk.sign(msg).signature          # 64 字节

    # 交易 = shortvec(签名数) + 签名 + 消息
    raw = shortvec(1) + bytes(sig) + msg

    import base64
    return raw, base64.b64encode(raw).decode(), base58.b58encode(bytes(sig)).decode()


# --------------------------------------------------------------------------
# 节点交互
# --------------------------------------------------------------------------
def rpc_single(rpc_url: str, method: str, params: list, timeout: int = 25):
    res, err = C.rpc_single(rpc_url, method, params, timeout=timeout)
    return res, err


def get_balance(rpc_url: str, addr: str, timeout: int = 25) -> int:
    res, err = rpc_single(rpc_url, "getBalance", [addr], timeout=timeout)
    if isinstance(res, dict):
        return int(res.get("value", 0))
    return 0


def get_latest_blockhash(rpc_url: str, timeout: int = 25) -> str:
    res, err = rpc_single(rpc_url, "getLatestBlockhash", [{"commitment": "finalized"}],
                          timeout=timeout)
    if isinstance(res, dict):
        val = res.get("value") or {}
        if val.get("blockhash"):
            return val["blockhash"]
    # 退回旧接口
    res2, err2 = rpc_single(rpc_url, "getRecentBlockhash", [], timeout=timeout)
    if isinstance(res2, dict):
        val = res2.get("value") or {}
        if val.get("blockhash"):
            return val["blockhash"]
    raise RuntimeError(f"无法获取 blockhash: {err or err2}")


def get_token_accounts(rpc_url: str, owner: str, mint: str, timeout: int = 25) -> list:
    """查询 owner 持有的某 mint 的所有 token account 及余额。"""
    res, err = rpc_single(
        rpc_url, "getTokenAccountsByOwner",
        [owner, {"mint": mint}, {"encoding": "jsonParsed"}], timeout=timeout)
    if not isinstance(res, dict):
        return []
    out = []
    for item in res.get("value", []) or []:
        try:
            info = item["account"]["data"]["parsed"]["info"]
            out.append({
                "pubkey": item["pubkey"],
                "amount": int(info["tokenAmount"]["amount"]),
                "decimals": int(info["tokenAmount"]["decimals"]),
                "ui": float(info["tokenAmount"]["uiAmount"] or 0),
            })
        except Exception:
            continue
    return out


def send_transaction(rpc_url: str, b64_tx: str, timeout: int = 30) -> tuple:
    """提交交易。返回 (是否成功, 签名或错误)。"""
    res, err = rpc_single(
        rpc_url, "sendTransaction",
        [b64_tx, {"encoding": "base64", "skipPreflight": False,
                  "preflightCommitment": "confirmed"}],
        timeout=timeout)
    if isinstance(res, str):
        return True, res
    return False, str(err or res)


# --------------------------------------------------------------------------
# 高层：归集单个 Solana 地址
# --------------------------------------------------------------------------
# 保留少量 lamports 作租金/手续费缓冲
KEEP_LAMPORTS = 890880 + 5000 * 3


def sweep_address(src: str, dst: str, privkey_hex: str, broadcast_it: bool = False,
                  rpc_url: str = None, timeout: int = 25) -> list:
    """归集单个 Solana 地址的 SOL + SPL USDT/USDC。

    返回 [(kind, symbol, raw_amount, ok, reason, sig)]。
    """
    out = []
    rpc = rpc_url or C.SOLANA_RPC[0]

    try:
        seed = bytes.fromhex(privkey_hex)[:32]
        my_pub = pubkey_from_seed(seed)
        my_addr = pk_str(my_pub)
        if my_addr != src:
            return [("native", "SOL", 0, False,
                     f"私钥推导地址({my_addr[:12]}…)与源地址({src[:12]}…)不一致", ""),
                    ("spl", "USDT", 0, False, "私钥与源地址不匹配", "")]
    except Exception as exc:
        return [("native", "SOL", 0, False, f"私钥解析失败: {exc}", ""),
                ("spl", "USDT", 0, False, f"私钥解析失败: {exc}", "")]

    try:
        dst_pub = pk_bytes(dst)
    except Exception as exc:
        return [("native", "SOL", 0, False, f"目标地址不可用: {exc}", ""),
                ("spl", "USDT", 0, False, f"目标地址不可用: {exc}", "")]

    # --- blockhash ---
    try:
        blockhash = get_latest_blockhash(rpc, timeout=timeout)
    except Exception as exc:
        return [("native", "SOL", 0, False, f"获取 blockhash 失败: {exc}", ""),
                ("spl", "USDT", 0, False, f"获取 blockhash 失败: {exc}", "")]

    # --- SOL 余额 ---
    lamports = 0
    try:
        lamports = get_balance(rpc, src, timeout=timeout)
    except Exception:
        pass

    # --- SPL 代币 ---
    tokens = []
    for mint, sym in ((C.SOLANA_USDT, "USDT"), (C.SOLANA_USDC, "USDC")):
        try:
            for acc in get_token_accounts(rpc, src, mint, timeout=timeout):
                if acc["amount"] > 0:
                    tokens.append((sym, mint, acc))
        except Exception:
            pass

    has_token = bool(tokens)
    # 若只有代币没有 SOL，无法支付手续费
    if lamports < KEEP_LAMPORTS and (has_token or lamports > 0):
        reason = (f"SOL 不足以支付手续费（余额 {lamports/1e9:.9f}，"
                  f"需保留 {KEEP_LAMPORTS/1e9:.6f}）")
        if has_token:
            out.append(("spl", "USDT", 0, False, reason, ""))
        out.append(("native", "SOL", 0, False, reason, ""))
        return out

    # --- 先转代币（需要 SOL 付手续费；SOL 放最后走）---
    for sym, mint, acc in tokens:
        try:
            src_ata = acc["pubkey"]
            dst_ata, _bump = find_ata(dst, mint)
            ixs = [
                ix_create_ata_idempotent(my_addr, dst, mint, dst_ata),
                ix_transfer_checked(src_ata, mint, dst_ata, my_addr,
                                    acc["amount"], acc["decimals"]),
            ]
            raw, b64, sig = build_signed_tx(ixs, my_addr, seed, blockhash)
            if broadcast_it:
                ok, info = send_transaction(rpc, b64, timeout=timeout)
                out.append(("spl", sym, acc["amount"], ok,
                            "已广播" if ok else f"广播失败: {info}",
                            info if ok else ""))
            else:
                out.append(("spl", sym, acc["amount"], True,
                            "dry-run（已签名，未广播）", sig))
        except Exception as exc:
            out.append(("spl", sym, 0, False, f"{type(exc).__name__}: {exc}", ""))

    if not tokens:
        out.append(("spl", "USDT", 0, False, "USDT/USDC 余额为 0", ""))

    # --- SOL ---
    send = lamports - KEEP_LAMPORTS
    if send <= 0:
        out.append(("native", "SOL", 0, False,
                    f"SOL 余额不足以支付手续费（余额 {lamports/1e9:.9f}）", ""))
    else:
        try:
            ix = ix_transfer_sol(my_addr, dst, send)
            raw, b64, sig = build_signed_tx([ix], my_addr, seed, blockhash)
            if broadcast_it:
                ok, info = send_transaction(rpc, b64, timeout=timeout)
                out.append(("native", "SOL", send, ok,
                            "已广播" if ok else f"广播失败: {info}",
                            info if ok else ""))
            else:
                out.append(("native", "SOL", send, True,
                            "dry-run（已签名，未广播）", sig))
        except Exception as exc:
            out.append(("native", "SOL", 0, False, f"{type(exc).__name__}: {exc}", ""))

    return out
