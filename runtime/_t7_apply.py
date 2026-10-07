# -*- coding: utf-8 -*-
"""T7 收口：更正 需求文档.md §7.2 的「18.6 RCE 缺失」误判。

★ 二进制读写，零换行转换（P-36）。
★ eol 断言：CRLF + LONE_CR 不变（P-37）。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib

P = USDT_ROOT + r"\09-docs\analysis\需求文档.md"

OLD_GAP = """**缺口**：
- **18.6 的 RCE 阶段缺失**：`rce_module_18.6.js` 仅 **85 字节存根**（`dummyy` 函数）
- **18.7+ 无版本键**"""

NEW_GAP = """**缺口**：
- ~~**18.6 的 RCE 阶段缺失**：`rce_module_18.6.js` 仅 85 字节存根~~
  ★★ **【T7 更正（二期，2026 本轮）】该判断【有误】** ——
  **18.6 的 RCE【并不缺失】**：它把 RCE 从 **page 上下文整体搬进了 worker**。
  铁证：① `rce_loader.js` 的 18.6 分支只发 **`type:'stage1_rce'`**、
  **从不 `new check_attempt()`**（18.4 分支才那么做）；
  ② `rce_worker_18.6.js` 的 `stage1_rce` 处理（L10188–10201）**无任何
  `rceCode`/`check_attempt` 痕迹**，RCE 由 worker 内 `main()` 自行完成；
  ③ 85 B 存根内的 `dummyy` **无任何调用点** ⇒ **是死代码/孤儿文件**。
  **⇒ `rce_module_18.6.js` 的 85 B 是【正确的架构结果】，不是残缺。**
- ★★ **【T7 新发现·真实缺口】18.6 的文件【未部署到后端模板】**
  （详见下方「扩展方法」第 1 条）：
  `02-backend-node/src_restored/plugins/c2/services/chain-darksword.js:51-54`
  的 `DARKSWORD_MODULES_EXTRA` **已登记** `ds_rce_worker_186` / `ds_rce_module_186`，
  但 **`02-backend-node/templates/darksword/` 下这两个文件【不存在】**；
  且 `05-ios/darksword/server.py:100` 的 `SYMLINKS` **只映射 18.4**。
- **18.7+ 无版本键**"""

OLD_METHOD1 = """1. **补 18.6 RCE**：`rce_module_18.6.js` 仅 85 字节存根，但
   **`rce_worker_18.6.js` 有 526,012 字节**（18.4 版仅 44,086，**约 12 倍**），
   且实测含真实利用原语：
   ```javascript
   const no_cow = 1.1;                    // JSC 数组类型混淆常用常量
   const unboxed_arr = [no_cow];
   const boxed_arr = [{}];
   ```
   > **注**：该文件内 `sbx0_offsets` / `linkedit_to_device` / `MessageName`
   > 命中均为 **0** —— 说明它**不是**沙箱逃逸模块，而是 **RCE 阶段的完整实现**。
   > **它是恢复 18.6 RCE 的唯一线索**，建议优先分析。"""

NEW_METHOD1 = """1. ★★ **【T7 更正】不是"补 18.6 RCE"，而是"部署 18.6 的既有文件"**：
   `rce_worker_18.6.js`（**526,012 B / 10,206 行**）**就是 18.6 的完整 RCE 实现**
   （**worker 内自包含**）。**12 倍差异的主因**：其 `rce_offsets` 巨型表
   **≈442,884 B（占全文件 84.2%）** —— 18.4 把偏移库放在 page 侧
   `rce_module.js`（174,524 B），18.6 **内联进 worker**
   ⇒ **两者是同一架构的两种切分，不是"完整 vs 残缺"。**
   > **注**：`sbx0_offsets` 命中 **0**（**证明它非沙箱逃逸模块**）；
   > 但 `linkedit_to_device` 命中 **2**（**版本键含 `'18,4'…'18,6,2'`**）、
   > `device_chipset` **156 条** ⇒ **它自带 18.6 的偏移**，
   > **不需要外部补表**。且其尾段 **L10170 `getJS('/sbx0_main_18.4.js')`**
   > ⇒ **RCE 完成后自行接力到沙箱逃逸**。
   >
   > ★★ **绝不要用 `rce_worker_18.6.js` 覆盖 85 B 存根** ——
   > 会在 page 主线程与真正的 worker **抢写 `self[0]/self[1]`**
   > （worker L9–10 也写这对槽位）、page 无 `WorkerGlobalScope`
   > 导致 vtable 扫描不可能成立、且白付 526 KB 下载。
   >
   > ★★ **真实待办 = 部署缺口**（**另立卡 T18**）：
   > ① `chain-darksword.js:51-54` 已登记 18.6 两模块，但
   >   **`02-backend-node/templates/darksword/` 下无这两个文件**；
   > ② `05-ios/darksword/server.py:100` 的 `SYMLINKS` 只映射 `rce_worker_18.4.js`；
   > ③ `_templates/darksword/` 下无 18.6 文件。
   > ⇒ **18.6 能否真被下发，未验证。**"""

raw = open(P, "rb").read()
before = hashlib.sha256(raw).hexdigest()
print("  base sha256: %s  bytes %d" % (before[:16], len(raw)))

n1 = raw.count(OLD_GAP.encode("utf-8"))
n2 = raw.count(OLD_METHOD1.encode("utf-8"))
print("  OLD_GAP 命中: %d" % n1)
print("  OLD_METHOD1 命中: %d" % n2)
if n1 != 1 or n2 != 1:
    print("  ★ 命中数不为 1 ⇒ abort")
    raise SystemExit(1)

out = raw.replace(OLD_GAP.encode("utf-8"), NEW_GAP.encode("utf-8"))
out = out.replace(OLD_METHOD1.encode("utf-8"), NEW_METHOD1.encode("utf-8"))


def eol(b):
    crlf = b.count(b"\r\n")
    return crlf, b.count(b"\n") - crlf, b.count(b"\r") - crlf


cb, lb, crb = eol(raw)
ca, la, cra = eol(out)
print("  eol: CRLF %d→%d  LONE_LF %d→%d  LONE_CR %d→%d" % (cb, ca, lb, la, crb, cra))
assert cb == ca and crb == cra, "eol 风格被改！"

open(P, "wb").write(out)
after = hashlib.sha256(open(P, "rb").read()).hexdigest()
print("  → after %s  (delta %+d)" % (after[:16], len(out) - len(raw)))
print("  ✅ 已更正")
