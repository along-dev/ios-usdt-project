#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W-IOS-GAP2 判据：`[HOST_PLACEHOLDER]` 落码后的反向断言（R-1..R-7）＋ S-2a/S-2b。

用法：python verify_w_ios_gap2_host.py
只读；不启动服务。R-8（行为级）**本卡未授权**，脚本**只声明未覆盖，不判 PASS**。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_CB = ROOT / "02-backend-node/src_restored/plugins/c2/services/config-builder.js"
SRC_RT = ROOT / "02-backend-node/src_restored/plugins/c2/routes/config.js"
FLAT_CB = ROOT / "02-backend-node/src/app_dist_plugins_c2_services_config-builder.js"
FLAT_RT = ROOT / "02-backend-node/src/app_dist_plugins_c2_routes_config.js"

fails = []


def ok(cond, label, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + (("  — " + str(detail)) if detail else ""))
    if not cond:
        fails.append(label)


def read(p):
    return p.read_text(encoding="utf-8")


def main():
    s_cb, s_rt = read(SRC_CB), read(SRC_RT)
    f_cb, f_rt = read(FLAT_CB), read(FLAT_RT)

    # ---- R-1..R-6：静态断言 ----
    ok(s_cb.count("HOST_PLACEHOLDER") == 0,
       "R-1 源侧 config-builder.js 无 HOST_PLACEHOLDER", s_cb.count("HOST_PLACEHOLDER"))
    ok(f_cb.count("HOST_PLACEHOLDER") == 2,
       "R-2 扁平副本仍含 2 处（登记为**已知分叉**，非漏改）", f_cb.count("HOST_PLACEHOLDER"))
    # R-3 ★ 收紧：**锚定 cacheKey 那一行**（原写法 `":${host}`" in s_rt or "${host}" in s_rt`
    #       只要 `${host}` 出现在文件任意位置即过 —— 断言比标签弱）
    ck_line = next((l.strip() for l in s_rt.splitlines() if "const cacheKey" in l), "")
    ok("${host}" in ck_line,
       "R-3 缓存键**那一行**含 host 维度（非全文任意位置）", ck_line)
    # R-4 ★ 收紧：断言**整句** `reply.header('Vary', 'Host')`（原仅查两个子串是否存在）
    ok(bool(re.search(r"reply\.header\(\s*'Vary'\s*,\s*'Host'\s*\)", s_rt)),
       "R-4 有**整句** reply.header('Vary', 'Host')")
    ok(bool(re.search(r"channel\s*\?\s*`\$\{scheme\}://\$\{host\}`\s*:\s*null", s_rt)),
       "R-5 !channel 时不构造 origin（`channel ? ... : null`）")
    # ★ Z-01（复核登记，本轮不改）：该守卫的正则放行主机部分的空格/换行（`http://a b` 亦 match）。
    #   当前**不可达**（origin 仅在 channel 命中后、由已登记域名拼出）⇒ 登记为「依赖上游不变量」。
    #   复核方诚实标注：**「Node 拒 header 内 CR/LF 这一前提未实测」**。
    ok("origin 缺失或非法" in s_cb, "R-6 fail-loud 守卫在位")
    ok(bool(re.search(r"xfpRaw\s*===\s*'http'\s*\|\|\s*xfpRaw\s*===\s*'https'", s_rt)),
       "R-9 scheme 白名单限定 {http,https}，其余回落 http")
    ok("no_channel_for_host" in s_cb and bool(re.search(r"reason:\s*config\.reason", s_rt)),
       "R-10 !channel ⇒ 显式 unsupported（源产出该 reason，路由原样透传 `config.reason`）")
    ok(bool(re.search(r"logger\.warn\(\{\s*host\s*\}", s_rt)),
       "R-11 Host 未命中记 WARN 且只带 host（不含 body/凭据）")

    # ---- S-2a：对 src_restored 单一实现的**自洽性** ----
    m = re.search(r"export async function getConfigJson\(([^)]*)\)", s_cb)
    params = [p.strip() for p in m.group(1).split(",")] if (m and m.group(1).strip()) else []
    ok(m is not None and len(params) == 3,
       "S-2a-1 getConfigJson 形参个数 == 3（channel, device, origin）", params)
    # S-2a-2 ★ 收紧：五键必须落在 **`return { … }` 块内**（原写法在整个源文件里找 `\bkey\s*:`
    #           ⇒ 等于"文件里出现过这些词"，≠"返回对象含这五键"）
    rb = re.search(r"(?ms)\n\s*return \{\n(.*?)\n\s*\};", s_cb)
    ret_block = rb.group(1) if rb else ""
    ret_keys = [k for k in ("settings", "chain", "chainReach", "core", "entries")
                if re.search(r"\b%s\s*:" % k, ret_block)]
    ok(bool(ret_block) and len(ret_keys) == 5,
       "S-2a-2 返回对象含五键（**限于 return { } 块内**）", ret_keys)

    # ---- S-2b：KNOWN_DIVERGENCES 分叉探测器（**断言"确实分叉"**） ----
    #   D1 形参个数：源 3 vs 扁平 1；D2 返回字段：源有 chain/chainReach，扁平无。
    #   ★ 若某条**消失**（有人同步/删改了扁平副本）⇒ 报红并要求**重新裁决**，不静默。
    fm = re.search(r"export async function getConfigJson\(([^)]*)\)", f_cb)
    fparams = [p.strip() for p in fm.group(1).split(",")] if fm and fm.group(1).strip() else []
    ok(len(params) != len(fparams),
       "S-2b-D1 已知分叉『形参个数』仍成立（源 %d vs 扁平 %d）" % (len(params), len(fparams)),
       "若此项消失 ⇒ 需重新裁决")
    flat_has_chain = bool(re.search(r"\bchainReach\s*:", f_cb))
    ok(bool(re.search(r"\bchainReach\s*:", s_cb)) and not flat_has_chain,
       "S-2b-D2 已知分叉『返回字段 chainReach』仍成立（源有 / 扁平无）",
       "若此项消失 ⇒ 需重新裁决")
    # 扁平副本侧旁证：其路由缓存键亦无 host（同代陈旧快照）
    ok("${host}" not in f_rt, "S-2b-D3 扁平副本路由缓存键仍无 host（同代陈旧快照）")

    # ---- R-8：行为级未覆盖（**不判 PASS**） ----
    print("SKIP  R-8 行为级（真实响应 host 正确 / 伪造 Host 不出现 / 同渠道多域名不串味）"
          "—— 需启服务，**本卡未授权** ⇒ 登记为未覆盖面，不以静态绿冒充")
    print("\nRESULT: " + ("ALL PASS" if not fails else "%d FAILED" % len(fails)))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
