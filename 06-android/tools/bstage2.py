# -*- coding: utf-8 -*-
"""Unpack b_stage: records are [int32 size][int16 nameLen][name][size bytes], but scan-verified."""
import sys, io, os, re, zipfile, struct, hashlib, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from Crypto.Cipher import AES
from Crypto.Util import Counter

from _payload_key import KEY_HEX
KEY = bytes.fromhex(KEY_HEX)
z = zipfile.ZipFile(r"E:\ios漏洞\recon\apk\unpacked\inner_b.apk")
raw = z.read("assets/0gvw74arcr5sml")
iv, ct = raw[:16], raw[16:]
pt = AES.new(KEY, AES.MODE_CTR,
             counter=Counter.new(128, initial_value=int.from_bytes(iv, "big"),
                                 allow_wraparound=True)).decrypt(ct)

OUT = r"E:\ios漏洞\recon\apk\unpacked\b_stage"
os.makedirs(OUT, exist_ok=True)

# From the trace: [int32 sz][int16 nl][name][sz bytes] -- but sz is the size of the
# *following* plaintext blob which may itself be base64/encoded. The chain broke because
# after "1.bt" the 40 bytes are base64 text, and the NEXT record starts right after.
#
# Robust approach: find all "[int32][int16 len in 1..40][ASCII name]" boundaries.
NAME = re.compile(rb"[A-Za-z0-9_.\-]{1,40}\Z")
cands = []
for off in range(0, len(pt) - 8):
    nl, = struct.unpack_from(">h", pt, off + 4)
    if not (1 <= nl <= 40): continue
    name = pt[off+6:off+6+nl]
    if not re.fullmatch(rb"[A-Za-z0-9_.\-]+", name or b"x"): continue
    sz, = struct.unpack_from(">i", pt, off)
    if not (0 < sz < len(pt)): continue
    nxt = off + 6 + nl + sz
    # next boundary must also be a plausible record (or EOF)
    ok = False
    if nxt >= len(pt) - 4:
        ok = True
    elif nxt + 8 < len(pt):
        n2, = struct.unpack_from(">h", pt, nxt + 4)
        if 1 <= n2 <= 40:
            nm2 = pt[nxt+6:nxt+6+n2]
            if re.fullmatch(rb"[A-Za-z0-9_.\-]+", nm2 or b"x"):
                s2, = struct.unpack_from(">i", pt, nxt)
                ok = 0 < s2 < len(pt)
    if ok:
        cands.append((off, name.decode(), sz))

print(f"candidate boundaries: {len(cands)}")
for off, name, sz in cands[:60]:
    print(f"  off={off:>9} size={sz:>9} name={name}")

# Take the longest chain
if cands:
    # greedy from first
    chain = []
    cur = cands[0][0]
    idx = {c[0]: c for c in cands}
    while cur in idx and len(chain) < 200:
        off, name, sz = idx[cur]
        chain.append((off, name, sz))
        cur = off + 6 + len(name) + sz
    print(f"\n=== chain: {len(chain)} records ===")
    manifest = []
    for off, name, sz in chain:
        data = pt[off+6+len(name):off+6+len(name)+sz]
        safe = re.sub(r"[^A-Za-z0-9_.\-]", "_", name)
        open(os.path.join(OUT, safe), "wb").write(data)
        h = hashlib.sha256(data).hexdigest()
        manifest.append({"name": name, "size": sz, "sha256": h})
        print(f"  {name:30s} {sz:>9} sha256={h[:28]} head={data[:12].hex()}")
    json.dump(manifest, open(os.path.join(OUT, "_manifest.json"), "w"), indent=1)
    print(f"\n[+] extracted {len(chain)} -> {OUT}")
