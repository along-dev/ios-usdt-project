#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W-IOS-PKG2 · IPA 流水线自测（反向断言为主）
用法：python selftest_ipa_pipeline.py
"""
import hashlib
import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PIPE = os.path.join(HERE, "ipa_pipeline.py")
REF = os.path.join(REPO, "05-ios", "reference", "ipa")
DIST = os.path.join(REPO, "05-ios", "dist")
PY = sys.executable
DYL = "Payload/Filza.app/Frameworks/FilzaApplySandboxExt.dylib"

# X-02：直接加载被测模块，对**源码常量** `INJECT_MODES` 做断言（而非对已被断言过的产物值取子集）
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("_ipa_pipeline_under_test", PIPE)
_pipe = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_pipe)
INJECT_MODES = tuple(_pipe.INJECT_MODES)

fails = 0


def ok(cond, label, detail=""):
    global fails
    print(("PASS  " if cond else "FAIL  ") + label + (("  — " + str(detail)) if detail else ""))
    if not cond:
        fails += 1


def run(args):
    r = subprocess.run([PY, PIPE] + args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def extract_dylib(ipa, out):
    with zipfile.ZipFile(ipa) as z:
        open(out, "wb").write(z.read(DYL))
    return out


def main():
    tmp = tempfile.mkdtemp(prefix="ipak_")
    shell = os.path.join(REF, "FilzaSlop-v1.0.0-unsigned.ipa")      # 已含载入命令
    bare = os.path.join(REF, "Filza_4.0_NoUS_Crack.ipa")            # 真裸壳
    dyl = extract_dylib(os.path.join(REF, "FilzaEscaped_DS_1.2.ipa"), os.path.join(tmp, "ds.dylib"))

    # R1 未登记外壳 ⇒ 拒绝
    fake = os.path.join(tmp, "fake.ipa")
    open(fake, "wb").write(b"PK\x05\x06" + b"\x00" * 18)            # 空 zip
    rc, out = run(["build", "--base-shell", fake, "--dylib", dyl, "--version", "t"])
    ok(rc == 3 and "外壳未登记" in out, "R1 未登记外壳 ⇒ 拒绝(exit 3)", rc)

    # R2 未登记 dylib ⇒ 拒绝
    fdyl = os.path.join(tmp, "x.dylib"); open(fdyl, "wb").write(b"\x00" * 64)
    rc, out = run(["build", "--base-shell", shell, "--dylib", fdyl, "--version", "t"])
    ok(rc == 4 and "dylib 未登记" in out, "R2 未登记 dylib ⇒ 拒绝(exit 4)", rc)

    # R3 裸壳（bundle id 正确但主二进制无载入命令）⇒ 拒绝
    #    夹具：把真实壳主二进制里的 dylib 名做**等长**改名（不破坏 Mach-O 结构）
    bareshell = os.path.join(tmp, "bare.ipa")
    with zipfile.ZipFile(shell) as zi, zipfile.ZipFile(bareshell, "w", zipfile.ZIP_DEFLATED) as zo:
        for i in zi.infolist():
            data = zi.read(i.filename)
            if i.filename == "Payload/Filza.app/Filza":
                data = data.replace(b"FilzaApplySandboxExt.dylib", b"FilzaApplySandboxExX.dylib")
            ni = zipfile.ZipInfo(i.filename, date_time=i.date_time)
            ni.create_system = i.create_system; ni.external_attr = i.external_attr
            zo.writestr(ni, data)
    rc, out = run(["build", "--base-shell", bareshell, "--dylib", dyl, "--version", "t",
                   "--out", os.path.join(tmp, "b-unsigned.ipa"), "--allow-unregistered",
                   "--inject", "slot"])
    ok(rc == 8 and "裸壳" in out, "R3a `--inject slot` 遇裸壳 ⇒ 拒绝(exit 8)", rc)
    rc, out = run(["build", "--base-shell", bare, "--dylib", dyl, "--version", "t"])
    ok(rc == 7, "R3b 真 Filza 壳(NoUS_Crack) ⇒ 被 **bundle-id 白名单**拒(exit 7)："
                "它在 registry 里登记为『不可组装』；裸壳支路由 R3a 合成夹具覆盖", rc)

    # R4 无签名产出名不含 -unsigned ⇒ 拒绝
    rc, out = run(["build", "--base-shell", shell, "--dylib", dyl, "--version", "t",
                   "--out", os.path.join(tmp, "o.ipa")])
    ok(rc == 5 and "-unsigned" in out, "R4 无签名名缺 -unsigned ⇒ 拒绝(exit 5)", rc)

    # R5 正常组装 ⇒ 成功 + verify 全绿
    outdir = os.path.join(tmp, "ok")
    os.makedirs(outdir, exist_ok=True)
    outp = os.path.join(outdir, "FilzaSlop-9.9.9-unsigned.ipa")
    rc, out = run(["build", "--base-shell", shell, "--dylib", dyl, "--version", "9.9.9", "--out", outp])
    ok(rc == 0 and os.path.exists(outp), "R5a 正常组装成功", rc)
    rc2, vout = run(["verify", "--ipa", outp])
    ok(rc2 == 0 and "removed(OK)" in vout and "9.9.9" in vout and "MISSING(BAD)" not in vout,
       "R5b 产物 verify：URL scheme 已删 / 版本已写 / dylib+载入命令在位", "")

    # R6 可复现：同输入两次 ⇒ 同 sha256
    outp2 = os.path.join(outdir, "FilzaSlop-9.9.9-unsigned-2.ipa")
    run(["build", "--base-shell", shell, "--dylib", dyl, "--version", "9.9.9", "--out", outp2])
    ok(sha(outp) == sha(outp2), "R6 可复现：两次构建同 sha256", sha(outp)[:16])

    # R7 manifest 记录的产物 sha256 == 实际
    man = json.load(open(outp + ".manifest.json", encoding="utf-8"))
    ok(man["output"]["sha256"] == sha(outp) and man["base_shell"]["sha256"] == sha(shell)
       and man["dylib"]["sha256"] == sha(dyl), "R7 manifest 记录 sha256 与实际一致")

    # R8 符号链接保留（fixture：向真实壳注入一条 symlink 再走流水线）
    fix = os.path.join(tmp, "sym.ipa")
    with zipfile.ZipFile(shell) as zi, zipfile.ZipFile(fix, "w", zipfile.ZIP_DEFLATED) as zo:
        for i in zi.infolist():
            ni = zipfile.ZipInfo(i.filename, date_time=i.date_time)
            ni.create_system = i.create_system; ni.external_attr = i.external_attr
            zo.writestr(ni, zi.read(i.filename))
        sl = zipfile.ZipInfo("Payload/Filza.app/sloptest-link", date_time=(1980, 1, 1, 0, 0, 0))
        sl.create_system = 3; sl.external_attr = (0o120777 << 16)
        zo.writestr(sl, "Filza")                                     # symlink 内容=目标
    outfix = os.path.join(outdir, "FilzaSlop-9.9.8-unsigned.ipa")
    rc, out = run(["build", "--base-shell", fix, "--dylib", dyl, "--version", "9.9.8",
                   "--out", outfix, "--allow-unregistered"])
    with zipfile.ZipFile(outfix) as z:
        inf = {i.filename: i for i in z.infolist()}
        is_link = (inf.get("Payload/Filza.app/sloptest-link").external_attr >> 16) & 0xF000 == 0xA000
        tgt = z.read("Payload/Filza.app/sloptest-link").decode() if is_link else ""
    ok(rc == 0 and is_link and tgt == "Filza", "R8 符号链接保留（fixture）", "-> %s" % tgt)

    # R9 权限位保留（真实产物：可执行条目数不变）
    def xcount(p):
        with zipfile.ZipFile(p) as z:
            return sum(1 for i in z.infolist() if ((i.external_attr >> 16) & 0o111))
    # ★ X-04：用 `==` 而非 `>=` —— 本流水线**不允许新增可执行条目**（放宽即缺陷）
    ok(xcount(outp) == xcount(shell), "R9 可执行位保留（== ，不得放宽）", "%d -> %d" % (xcount(shell), xcount(outp)))

    # R10 条目数不丢
    with zipfile.ZipFile(shell) as a, zipfile.ZipFile(outp) as b:
        ok(len(a.infolist()) == len(b.infolist()), "R10 条目数不变",
           "%d -> %d" % (len(a.infolist()), len(b.infolist())))

    # R11 注册表登记的可执行位/dylib 内容真的换了
    with zipfile.ZipFile(outp) as z:
        ok(hashlib.sha256(z.read(DYL)).hexdigest() == hashlib.sha256(open(dyl, "rb").read()).hexdigest(),
           "R11 产物内 dylib == 注入的 dylib")

    # ==================== X-3 合并后的新增断言 ====================
    import json as _json

    def mainbin(p):
        with zipfile.ZipFile(p) as z:
            app = [n for n in z.namelist() if n.endswith(".app/Info.plist")][0][:-len("Info.plist")]
            pl = plistlib.loads(z.read(app + "Info.plist"))
            return z.read(app + pl["CFBundleExecutable"])

    import struct as _st

    def ncmds_of(p):
        b = mainbin(p)
        return _st.unpack("<I", b[16:20])[0]

    # N1 slot 模式：真实壳默认 ⇒ slot-replaced，且**主二进制零改动**
    n1 = os.path.join(outdir, "FilzaSlop-9.9.7-unsigned.ipa")
    rc, out = run(["build", "--base-shell", shell, "--dylib", dyl, "--version", "9.9.7", "--out", n1])
    man1 = _json.load(open(n1 + ".manifest.json", encoding="utf-8"))
    ok(rc == 0 and man1["inject_mode"] == "slot-replaced", "N1 slot 模式 ⇒ inject_mode=slot-replaced", man1.get("inject_mode"))
    ok(hashlib.sha256(mainbin(n1)).hexdigest() == hashlib.sha256(mainbin(shell)).hexdigest(),
       "N1 主二进制零改动（sha 相同）")
    ok(man1["ncmds_before"] == man1["ncmds_after"], "N1 ncmds 不变", "%s->%s" % (man1["ncmds_before"], man1["ncmds_after"]))
    ok(ncmds_of(n1) == man1["ncmds_before"],
       "N1 交叉核对：独立读数器 ncmds_of(产物) == 期望", "%s vs %s" % (ncmds_of(n1), man1["ncmds_before"]))

    # N2 **默认模式（auto）** 下无槽位壳 ⇒ linkedit-appended，**ncmds +1**
    n2 = os.path.join(outdir, "FilzaSlop-9.9.6-unsigned.ipa")
    rc, out = run(["build", "--base-shell", bareshell, "--dylib", dyl, "--version", "9.9.6",
                   "--out", n2, "--allow-unregistered"])
    man2 = _json.load(open(n2 + ".manifest.json", encoding="utf-8"))
    ok(rc == 0 and man2["inject_mode"] == "linkedit-appended",
       "N2 默认(auto): 无槽位壳 ⇒ inject_mode=linkedit-appended", man2.get("inject_mode"))
    ok(man2["ncmds_after"] == man2["ncmds_before"] + 1,
       "N2 ncmds 递增 +1（52→53）", "%s->%s" % (man2["ncmds_before"], man2["ncmds_after"]))
    ok(ncmds_of(n2) == man2["ncmds_before"] + 1,
       "N2 交叉核对：独立读数器 ncmds_of(产物) == 期望(+1)", "%s vs %s" % (ncmds_of(n2), man2["ncmds_before"] + 1))
    rcv, vout = run(["verify", "--ipa", n2])
    ok(rcv == 0 and "load_cmd   : OK" in vout, "N2 产物 load_cmd OK")

    # N3b 模式与基座匹配性：反向
    rc, out = run(["build", "--base-shell", shell, "--dylib", dyl, "--version", "t",
                   "--out", os.path.join(tmp, "z2-unsigned.ipa"), "--inject", "append"])
    ok(rc == 8, "N3b `--inject append` 对有槽位壳 ⇒ 拒绝(exit 8)", rc)

    # N9 ★ 诚实登记：本批**真实基座**（registry 内 has_load_command=True）在默认 auto 下
    #    全部走 slot-replaced ⇒ **无槽分支在真实基座上无法触发**（只能靠合成夹具覆盖）。
    _reg = _json.load(open(os.path.join(HERE, "registry.json"), encoding="utf-8"))
    slotted = [s for s in _reg["shells"] if s.get("has_load_command") and s.get("dylib_present")]
    mha = [s for s in slotted if s.get("bundle_id") == "com.apple.mobile.MobileHouseArrest"]
    nonmha = [s for s in slotted if s.get("bundle_id") != "com.apple.mobile.MobileHouseArrest"]
    probe = os.path.join(outdir, "_probe-unsigned.ipa")
    modes, built, failed = set(), 0, []
    for s in mha:
        rcp, _o = run(["build", "--base-shell", os.path.join(REPO, s["path"]), "--dylib", dyl,
                       "--version", "probe", "--out", probe])
        if rcp == 0:
            built += 1
            modes.add(_json.load(open(probe + ".manifest.json", encoding="utf-8"))["inject_mode"])
        else:
            failed.append((s["id"], rcp))
    # ★ 先断言"可接受基座数全成功"，否则单元素集也可能因多数 rc!=0 而过绿
    ok(built == len(mha), "N9a MHA 子集基座全部构建成功（%d/%d）" % (built, len(mha)), "failed=%s" % failed)
    ok(modes == {"slot-replaced"},
       "N9b MHA 子集(%d)默认 auto 下全走 slot-replaced ⇒ 无槽分支**无法在真实基座触发**" % len(mha),
       sorted(modes))
    # ★ N9c 裁定后：DS 代际基座**已通过 bundle-id 白名单**（参数化生效），
    #    但被**第二条独立门禁**拦下 —— 其主二进制含 LC_CODE_SIGNATURE（**已签名**）⇒ exit 9。
    #    故 DS 代际当前仍不可组装，原因已从"bundle id"变为"**基座已签名**"（需未签名壳或重签步骤）。
    ds_rc = {}
    for s in nonmha:
        rcp, _o = run(["build", "--base-shell", os.path.join(REPO, s["path"]), "--dylib", dyl,
                       "--version", "probe", "--out", probe])
        ds_rc[s["id"]] = rcp
    ok(bool(nonmha) and all(v == 9 for v in ds_rc.values()),
       "N9c DS 代际基座(%d)：bundle-id 白名单已放行，但被**已签名**门禁拦(exit 9) ⇒ 第二条独立边界" % len(nonmha),
       ds_rc)

    # N9d ★ 反向：**未登记**的 bundle-id ⇒ 仍 exit 7（证明白名单没被架空）
    rc, out = run(["build", "--base-shell", shell, "--dylib", dyl, "--version", "probe",
                   "--out", os.path.join(tmp, "bid-unsigned.ipa"), "--bundle-id", "com.example.evil"])
    ok(rc == 7 and "登记允许集合" in out, "N9d 未登记 bundle-id ⇒ 拒绝(exit 7)，白名单未被架空", rc)

    # N9e 登记为「不可组装」的基座（裸壳）⇒ 即便用其自身 id 也 exit 7
    rc, out = run(["build", "--base-shell", bare, "--dylib", dyl, "--version", "probe",
                   "--out", os.path.join(tmp, "bid2-unsigned.ipa")])
    ok(rc == 7 and "不可组装" in out, "N9e 登记为『不可组装』的基座 ⇒ 拒绝(exit 7)", rc)

    # N4 manifest.plist：三类 asset 齐全 + itms-services 入口
    n4 = os.path.join(outdir, "FilzaSlop-9.9.5-unsigned.ipa")
    rc, out = run(["build", "--base-shell", shell, "--dylib", dyl, "--version", "9.9.5", "--out", n4,
                   "--manifest-url", "https://cdn.example.test/ipa/FilzaSlop-9.9.5-unsigned.ipa",
                   "--icon57-url", "https://cdn.example.test/ipa/i57.png",
                   "--icon512-url", "https://cdn.example.test/ipa/i512.png", "--title", "FilzaSlop"])
    man4 = _json.load(open(n4 + ".manifest.json", encoding="utf-8"))
    kinds = sorted(a["kind"] for a in man4["manifest_assets"])
    ok(rc == 0 and kinds == ["display-image", "full-size-image", "software-package"],
       "N4 manifest 三类 asset 齐全", kinds)
    ok(os.path.exists(n4 + ".manifest.plist"), "N4 manifest.plist 落盘")
    mk = plistlib.loads(open(n4 + ".manifest.plist", "rb").read())
    ok(mk["items"][0]["metadata"]["bundle-identifier"] == "com.apple.mobile.MobileHouseArrest"
       and len(mk["items"][0]["assets"]) == 3, "N4 manifest.plist 结构正确（3 assets + bundle id）")
    ok((man4.get("itms_services_url") or "").startswith("itms-services://?action=download-manifest&url="),
       "N4 itms-services OTA 入口存在", man4.get("itms_services_url"))

    # N5 含注入后仍可复现
    n5a = os.path.join(outdir, "FilzaSlop-9.9.4-unsigned.ipa")
    n5b = os.path.join(outdir, "FilzaSlop-9.9.4-unsigned-b.ipa")
    run(["build", "--base-shell", bareshell, "--dylib", dyl, "--version", "9.9.4", "--out", n5a,
         "--inject", "auto", "--allow-unregistered"])
    run(["build", "--base-shell", bareshell, "--dylib", dyl, "--version", "9.9.4", "--out", n5b,
         "--inject", "auto", "--allow-unregistered"])
    ok(sha(n5a) == sha(n5b), "N5 含 Mach-O 注入后仍可复现（两次同 sha256）", sha(n5a)[:16])

    # N6 landed-only 诚实：fat 主二进制 ⇒ 标 landed-only，且默认拒绝
    fatshell = os.path.join(tmp, "fat.ipa")
    with zipfile.ZipFile(shell) as zi, zipfile.ZipFile(fatshell, "w", zipfile.ZIP_DEFLATED) as zo:
        for i in zi.infolist():
            data = zi.read(i.filename)
            if i.filename == "Payload/Filza.app/Filza":
                data = b"\xca\xfe\xba\xbe" + b"\x00" * 200
            ni = zipfile.ZipInfo(i.filename, date_time=i.date_time)
            ni.create_system = i.create_system; ni.external_attr = i.external_attr
            zo.writestr(ni, data)
    rc, out = run(["build", "--base-shell", fatshell, "--dylib", dyl, "--version", "t",
                   "--out", os.path.join(tmp, "f-unsigned.ipa"), "--inject", "auto", "--allow-unregistered"])
    ok(rc == 12 and "landed-only" in out, "N6a 无法注入 ⇒ 默认拒绝(exit 12)", rc)
    n6 = os.path.join(outdir, "FilzaSlop-9.9.3-unsigned.ipa")
    rc, out = run(["build", "--base-shell", fatshell, "--dylib", dyl, "--version", "9.9.3", "--out", n6,
                   "--inject", "auto", "--allow-unregistered", "--allow-landed-only"])
    man6 = _json.load(open(n6 + ".manifest.json", encoding="utf-8"))
    ok(rc == 0 and man6["inject_mode"] == "landed-only",
       "N6b 显式接受 ⇒ 如实标 inject_mode=landed-only（绝不假装已注入）", man6.get("inject_mode"))

    # N7 ★ 对**源码常量**断言取值全集恰为三值（原版对已被断言过的产物值取子集 ⇒ 恒真）
    ok(set(INJECT_MODES) == {"slot-replaced", "linkedit-appended", "landed-only"},
       "N7 源码常量 INJECT_MODES == 三值集合", sorted(INJECT_MODES))
    ok(set([man1["inject_mode"], man2["inject_mode"], man6["inject_mode"]]) <= set(INJECT_MODES),
       "N7b 实测产物取值均落在常量全集中")

    # N8 `--inject none` 不新增取值 ⇒ 归入 landed-only
    n8 = os.path.join(outdir, "FilzaSlop-9.9.2-unsigned.ipa")
    rc, out = run(["build", "--base-shell", shell, "--dylib", dyl, "--version", "9.9.2",
                   "--out", n8, "--inject", "none", "--allow-landed-only"])
    man8 = _json.load(open(n8 + ".manifest.json", encoding="utf-8"))
    ok(rc == 0 and man8["inject_mode"] == "landed-only",
       "N8 `--inject none` ⇒ inject_mode=landed-only（不新增取值）", man8.get("inject_mode"))

    shutil.rmtree(tmp, ignore_errors=True)
    print("\nRESULT: " + ("ALL PASS" if fails == 0 else "%d FAILED" % fails))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
