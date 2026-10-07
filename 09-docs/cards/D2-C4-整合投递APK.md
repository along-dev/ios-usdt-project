---
id: D2-C4
mode: 实施
wave: D2
depends: [R5-C2]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  建立**投递包目录** `06-android/apk/{japapp,samples}/` 并搬运源素材。
  ★ 只做**目录建立 + 文件搬运 + manifest**，**不改任何代码**。
  ★ 与 `06-android/reference/apk/`（R5-C2 的**参照**）**必须分开**（参考素材方案 `:25`）。
  门禁强度自知：判据须核【sha256 与源一致】+【与 reference 目录不重叠混淆】。
来源: `完整版本开发方案_终版.md:198`（D2-C4：`06-android/apk/{japapp,samples}/`）
      + **`三项交付物核实_APK_IPA_无感.md:28-29`**（★ 主方案 §1.2 的**权威映射表**）
      + `参考素材搬运方案_IPA_APK_H5.md:25`（投递与参照必须分开）
      + ★ **Owner 裁决 (b)**：投递包 = 最小集（载荷 + 样本），非"参照的全量副本"
base:
  - path: 06-android\reference\apk\_MANIFEST.txt
    sha256: 7aaa8756c1e76985e15d0add15882ac5da2df4d5647e697b8a34c38a05daeb23
    bytes: 715
    eol: LF
allowed_paths:
  - 06-android\apk\**（★ 新建：投递包目录）
  - E:\ios漏洞\_integration\_fix_work\verify_d2c4_apk_delivery.py
forbidden_paths:
  - "06-android\\reference\\**（R5-C2 的参照目录，只读、不动）"
  - "06-android\\stage\\**、06-android\\full\\**、06-android\\tools\\**（只读）"
  - "05-ios\\**、02-backend-node\\**、03-web-admin\\**（不动）"
  - "★ 源素材（E:\\ios漏洞\\pjuyr\\**、E:\\ios漏洞\\recon\\**）—— 只读"
  - "09-docs\\spec\\contracts.md"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_d2c4_apk_delivery.py    # 动前红 / 动后绿
packages: {}
---

# D2-C4 [R2] 整合投递 APK → `06-android/apk/{japapp,samples}/`

## ★★ 规格来源：**方案 `:49-55` 的权威分类表**（Owner 裁 (a) 采此）

| # | 文件 | sha256(前12) | 大小 | 用途 |
|---|---|---|---|---|
| 1 | **`japapp.apk`** | `30d6701dd6ed` | 16,603,645 | **载荷 APK** |
| 2 | **`child_milkstream.apk`** | `cdbb17465b64` | 15,789,421 | **载荷 APK（子）** |
| 3 | **`myav.apk`** | `3d0180ea7301` | 24,139,973 | **样本** |
| 4 | **`strip.apk`** | `be31865a4a9d` | 16,043,281 | **脱壳链 L1 入口样本** |
| 5 | **`inner_b.apk`** | `0e3f9bad4c4b` | 7,748,611 | **脱壳链 L2 产物** |

**⇒ 恰好 5 条唯一。**

## ★★★ Owner 裁决 (a)：`samples/` 的来源已更正（**这是本卡的关键裁决**）

### 背景：两处文档冲突

| 文档 | 说法 |
|---|---|
| **方案 `:49-55`**（权威分类表） | 5 条唯一：**载荷 = japapp + child**；**样本 = myav + strip + inner_b**；并**明写** "`recon/apk2/jxrdxzps.apk` / `9812f565298c.apk` 与 `japapp.apk` **同哈希**" |
| `三项交付物核实:29` | `recon/apk2/*.apk` → `samples/` |

### ★ 实测证明两处冲突

```
recon/apk2/jxrdxzps.apk       = 30d6701dd6ed010c…  (16,603,645 B)
recon/apk2/9812f565298c.apk   = 30d6701dd6ed010c…  (16,603,645 B)
japapp_milkstream/japapp.apk  = 30d6701dd6ed010c…  (16,603,645 B)   ← 同一份！
```

**⇒ 若按 `三项交付物核实:29`，`samples/` 会装 `japapp.apk` 的副本
⇒ `japapp/` 与 `samples/` 出现**同一 sha256** ⇒ 正是 **P-2**（多副本）。**

### ★ Owner 裁决 (a)：**采方案 `:49-55` 的权威分类**

| 目标目录 | 内容 |
|---|---|
| **`06-android/apk/japapp/`** | **`japapp.apk` + `child_milkstream.apk`**（2 个载荷） |
| **`06-android/apk/samples/`** | **`myav.apk` + `strip.apk` + `inner_b.apk`**（3 个样本） |

**⇒ 5 条唯一，无一条重复出现在两个目录** ✓

