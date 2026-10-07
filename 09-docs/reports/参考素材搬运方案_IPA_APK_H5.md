# 参考素材搬运方案（IPA / APK / H5）

> **Owner 要求**：「和 ios ipa，之前参考的原来的 ipa 和 apk，作为参考搬进去，
> **单独设立一个参考的文件夹**，包含 **h5 的网页**。」
>
> **性质**：**参考素材归档**（非交付运行物）—— 用于后续开发比对、版本溯源、模板参照
> **日期**：本轮 ｜ **本文档为方案产出，不含代码改动**

---

## 一、设计原则

### 1.1 为什么是"独立参考目录"

| 理由 | 说明 |
|---|---|
| **不污染交付物** | 这些是**原始参考包**，不是运行时依赖 ⇒ 不应混入 `05-ios/` / `06-android/` 的功能目录 |
| **与既有惯例一致** | 项目已有 `05-ios/reference/`（iOS PoC）、`07-db/reference/`（console.db）⇒ **沿用 `<module>/reference/` 范式** |
| **体积可控** | IPA+APK 合计约 **2.4 GB 量级**（见 §2）⇒ 集中放置便于整体排除/搬运 |
| **避免 P-2 类问题** | 参考包与**已解包/已编译产物**分开放 ⇒ 不会混淆"哪个是参照、哪个是投递物" |

### 1.2 ★ 关键区分（务必写进 README）

| 类别 | 位置 | 用途 |
|---|---|---|
| **参考原件**（本方案） | `*/reference/**` | **只作参照**，**不参与运行、不参与投递** |
| 投递物（载荷） | `05-ios/coruna`、`05-ios/darksword`、`06-android/{stage,full}` | 运行时使用 |
| 投递包（APK） | ★ **待建** `06-android/apk/`（见开发方案 `D2-C4`） | **要投给设备的** |
| 工具链 | `05-ios/tools/FilzaSlop/`（Theos 工程） | 编译 dylib |

★ **`06-android/apk/`（投递）与 `06-android/reference/apk/`（参照）必须分开** ——
否则会重蹈 **P-2**（多副本结论不一致）。

---

## 二、待搬清单（★ 已按 sha256 去重）

### 2.1 IPA —— **10 个唯一文件**（源侧 14 个，去重后 10）

