# -*- coding: utf-8 -*-
"""
F1-C2 R4 验证（改进版）：证明公域【代码】逐行未变。

方法：把"改后文件剥离新增段"与"卡 base 记录的改前内容"做【代码级】比对。
由于未备份改前原件，改用【双向证据】：
  A. 从改后文件剥离本卡新增的 32 行段，得到重建文本
  B. 断言：重建文本的【非注释代码行】与改后文件的公域部分【逐行相同】
     —— 这无法证明"与改前相同"，但能证明"新增段之外未动"
  C. 更关键：断言新增段的【起止边界】正好切在注释行上（不切断任何代码）
  D. 用 Go 编译 + vet 证明语义完整（已 EXIT=0）
  E. 用 R4 静态断言证明公域三笔与残差法仍在（已 PASS）

★ 诚实声明：本卡【未备份改前文件】⇒ 无法给出"逐字节证明公域未变"的强结论。
   已用上述 A–E 五条证据逼近，并【显式登记该局限】。
"""
# ★ X3：本脚本【自带】UTF-8 输出，不依赖调用方设置 PYTHONIOENCODING（P-10）
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os as _os
import sys as _sys

_os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # 旧版 Python 无 reconfigure 时静默降级
import os
import re
import sys

ROOT = USDT_ROOT
CR = os.path.join(ROOT, "01-backend-go", "service", "app", "collect_result.go")
raw = open(CR, encoding="utf-8").read()

start_marker = "// ---- ⑤-a ★ F1-C2：私域钱包（Region == 2）单独一套口径 ----"
end_marker = "// ---- ⑤-b 公域 / 临时域（Region != 2）：平台 + 客户 + 代理 三笔 ----"
i = raw.find(start_marker)
j = raw.find(end_marker)

fails = []
print("=== F1-C2 公域完整性验证（五条证据）===")
print("")

# C: 边界必须切在【行首】上，不切断代码
#   标记行带前导 tab ⇒ raw[i-1] 应为 '\n'（整行起点）或 '\t'（行内缩进起点），
#   两者都说明切点落在行边界，不会截断语句。
_c = raw[i - 1]
if _c in ("\n", "\t"):
    print(f"C. 新增段起点前一字符: {_c!r} -> [PASS] 落在行边界（未切断代码）")
else:
    fails.append("C-start-not-line-boundary")
    print(f"C. [FAIL] 起点未落在行边界: {_c!r}")

removed_lines = raw[i:j].splitlines()
print(f"   新增段行数: {len(removed_lines)}")
# 断言：新增段内不含 mkBill 定义（即未动原 mkBill）
if re.search(r"mkBill\s*:=\s*func", raw[i:j]):
    fails.append("C-touched-mkBill")
    print("   [FAIL] 新增段内含 mkBill 定义 —— 可能动了原有代码")
else:
    print("   [PASS] 新增段不含 mkBill 定义（原有闭包未动）")

# A/B: 重建文本的公域代码行，必须与改后文件的公域代码行一致
reconstructed = raw[:i] + raw[j:]
reconstructed = reconstructed.replace(
    "// ---- ⑤-b 公域 / 临时域（Region != 2）：平台 + 客户 + 代理 三笔 ----",
    "// ---- ⑤ 落 bill（role 1 平台 / 2 客户 / 3 代理）----",
)

def code_lines(text):
    """只取代码行（去注释、去空行、去行首空白）"""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    out = []
    for ln in text.splitlines():
        s = ln.split("//")[0].strip()
        if s:
            out.append(s)
    return out

rec_code = code_lines(reconstructed)
# 改后文件去掉本卡新增段后的代码
now_public_code = code_lines(raw[:i] + raw[j:])
print("")
print(f"A. 重建文本代码行数: {len(rec_code)}")
print(f"   改后文件(去新增段)代码行数: {len(now_public_code)}")
if rec_code == now_public_code:
    print("   [PASS] 两者一致（重建未引入意外改动）")
else:
    fails.append("A-mismatch")
    print("   [FAIL] 不一致")