**理由**：
1. 方案 `:49-55` 是**权威分类表**，且**主动指出了同哈希问题**；
2. `三项交付物核实:59` 也印证 —— 它列的"交付缺口"**只有载荷 APK**，
   **未把"样本"列为缺口**（说明 samples 不是核心缺口）；
3. (b)/(c) 会产生"同一 sha256 出现在两个投递子目录"，
   与参考素材方案 `:25`「投递与参照必须分开」的**同理**（防 P-2）。

## ★ 源素材清单（**实测存在**，2026-09-30）

```
E:\ios漏洞\pjuyr\all_assets\pjuyr_all_assets\japapp_milkstream\japapp.apk           30d6701dd6ed010c…  16,603,645 B
E:\ios漏洞\pjuyr\all_assets\pjuyr_all_assets\japapp_milkstream\child_milkstream.apk cdbb17465b64d74f…  15,789,421 B
E:\ios漏洞\pjuyr\all_assets\pjuyr_all_assets\myavlive\myav.apk                      3d0180ea7301c8d0…  24,139,973 B
E:\ios漏洞\recon\apk\strip.apk                                                      be31865a4a9de652…  16,043,281 B
E:\ios漏洞\recon\apk\unpacked\inner_b.apk                                           0e3f9bad4c4b88a7…   7,748,611 B
```

★ **注意**：`japapp_milkstream\vault_extracted\payload\child.apk` 与 `child_milkstream.apk`
**同哈希**（`cdbb17465b64d74f`）⇒ **去重后只搬一份**。

★ **`recon/apk2/*.apk` 不采用**（与 `japapp.apk` 同哈希，见上）。

## ★ 规格

### (a) 建立目录

```
06-android/apk/
├── japapp/          ← 载荷 APK
│   └── _MANIFEST.txt
└── samples/         ← 样本
    └── _MANIFEST.txt
```

### (b) 搬运规则

| 目标 | 内容 |
|---|---|
| `apk/japapp/` | **载荷 APK**（`japapp.apk`、`child_milkstream.apk`；★ 是否含 `child.apk` 须**按 sha256 去重后决定**） |
| `apk/samples/` | **样本**（`recon/apk2/*.apk`） |

★ **按 sha256 去重**（同内容只留一份）—— 参照 `参考素材搬运方案:101` 的命名规范。
★ **命名规范化**：去空格、统一可移植命名（`参考素材搬运方案:101`）。
★ **每个目录写 `_MANIFEST.txt`**：`sha256  filename  bytes  用途`（格式参照 `reference/apk/_MANIFEST.txt`）。

### (c) ★ 不得动 `reference/apk/`

**参照目录（R5-C2 建）保持原样**，本卡**只新增** `06-android/apk/`。

## ★ 判据要求

| # | 断言 |
|---|---|
| **P1** | `06-android/apk/{japapp,samples}/` 均存在 |
| **P2** | `japapp/` 至少含 1 个 `.apk`，且其 **sha256 与源一致** |
| **P3** | `samples/` 至少含 1 个 `.apk`，且其 **sha256 与源一致** |
| **P4** | ★ **每个目录有 `_MANIFEST.txt`**，格式含 `sha256  filename  bytes  用途` |
| **P5** | ★ **`reference/apk/` 未被改**（`_MANIFEST.txt` sha256 = base） |
| **P6** | ★ **`japapp/` 与 `samples/` 之间无同一 sha256**（防 P-2：同一文件不得出现在两个投递子目录） |
| **P7** | ★ **`apk/` 与 `reference/apk/` 的文件集合不完全相同**（证明投递集与参照集是独立的） |
| **P8** | 守护：`_manifest.sha256` 未改 |

★ **P2/P3 是本卡核心** —— 必须证明"搬的是真素材"（sha256 与源逐字节一致）。
★ **P6 是 Owner 裁 (a) 的直接验证** —— 若 samples 误用 `recon/apk2/*.apk`，P6 必红。

## 不在范围

- **不改任何代码**（纯搬运 + manifest）
- **不动 `reference/apk/`**
- 不修改源素材（只读）

## 证据要求

- 判据动前红 / 动后绿两次真实退出码
- ★ **每个搬运文件的 sha256 + bytes + 源路径 → 目标路径对照表**
- `_MANIFEST.txt` 的内容
- ★ 声明：**未改 `reference/apk/`**、**未改任何代码**

## 停靠点

1. 若**源素材路径与文档不符**（文件不存在）⇒ 停下升级
2. 若**搬运会与 `reference/apk/` 重叠**（P-2 风险）⇒ 停下升级
3. 若**同一 sha256 出现在两个目标目录** ⇒ 去重后仍冲突 ⇒ 停下升级
4. 若**总量异常大**（>200 MB）⇒ 停下升级（可能误搬全量）
