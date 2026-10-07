# -*- coding: utf-8 -*-
r"""Decrypt + unpack b.apk's assets/0gvw74arcr5sml (AES-256-CTR, IV as big-endian counter).

★ W-AND-01 修正（2026-10-03）：本文件原按
      「重复 [int32 BE size][int16 BE nameLen][name][size bytes]」
  解析，该格式【错】—— 在同一份数据上解析到第 2 条即断裂（sz=2049917272 为乱值）。
  实测为【fail】（README §二 与 D0-C1 记录一致）。

  与 tools/bdecrypt.py 一致的【正确】格式（CTR 明文实证，slack=0）：
      [int32 BE count]  然后 count × { [int16 BE nameLen][name UTF-8]
                                      [int32 BE size][size bytes] }

★ 反向要求：结构违规【必须报错退出】（非零退出码，且不落任何文件），
  不得静默返回半截结果。故解析阶段一次跑完后校验 slack（余量必须为 0），
  全部通过后才写盘。

用法:
    python bstage.py [apk_path] [out_dir]
    - apk_path 默认 06-android/apk/samples/inner_b.apk（L2 产物 b.apk 的本地副本）
    - out_dir  默认 $DSH_VERIFY_TMP/b_stage（未设则【系统临时目录】/b_stage）

  ★ 产物目录默认【不落仓库、不落原始素材树】。原实现硬编码
    E:\ios漏洞\recon\apk\unpacked\b_stage（原始素材树，禁写），已改。
"""
import sys, io, os, re, zipfile, struct, hashlib, json, tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from Crypto.Cipher import AES
from Crypto.Util import Counter

from _payload_key import KEY_HEX
KEY = bytes.fromhex(KEY_HEX)
ASSET = "assets/0gvw74arcr5sml"

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(HERE, "..", "..")
DEFAULT_APK = os.path.join(PROJ, "06-android", "apk", "samples", "inner_b.apk")
VERIFY_TMP = (os.environ.get("DSH_VERIFY_TMP") or "").strip()
DEFAULT_OUT = os.path.join(VERIFY_TMP or tempfile.gettempdir(), "b_stage")

NAME_RE = re.compile(r"[A-Za-z0-9_./\-]+")


def fail(msg):
    """结构违规：报错并【非零退出】。调用方此前不得落任何产物。"""
    sys.stdout.flush()
    print(f"[FAIL] {msg}", file=sys.stderr)
    raise SystemExit(2)


def load_plaintext(apk_path):
    if not os.path.isfile(apk_path):
        fail(f"apk not found: {apk_path}")
    try:
        with zipfile.ZipFile(apk_path) as z:
            raw = z.read(ASSET)
    except KeyError:
        fail(f"asset {ASSET} not present in {apk_path}")
    except zipfile.BadZipFile as e:
        fail(f"not a readable zip: {apk_path} ({e})")
    if len(raw) <= 16:
        fail(f"asset {ASSET} too short: {len(raw)} bytes (need >16 for IV)")
    iv, ct = raw[:16], raw[16:]
    ctr = Counter.new(128, initial_value=int.from_bytes(iv, "big"),
                      allow_wraparound=True)
    pt = AES.new(KEY, AES.MODE_CTR, counter=ctr).decrypt(ct)
    return iv, pt


def parse_container(pt):
    """count 前缀容器。任何结构违规 ⇒ fail()（非零退出）；返回 (entries, slack)。"""
    if len(pt) < 4:
        fail(f"plaintext too short for count header: {len(pt)} bytes")
    count, = struct.unpack_from(">i", pt, 0)
    if not (1 <= count <= 100000):
        fail(f"implausible entry count {count} at off=0 "
             f"(not a b_stage container, or corrupted)")
    off = 4
    entries = []
    for i in range(count):
        if off + 2 > len(pt):
            fail(f"record {i}: truncated at nameLen (off={off}, len={len(pt)})")
        nl, = struct.unpack_from(">h", pt, off)
        if not (1 <= nl <= 255):
            fail(f"record {i}: implausible nameLen {nl} at off={off} "
                 f"(not a b_stage container, or corrupted)")
        off += 2
        if off + nl > len(pt):
            fail(f"record {i}: truncated at name (off={off}, nl={nl}, len={len(pt)})")
        try:
            name = pt[off:off + nl].decode("utf-8")
        except UnicodeDecodeError as e:
            fail(f"record {i}: name not valid utf-8 at off={off} ({e})")
        if not NAME_RE.fullmatch(name):
            fail(f"record {i}: illegal name {name!r} at off={off}")
        off += nl
        if off + 4 > len(pt):
            fail(f"record {i} ({name}): truncated at size field "
                 f"(off={off}, len={len(pt)})")
        sz, = struct.unpack_from(">i", pt, off)
        off += 4
        if not (0 <= sz <= len(pt) - off):
            fail(f"record {i} ({name}): size {sz} exceeds remaining "
                 f"{len(pt) - off} bytes")
        entries.append((name, pt[off:off + sz]))
        off += sz
    slack = len(pt) - off
    if slack != 0:
        fail(f"trailing slack {slack} bytes after {count} records "
             f"(count/format mismatch — refusing to emit partial results)")
    return entries, slack


def main():
    apk_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_APK
    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT

    iv, pt = load_plaintext(apk_path)
    print(f"apk    = {apk_path}")
    print(f"IV     = {iv.hex()}")
    print(f"pt     = {len(pt)} bytes  head={pt[:16].hex()}")

    # ★ 先全量解析并通过 slack 校验，再落盘（反向：坏样本不得留下半截产物）
    entries, slack = parse_container(pt)
    print(f"count  = {len(entries)}   slack = {slack}")

    os.makedirs(out_dir, exist_ok=True)
    manifest = []
    for name, data in entries:
        safe = re.sub(r"[^A-Za-z0-9_.\-]", "_", name)
        with open(os.path.join(out_dir, safe), "wb") as f:
            f.write(data)
        h = hashlib.sha256(data).hexdigest()
        manifest.append({"name": name, "size": len(data), "sha256": h})
        print(f"  {name:44s} {len(data):>9} bytes  sha256={h[:24]}")
    with open(os.path.join(out_dir, "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    print(f"\n[+] {len(entries)} files -> {out_dir}")


if __name__ == "__main__":
    main()
