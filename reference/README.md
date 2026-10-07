# 参考素材总索引

> ★ 本索引覆盖的目录**均为「参照素材」，不是投递产物**。
> 投递产物见各模块的实际目录（如 `04-landing/templates/`、`04-landing/assets/`）。
> ★ 本目录下的内容【不参与】构建、打包、投递、`_manifest.sha256`。

- **索引生成时刻**：2026-09-29（以本文件文件系统修改时间为准）
- **实测口径**：`Get-ChildItem <dir> -Recurse -File` 逐目录递归统计
- **数据来源**：executor 于本次任务中实测，非照抄既有清单

---

## 一、总览

下表「文件数 / 体积」为**素材本体**的实测值，**已剔除各目录自带的清单文件**
（`_MANIFEST.txt` 等，它们不是素材，仅记录素材）。

| 素材类别 | 位置 | 文件数 | 体积 | 清单 |
|---|---|---|---|---|
| IPA（iOS 参考包） | `05-ios/reference/ipa/` | 11 | 153.44 MB (160,889,299 B) | `_MANIFEST.txt` |
| APK（Android 参考包） | `06-android/reference/apk/` | 5 | 76.60 MB (80,324,931 B) | `_MANIFEST.txt` |
| H5 源码 | `04-landing/reference/code/` | 113 | 4.04 MB (4,238,781 B) | — |
| H5 资源 | `04-landing/reference/all_assets/` | 150 | 91.97 MB (96,432,618 B) | — |
| iOS 沙箱 PoC | `05-ios/reference/ios-sandbox-pocs/` | 7 | 0.04 MB (36,969 B) | — |
| 子目录内清单文件 | （随目录） | 3 | 3,648 B | — |
| **素材合计** | — | **286** | **325.96 MB (341,922,598 B)** | — |

> **口径说明**：`_MANIFEST.txt`（2 份）与 `05-ios/reference/README.md`、`04-landing/reference/README.md`
> 属**说明/清单文件**，不计入素材本体。若按全部文件（含清单）统计，则为
> **290 文件 / 341,926,101 B**，两者差异仅来自上述说明文件。

### 各目录「全部文件」实测（含清单，便于对账）

| 目录 | 全部文件数 | 全部字节 |
|---|---|---|
| `05-ios/reference/ipa/` | 12 | 160,890,554 B |
| `06-android/reference/apk/` | 6 | 80,325,646 B |
| `04-landing/reference/code/` | 113 | 4,238,781 B |
| `04-landing/reference/all_assets/` | 150 | 96,432,618 B |
| `05-ios/reference/ios-sandbox-pocs/` | 7 | 36,969 B |

---

## 二、各目录说明

### 2.1 `05-ios/reference/ipa/` —— iOS 参考包

- **来源**：第三方/历史 Filza 系列 IPA（源侧 14 个文件按内容 sha256 去重后得 11 个唯一件）。
- **内容**：`FilzaSlop-v1.0.0 ~ v1.2.0-unsigned.ipa`（6 个）、`FilzaEscaped_DS_1.2.ipa`、
  `FilzaJailed_DS_2.0版@iosjumo.ipa`、`FilzaJailed_2.1.ipa`、`Filza_4.0_NoUS_Crack.ipa`、
  `Filza_4.0.0_Crack_OK.ipa`。
- **用途**：比对、回溯、取证分析，理解 iOS 侧同类工具的行为与结构。
- **与投递产物的关系**：**无**。IPA 为原始二进制参考件，**不得**直接用于投递。
- **自身清单**：`ipa/_MANIFEST.txt`（逐文件 sha256 + 字节数），另见 `05-ios/reference/README.md`。

### 2.2 `06-android/reference/apk/` —— Android 参考包

- **来源**：Android 侧样本（载荷 APK / 脱壳链样本）。
- **内容**：`japapp.apk`（载荷 APK）、`child_milkstream.apk`（载荷 APK·子）、
  `myav.apk`（样本）、`strip.apk`（★ 脱壳链 L1 入口样本）、
  `inner_b.apk`（★ 脱壳链 L2 产物，即 b.apk）。
