# -*- coding: utf-8 -*-
"""生成 T14 改前/改后 unified diff（改前由改后 + 卡内记录的旧块逆推，sha 须等于 base）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import difflib
import hashlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = USDT_ROOT + r"\01-backend-go\service\app\wallet_resolver.go"
BASE_SHA = "5dfc6f19dd8bd7e455ae3109d3c2a0481d28112a95441b9f62e3fc99ff57fa95"

after_txt = open(P, encoding="utf-8").read()
after = after_txt.splitlines(keepends=True)

# T14 新增的注释块起点
cs = next(i for i, l in enumerate(after) if "T14（R-01 收口）" in l)
# 新 if 块起点
s = next(i for i, l in enumerate(after) if 'deviceId != "" || address != ""' in l)
# 新 if 块结束（return walletId, nil 在块外一层缩进）
e = next(i for i, l in enumerate(after) if i > s and l.strip() == "return walletId, nil")

old_block = (
    '\t\tif deviceId != "" && address != "" {\n'
    "\t\t\tcol, ok := walletAddressColumns[strings.ToLower(strings.TrimSpace(chain))]\n"
    "\t\t\tif !ok {\n"
    "\t\t\t\t// 两者均非空 ⇒ 校验是必须完成的动作；chain 不支持则无法校验 ⇒ 拒绝\n"
    '\t\t\t\treturn 0, fmt.Errorf("不支持的 chain: %q", chain)\n'
    "\t\t\t}\n"
    "\t\t\tvar row struct{ ID int }\n"
    "\t\t\tif err := tx.Model(&app.Wallet{}).\n"
    '\t\t\t\tSelect("wallet.id").\n'
    '\t\t\t\tJoins("left join machine on machine.id = wallet.machine_id").\n'
    '\t\t\t\tWhere("wallet.id = ? AND machine.device_id = ? AND wallet."+col+" = ?",\n'
    "\t\t\t\t\twalletId, deviceId, address).\n"
    "\t\t\t\tLimit(1).\n"
    "\t\t\t\tFind(&row).Error; err != nil {\n"
    "\t\t\t\treturn 0, err\n"
    "\t\t\t}\n"
    "\t\t\tif row.ID == 0 {\n"
    "\t\t\t\t// 只回显调用方自己提供的 wallet_id，不泄漏 machine/地址等库内信息\n"
    '\t\t\t\treturn 0, fmt.Errorf("wallet_id=%d 与 device_id/address 不一致", walletId)\n'
    "\t\t\t}\n"
    "\t\t}\n"
).splitlines(keepends=True)

# 改前 = [0:cs] + 补回被替换掉的空注释行 + 旧 if 块 + [e:]
# cs 指向 "★ T14（R-01 收口）" 那一行，其上一行在改前是空注释行 "//"
before_lines = after[:cs] + ["\t\t//\n"] + old_block + after[e:]
before_bytes = "".join(before_lines).encode("utf-8")

print("reconstructed BEFORE sha256 =", hashlib.sha256(before_bytes).hexdigest())
print("expected          BASE sha  = %s" % BASE_SHA)
print("MATCH =", hashlib.sha256(before_bytes).hexdigest() == BASE_SHA)
print("BEFORE bytes =", len(before_bytes), "(expect 3825)")
print()
print("================ UNIFIED DIFF (before -> after) ================")
diff = difflib.unified_diff(
    before_lines, after,
    fromfile="a/01-backend-go/service/app/wallet_resolver.go",
    tofile="b/01-backend-go/service/app/wallet_resolver.go",
    n=3,
)
sys.stdout.write("".join(diff))