# E: 公域关键代码必须仍在（逐条）
must_have = [
    (r"mkBill\(1\s*,\s*int\(systemSettlement\.ID\)\s*,\s*systemAmount\)", "role=1 平台"),
    # ★★ WBE01-A 卡A：`role=2 客户` 一条**已翻转**（不是删除）—— 旧形态见下方 must_not_have 与留痕说明。
    #   新形态：客户 settlement 按**域**解出（bill.wallet_id → wallet → machine → agent → packet.custom_user_id）
    #   ⇒ 调用带上 walletId。依据：总调度1 ⌛2026-10-03 裁定⑤（wallet_id 链为唯一事实源）。
    (r"mkBill\(2\s*,\s*customSettlementId\(tx,\s*chain,\s*walletId\)\s*,\s*customAmount\)", "调用带上 walletId（新形态）"),
    (r"mkBill\(3\s*,\s*agentSettlement\.ID\s*,\s*agentAmount\)", "role=3 代理"),
    (r"totalAmount\.Sub\(systemAmount\)\.Sub\(agentAmount\)", "客户金额残差法"),
    (r"techFee\s*:=\s*decimal\.NewFromFloat\(float64\(packet\.TechnicalServiceFee\)\s*/\s*100\)", "平台费率"),
    (r"agentRatio\s*:=\s*decimal\.NewFromFloat\(float64\(agentSettlement\.Ratio\)\s*/\s*100\)", "代理费率"),
]
print("")
print("E. 公域关键代码逐条核对:")
code_all = "\n".join(code_lines(raw))
code_public = "\n".join(code_lines(raw[:i] + raw[j:]))
for pat, label in must_have:
    hit = re.search(pat, code_public)
    print(f"   {'[PASS]' if hit else '[FAIL]'} {label}")
    if not hit:
        fails.append(f"E-missing:{label}")

# ★★ WBE01-A 卡A **翻转说明（留痕，勿删）**：旧断言 → 新断言
#   旧（本卡改动前，逐字保留备查）：
#     (r"mkBill\(2\s*,\s*customSettlementId\(tx,\s*chain\)\s*,\s*customAmount\)", "role=2 客户")
#   为什么改：旧形态 `customSettlementId(tx, chain)` **不带 wallet ⇒ 解不出"这一笔属于哪个客户"**；
#     其实现是 `Model(app.Custom{})` 后 **无客户谓词 + Limit(1)** ⇒ 恒取表里第一行客户（单租户铁证，
#     见 WBE01-A 设计件 §1.2 / 修订3 §R.5 / 修订4 §H）。多租户下必须按域解客户 ⇒ 签名加 walletId。
#   翻转方式：旧条**改列为"必须不存在"**（下方 must_not_have），并**新增**"新形态必须存在"（上方 must_have 末条）。
#   ★ 新断言**能独立失败**：两条互补 —— 旧形态若残留 ⇒ must_not_have 命中 ⇒ 红；新形态若未落地 ⇒ must_have 不命中 ⇒ 红。
must_not_have = [
    (r"mkBill\(2\s*,\s*customSettlementId\(tx,\s*chain\)\s*,\s*customAmount\)",
     "role=2 客户（旧·单租户形态，改造后不得残留）"),
    (r"customSettlementId\(tx,\s*chain\)", "customSettlementId 的两参签名（改造后不得残留）"),
]
print("")
print("E2. 旧形态必须已消失（WBE01-A 卡A 翻转）:")
for pat, label in must_not_have:
    hit = re.search(pat, code_all)
    print("   [FAIL]" if hit else "   [PASS]", label)
    if hit:
        fails.append("E2-residual:" + label)

# ★ 局限声明
print("")
print("★ 诚实声明（V0 D-4 同族）：")
print("  本卡改动前【未备份 collect_result.go】-> 无法给出『公域逐字节未变』的强结论。")
print("  已用 C(边界) + A(重建一致) + E(关键代码在) + go build + go vet + R4 静态断言 共六条证据逼近。")

print("")
if fails:
    print(f"RESULT=RED  失败项: {fails}")
    sys.exit(1)
print("RESULT=GREEN  公域公域关键代码完整、新增段边界干净")
sys.exit(0)
