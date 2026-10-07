# -*- coding: utf-8 -*-
"""输入加载：从目录递归扫描 / 指定文件 / 命令行参数中提取助记词与私钥。

支持三种入口（用户要求全部支持）：
  1. --scan-dir DIR   递归扫描目录，关键词过滤 + 内容正则提取
  2. --file PATH      指定单个或多个文件
  3. --mnemonic / --privkey   命令行直接传入

提取规则保持保守：宁少勿错。每条结果都记录来源文件与行号，便于人工复核。
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Iterable

from .derive import _WORDLIST, validate_mnemonic
from .privkey import recognize as pk_recognize, canonical as pk_canonical, fingerprint as pk_fp

# --------------------------------------------------------------------------
# 正则
# --------------------------------------------------------------------------
# 私钥：0x + 64 hex，或裸 64 hex（需上下文佐证），或 WIF
RE_PRIV_0X = re.compile(r"\b0[xX]([0-9a-fA-F]{64})\b")
RE_PRIV_BARE = re.compile(r"(?<![0-9a-fA-Fx])([0-9a-fA-F]{64})(?![0-9a-fA-F])")
# WIF：主网 5/K/L、测试网 9/c
RE_WIF = re.compile(r"\b([5KL9c][1-9A-HJ-NP-Za-km-z]{50,51})\b")
# --- 变体扩展 ---
# 0x 前缀 + 任意 8~63 位 hex（覆盖省略前导零的短写法）
RE_PRIV_0X_SHORT = re.compile(r"\b0[xX]([0-9a-fA-F]{8,63})\b")
# TRON 41 前缀写法：41 + 64hex（共 66 位 hex，0x 前缀可选）
RE_PRIV_TRON41 = re.compile(r"\b(?:0[xX])?(41[0-9a-fA-F]{64})\b")
# hex 分组写法：16 组 4 位，分隔符必须统一（空格 或 连字符 二选一）
RE_PRIV_GROUPED_SP = re.compile(r"(?<![0-9a-fA-F])((?:[0-9a-fA-F]{4} ){15}[0-9a-fA-F]{4})(?![0-9a-fA-F])")
RE_PRIV_GROUPED_DASH = re.compile(r"(?<![0-9a-fA-F])((?:[0-9a-fA-F]{4}-){15}[0-9a-fA-F]{4})(?![0-9a-fA-F])")
RE_PRIV_GROUPED8 = re.compile(r"(?<![0-9a-fA-F])([0-9a-fA-F]{8}(?:[ -][0-9a-fA-F]{8}){7})(?![0-9a-fA-F])")
# 冒号分隔（2 位一组）
RE_PRIV_COLON = re.compile(r"(?<![0-9a-fA-F])((?:[0-9a-fA-F]{2}:){31}[0-9a-fA-F]{2})(?![0-9a-fA-F])")
# base64 的 32 字节（44 字符含 = 填充）。注意不能用 \b，因为 / 与 = 不构成词边界
RE_PRIV_B64 = re.compile(r"(?<![A-Za-z0-9+/])([A-Za-z0-9+/]{43}=)(?![A-Za-z0-9+/=])")
# 助记词：12/15/18/21/24 个连续小写字母单词
RE_MNEMONIC = re.compile(r"\b((?:[a-z]{3,8}[ \t]+){11,23}[a-z]{3,8})\b")

# JSON 负向字段名：这些字段的值几乎不可能是私钥（哈希/ID/签名等）
NEG_FIELD = re.compile(
    r"(?i)(sha\d*|_?hash$|^hash|txid|tx_?id|block_?id|_id$|^id$|"
    r"signature|sig$|_sig|topic|selector|merkle|root$|"
    r"cert|pubkey_|_pubkey|fingerprint|checksum|digest|"
    r"nonce|salt|uuid|trace|request_?id|session_?id|"
    r"create_?time|update_?time|timestamp|_at$)"
)
# 敏感文件扩展名
TEXT_EXTS = {".txt", ".json", ".md", ".csv", ".log", ".env", ".ini", ".yaml", ".yml",
             ".js", ".ts", ".py", ".go", ".java", ".c", ".cpp", ".h", ".xml", ".html", ".bak"}
# 噪声扩展名（内容为哈希/摘要）
NOISE_EXTS = {".sum", ".mf", ".sf", ".dsa", ".rsa", ".ec", ".lock"}
# 扫描时跳过的目录
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".cache", ".venv", "venv",
             "site-packages", "dist", "build", ".next", "target", "$RECYCLE.BIN",
             "System Volume Information", "Windows", "AppData"}
# 扫描时跳过的明显无关文件（降低噪声与体积）
MAX_FILE_BYTES = 4 * 1024 * 1024

# 已知的纯噪声文件（内容全是哈希/摘要，不可能含私钥）
#   · MANIFEST.MF / *.SF : APK v1 签名清单，逐行 SHA-256-Digest
#   · go.sum             : Go 模块校验和
#   · *.lock             : 依赖锁文件
NOISE_FILES = re.compile(
    r"(?i)^(manifest\.mf|.*\.sf|.*\.dsa|.*\.rsa|.*\.ec|go\.sum|"
    r"package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|"
    r"cargo\.lock|composer\.lock|gemfile\.lock)$"
)

# 快速模式下，超过此大小且文件名无密钥线索的文件直接跳过
FAST_SKIP_BYTES = 256 * 1024
# 文件名/路径中暗示可能含密钥的词
KEY_HINT = re.compile(
    r"(?i)(wallet|mnemonic|助记|私钥|privkey|priv_?key|secret|seed|key|cred|"
    r"vault|account|bip39|bip44|keystore|deploy|owner|signer)"
)


@dataclass
class Found:
    kind: str            # mnemonic | privkey
    value: str           # 规范形式：助记词原文 / 私钥统一为小写 64 位 hex
    source: str          # 文件路径 或 "cli"
    line: int = 0
    note: str = ""
    variants: list = field(default_factory=list)  # 该私钥被发现的原始写法列表

    def key(self):
        return (self.kind, self.value)

    def add_variant(self, source: str, line: int, origin: str):
        """登记一处原始变体来源（用于"还原存储"）。"""
        item = {"source": source, "line": line, "origin": origin}
        for v in self.variants:
            if v["source"] == source and v["line"] == line and v["origin"] == origin:
                return
        self.variants.append(item)


class LoadReport:
    """加载过程的统计与告警，便于向用户说明"扫了什么、跳了什么"。"""

    def __init__(self, fast: bool = False, progress: bool = False):
        self.files_scanned = 0
        self.files_skipped = 0
        self.files_seen = 0
        self.hits = 0
        self.bytes_read = 0
        self.errors: list = []
        self.fast = fast          # 大文件快速跳过
        self.progress = progress  # 打印进度

    def to_dict(self):
        return {
            "files_seen": self.files_seen,
            "files_scanned": self.files_scanned,
            "files_skipped": self.files_skipped,
            "hits": self.hits,
            "bytes_read": self.bytes_read,
            "errors": self.errors[:50],
        }


# --------------------------------------------------------------------------
# 内容提取
# --------------------------------------------------------------------------
def _dedupe_words(text: str) -> str:
    return " ".join(text.split())


def extract_from_text(text: str, source: str, report: LoadReport = None) -> list:
    """从一段文本中提取助记词与私钥。"""
    found = []

    # --- 助记词 ---
    for m in RE_MNEMONIC.finditer(text):
        cand = _dedupe_words(m.group(1))
        words = cand.split()
        if len(words) not in (12, 15, 18, 21, 24):
            continue
        if _WORDLIST is not None:
            # 必须有足够比例的单词命中 BIP39 词表，避免把普通英文句子当助记词
            hits = sum(1 for w in words if w in _WORDLIST)
            if hits < len(words) * 0.9:
                continue
        ok, why = validate_mnemonic(cand)
        if not ok:
            if report is not None and "校验和" not in why:
                pass
            continue
        line = text[:m.start()].count("\n") + 1
        found.append(Found("mnemonic", cand, source, line, f"{len(words)}词"))

    # ======================================================================
    # 私钥：所有形态统一交给 privkey.recognize 解析并规范化
    # 收集原始候选 -> 规范化 -> 记录来源变体
    # ======================================================================
    seen_spans = set()   # (start, end) 已处理的文本区间，避免重复计数

    def line_of(pos: int) -> int:
        return text[:pos].count("\n") + 1

    # 负向上下文：出现这些词说明该 64hex 更可能是哈希/摘要而非私钥
    NEG_CTX = re.compile(
        r"(?i)(tx_?hash|txhash|transaction_?hash|block_?hash|blockhash|"
        r"sha256|sha1|sha512|keccak|md5|hash\s*[=:]|digest|checksum|"
        r"signature|sig\s*[=:]|event_?topic|topic0|selector|"
        r"merkle|root\s*[=:]|commitment|ipfs|nonce\s*[=:]|"
        r"bytecode|runtime_?code|deployed_?bytecode|"
        r"salt|id\s*[=:]|uuid|request_?id|trace_?id)"
    )
    # 正向上下文：强证据说明是私钥
    POS_CTX = re.compile(
        r"(?i)(private_?key|privkey|priv_?key|secret_?key|secretkey|"
        r"privatekey|私钥|pk\s*[=:]|key_?hex|wallet_?key|signer_?key|"
        r"mnemonic|助记)"
    )

    def add_pk(raw_candidate: str, pos: int, hint: str, need_ctx: bool = False,
               strict: bool = False):
        """识别 + 规范化一条私钥候选。

        strict=True 时（用于 0x+64hex 这类最容易误报的形态）：
          · 若附近有负向词（hash/sha256/signature 等）→ 丢弃
          · 且必须同时有正向词（private_key/privkey/私钥 等）才保留
        """
        s = (raw_candidate or "").strip()
        if not s:
            return
        ctx_start = max(0, pos - 160)
        ctx = text[ctx_start:pos + len(s) + 80]

        if strict:
            if NEG_CTX.search(ctx):
                return
            if not POS_CTX.search(ctx):
                return

        if need_ctx:
            low = ctx.lower()
            if not re.search(r"(private|priv|secret|key|pk|私钥|wallet|seed|mnemonic)", low):
                return

        priv_hex, form, note = pk_recognize(s)
        if not priv_hex:
            return
        f = Found(
            "privkey", priv_hex, source, line_of(pos),
            f"{note} [{hint}]",
        )
        f.add_variant(source, line_of(pos), _trunc(s))
        found.append(f)

    # 1) 0x41 + 64hex（TRON 0x41 前缀写法）—— 必须先于普通 0x64 匹配，
    #    否则 RE_PRIV_0X 会先吃掉它的 span，导致 41 形态被误判为普通私钥
    for m in RE_PRIV_TRON41.finditer(text):
        add_pk(m.group(1), m.start(), "tron41")
        seen_spans.add((m.start(), m.end()))

    # 2) 0x + 64hex（跳过已被 TRON41 覆盖的区间）
    #    这是最高误报形态（交易哈希/事件签名都长这样）→ strict 过滤
    for m in RE_PRIV_0X.finditer(text):
        if (m.start(), m.end()) in seen_spans:
            continue
        # 若该区间落在某个已处理的 TRON41 区间内，也跳过
        if any(m.start() >= s and m.end() <= e for s, e in seen_spans):
            continue
        seen_spans.add((m.start(), m.end()))
        add_pk("0x" + m.group(1), m.start(), "0x64", strict=True)

    # 3) WIF（WIF 本身是 Base58Check，几乎无误报，不需要 strict）
    for m in RE_WIF.finditer(text):
        if (m.start(), m.end()) in seen_spans:
            continue
        seen_spans.add((m.start(), m.end()))
        add_pk(m.group(1), m.start(), "wif")

    # 4) 0x + 短 hex（8~63 位，省略前导零）—— 极易把合约地址误补成私钥 → strict
    for m in RE_PRIV_0X_SHORT.finditer(text):
        if (m.start(), m.end()) in seen_spans:
            continue
        seen_spans.add((m.start(), m.end()))
        add_pk("0x" + m.group(1), m.start(), "0x短hex", strict=True)

    # 5) base64（44 字符）—— 必须有关键词佐证，否则会把哈希/摘要当私钥
    for m in RE_PRIV_B64.finditer(text):
        if (m.start(), m.end()) in seen_spans:
            continue
        seen_spans.add((m.start(), m.end()))
        add_pk(m.group(1), m.start(), "base64", strict=True)

    # 6) 冒号分隔
    for m in RE_PRIV_COLON.finditer(text):
        if (m.start(), m.end()) in seen_spans:
            continue
        seen_spans.add((m.start(), m.end()))
        add_pk(m.group(1), m.start(), "冒号分隔")

    # 7) 分组写法（4 位空格 / 4 位连字符 / 8 位分组）
    for rx, label in ((RE_PRIV_GROUPED_SP, "分组-空格"),
                      (RE_PRIV_GROUPED_DASH, "分组-连字符"),
                      (RE_PRIV_GROUPED8, "分组-8位")):
        for m in rx.finditer(text):
            if any(m.start() >= s and m.end() <= e for s, e in seen_spans):
                continue
            seen_spans.add((m.start(), m.end()))
            add_pk(m.group(1), m.start(), label)

    # 8) 裸 64hex（最高误报风险，必须有关键词佐证，且排除哈希类上下文）
    for m in RE_PRIV_BARE.finditer(text):
        if any(m.start() >= s and m.end() <= e for s, e in seen_spans):
            continue
        val = m.group(1)
        # 已被 0x / 41 / 分组形式覆盖的跳过
        if f"0x{val}" in text or f"0X{val}" in text or f"0x41{val}" in text:
            continue
        # 明显非私钥的模式
        if len(set(val.lower())) < 5:
            continue
        seen_spans.add((m.start(), m.end()))
        add_pk(val, m.start(), "裸hex", need_ctx=True, strict=True)

    return found


def _trunc(s: str, n: int = 26) -> str:
    s = str(s)
    return s if len(s) <= n else s[:n] + "…"


def extract_from_json(obj, source: str, path: str = "$", out: list = None) -> list:
    """递归解析 JSON，按字段名关键词识别助记词 / 私钥（含各种变体）。

    字段名策略（避免把哈希类字段误判为私钥）：
      · 命中"正向字段名"（private_key / privkey / secretKey / 私钥 …）→ 严格识别
      · 命中"负向字段名"（*_sha256 / hash / txid / signature / id …）→ 直接跳过
      · 其余字段 → 不单独识别该值，但值里的文本仍会走 extract_from_text
    """
    if out is None:
        out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            if isinstance(v, str):
                if NEG_FIELD.search(kl):
                    continue
                if re.search(r"(mnemonic|seed_?phrase|助记词|recovery)", kl):
                    ok, _ = validate_mnemonic(v)
                    if ok:
                        out.append(Found("mnemonic", _dedupe_words(v), source, 0,
                                         f"json字段 {path}.{k}"))
                elif re.search(r"(private_?key|privkey|priv_?key|secret_?key|secretkey|私钥|wif|key_?hex|signer_?key)", kl):
                    # 统一走 recognize，覆盖 0x / 裸hex / WIF / base64 等变体
                    priv_hex, form, note = pk_recognize(v)
                    if priv_hex:
                        out.append(Found("privkey", priv_hex, source, 0,
                                         f"{note} [json字段 {path}.{k}] 原始形态={_trunc(v)}"))
                elif re.fullmatch(r"(pk|key|private)", kl.strip()):
                    # 字段名极短且明确（pk / key / private）
                    priv_hex, form, note = pk_recognize(v)
                    if priv_hex:
                        out.append(Found("privkey", priv_hex, source, 0,
                                         f"{note} [json字段 {path}.{k}] 原始形态={_trunc(v)}"))
                else:
                    # 其余字段：仅当值本身内含明显的私钥文本时才提取
                    # （例如 {"note": "privkey: 0x..."}），不做裸值回退识别
                    if len(v) < 4096:
                        out.extend(extract_from_text(v, f"{source}#{path}.{k}"))
            else:
                extract_from_json(v, source, f"{path}.{k}", out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            extract_from_json(v, source, f"{path}[{i}]", out)
    elif isinstance(obj, str):
        out.extend(extract_from_text(obj, source))
    return out


# --------------------------------------------------------------------------
# 文件 / 目录
# --------------------------------------------------------------------------
def load_file(path: str, report: LoadReport) -> list:
    """从单个文件加载。JSON 走结构化解析，其余走文本正则。"""
    found = []
    # 纯噪声文件直接跳过（APK 签名清单 / 依赖锁文件等）
    if NOISE_FILES.match(os.path.basename(path)):
        report.files_skipped += 1
        return found
    try:
        st = os.stat(path)
        if st.st_size > MAX_FILE_BYTES:
            report.files_skipped += 1
            report.errors.append(f"跳过（超过 {MAX_FILE_BYTES // 1024 // 1024}MB）: {path}")
            return found
        with open(path, "rb") as fh:
            raw = fh.read()
        report.files_scanned += 1
        report.bytes_read += len(raw)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw.decode("latin-1")
            except Exception:
                report.errors.append(f"编码无法解析: {path}")
                return found
    except PermissionError:
        report.errors.append(f"权限拒绝: {path}")
        return found
    except Exception as exc:
        report.errors.append(f"读取失败 {path}: {type(exc).__name__}")
        return found

    if path.lower().endswith(".json"):
        try:
            found.extend(extract_from_json(json.loads(text), path))
            # JSON 里也可能嵌着原始文本
            found.extend(extract_from_text(text, path, report))
            return found
        except Exception:
            pass

    found.extend(extract_from_text(text, path, report))
    return found


def scan_dir(root: str, report: LoadReport, keyword: str = "", exts: set = None) -> list:
    """递归扫描目录。keyword 为空时扫描所有文本类文件。"""
    found = []
    exts = exts or TEXT_EXTS
    kw_re = re.compile(keyword, re.I) if keyword else None

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            ext = os.path.splitext(fn)[1].lower()
            report.files_seen += 1
            if NOISE_FILES.match(fn) or ext in NOISE_EXTS:
                report.files_skipped += 1
                continue
            if kw_re is not None:
                # 关键词模式：文件名或扩展名匹配即可（允许无扩展名）
                if not (kw_re.search(fn) or kw_re.search(dirpath)):
                    report.files_skipped += 1
                    continue
            elif ext not in exts:
                report.files_skipped += 1
                continue
            else:
                # 扩展名合格，但若文件名/路径不含任何密钥线索且体积很大，
                # 跳过 —— 避免把上万个无关的源码/数据文件全读一遍
                if (report.fast and os.path.getsize(full) > FAST_SKIP_BYTES
                        and not KEY_HINT.search(fn) and not KEY_HINT.search(dirpath)):
                    report.files_skipped += 1
                    continue
            got = load_file(full, report)
            if got:
                found.extend(got)
                report.hits += len(got)
            if report.progress and report.files_scanned % 2000 == 0:
                print(f"  [扫描] 已读 {report.files_scanned} 文件，"
                      f"命中 {report.hits} 条", flush=True)
    return found


def dedupe(items: Iterable[Found]) -> list:
    """按规范值去重：同一私钥的不同变体会合并为一条，并保留全部原始来源。

    这正是"还原存储"的核心：无论文件里写的是 0x 前缀、大写、分组、
    WIF 还是补零形式，最终只保留一条规范记录，同时能追溯每一处变体。
    """
    seen = {}
    order = []
    for it in items:
        k = it.key()
        if k in seen:
            prev = seen[k]
            # 合并变体来源
            if it.variants:
                for v in it.variants:
                    prev.add_variant(v["source"], v["line"], v["origin"])
            else:
                prev.add_variant(it.source, it.line, "(text)")
            # 备注合并
            if it.note and it.note not in prev.note:
                prev.note = (prev.note + "; " + it.note).strip("; ")
            continue
        if not it.variants:
            it.add_variant(it.source, it.line, "(text)")
        seen[k] = it
        order.append(it)
    return order


def build_variant_store(found: list) -> dict:
    """构建"变体还原存储"：以规范私钥为主键，记录它所有原始写法与来源。

    返回结构（可直接 JSON 落盘）：
      {
        "<64hex 规范私钥>": {
            "fingerprint": "<sha256 前12位，用于安全引用>",
            "variant_count": N,
            "forms": ["0x前缀", "WIF 主网·压缩", ...],   # 识别出的形态类别
            "sources": [ {"source": "...", "line": 3, "origin": "0x4c08…"}, ... ],
            "canonical": { "hex": "...", "hex_0x": "...", "wif_compressed": "...", ... }
        }
      }
    """
    store = {}
    for it in found:
        if it.kind != "privkey":
            continue
        ph = it.value
        if ph not in store:
            forms = []
            m = re.search(r"^([^\[]+)", it.note or "")
            if m:
                forms.append(m.group(1).strip())
            store[ph] = {
                "fingerprint": pk_fp(ph),
                "variant_count": 0,
                "forms": forms,
                "sources": [],
                "canonical": pk_canonical(ph),
            }
        entry = store[ph]
        for v in it.variants:
            entry["sources"].append(v)
        entry["variant_count"] = len(entry["sources"])
        # 汇总形态描述
        for part in (it.note or "").split(";"):
            part = part.strip()
            m = re.match(r"^([^\[（(]+)", part)
            if m:
                label = m.group(1).strip()
                if label and label not in entry["forms"]:
                    entry["forms"].append(label)
    return store


def gather(scan_dirs=None, files=None, mnemonics=None, privkeys=None,
           keyword: str = "", exts: set = None,
           fast: bool = True, progress: bool = True) -> tuple:
    """统一入口：返回 (Found 列表, LoadReport)。

    fast=True 时对大且无密钥线索的文件快速跳过（大幅提速）。
    """
    report = LoadReport(fast=fast, progress=progress)
    items = []

    for d in (scan_dirs or []):
        if not os.path.isdir(d):
            report.errors.append(f"目录不存在: {d}")
            continue
        if progress:
            print(f"  [扫描] 进入目录 {d}", flush=True)
        got = scan_dir(d, report, keyword=keyword, exts=exts)
        items.extend(got)
        if progress:
            print(f"  [扫描] {d} 完成：已读 {report.files_scanned} 文件，"
                  f"累计命中 {len(items)} 条", flush=True)

    for f in (files or []):
        if os.path.isdir(f):
            items.extend(scan_dir(f, report, keyword=keyword, exts=exts))
        elif os.path.isfile(f):
            got = load_file(f, report)
            report.hits += len(got)
            items.extend(got)
        else:
            report.errors.append(f"文件不存在: {f}")

    for m in (mnemonics or []):
        s = _dedupe_words(m)
        ok, why = validate_mnemonic(s)
        if ok:
            items.append(Found("mnemonic", s, "cli", 0, "命令行参数"))
        else:
            report.errors.append(f"命令行助记词无效: {why}")

    for p in (privkeys or []):
        items.append(Found("privkey", p.strip(), "cli", 0, "命令行参数"))

    return dedupe(items), report
