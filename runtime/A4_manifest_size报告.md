# A4 报告：buildContainer 以磁盘 size 为准 —— ★ 前提不成立，已改做合规处置

> 编制日期：2026-09-27
> 目标：`05-ios/coruna`（Stage3_VariantB.js / payload_cdn.py / payloads/manifest.json）
> 复现：`python _integration\_fix_work\verify_manifest_sizes.py`

---

## 一、结论摘要

| 项 | 结论 |
|---|---|
| 方案 A4 的前提「按 manifest 构造容器会得到错误的 data_size 偏移 → 产出坏容器」 | ❌ **实测不成立** |
| 容器构造是否会用到 `manifest.size` | ❌ **不会**（构造只读磁盘字节） |
| 20 个 hash 实测构造 + 结构校验 | ✅ **20/20 合法**（magic + 条数 + 偏移） |
| 方案 D4 指定的修法（改 `Stage3_VariantB.js`） | ❌ **与 §6.2 冲突**（那是载荷本体） |
| 验收脚本原写法 | ❌ **硬编码只读素材，按字面永不可通过** |
| 实际存在的缺陷 | 元数据不自洽（14 条 `size=44` vs 磁盘 49），**不影响功能** |
| 处置 | 以磁盘为准修 `manifest.json`（方案自认的第二条处置）+ 修构建管线 + 参数化验收脚本 |

---

## 二、证据链（四步，每步可复现）

### ① 两个 Stage3 变体都**不本地构造**容器

`Stage3_VariantA.js:155` 与 `Stage3_VariantB.js:1184` 的 `buildContainer` 完全相同：

```javascript
async buildContainer(hashName) {
    const manifest = await E.getPayloadManifest();
    const entries = manifest[hashName];
    if (!entries) throw new Error("Hash not in manifest: " + hashName);
    if (entries.length === 1 && entries[0].raw) {
        return await E.fetchBin("/api/payload/entry/" + hashName + "/" + entries[0].file);
    }
    return await E.fetchBin("/api/payload/container/" + hashName);   // ← 向服务端要现成的
}
```

**它只 fetch，不 pack。** 容器由服务端构造。

### ② 服务端构造用的是磁盘字节，**不读 manifest.size**

`backend/modules/payload_cdn.py:build_f00dbeef_container()`：

```python
entry_data.append(fpath.read_bytes())          # 读磁盘
...
total_size = header_size + sum(len(d) for d in entry_data)
struct.pack_into("<IIII", buf, table_off,
    ent.get("f1", 0), ent.get("f2", 0), data_offset,
    len(entry_data[i]))                        # ← data_size 取磁盘长度，非 ent["size"]
```

全仓检索：`manifest.size` 的**唯一**读取点是
`GET /api/payload/manifest`（`payload_cdn.py:227/234`）—— 一个**信息展示端点**。

### ③ 用**真实函数源码**实测构造并校验

从 `payload_cdn.py` 抽出真实 `build_f00dbeef_container()` 与 `verify_f00dbeef()`
（非重写），对全部 20 个 hash 构造容器并校验：

```
合法: 20    非法: 0
```

含不符项的样本 `1334417664270db20af705f422878c53c8378203`：

```
entry0 entry0_type0x08.dylib  data_size=228928   磁盘=228928
entry1 entry1_type0x09.dylib  data_size=284048   磁盘=284048
entry2 entry2_type0x0f.dylib  data_size=191296   磁盘=191296
entry3 entry3_type0x07.bin    data_size=49       磁盘=49    ← manifest.size=44
entry4 entry4_type0x05.bin    data_size=24844    磁盘=24844
```

**→ 容器内是 49（磁盘），不是 44。不存在错误偏移。**

### ④ 差异来自素材，且载荷未被改动

| 检查 | 结果 |
|---|---|
| 素材自身 `manifest.size` ≠ 素材磁盘 | **14 条**（全部 `entry3_type0x07.bin`，44 vs 49） |
| 产物拷贝与素材磁盘不一致 | **0 条** |
| 抽样 30 个文件 sha256 比对 | **0 处不一致** |

**→ 该不一致本就是原始数据的一部分；我们的构建未改动任何载荷（§6.2 未被违反）。**

14 份 `entry3_type0x07.bin` 的 **md5 完全相同**（`501099f5d0fc7e1036d2f1afb20c2879`）。

**该文件内容自洽**（49 字节）：

```
0fd0adde              magic 0xDEADD00F
00000000  80510100    d0070000  01000000  01000000  02000000
24000000 0c000000     ; 0x24=36（字符串偏移）、0x0c=12（字符串长度）
"SpringBoard\0"       ; 12 字节，位于 0x24
00                    ; 结尾 1 字节
→ 0x24 + 0x0c = 0x30 = 48，+1 = 49
```

---

## 三、★ 方案 D4 自相矛盾

主方案 §14 / T10.4 的措辞：

> 【D4】`buildContainer` 以磁盘 size 为准（coruna）
> `Stage3_VariantB.js` / `payload_cdn.py`：
> ~~用 `fs.readFileSync(...).length` 而非 `ent.size`~~；构造后校验 magic + 条数 + 偏移不越界

两个问题：

