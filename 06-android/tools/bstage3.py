# -*- coding: utf-8 -*-
"""Parse b_stage blob by locating record headers [int32 sz][int16 nl][name] and slicing."""
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

# Find every header: [int32 sz][int16 nl][printable name of len nl]
hdr = []
for off in range(0, len(pt) - 6):
    sz, = struct.unpack_from(">i", pt, off)
    nl, = struct.unpack_from(">h", pt, off + 4)
    if not (1 <= nl <= 40):
        continue
    if off + 6 + nl > len(pt):
        continue
    nm = pt[off + 6:off + 6 + nl]
    if not re.fullmatch(rb"[A-Za-z0-9_.\-]+", nm):
        continue
    if sz <= 0 or sz > len(pt):
        continue
    hdr.append((off, sz, nm.decode()))

print(f"raw headers found: {len(hdr)}")
# The data region for record i is [off+6+nl, next_off). The 'sz' appears to be the
# DECODED size; the stored data is the slice up to the next header.
# Keep only headers whose gap to the next header is >= 0
hdr.sort()
recs = []
for i, (off, sz, nm) in enumerate(hdr):
    data_start = off + 6 + len(nm)
    data_end = hdr[i+1][0] if i + 1 < len(hdr) else len(pt)
    gap = data_end - data_start
    recs.append((off, sz, nm, data_start, gap))

print(f"\n{'name':28s} {'declared':>10} {'gap':>10}  ratio")
for off, sz, nm, ds, gap in recs:
    r = gap / sz if sz else 0
    print(f"{nm:28s} {sz:>10} {gap:>10}  {r:.3f}")

manifest = []
for off, sz, nm, ds, gap in recs:
    data = pt[ds:ds+gap]
    safe = re.sub(r"[^A-Za-z0-9_.\-]", "_", nm)
    open(os.path.join(OUT, safe), "wb").write(data)
    manifest.append({"name": nm, "declared": sz, "stored": gap,
                     "sha256": hashlib.sha256(data).hexdigest()})
json.dump(manifest, open(os.path.join(OUT, "_manifest.json"), "w"), indent=1)
print(f"\n[+] wrote {len(recs)} files -> {OUT}")
