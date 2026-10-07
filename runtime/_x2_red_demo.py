# -*- coding: utf-8 -*-
"""X2 判别力演示（★ 只操作副本，绝不改真判据）。

对每个新断言，构造一个【负例】—— 把被测条件改坏 —— 证明断言会 FAIL。
若某断言在负例下仍 PASS ⇒ 说明它是弱断言 ⇒ 本演示报红。

用法： python _x2_red_demo.py
"""
import io
import os
import re
import shutil
import subprocess
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

D = r"X:\_integration\_fix_work"
TMP = os.path.join(D, "_x2_reddemo")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")

out = []


def show(tag, ok, detail):
    out.append((tag, ok, detail))
    print(f"  [{'OK' if ok else 'BAD'}] {tag}: {detail}")


def run(path, args=()):
    p = subprocess.run([sys.executable, path, *args], cwd=D, env=ENV,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def copy(name):
    os.makedirs(TMP, exist_ok=True)
    dst = os.path.join(TMP, name)
    shutil.copy2(os.path.join(D, name), dst)
    return dst


def patch(path, old, new, count=1):
    s = io.open(path, encoding="utf-8").read()
    assert old in s, f"锚点未找到: {old[:60]!r}"
    s = s.replace(old, new, count)
    io.open(path, "w", encoding="utf-8", newline="\n").write(s)


print("=== X2 判别力演示（负例构造，仅作用于 _x2_reddemo/ 副本）===")
print("")

# ---------------------------------------------------------------------------
# #2  D5：SKIP 不再冒充 PASS
# ---------------------------------------------------------------------------
print("#2 D5 SKIP —— 证明「不再冒充 PASS」:")
rc, o = run(os.path.join(D, "verify_d1c5b_admin_data.py"), ("--no-clear",))
has_skip = "[SKIP] D5" in o
old_true = bool(re.search(r"rec\([^,]*D5[^,]*,\s*True", o)) or "PASS] D5" in o
n_pass = re.search(r"=== (\d+)/(\d+) 通过 ===", o)
show("#2 D5 输出含 [SKIP]", has_skip, "命中" if has_skip else "★ 未命中")
show("#2 D5 不再输出 [PASS]", not old_true, "无 PASS" if not old_true else "★ 仍在冒充 PASS")
# 计数不含 SKIP：D6 也是 SKIP ⇒ 9/9 而非 10/10（原为 10/10，含 2 个假 PASS）
show("#2 SKIP 未计入通过率", bool(n_pass) and n_pass.group(1) == n_pass.group(2),
      f"{n_pass.group(0) if n_pass else '?'}（SKIP 不计数 ⇒ 未虚增分母）")

# ---------------------------------------------------------------------------
# #3 P7c「双用途已如实登记」：负例 = 删掉登记逻辑
# ---------------------------------------------------------------------------
print("")
print("#3 P7c 登记自证 —— 负例：把登记分支改为空（不产生登记文本）:")
c3 = copy("verify_d2c4_apk_delivery.py")
rc0, o0 = run(c3)
show("#3 正例 PASS", rc0 == 0 and "PASS] P7c 双用途事实已如实登记" in o0, f"EXIT={rc0}")
patch(c3,
      'registration_lines.append("投递集与参照集的 sha256 集合完全相同")',
      'pass  # ★负例：不登记')
rc1, o1 = run(c3)
show("#3 负例 FAIL（有判别力）",
      rc1 != 0 and "FAIL] P7c 双用途事实已如实登记" in o1,
      f"EXIT={rc1}；" + ("已报红 ✓" if rc1 != 0 else "★ 仍然 PASS ⇒ 弱断言未消除"))

# ---------------------------------------------------------------------------
# #4 P7c 集合比较：负例 = 篡改集合关系（ref 集合人为改空）
# ---------------------------------------------------------------------------
print("")
print("#4 P7c 真实集合比较 —— 负例：把参照集算空 ⇒ same_set 翻转:")
c4 = copy("verify_d2c4_apk_delivery.py")
patch(c4, "ref_shas = set(ref.values())", "ref_shas = set()  # ★负例")
rc2, o2 = run(c4)
flipped = "相等=False" in o2
show("#4 负例 same_set 翻转为 False（真的在算）", flipped,
      "已翻转 ✓" if flipped else "★ 未翻转 ⇒ 集合比较是假的")
show("#4 负例断言报红", rc2 != 0,
      f"EXIT={rc2} " + ("已报红 ✓" if rc2 != 0 else "★ 未报红"))

# ---------------------------------------------------------------------------
# #5 V6：负例 = 删掉声明文本（declaration 置空）
# ---------------------------------------------------------------------------
print("")
print("#5 V6 声明自证 —— 负例：把声明文本置空:")
c5 = copy("verify_d2c5_filzaslop_static.py")
rc3, o3 = run(c5)
show("#5 正例 PASS", "PASS] V6 已如实声明未真编译" in o3, f"EXIT={rc3}")
patch(c5,
      'declaration = ("本判据未在真 Theos / 真 iOS SDK 上编译；"\n'
      '                   "结论仅覆盖静态层面；不得表述为「已验证可编译出 dylib」")',
      'declaration = ""  # ★负例：声明文本清空')
rc4, o4 = run(c5)
show("#5 负例 FAIL（有判别力）",
      "FAIL] V6 已如实声明未真编译" in o4,
      "已报红 ✓" if "FAIL] V6" in o4 else "★ 仍然 PASS ⇒ 弱断言未消除")
# ★ 第二负例：环境前提被破坏（伪造 THEOS 存在）⇒ 也应报红
c5b = copy("verify_d2c5_filzaslop_static.py")
patch(c5b, 'THEOS_ABSENT = (os.environ.get("THEOS", "") == "")',
      'THEOS_ABSENT = False  # ★负例：伪造 Theos 存在')
rc6, o6 = run(c5b)
show("#5 负例2（伪造 Theos 存在）FAIL", "FAIL] V6" in o6,
      "已报红 ✓" if "FAIL] V6" in o6 else "★ 未报红")

# ---------------------------------------------------------------------------
# #6 money_path：负例 = 登记文本与实测脱节
# ---------------------------------------------------------------------------
print("")
print("#6 money_path 登记自证 —— 负例：登记文本写死，脱离实测:")
c6 = copy("verify_money_path.py")
patch(c6,
      'registration = (f"code={code} bill行={n} "',
      'registration = (f"code=NOT_MEASURED bill行=NOT_MEASURED "')
rc5, o5 = run(c6)
show("#6 负例 FAIL（有判别力）",
      "FAIL] (c) to_address 不符" in o5,
      "已报红 ✓" if "FAIL] (c) to_address 不符" in o5 else "★ 仍然 PASS ⇒ 与实测脱节也不报红")

print("")
bad = [t for t, ok, _ in out if not ok]
print(f"=== 演示 {len(out) - len(bad)}/{len(out)} 项符合预期 ===")
for t, ok, d in out:
    print(f"  {'✓' if ok else '✗'} {t}: {d}")
print("DEMO=OK" if not bad else "DEMO=BAD")
sys.exit(0 if not bad else 1)