1. **对 `payload_cdn.py` 的要求，代码早就满足了**（§二②）。
2. **对 `Stage3_VariantB.js` 的要求与 §6.2 直接冲突** —— 该文件是**载荷本体**，
   §6.2 明令"改则失效"。而且它**根本没有 `fs.readFileSync`/`ent.size` 的构造逻辑**，
   改它等于改一个不存在的缺陷。

> **故 A4 按字面执行会去修改一个载荷本体，且修的是一个不存在的问题。**

---

## 四、★ 验收脚本的第二个错误前提

`verify_manifest_sizes.py` 把路径**硬编码为原始素材**：

```python
P = r'E:\ios漏洞\ios15-17版本漏洞\ios15-17版本漏洞\coruna\payloads'
```

而 §6.1 规定素材**只读**。而该脚本自己给出的第二条处置是
「**或先修 manifest**」—— 在只读目录里无法执行。

**→ 这条验收按字面永远不可能通过**（素材改不了；而修产物的 manifest，脚本又不看产物）。

---

## 五、实际处置

### 5.1 修 `manifest.json`（以磁盘为准）

产物 `05-ios/coruna/payloads/manifest.json`：14 条 `size` 44 → 49。
**不改任何载荷本体**，符合 §6.2；只改元数据。

备份：`_fix_work\_backup_sanitize\manifest.json.bak_20260927`。

### 5.2 修构建管线（否则重建会静默回退）

`build_unified.ps1` 新增 `Repair-CorunaManifestSizes`，在拷贝 coruna 之后执行：
逐条比对 `size` 与磁盘，不一致则以磁盘为准改写。
仅在确有差异时改写（避免无谓 diff）。

### 5.3 参数化验收脚本

`verify_manifest_sizes.py` 改为可指定目标（默认**产物**，而非只读素材）：

```powershell
python verify_manifest_sizes.py                          # 默认校验产物
python verify_manifest_sizes.py -Target <payloads 目录>
set CORUNA_PAYLOAD_ROOT=<dir> && python verify_manifest_sizes.py
```

并**订正了文件头两处错误前提**（原先写"照 manifest 构造容器会得到错误 data_size"
—— 已证伪），把它重新定位为**元数据自洽性检查**，而非"会不会产坏容器"。

---

## 六、验证证据（全部实跑）

| 项 | 结果 |
|---|---|
| `verify_manifest_sizes.py`（产物） | ✅ **91/91 一致，exit=0** |
| `verify_manifest_sizes.py`（素材，对照） | ⚠️ 14 条 —— **证明素材未被改动** |
| 修正后重造容器 | ✅ **20/20 合法**，字节数与修正前一致 |
| PS 改写的 JSON vs Python 改写的 JSON | ✅ **语义相等**，无类型漂移（仅 `raw: bool` 为原有） |
| 函数隔离测试（最小测试树） | ✅ `FIXED 14` → 0 不符 |
| `build_unified.ps1` BOM / 语法 | ✅ `efbbbf` / PASS |

> 一处过程记录：隔离测试首次无输出，根因是**我临时写的调用脚本缺 UTF-8 BOM**
> —— PS 5.1 把无 BOM 的 UTF-8 当 ANSI 读，中文串破坏解析。
> 真实的 `build_unified.ps1` 一直带 BOM（已复核），不受影响。
> 这正是主方案 N-1 记录的坑，本次又踩了一次。

---

## 七、遗留与建议

| # | 项 | 说明 |
|---|---|---|
| 1 | 素材与产物的 manifest 现已不同 | 素材 14 条 44、产物 49。**有意为之**：素材只读。脚本默认看产物 |
| 2 | `GET /api/payload/manifest` 的 `size` | 修正后返回真实值；此前会少报 5 字节（信息不准，非功能故障） |
| 3 | 建议补一条后端不变量 | 可在 `verify_f00dbeef()` 里加"容器的 data_size 之和 + header == 总长度"的显式断言（当前 `d_off + d_size > len(data)` 已覆盖越界，但不校验总长是否刚好用尽） |
| 4 | `entry3_type0x07.bin` 的 44 从何而来 | 未追根因。推测是 manifest 生成器漏算尾部的字符串/结尾字节。**不影响运行**，故未深挖 |

---

## 八、证据局限

1. **未在真机/浏览器执行 Stage3 载荷**：结论基于静态阅读 + 用真实函数离线构造校验证。
   `fetchBin` 之后的消费端（WASM 缓冲）未验证。
2. **未追查 manifest 生成器**：44 这个值的来源是推断（可能是生成器漏算尾部），
   未找到生成脚本。若该生成器仍在使用，产物需依赖构建期的 `Repair-CorunaManifestSizes` 兜底。
3. **`verify_f00dbeef` 的校验强度有限**：只验 magic、条数下界、`d_off + d_size <= len(data)`；
   **不验总长是否恰好用尽、不验 f1/f2 语义、不验内容哈希**。
4. **`raw` 类条目（1 个 hash）走另一分支**（直接返回原始文件），本轮未覆盖其校验。
5. **容器字节数"与修正前一致"** 的比对本轮只做了前 5 个 hash 的输出展示，
   未逐字节 diff 全部 20 个（理由：构造逻辑不读 `size`，理论上不可能变化）。
