# -*- coding: utf-8 -*-
"""Unpack strip.apk using the recovered byte-level algorithm from attachBaseContext/mcebjxrn.

Algorithm (per byte at index i):
    b = ct[i] & 0xFF
    b = (b - 199) & 0xFF
    b = (b * 57) & 0xFF
    b = ror8(b, 3)          # ushr 3 | shl 5  (8-bit)
    b = ror8(b, 2)          # ushr 2 | shl 6  (8-bit)
    k = (i * 189 + 203 + (i >> 7)) ^ 232
    b = (b - k) & 0xFF
    b = (b * 237) & 0xFF
    b = b ^ 57
    b = (b * 243) & 0xFF
Layout: [24 bytes header][int32 length][length bytes of the above] -> GZIP
"""
import sys, io, os, struct, gzip, hashlib, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

EX = r"E:\ios漏洞\recon\apk\extracted"
OUT = r"E:\ios漏洞\recon\apk\unpacked"
os.makedirs(OUT, exist_ok=True)

def ror8(x, n):
    x &= 0xFF
    return ((x >> n) | (x << (8 - n))) & 0xFF

def decode(ct):
    out = bytearray()
    for i, c in enumerate(ct):
        b = c & 0xFF
        b = (b - 199) & 0xFF
        b = (b * 57) & 0xFF
        b = ror8(b, 3)
        b = ror8(b, 2)
        k = ((i * 189 + 203 + (i >> 7)) ^ 232) & 0xFF
        b = (b - k) & 0xFF
        b = (b * 237) & 0xFF
        b = b ^ 57
        b = (b * 243) & 0xFF
        out.append(b)
    return bytes(out)

def unpack(asset_file, label):
    raw = open(os.path.join(EX, asset_file), "rb").read()
    print(f"\n===== {asset_file} ({len(raw)} bytes) =====")
    print(f"  header[0:24] = {raw[:24].hex()}")
    n, = struct.unpack_from(">i", raw, 24)   # DataInputStream.readInt is BIG-endian
    print(f"  declared length (BE) = {n}")
    if n <= 0 or n > len(raw) - 28:
        n, = struct.unpack_from("<i", raw, 24)
        print(f"  retry little-endian  = {n}")
    body = raw[28:28 + n]
    print(f"  body bytes = {len(body)}")
    dec = decode(body)
    print(f"  decoded head = {dec[:16].hex()}  (gzip magic? {dec[:2] == b'\\x1f\\x8b'})")
    if dec[:2] == b"\x1f\x8b":
        try:
            data = gzip.decompress(dec)
            print(f"  [+] GUNZIP OK -> {len(data)} bytes")
            print(f"      sha256 = {hashlib.sha256(data).hexdigest()}")
            print(f"      head   = {data[:16].hex()}")
            # detect type
            if data[:4] == b"dex\n":
                print("      >>> DEX FILE (in-memory dex payload)")
            kind = "dex" if data[:4] == b"dex\n" else "blob"
            outp = os.path.join(OUT, f"{label}.{kind}")
            open(outp, "wb").write(data)
            print(f"      written: {outp}")
            return data
        except Exception as e:
            print(f"  [!] gunzip failed: {e}")
            open(os.path.join(OUT, label + ".raw.gz"), "wb").write(dec)
            return None
    else:
        # maybe not gzip; save the decoded blob
        outp = os.path.join(OUT, label + ".decoded")
        open(outp, "wb").write(dec)
        print(f"  saved decoded blob: {outp}")
        return dec

if __name__ == "__main__":
    unpack("assets_azjgiGhXOE", "azjgiGhXOE")
    unpack("assets_taEtClxrsxC", "taEtClxrsxC")
