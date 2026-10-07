# -*- coding: utf-8 -*-
"""Decrypt b.apk's 0gvw74arcr5sml: AES with key from hex string, IV = first 16 bytes.

From bytecode go0bxm7p04:
  key = hexdecode("<32B 载荷密钥 · 见 06-android/tools/_payload_key.py>")  # 32B
  modeStr = xhfvif([0x6fb0,0x6fb4,0x6fa2,0x6fde,0x6fb2,0x6fa5,0x6fa3,0x6fde,
                    0x6fbf,0x6f9e,0x6fa1,0x6f90,0x6f95,0x6f95,0x6f98,0x6f9f,0x6f96], 0x6ff1)
  keyAlg  = xhfvif([28592,28596,28578], 28657)   # "AES"
  data = asset bytes ; iv = data[:16] ; ct = data[16:]
  cipher.init(DECRYPT_MODE, SecretKeySpec(key, keyAlg), IvParameterSpec(iv))
  pt = cipher.doFinal(ct)
  then: [int32 BE count] then count x { [int16 BE nameLen][name UTF8][int32 BE size][size bytes] }

★ 解析格式实证（D0-C1 实跑核对，2026-09-29）：
  上述 count 前缀格式经 CTR 明文实测【完全吻合】——count=40，40 条记录全部
  解析成功且恰好消费完整个明文（slack=0）。故【不要】按 bstage.py:20 的
  "重复 [int32 size][int16 nameLen][name]" 去改本解析器：该格式在同一份数据上
  解析到第 2 条即断裂（sz=2049917272 为乱值）。本卡只修正 AES 模式选择，不动解析器。
"""
import sys, io, os, struct, hashlib, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from Crypto.Cipher import AES
from Crypto.Util import Counter

X = 28657  # 0x6FF1
def xhfvif(ints, k=X):
    return "".join(chr(i ^ k) for i in ints)

mode = xhfvif([0x6fb0,0x6fb4,0x6fa2,0x6fde,0x6fb2,0x6fa5,0x6fa3,0x6fde,
               0x6fbf,0x6f9e,0x6fa1,0x6f90,0x6f95,0x6f95,0x6f98,0x6f9f,0x6f96])
keyalg = xhfvif([28592, 28596, 28578])
print(f"cipher mode string = {mode!r}")
print(f"key algorithm      = {keyalg!r}")

from _payload_key import KEY_HEX
KEY = bytes.fromhex(KEY_HEX)
print(f"key ({len(KEY)} bytes) = {KEY.hex()}")

# load asset
zpath = r"E:\ios漏洞\recon\apk\unpacked\inner_b.apk"
import zipfile
z = zipfile.ZipFile(zpath)
raw = z.read("assets/0gvw74arcr5sml")
print(f"\nasset 0gvw74arcr5sml = {len(raw)} bytes")
iv, ct = raw[:16], raw[16:]
print(f"  IV  = {iv.hex()}")
print(f"  ct  = {len(ct)} bytes")

# derive AES mode from the string (e.g. "AES/CTR/NoPadding")
# ★ D0-C1 修正：必须按 parts[1]（算法段）分派，不能只看 len(parts)。
#   缺陷原文：`if len(parts) == 3: MODE_CBC` ⇒ "AES/CTR/NoPadding" 也被当成 CBC，
#   解出乱码且不报错（静默出错）。
parts = mode.split("/")
print(f"  mode parts = {parts}")
alg = parts[1].upper() if len(parts) >= 2 else "CBC"
print(f"  selected algorithm = {alg}")
try:
    if alg == "CTR":
        # CTR 的"IV"是 128-bit 大端计数器初值，语义等同 IvParameterSpec(iv)
        # ★ 必须用 Counter.new(128, initial_value=iv)，不得用 nonce=iv（语义不同）
        ctr = Counter.new(128, initial_value=int.from_bytes(iv, "big"),
                          allow_wraparound=True)
        cipher = AES.new(KEY, AES.MODE_CTR, counter=ctr)
    elif alg == "ECB":
        cipher = AES.new(KEY, AES.MODE_ECB)
    elif alg == "CBC":
        cipher = AES.new(KEY, AES.MODE_CBC, iv)
    else:
        raise ValueError(f"unsupported cipher algorithm: {alg!r}")
    pt = cipher.decrypt(ct)
except Exception as e:
    print("AES err:", e); sys.exit(1)

print(f"  decrypted = {len(pt)} bytes  head={pt[:24].hex()}")

# strip PKCS5/7 padding
pad = pt[-1] if pt else 0
if 1 <= pad <= 16 and pt[-pad:] == bytes([pad]) * pad:
    pt = pt[:-pad]
    print(f"  padding stripped ({pad}), now {len(pt)} bytes")

OUT = r"E:\ios漏洞\recon\apk\unpacked\b_stage"
os.makedirs(OUT, exist_ok=True)

# parse: int32 BE count, then entries
off = 0
count, = struct.unpack_from(">i", pt, off); off += 4
print(f"\n  entry count = {count}")
for i in range(count):
    nl, = struct.unpack_from(">h", pt, off); off += 2
    name = pt[off:off+nl].decode("utf-8", "replace"); off += nl
    sz, = struct.unpack_from(">i", pt, off); off += 4
    data = pt[off:off+sz]; off += sz
    safe = re.sub(r"[^A-Za-z0-9_.\-]", "_", name)
    out = os.path.join(OUT, safe)
    open(out, "wb").write(data)
    print(f"    {name:44s} {sz:>10} bytes  sha256={hashlib.sha256(data).hexdigest()[:24]}  head={data[:12].hex()}")
print(f"\n[+] extracted to {OUT}")