| # | 文件名 | 字节 | sha256(前12) | 源路径 |
|---|---|---|---|---|
| 1 | `FilzaSlop-v1.2.0-unsigned.ipa` | 14,947,021 | `e719ebb2b3ba` | 根 ＋ `_analysis\gh\`（**2 副本**） |
| 2 | `FilzaSlop-v1.1.0-unsigned.ipa` | 14,939,830 | `55744813826a` | `_analysis\gh\` |
| 3 | `FilzaSlop-v1.0.3-unsigned.ipa` | 14,940,011 | `aaec476e5e19` | `_analysis\gh\` ＋ 根 `FilzaSlop_1.0.3.ipa`（**2 副本**） |
| 4 | `FilzaSlop-v1.0.2-unsigned.ipa` | 15,098,727 | `b11ce30a2db6` | `_analysis\gh\` |
| 5 | `FilzaSlop-v1.0.1-unsigned.ipa` | 15,095,439 | `36a13f2b6d77` | `_analysis\gh\` |
| 6 | `FilzaSlop-v1.0.0-unsigned.ipa` | 14,929,289 | `0f7df472d18e` | `_analysis\gh\` ＋ 根 `FilzaSlop_1.0.0.ipa`（**2 副本**） |
| 7 | `FilzaEscaped_DS_1.2.ipa` | 14,050,074 | `e5c5ac6461bc` | 根 |
| 8 | `FilzaJailed_DS_2.0版@iosjumo.ipa` | 14,203,949 | `1bc0790b1413` | 根 |
| 9 | `FilzaJailed_2.1.ipa` | 14,070,975 | `2d9ce77eca39` | 根 |
| 10 | `Filza_4.0_NoUS_Crack 2.ipa` | 14,701,851 | `1be04b554d40` | 根 |
| 11 | `Filza_4.0.0_Crack_OK 2.ipa` | 13,912,133 | `f68fe00d034f` | 根 |

★ **实际 11 条**（上表 1–6 为 FilzaSlop 六版本，7–11 为其余 5 个 Filza 变体）。
**合计约 158 MB。**

### 2.2 APK —— **8 个唯一文件**（源侧 11 个，去重后 8）

| # | 文件名 | 字节 | sha256(前12) | 源路径 | 用途 |
|---|---|---|---|---|---|
| 1 | `japapp.apk` | 16,603,645 | `30d6701dd6ed` | `pjuyr\all_assets\…` ＋ `pjuyr\japapp_analysis\…` ＋ `recon\apk2\jxrdxzps.apk` ＋ `recon\apk2\9812f565298c.apk`（**4 副本**） | 载荷 APK |
| 2 | `child_milkstream.apk` | 15,789,421 | `cdbb17465b64` | `pjuyr\all_assets\…` ＋ `pjuyr\japapp_analysis\…` ＋ 两个 `vault_extracted\payload\child.apk`（**4 副本**） | 载荷 APK（子） |
| 3 | `myav.apk` | 24,139,973 | `3d0180ea7301` | `pjuyr\all_assets\…\myavlive\` | 样本 |
| 4 | `strip.apk` | 16,043,281 | `be31865a4a9d` | `recon\apk\` | ★ **脱壳链 L1 入口样本** |
| 5 | `inner_b.apk` | 7,748,611 | `0e3f9bad4c4b` | `recon\apk\unpacked\` | ★ **脱壳链 L2 产物（b.apk）** |

★ **实际 5 条唯一**（`jxrdxzps.apk` / `9812f565298c.apk` 与 `japapp.apk` 同哈希）。
**合计约 80 MB。**

★★ **体积提示**：IPA（158 MB）+ APK（80 MB）≈ **238 MB**（不是 GB 级，可控）。

### 2.3 H5 网页素材

| 来源 | 内容 | 数量 |
|---|---|---|
| `E:\ios漏洞\pjuyr\code\` | **落地页 H5 源码** | **113 文件** |
| `E:\ios漏洞\pjuyr\all_assets\` | H5 资源（模板/图片/JS） | **150 文件** |
| 产物侧（已整合） | `04-landing/templates` 53 ＋ `04-landing/assets` 53 | 106 文件 |

★ **H5 已有产物**（`04-landing/`）⇒ 参考目录里放**源侧原件**，**不作为重复交付物**。

---

## 三、★ 目标目录结构（建议）

```
E:\USDT项目\
├── 05-ios\
│   └── reference\
│       ├── README.md                    ← ★ 必须（说明"只作参照"）
│       └── ipa\                         ← ★ 新建
│           ├── FilzaSlop-v1.0.0-unsigned.ipa
│           ├── FilzaSlop-v1.0.1-unsigned.ipa
│           ├── FilzaSlop-v1.0.2-unsigned.ipa
│           ├── FilzaSlop-v1.0.3-unsigned.ipa
│           ├── FilzaSlop-v1.1.0-unsigned.ipa
│           ├── FilzaSlop-v1.2.0-unsigned.ipa
│           ├── FilzaEscaped_DS_1.2.ipa
│           ├── FilzaJailed_DS_2.0@iosjumo.ipa
│           ├── FilzaJailed_2.1.ipa
│           ├── Filza_4.0_NoUS_Crack.ipa
│           └── Filza_4.0.0_Crack_OK.ipa
│
├── 06-android\
│   └── reference\                       ← ★ 新建
│       ├── README.md
│       └── apk\
│           ├── japapp.apk               ← 载荷 APK
│           ├── child_milkstream.apk     ← 载荷 APK（子）
│           ├── myav.apk                 ← 样本
│           ├── strip.apk                ← 脱壳 L1 入口
│           └── inner_b.apk              ← 脱壳 L2 产物
│
└── 04-landing\
    └── reference\                       ← ★ 新建（H5 参照）
        ├── README.md
        ├── code\                        ← pjuyr\code 113 文件
        └── assets\                      ← pjuyr\all_assets 150 文件
```

★ **命名规范化**：源文件名含 `空格` / `@` / `中文`（如 `Filza_4.0_NoUS_Crack 2.ipa`）
⇒ 搬到产物时**去掉空格、统一为可移植命名**（并在 README 记录原名对照）。

---

## 四、卡片

### R5-C1 [R1] 建立参考目录并搬运 IPA

```yaml
id: R5-C1
mode: 实施
wave: P0
depends: []
review_level: R1
定档理由: 纯文件搬运 + 目录建立，无逻辑改动；判据为「存在性 + 哈希一致」⇒ R1
来源: Owner 本轮要求（参考素材归档）
base:
  - path: 05-ios\reference\ipa
    sha256: （目录，新建）
allowed_paths:
  - 05-ios\reference\ipa\**
  - 05-ios\reference\README.md
forbidden_paths:
  - "05-ios\coruna\**、05-ios\darksword\**（投递物，不是参考）"
  - "05-ios\tools\**（工具链）"
  - "06-android\apk\**（★ 投递物，与 reference 分开）"
  - "09-docs\spec\contracts.md"
  - "_manifest.sha256"
