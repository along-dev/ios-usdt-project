#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W-IOS-PKG · IPA 组装流水线（参数化：〈外壳 × dylib 代际〉；不预设某一代）

★ X-3 合并版（2026-10-03，Owner 授权）：以本脚本为骨架，并入参照终端 B 的
  `05-ios/tools/ipa_assemble.py` 两项能力：
    ① Mach-O `LC_LOAD_DYLIB` 注入（含如实 `inject_mode` 字段）；
    ② `manifest.plist` 生成（三类 asset ＋ `itms-services://` OTA 入口）。
  骨架方原有四项**保持不变**：登记表强制 / 反向断言 / 符号链接保真（`external_attr`）/ 可复现。

用法：
  python ipa_pipeline.py seed  [--dir 05-ios/reference/ipa]
  python ipa_pipeline.py build --base-shell <ipa> --dylib <path> --version <str>
          [--inject slot|append|auto|none]   # 默认 slot（保守：与合并前行为一致）
          [--extra-dylib <path>]...          # 额外载荷，落盘待运行期 dlopen
          [--manifest-url <ipa 的公开 URL>] [--icon57-url <u>] [--icon512-url <u>] [--title <s>]
          [--out <ipa>] [--sign <p12>] [--allow-unregistered] [--allow-landed-only]
  python ipa_pipeline.py verify --ipa <ipa>

`inject_mode` 取值全集（**与 B 的 `ipa_assemble.py` 对齐，全仓只有这一套**）：
  slot-replaced     基座已声明 `LC_LOAD_DYLIB → FilzaApplySandboxExt.dylib` ⇒ 只替换该槽位内容，
                    **主二进制零改动**（ncmds 不变）。
  linkedit-appended 基座未声明槽位 ⇒ 在 load command 区后的零填充里**追加**一条 `LC_LOAD_DYLIB`
                    （bootstrap 模式；**ncmds +1**）。
  landed-only       两种改写都不可行（如 fat / 无空洞）⇒ **文件已落盘但不会被加载**。
                    ★ **绝不假装已注入**；且须显式 `--allow-landed-only`，否则拒绝产出。
  none              `--inject none`：只落盘，不走 Mach-O 注入（显式声明用）。

红线（违反即拒绝）：
  1. 外壳 / dylib 的 sha256 必须在 registry.json 登记（`--allow-unregistered` 可豁免，记入 manifest）。
  2. `slot` 模式要求基座已声明槽位；`append` 模式要求基座**未**声明且存在安全空洞；均不满足 ⇒ 拒绝。
  3. `landed-only` 结果须显式 `--allow-landed-only`。
  4. 无签名产出，文件名**必须**含 `-unsigned`。
  5. 重打包保留符号链接与权限位（`external_attr` / `create_system`）；全程**不落地解包**（规避 Windows MAX_PATH）。
  6. 产物 sha256 **可复现**：保留源条目顺序与时间戳。
