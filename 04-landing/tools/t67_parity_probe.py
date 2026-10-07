# -*- coding: utf-8 -*-
"""T67 交付① —— 「产物 vs 参照」可复跑对照方法（★ 只读，⛔ 不改任何受审面）。

口径（本件自定义，写在此处以免漂移）：
  产物 = 04-landing/templates/<name>.html     参照 = 04-landing/reference/code/pjuyr_code/templates/<name>.html
  逐对取三把尺：① <title> ② 标签序列相似度（difflib.SequenceMatcher on 标签名序列）
                ③ CSS 类名集合 Jaccard
  ★ 量尺前置断言（卡的硬要求）：(a) **同源对**（文件 vs 它自己）⇒ 差异应 ≈ 0
                                (b) **负控**（故意配错的一对）⇒ 必须**非 0**（否则量尺是恒绿）
用法： python t67_parity_probe.py            # 量尺自证 + 全量逐对
      python t67_parity_probe.py --selftest  # 只跑量尺自证
"""
from __future__ import annotations
import io, os, re, sys, difflib, json

ROOT = r"E:\USDT项目\04-landing"
PROD = os.path.join(ROOT, "templates")
REF = os.path.join(ROOT, "reference", "code", "pjuyr_code", "templates")

TAG = re.compile(r"<\s*([a-zA-Z][\w-]*)")
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
CLS = re.compile(r'class\s*=\s*"([^"]*)"', re.I)


def read(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def tags_of(t):
    return [m.group(1).lower() for m in TAG.finditer(t)]


def title_of(t):
    m = TITLE.search(t)
    return (m.group(1).strip() if m else "")


def classes_of(t):
    s = set()
    for m in CLS.finditer(t):
        for c in m.group(1).split():
            if c:
                s.add(c)
    return s


def metrics(pa, pb):
    ta, tb = read(pa), read(pb)
    ja, jb = tags_of(ta), tags_of(tb)
    ca, cb = classes_of(ta), classes_of(tb)
    tag_sim = difflib.SequenceMatcher(None, ja, jb).ratio()
    jac = (len(ca & cb) / len(ca | cb)) if (ca | cb) else 1.0
    return {
        "tag_sim": round(tag_sim, 4),
        "cls_jac": round(jac, 4),
        "title_a": title_of(ta)[:60], "title_b": title_of(tb)[:60],
        "title_eq": title_of(ta) == title_of(tb),
        "tags_a": len(ja), "tags_b": len(jb),
        "bytes_a": len(ta.encode("utf-8")), "bytes_b": len(tb.encode("utf-8")),
    }


def verdict(m):
    """缺口形状定性（本件口径）。"""
    if m["tag_sim"] >= 0.98 and m["cls_jac"] >= 0.98 and m["title_eq"]:
        return "≈同源"
    if m["tag_sim"] < 0.30:
        return "整页缺/几乎无关"
    if m["tag_sim"] < 0.75:
        return "结构大幅缩水"
    if not m["title_eq"] or m["cls_jac"] < 0.75:
        return "简化为静态/细节不一致"
    return "细节不一致"


def selftest():
    print("=== 量尺前置断言 ===")
    same = os.path.join(PROD, "apumex.html")
    if not os.path.exists(same):
        print("  [FAIL] 找不到用于自证的样本"); return 2
    m1 = metrics(same, same)
    print("  (a) 同源对（文件 vs 它自己）⇒ tag_sim=%s cls_jac=%s title_eq=%s ⇒ 差异≈0 ? %s"
          % (m1["tag_sim"], m1["cls_jac"], m1["title_eq"], m1["tag_sim"] == 1.0 and m1["cls_jac"] == 1.0))
    other = os.path.join(PROD, "arabic.html")
    ok = True
    if os.path.exists(other):
        m2 = metrics(same, other)
        red = (m2["tag_sim"] < 0.98) or (m2["cls_jac"] < 0.98)
        print("  (b) 负控（故意配错：apumex vs arabic）⇒ tag_sim=%s cls_jac=%s ⇒ 非 0 ? %s"
              % (m2["tag_sim"], m2["cls_jac"], red))
        ok = red
    else:
        print("  [WARN] 无第二件可做负控")
    ok = ok and (m1["tag_sim"] == 1.0 and m1["cls_jac"] == 1.0)
    print("SELFTEST=%s" % ("OK" if ok else "BAD"))
    return 0 if ok else 2


def main():
    if "--selftest" in sys.argv:
        return selftest()
    rc = selftest()
    print()
    if rc != 0:
        print("★ 量尺自证未过 ⇒ 按卡：**先怀疑量尺坏了**，⛔ 不继续出差异清单。"); return rc
    prods = sorted(f for f in os.listdir(PROD) if f.endswith(".html"))
    refs = set(f for f in os.listdir(REF) if f.endswith(".html")) if os.path.isdir(REF) else set()
    print("== 逐对对照（产物 %d 件 ↔ 参照 %d 件）==" % (len(prods), len(refs)))
    rows, missing_in_ref, missing_in_prod = [], [], []
    for f in prods:
        if f not in refs:
            missing_in_ref.append(f); rows.append({"file": f, "verdict": "★参照侧无同名件（无从配对）"}); continue
        m = metrics(os.path.join(PROD, f), os.path.join(REF, f))
        m["file"] = f; m["verdict"] = verdict(m)
        rows.append(m)
    for f in sorted(refs - set(prods)):
        missing_in_prod.append(f)
    print(json.dumps(rows, ensure_ascii=False, indent=1))
    print()
    print("== 汇总 ==")
    from collections import Counter
    c = Counter(r["verdict"] for r in rows)
    for k, v in c.most_common():
        print("  %-28s %d" % (k, v))
    print("  参照有而产物无（整页缺候选）: %d 件" % len(missing_in_prod))
    print("  产物有而参照无同名件: %d 件 %s" % (len(missing_in_ref), missing_in_ref[:6]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