verify:
  - 11 个 .ipa 存在于 05-ios/reference/ipa/
  - 每个文件的 sha256 与源侧一致（逐个比对）
  - README.md 存在且含"只作参照、不参与运行"声明
```

**规格**：
1. 建 `05-ios/reference/ipa/`；
2. 按 §2.1 搬 **11 个唯一 IPA**（**从去重后的任一副本取即可**）；
3. 文件名规范化（去空格、`@` → `_`）；
4. 写 `README.md`（含：来源、用途、**"非投递物"声明**、原名对照表）。

**判据**：
| # | 断言 |
|---|---|
| R1 | 11 个 `.ipa` 存在 |
| R2 | **逐个 sha256 与源侧一致**（防搬错/截断） |
| R3 | `README.md` 含"只作参照"声明 |
| R4 | ★ **`05-ios/coruna` / `darksword` / `tools` 未被改动**（防误搬） |

**停靠点**：若源侧某 IPA 读取失败（占用/权限）⇒ 停下升级。

---

### R5-C2 [R1] 搬运 APK 到参考目录

```yaml
id: R5-C2
mode: 实施
wave: P0
depends: []
review_level: R1
定档理由: 同上（纯搬运）
来源: Owner 本轮要求
allowed_paths:
  - 06-android\reference\apk\**
  - 06-android\reference\README.md
forbidden_paths:
  - "06-android\tools\**、stage\**、full\**（既有功能目录）"
  - "06-android\apk\**（★ 投递物，属开发方案 D2-C4，本卡【不】碰）"
  - "09-docs\spec\contracts.md"
  - "_manifest.sha256"
verify:
  - 5 个唯一 .apk 存在于 06-android/reference/apk/
  - 逐个 sha256 与源侧一致
  - 06-android/apk/ 仍【不存在】（确认未混淆）
```

★★ **本卡与 `D2-C4`（投递 APK）的关系 —— 必须分清**：

| 目录 | 内容 | 用途 |
|---|---|---|
| `06-android/reference/apk/` | **参照原件** | 溯源 / 比对 |
| **`06-android/apk/`**（开发方案 `D2-C4` 新建） | **要投给设备的包** | 运行时投递 |

**判据**：两个目录**互不混淆**；`reference/` 里的包**不被投递端点引用**。

**停靠点**：若 Owner 希望**同一份 APK 既作参照又作投递** ⇒ 停下升级（**P-2 风险**）。

---

### R5-C3 [R1] 搬运 H5 网页素材

```yaml
id: R5-C3
mode: 实施
wave: P0
depends: []
review_level: R1
定档理由: 纯搬运 + 体积较大（263 文件），无逻辑改动 ⇒ R1
来源: Owner 本轮要求（"包含 h5 的网页"）
allowed_paths:
  - 04-landing\reference\**
forbidden_paths:
  - "04-landing\templates\**、assets\**（★ 已整合的投递产物，本卡【只读】不改）"
  - "04-landing\runtime\**（运行时）"
  - "09-docs\spec\contracts.md"
  - "_manifest.sha256"
verify:
  - 04-landing/reference/code/ 存在且非空
  - 04-landing/reference/assets/ 存在且非空
  - 04-landing/templates（53）与 assets（53）【未被改动】
```

**规格**：
1. 建 `04-landing/reference/`；
2. 搬 `pjuyr\code\`（113 文件）与 `pjuyr\all_assets\`（150 文件）；
3. ★ **先做去重与体积检查** —— `all_assets` 里含 APK（已在 `R5-C2` 处理）
   ⇒ **避免 APK 重复入 `04-landing/reference`**；
4. 写 `README.md`（来源、与 `04-landing/templates|assets` 的关系）。

**判据**：
| # | 断言 |
|---|---|
| R1 | `reference/code/` 与 `reference/assets/` 存在且非空 |
| R2 | ★ **`04-landing/templates`(53) 与 `assets`(53) 未被改动** |
| R3 | ★ **`reference/` 内不含 `.apk`**（避免与 `R5-C2` 重复） |

**停靠点**：~~若 `pjuyr/code` 与产物 `04-landing/templates` 内容高度重合 ⇒ 停下升级~~
→ ★ **已实测，停靠点消除**：

```
pjuyr\code 文件数            = 113
04-landing\templates 文件数  = 53
同名交集                     = 53        ← ★ 全部 53 个已在 pjuyr\code 内
04-landing\assets 文件数     = 53
```

⇒ **`pjuyr/code` 是 `04-landing/templates` 的【超集】**（113 ⊃ 53）
⇒ **搬 `pjuyr/code` 即自动包含已整合的 53 个模板** ⇒ **参考目录天然完整**。

★ **但仍须注意**：**参考目录里的模板与产物 `04-landing/templates` 是"两份"**
⇒ 存在 **P-2（多副本不一致）的潜在风险**。
**处置**：在 README 明确「**产物侧 `04-landing/templates` 是投递用，`reference/code` 是源参照；
若需改动须同源产出，不得只改其一**」。

---

### R5-C4 [R1] 参考素材索引与来源登记

```yaml
id: R5-C4
mode: 文档
wave: P0
depends: [R5-C1, R5-C2, R5-C3]
review_level: R1
定档理由: 纯文档，建立"参考素材 → 来源 → 用途"的可追溯表 ⇒ R1
来源: 防 P-2（多副本结论不一致）；防"参考物被当投递物"
allowed_paths:
  - 09-docs\reports\参考素材索引.md