"""
import argparse
import hashlib
import json
import os
import plistlib
import struct
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, "registry.json")
TWEAK_DYLIB_NAME = "FilzaApplySandboxExt.dylib"
MHA_BUNDLE_ID = "com.apple.mobile.MobileHouseArrest"
FIXED_EPOCH = (1980, 1, 1, 0, 0, 0)
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
INJECT_DIR = "Frameworks"

MH_MAGIC_64 = 0xFEEDFACF
MH_MAGIC = 0xFEEDFACE
LC_LOAD_DYLIB = 0x0C
LC_LOAD_WEAK_DYLIB = 0x80000018
LC_REEXPORT_DYLIB = 0x18
LC_CODE_SIGNATURE = 0x1D
FAT_MAGIC = 0xCAFEBABE
FAT_MAGIC_64 = 0xCAFEBABF

INJECT_MODES = ("slot-replaced", "linkedit-appended", "landed-only")

# ★ DS 门禁白名单（裁定，⌛2026-10-03）：`--bundle-id` 的取值**必须命中 registry 中该基座
#   声明的允许集合**，命令行不得自由给。集合由 `seed` 生成、可人工策展。
#   下列基座**登记为不可组装**（裸壳 / 非交付参考件）⇒ 允许集合为空。
SHELLS_NOT_FOR_ASSEMBLY = {
    "Filza_4.0.0_Crack_OK.ipa",
    "Filza_4.0_NoUS_Crack.ipa",
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def die(msg, code=2):
    sys.stderr.write("REFUSE: " + msg + "\n")
    sys.exit(code)


def rel(p):
    try:
        return os.path.relpath(p, REPO_ROOT).replace("\\", "/")
    except ValueError:
        return os.path.abspath(p).replace("\\", "/")


# ---------------------------------------------------------------- Mach-O
def macho_load_dylibs(buf):
    """返回 (dylib 路径列表, 是否含 LC_CODE_SIGNATURE, ncmds)。仅解析 32/64 位小端。"""
    if len(buf) < 32:
        return [], False, 0
    magic = struct.unpack("<I", buf[:4])[0]
    if magic not in (MH_MAGIC_64, MH_MAGIC):
        return [], False, 0
    is64 = magic == MH_MAGIC_64
    ncmds = struct.unpack("<I", buf[16:20])[0]
    off = 32 if is64 else 28
    dylibs, signed = [], False
    for _ in range(ncmds):
        if off + 8 > len(buf):
            break
        cmd, size = struct.unpack("<II", buf[off:off + 8])
        if size <= 0:
            break
        if cmd in (LC_LOAD_DYLIB, LC_LOAD_WEAK_DYLIB, LC_REEXPORT_DYLIB):
            no = struct.unpack("<I", buf[off + 8:off + 12])[0]
            s = off + no
            e = buf.find(b"\x00", s)
            if e > s:
                dylibs.append(buf[s:e].decode("utf-8", "replace"))
        elif cmd == LC_CODE_SIGNATURE:
            signed = True
        off += size
    return dylibs, signed, ncmds


def macho_is_fat(head):
    if len(head) < 4:
        return False
    return struct.unpack(">I", head[:4])[0] in (FAT_MAGIC, FAT_MAGIC_64)


def macho_inject_thin(buf, dylib_install_path):
    """
    在 thin 64 位 Mach-O 的 load command 区**零填充**处追加一条 LC_LOAD_DYLIB。
    返回 (ok, detail)。成功时 ncmds 与 sizeofcmds 各 +1 条命令长度。
    """
    data = bytearray(buf)
    if len(data) < 32 or struct.unpack("<I", data[:4])[0] != MH_MAGIC_64:
        return False, "非 thin 64 位 Mach-O"
    ncmds = struct.unpack("<I", data[16:20])[0]
    sizeofcmds = struct.unpack("<I", data[20:24])[0]
    lc_end = 32 + sizeofcmds
    if lc_end + 16 > len(data):
        return False, "load command 区越界"

    name_bytes = dylib_install_path.encode("utf-8") + b"\x00"
    cmdsize = (24 + len(name_bytes) + 7) & ~7
    pad = cmdsize - 24 - len(name_bytes)
    lc = (LC_LOAD_DYLIB.to_bytes(4, "little") + cmdsize.to_bytes(4, "little") +
          (24).to_bytes(4, "little") + (0).to_bytes(4, "little") +
          (0x00010000).to_bytes(4, "little") + (0x00010000).to_bytes(4, "little") +
          name_bytes + b"\x00" * pad)
    need = len(lc)

    if any(b != 0 for b in data[lc_end:lc_end + 16]):
        return False, "load command 区后非零填充（无安全空洞）"
    avail, i = 0, lc_end
    while i < len(data) and data[i] == 0 and avail < need:
        avail += 1
        i += 1
    if avail < need:
        return False, f"零填充不足（需 {need} 得 {avail}）"

    data[lc_end:lc_end + need] = lc
    data[16:20] = (ncmds + 1).to_bytes(4, "little")
    data[20:24] = (sizeofcmds + need).to_bytes(4, "little")
    return bytes(data), f"追加 LC_LOAD_DYLIB({need}B) 至偏移 {lc_end}"


# ---------------------------------------------------------------- 基座元信息
def read_base_meta(zf):
    names = zf.namelist()
    app = None
    for n in names:
        if n.endswith(".app/Info.plist"):
            app = n[: -len("Info.plist")]
            break
    if not app:
        return None
    info = plistlib.loads(zf.read(app + "Info.plist"))
    exe = info.get("CFBundleExecutable")
    return {"app_prefix": app, "app_name": app.rstrip("/").split("/")[-1],
            "exe_name": exe, "info": info, "names": names}


# ---------------------------------------------------------------- registry
def load_registry():
    if not os.path.exists(REGISTRY):
        die("registry.json 不存在；先跑 `seed`", 2)
    with open(REGISTRY, "r", encoding="utf-8") as f:
        return json.load(f)


def cmd_seed(args):
    d = args.dir
    shells, dylibs = [], []
    for fn in sorted(os.listdir(d)):
        if not fn.lower().endswith(".ipa"):
            continue
        p = os.path.join(d, fn)
        with zipfile.ZipFile(p) as z:
            meta = read_base_meta(z)
            if not meta:
                continue
            dpath = meta["app_prefix"] + INJECT_DIR + "/" + TWEAK_DYLIB_NAME
            exe_b = z.read(meta["app_prefix"] + meta["exe_name"]) if meta["exe_name"] else b""
            dyl, signed, _ = macho_load_dylibs(exe_b)
            bid = meta["info"].get("CFBundleIdentifier")
            not_for_asm = fn in SHELLS_NOT_FOR_ASSEMBLY
            _notes = []
            if not_for_asm:
                _notes.append("已登记为**不可组装**（裸壳/参考素材）")
            if signed:
                _notes.append("基座**已签名**（LC_CODE_SIGNATURE）⇒ 当前不可组装（需未签名壳或重签步骤）")
            shells.append({
                "id": fn, "path": rel(p), "sha256": sha256_file(p), "bytes": os.path.getsize(p),
                "bundle_id": bid,
                # ★ 允许集合：登记在册，`build --bundle-id` 只接受其中的值
                "allowed_bundle_ids": ([] if not_for_asm else ([bid] if bid else [])),
                "signed": bool(signed),
                "note": "；".join(_notes),
                "has_load_command": any(TWEAK_DYLIB_NAME in x for x in dyl),
                "dylib_present": dpath in meta["names"],
            })
            if dpath in meta["names"]:
                db = z.read(dpath)
                dylibs.append({"id": "%s::%s" % (fn, TWEAK_DYLIB_NAME),
                               "sha256": hashlib.sha256(db).hexdigest(),
                               "bytes": len(db), "extracted_from": fn})
    reg = {"schema": 1, "generated_at": args.stamp, "shells": shells, "dylibs": dylibs}
    with open(REGISTRY, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
    print("seeded: shells=%d dylibs=%d -> %s" % (len(shells), len(dylibs), REGISTRY))
    return 0


# ---------------------------------------------------------------- manifest.plist
def build_manifest_plist(ipa_url, bundle_id, bundle_version, title,
                         subtitle=None, icon57_url=None, icon512_url=None):
    """
    OTA 安装清单：三类 asset（software-package / display-image / full-size-image）。
    字段与参照终端 B 的 `ipa_assemble.py:554 build_manifest_plist` 语义一致。
    """
    assets = [{"kind": "software-package", "url": ipa_url}]
    if icon57_url:
        assets.append({"kind": "display-image", "url": icon57_url})
    if icon512_url:
        assets.append({"kind": "full-size-image", "url": icon512_url})
    item = {"assets": assets, "metadata": {
        "bundle-identifier": bundle_id, "bundle-version": str(bundle_version),
        "kind": "software", "title": title}}
    if subtitle:
        item["metadata"]["subtitle"] = subtitle
    return {"items": [item]}, assets


# ---------------------------------------------------------------- build
def cmd_build(args):
    reg = load_registry()
    shell_sha, dylib_sha = sha256_file(args.base_shell), sha256_file(args.dylib)
    reg_shells = {s["sha256"] for s in reg.get("shells", [])}
    reg_dylibs = {d["sha256"] for d in reg.get("dylibs", [])}
    if shell_sha not in reg_shells and not args.allow_unregistered:
        die("外壳未登记（sha256=%s）: %s" % (shell_sha[:16], args.base_shell), 3)
    if dylib_sha not in reg_dylibs and not args.allow_unregistered:
        die("dylib 未登记（sha256=%s）: %s" % (dylib_sha[:16], args.dylib), 4)

    out = args.out or os.path.join(
        REPO_ROOT, "05-ios", "dist",
        "FilzaSlop-%s%s.ipa" % (args.version, "" if args.sign else "-unsigned"))
    if not args.sign and "-unsigned" not in os.path.basename(out):
        die("无签名产出的文件名必须含 `-unsigned`：%s" % out, 5)
    if args.sign and "-unsigned" in os.path.basename(out):
        die("已签名产出的文件名不应含 `-unsigned`：%s" % out, 5)

    with zipfile.ZipFile(args.base_shell) as z:
        meta = read_base_meta(z)
        if not meta:
            die("外壳内找不到 *.app/Info.plist", 6)
        app, exe = meta["app_prefix"], meta["exe_name"]
        info = dict(meta["info"])
        # ★ bundle-id 白名单（裁定：登记在册，**不接受命令行自由值**）
        shell_entry = next((s for s in reg.get("shells", []) if s["sha256"] == shell_sha), None)
        # ★ Y-03：**运行期再校验一次** `SHELLS_NOT_FOR_ASSEMBLY`（原先它只在 seed 期生效，
        #   手工改 registry.json 即可让运行期放行裸壳）—— 不依赖"别手改 registry"这类纪律。
        if shell_entry is not None and shell_entry.get("id") in SHELLS_NOT_FOR_ASSEMBLY:
            die("该基座在**代码常量** SHELLS_NOT_FOR_ASSEMBLY 中登记为不可组装"
                "（运行期二次校验，不依赖 registry.json 内容）", 7)
        actual_bid = info.get("CFBundleIdentifier")
        if shell_entry is None:                       # 仅在 --allow-unregistered 下可达
            allowed_bids = [actual_bid] if actual_bid else []
        else:
            allowed_bids = list(shell_entry.get("allowed_bundle_ids") or [])
        want_bid = args.bundle_id or actual_bid
        if not allowed_bids:
            die("该基座在 registry 中登记为**不可组装**（allowed_bundle_ids 为空：裸壳/参考素材）", 7)
        if want_bid not in allowed_bids:
            die("bundle id %r 不在该基座的**登记允许集合** %s 内（白名单驱动，不接受任意值）"
                % (want_bid, allowed_bids), 7)
        if args.bundle_id and args.bundle_id != actual_bid:
            die("本轮只支持在登记集合内**确认**原 bundle id；改写 Info.plist 的 bundle id "
                "须另立卡（并考虑与之绑定的渲染码标识）", 7)
        if (app + "_CodeSignature/") in meta["names"]:
            die("外壳已签名；本流水线只接受未签名壳", 9)
        exe_bytes = z.read(app + exe)
        dyls, signed_bin, ncmds_before = macho_load_dylibs(exe_bytes)
        if signed_bin:
            die("外壳主二进制含 LC_CODE_SIGNATURE；只接受未签名壳", 9)
        slot_arc = app + INJECT_DIR + "/" + TWEAK_DYLIB_NAME
        has_slot = any(TWEAK_DYLIB_NAME in d for d in dyls)

    # ---- 注入模式决策（取值全集与 B 对齐）----
    # ★ X-07：初值取 **landed-only**（失败方向安全）——若决策链将来新增模式却漏赋值，
    #   landed-only 守卫会拒绝产出，而不是静默落盘。
    inject_mode, inject_detail, patched_exe = "landed-only", "未尝试", None
    if args.inject == "slot":
        if not has_slot:
            die("外壳是**裸壳**：主二进制无 LC_LOAD_DYLIB → %s；"
                "`--inject slot` 无法注入（可改用 `--inject auto|append` 追加载入命令）"
                % TWEAK_DYLIB_NAME, 8)
        inject_mode, inject_detail = "slot-replaced", "替换已声明槽位内容；主二进制零改动"
    elif args.inject == "append":
        if has_slot:
            die("`--inject append` 要求基座**未**声明槽位；该基座已有", 8)
        if macho_is_fat(exe_bytes[:8]):
            inject_mode, inject_detail = "landed-only", "fat 架构需外部分片，跳过 Mach-O 改写"
        else:
            patched, detail = macho_inject_thin(exe_bytes, "@executable_path/%s/%s" % (INJECT_DIR, TWEAK_DYLIB_NAME))
            if patched:
                patched_exe, inject_mode, inject_detail = patched, "linkedit-appended", detail
            else:
                inject_mode, inject_detail = "landed-only", "Mach-O 改写未成功：" + detail
    elif args.inject == "auto":
        if has_slot:
            inject_mode, inject_detail = "slot-replaced", "替换已声明槽位内容；主二进制零改动"
        elif macho_is_fat(exe_bytes[:8]):
            inject_mode, inject_detail = "landed-only", "fat 架构需外部分片，跳过 Mach-O 改写"
        else:
            patched, detail = macho_inject_thin(exe_bytes, "@executable_path/%s/%s" % (INJECT_DIR, TWEAK_DYLIB_NAME))
            if patched:
                patched_exe, inject_mode, inject_detail = patched, "linkedit-appended", detail
            else:
                inject_mode, inject_detail = "landed-only", "Mach-O 改写未成功：" + detail
    else:  # none —— ★ 不发新值：语义等同「未注入、仅落盘」⇒ 归入 landed-only
        inject_mode, inject_detail = "landed-only", "`--inject none`：显式选择不注入，仅落盘"

    assert inject_mode in INJECT_MODES, f"inject_mode 越出取值全集：{inject_mode!r}"
    if inject_mode == "landed-only" and not args.allow_landed_only:
        die("注入结果为 landed-only（文件落盘但不会被加载，**不等于已注入**）；"
            "确认接受请加 `--allow-landed-only`", 12)

    dylib_bytes = open(args.dylib, "rb").read()
    extras = []
    for p in (args.extra_dylib or []):
        h = sha256_file(p)
        if h not in reg_dylibs and not args.allow_unregistered:
            die("额外 dylib 未登记（sha256=%s）: %s" % (h[:16], p), 4)
        extras.append((os.path.basename(p), open(p, "rb").read(), h))

    # ---- 组装（流式：不落地解包，规避 Windows MAX_PATH）----
    replacements = {}
    replacements[slot_arc] = dylib_bytes        # 三种模式都落盘到槽位路径；区别只在是否改写主二进制
    if patched_exe is not None:
        replacements[app + exe] = patched_exe
    for n, b, _h in extras:
        replacements[app + INJECT_DIR + "/" + n] = b

    tmp = out + ".part"
    with zipfile.ZipFile(args.base_shell) as zi, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
        for zi_ in zi.infolist():
            name = zi_.filename
            if name == app + "Info.plist":
                info.pop("CFBundleURLTypes", None)
                info["FilzaSlopVersion"] = args.version
                data = plistlib.dumps(info, fmt=plistlib.FMT_BINARY if zi.read(name)[:8] == b"bplist00" else plistlib.FMT_XML)
            elif name in replacements:
                data = replacements.pop(name)
            else:
                data = zi.read(name)
            ni = zipfile.ZipInfo(name, date_time=zi_.date_time)
            ni.create_system = zi_.create_system or 3
            ni.external_attr = zi_.external_attr
            ni.compress_type = zipfile.ZIP_DEFLATED
            if name == slot_arc:                       # 仅被替换的 dylib 槽位设可执行位
                ni.external_attr = (0o100755 << 16)
            zo.writestr(ni, data)
        for name, data in replacements.items():          # 基座没有的新条目
            ni = zipfile.ZipInfo(name, date_time=FIXED_EPOCH)
            ni.create_system = 3
            ni.external_attr = (0o100755 << 16)
            zo.writestr(ni, data)
    os.replace(tmp, out)

    signed = run_sign(args.sign, out) if args.sign else False

    # ---- manifest.plist（OTA）----
    manifest_path = out + ".manifest.plist"
    itms = None
    manifest_assets = []
    if args.manifest_url:
        man, manifest_assets = build_manifest_plist(
            args.manifest_url, info.get("CFBundleIdentifier"), args.version,
            args.title or info.get("CFBundleDisplayName") or info.get("CFBundleName") or args.version,
            icon57_url=args.icon57_url, icon512_url=args.icon512_url)
        with open(manifest_path, "wb") as f:
            f.write(plistlib.dumps(man, fmt=plistlib.FMT_XML))
        man_url = args.manifest_url.rsplit("/", 1)[0] + "/" + os.path.basename(manifest_path)
        itms = "itms-services://?action=download-manifest&url=" + man_url

    out_sha = sha256_file(out)
    manifest = {
        "version": args.version, "signed": signed,
        "bundle_id": want_bid, "bundle_id_confirmed": args.bundle_id or None,
        "bundle_id_whitelist": allowed_bids,
        "inject_mode": inject_mode, "inject_detail": inject_detail,
        "ncmds_before": ncmds_before,
        "ncmds_after": macho_load_dylibs(_read_main(out, app, exe))[2],
        "base_shell": {"path": rel(args.base_shell), "sha256": shell_sha},
        "dylib": {"path": rel(args.dylib), "sha256": dylib_sha},
        "extra_dylibs": [{"name": n, "sha256": h} for n, _b, h in extras],
        "manifest_assets": manifest_assets,
        "itms_services_url": itms,
        "output": {"path": rel(out), "sha256": out_sha, "bytes": os.path.getsize(out)},
        "registry_hit": {"shell": shell_sha in reg_shells, "dylib": dylib_sha in reg_dylibs},
    }
    with open(out + ".manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("built:", out)
    print("  sha256=%s" % out_sha)
    print("  bytes=%d" % os.path.getsize(out))
    print("  inject_mode=%s（%s）" % (inject_mode, inject_detail))
    print("  ncmds: %d -> %s" % (ncmds_before, manifest["ncmds_after"]))
    if itms:
        print("  manifest.plist=%s" % manifest_path)
        print("  OTA=%s" % itms)
    return 0


def _read_main(ipa, app, exe):
    with zipfile.ZipFile(ipa) as z:
        return z.read(app + exe)


def run_sign(p12, ipa):
    from shutil import which
    tool = os.environ.get("IPA_SIGN_TOOL", "zsign")
    if not which(tool):
        die("签名工具 %r 不可用（设 IPA_SIGN_TOOL 指定）。签名段是外部依赖，见设计件 §6" % tool, 10)
    import subprocess
    r = subprocess.run([tool, "-k", p12, "-o", ipa, ipa])
    if r.returncode != 0:
        die("签名失败（%s 退出码 %d）" % (tool, r.returncode), 11)
    return True


# ---------------------------------------------------------------- verify
def cmd_verify(args):
    with zipfile.ZipFile(args.ipa) as z:
        meta = read_base_meta(z)
        if not meta:
            die("找不到 .app", 6)
        app, exe, info = meta["app_prefix"], meta["exe_name"], meta["info"]
        dyls, _s, ncmds = macho_load_dylibs(z.read(app + exe))
        dpath = app + INJECT_DIR + "/" + TWEAK_DYLIB_NAME
        present = dpath in meta["names"]
    print("ipa        :", args.ipa)
    print("sha256     :", sha256_file(args.ipa))
    print("bundle_id  :", info.get("CFBundleIdentifier"))
    print("url_types  :", "PRESENT(BAD)" if "CFBundleURLTypes" in info else "removed(OK)")
    print("slop_ver   :", info.get("FilzaSlopVersion"))
    print("dylib      :", dpath if present else "MISSING(BAD)")
    print("load_cmd   :", "OK" if any(TWEAK_DYLIB_NAME in x for x in dyls) else "MISSING(BAD)")
    print("ncmds      :", ncmds)
    return 0


def main():
    ap = argparse.ArgumentParser(description="W-IOS-PKG IPA 组装流水线（X-3 合并版）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("seed")
    s.add_argument("--dir", default=os.path.join(REPO_ROOT, "05-ios", "reference", "ipa"))
    s.add_argument("--stamp", default="")

    b = sub.add_parser("build")
    b.add_argument("--base-shell", required=True)
    b.add_argument("--dylib", required=True)
    b.add_argument("--bundle-id", help="★ 只用于**确认**：取值必须命中 registry 中该基座的允许集合")
    b.add_argument("--extra-dylib", action="append")
    b.add_argument("--version", required=True)
    b.add_argument("--inject", choices=["slot", "append", "auto", "none"], default="auto")
    b.add_argument("--out")
    b.add_argument("--sign")
    b.add_argument("--manifest-url")
    b.add_argument("--icon57-url")
    b.add_argument("--icon512-url")
    b.add_argument("--title")
    b.add_argument("--allow-unregistered", action="store_true")
    b.add_argument("--allow-landed-only", action="store_true")

    v = sub.add_parser("verify")
    v.add_argument("--ipa", required=True)

    a = ap.parse_args()
    return {"seed": cmd_seed, "build": cmd_build, "verify": cmd_verify}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