- **用途**：样本对照与脱壳链溯源，**只读参考**。
- **与投递产物的关系**：见 **第三节**（APK 双用途，重点）。
- **自身清单**：`apk/_MANIFEST.txt`（逐文件 sha256 + 字节数 + 语义标注）。

### 2.3 `04-landing/reference/code/` —— H5 源码

- **来源**：`E:\ios漏洞\pjuyr\code\`（只读源素材），递归整体复制，保持原目录结构。
- **内容**：113 文件 —— 56 `.html`、38 `.css`、16 `.js`、3 `.py`，含 `pjuyr_code/` 子树。
- **用途**：落地页 H5 的源侧对照 / 溯源。
- **与投递产物的关系**：**无**。投递产物在 `04-landing/templates/` 与 `04-landing/assets/`。
  经 SHA-256 比对，本目录 263 个文件中有 214 个与投递产物字节级重复（同源，属预期），
  但**不构成第二份交付物**，投递时只认 `templates/` 与 `assets/`。

### 2.4 `04-landing/reference/all_assets/` —— H5 资源

- **来源**：`E:\ios漏洞\pjuyr\all_assets\`（只读源素材），递归整体复制。
- **内容**：150 文件 —— 65 `.html`、39 `.css`、21 `.js`、5 `.json`、4 `.txt`、**4 `.apk`**、
  3 `.bt`、3 `.svg`、3 `.xml`、1 `.bin`、1 `.zip`、1 `.log`。
- **注意**：本目录内含 4 个 `.apk`，属 H5 素材包的一部分，**与 `06-android/reference/apk/`
  的 5 个业务样本不是同一批**，勿混为一谈。
- **用途**：H5 资源对照 / 溯源。
- **自身说明**：`04-landing/reference/README.md`。

### 2.5 `05-ios/reference/ios-sandbox-pocs/` —— iOS 沙箱 PoC

- **来源**：既有内容（非本批次搬入），只读参考。
- **内容**：7 文件 / 3 个 PoC 子目录：
  - `Geod-MCM-PoC/` —— `README.md`、`poc.m`
  - `InstallCoordination-PoC/` —— `README.md`、`poc.m`、`promise_graph.m`
  - `MobileHouseArrest-PoC/` —— `README.md`、`poc.m`
- **用途**：iOS 沙箱/服务机制的概念验证参考（Objective-C 源码级）。
- **与投递产物的关系**：**无**，纯参考素材。

---

## 三、★ 与投递产物的边界

**总原则：参考素材 ≠ 投递产物。禁止互相覆盖、混用、交叉引用。**

| 类别 | 路径 | 性质 | 是否参与构建/打包/投递/sha256 |
|---|---|---|---|
| IPA 参考包 | `05-ios/reference/ipa/` | **参照** | ✗ 否 |
| APK 参考包 | `06-android/reference/apk/` | **参照** | ✗ 否 |
| H5 源码 | `04-landing/reference/code/` | **参照** | ✗ 否 |
| H5 资源 | `04-landing/reference/all_assets/` | **参照** | ✗ 否 |
| iOS 沙箱 PoC | `05-ios/reference/ios-sandbox-pocs/` | **参照** | ✗ 否 |
| H5 模板产物 | `04-landing/templates/` | **投递** | ✓ 是 |
| H5 资源产物 | `04-landing/assets/` | **投递** | ✓ 是 |
| 运行时脚本 | `04-landing/runtime/landing-runtime.js` | **投递** | ✓ 是（F1-C5 已验收） |
| **Android 投递包** | `06-android/apk/` | **投递** | **目录当前不存在，见 3.1** |

### 3.1 ★★ APK 双用途说明（与 D2-C4 关联，重点）

存在**两个名字极为相似、但性质完全相反**的路径，后续操作**必须严格区分**：

| 路径 | 性质 | 当前状态 | 归属 |
|---|---|---|---|
| `06-android/reference/apk/` | **参照素材**（原始样本，只读） | ✅ **已存在**（5 个业务 APK + `_MANIFEST.txt`） | R5-C2 已归档 |
| `06-android/apk/` | **投递包**（deliverable） | ❌ **尚不存在**（实测 `Test-Path` = `False`） | 留给 **D2-C4** |

**明确结论与要求**：

1. `06-android/reference/apk/` 下的 5 个 APK **只作参照**，**不得**直接作为投递物对外投递。
2. `06-android/apk/`（投递包）**当前不存在**，将在 **D2-C4** 阶段产出。
   截至本索引生成时，`06-android/` 下仅有 `tools/`、`stage/`、`full/`、`reference/` 四个子目录。
3. **D2-C4 执行时禁止**把 `reference/apk/` 直接改名/移动/复制成 `apk/` 来充作投递包。
   投递包应按 D2-C4 自身的规范重新产出，并与参照素材**分列两目录**。
4. 两份 `_MANIFEST.txt` 的校验口径**互不通用**：投递包须有自己的清单，不得引用
   `reference/apk/_MANIFEST.txt` 充当投递校验依据。

### 3.2 其余边界细则

- `reference/` 下的任何文件**不参与**构建、打包、投递，**不进** `_manifest.sha256`。
- 需要调整投递产物时，**直接改投递目录**，**不得**从 `reference/` 反向同步或覆盖。
- 校验口径以各目录**自身**的清单/README 为准（`ipa/_MANIFEST.txt`、
  `reference/apk/_MANIFEST.txt`、`04-landing/reference/README.md`）。

---

## 四、处置规范

- **新增参考素材** ⇒ 须**同时更新本索引**与**对应目录的 manifest**
  （`ipa/`、`reference/apk/` 更新 `_MANIFEST.txt`；`04-landing/reference/` 更新其 `README.md`）。
- **移出参考素材** ⇒ 须**同时更新本索引**（并同步对应目录的 manifest）。
- **不得**修改素材本体内容（`.ipa`/`.apk`/H5 内容一律不动）。
- **不得**修改 `_manifest.sha256`（项目根投递哈希清单）。
- 更新本索引时，**文件数与体积须实测**，不得照抄历史数字；实测与既有清单不符时**以实测为准并注明**。

---

## 五、实测差异备忘

本次实测中，「素材本体」数量与体积**与 R5-C1/C2/C3 交付说明完全一致**，无实质差异。

唯一需要说明的口径差异：**递归统计会把各目录自带的清单文件一并计入**，
故出现「12 / 6」这类数字，比素材本体「11 / 5」各多 1。本索引统一以**剔除清单后的素材本体**为总览口径。

| 目录 | 素材本体 | 递归全部（含清单） | 差异来源 |
|---|---|---|---|
| `05-ios/reference/ipa/` | 11 文件 / 160,889,299 B | 12 文件 / 160,890,554 B | `_MANIFEST.txt` (+1,255 B) |
| `06-android/reference/apk/` | 5 文件 / 80,324,931 B | 6 文件 / 80,325,646 B | `_MANIFEST.txt` (+715 B) |
| `04-landing/reference/code/` | 113 文件 / 4,238,781 B | 同左 | — |
| `04-landing/reference/all_assets/` | 150 文件 / 96,432,618 B | 同左 | — |
| `05-ios/reference/ios-sandbox-pocs/` | 7 文件 / 36,969 B | 同左 | — |

---

## 六、约束声明（本索引写入时）

本次仅**新增** `E:\USDT项目\reference\README.md`（及承载它的 `reference\` 目录）。
**未修改**任何素材文件与前三张卡的产物，具体未触碰：

- `05-ios/reference/ipa/**`（含 `_MANIFEST.txt`）—— 未改
- `06-android/reference/apk/**`（含 `_MANIFEST.txt`）—— 未改
- `04-landing/reference/**`（含 `code/`、`all_assets/`、`README.md`）—— 未改
- `05-ios/reference/ios-sandbox-pocs/**`、`05-ios/reference/README.md` —— 未改
- `_manifest.sha256` —— 未改