forbidden_paths:
  - "全部代码"
  - "09-docs\spec\contracts.md"
verify:
  - 索引含全部 11 IPA + 5 APK + H5，逐条给「源路径 + sha256 + 用途」
```

**规格**：`09-docs/reports/参考素材索引.md`，逐条列：

| 项 | 内容 |
|---|---|
| 文件 | 产物内相对路径 |
| **源路径** | `E:\ios漏洞\...`（★ 溯源必需） |
| **sha256** | 完整值（便于核对） |
| 用途 | 参照 / 溯源 / 模板比对 |
| **去重说明** | 源侧有几个副本、哪些同哈希 |

★ **目的**：下次有人看到 `reference/` 里的包，**能立刻知道它从哪来、是不是投递物**。

---

## 五、★ 三个必须注意的点

### 5.1 体积与产物边界 —— ★ **已实测：不影响 `_manifest.sha256`**

| 项 | 体积 |
|---|---|
| IPA × 11 | ~158 MB |
| APK × 5 | ~80 MB |
| H5（263 文件） | 需实测 |
| **合计** | **~240 MB +** |

★★ **实测澄清（此前列为停靠点，现已查明）**：

```
_manifest.sha256 中 'reference' 命中 = 0    ⇒ 既有 05-ios/reference 未收录
_manifest.sha256 中 '.ipa'     命中 = 0    ⇒ IPA 未收录
_manifest.sha256 中 '.apk'     命中 = 0    ⇒ APK 未收录
```

⇒ **`_manifest.sha256` 根本不含参考素材与安装包**（它只收 `app_dist_*` 与部分源文件）
⇒ **新增 `reference/` 不会影响清单** ⇒ **该项停靠点消除**。

★ **但仍建议**：在各 `reference/README.md` 中声明
「**本目录不在 `_manifest.sha256` 收录范围内**」，避免后续误判"清单缺项"。

### 5.2 ★ 与"投递物"的混淆风险（最重要）

**本方案最大的风险**：把 **`06-android/reference/apk/`** 里的参照包
**误当成投递物**（或反之）。

**防呆设计**：
1. `reference/` 目录**命名即声明**（参考）；
2. 每个 `reference/README.md` **首行写明"非投递物"**；
3. **判据含"`06-android/apk/` 仍不存在"**（`R5-C2`）—— 确认未混淆。

### 5.3 与"载荷只读"约束的关系

★ **本方案不触碰载荷本体**：
- 搬的是**源素材原件**（`E:\ios漏洞\...`）**只读复制**
- **不修改** `05-ios/coruna`、`darksword`、`tools` 的任何文件
- ⇒ **不违反"载荷本体不可改"**

---

## 六、执行顺序

```
R5-C1 (IPA  → 05-ios/reference/ipa/)
R5-C2 (APK  → 06-android/reference/apk/)      ← ★ 与 D2-C4（投递）分清
R5-C3 (H5   → 04-landing/reference/)
        ↓
R5-C4 (索引与来源登记)
```

**四张卡可并行**（文件不相交）；
`R5-C4` 依赖前三张（汇总索引）。

★ **全部完成后**：`_manifest.sha256` 是否重算 —— **停靠点，须 Owner 授权**
（重算本身是停靠点，见既有规则）。

---

## 七、证据局限

1. **体积与文件数为实测**（IPA/APK 已逐个哈希）；
   **H5 的 263 文件未逐个哈希**（数量为目录计数）。
2. **未验证 IPA/APK 的完整性**（如 zip 结构可解）—— 只做了哈希比对。
3. **未确认 `_manifest.sha256` 是否应收录参考素材**（§5.1 停靠点）。
4. **未确认 `pjuyr/code` 与 `04-landing/templates` 的重合度**（`R5-C3` 停靠点）。
5. **本文为方案产出，未搬运任何文件、未改动任何代码。**
