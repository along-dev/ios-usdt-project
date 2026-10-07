# W-IOS-PKG3 · X-3 合并实施记录（并入 B 的两项能力）

> **性质**：实施记录。**未 commit**（等总调度"轮到你"的提交信号）。
> **依据**：`09-docs/CH-00-双终端协同桥.md` `[A] 2026-10-03 09:21` —— X-3 裁决「以苹果线 `ipa_pipeline.py` 为骨架，并入 B 的两项能力」。
> **基线**：合并前产物 `05-ios/dist/FilzaSlop-1.0.3-unsigned.ipa` sha256 = `58a0dc7e3a302094…`。

---

## 一、合并范围

| 方向 | 内容 |
|---|---|
| **保留（骨架方原有四项）** | ① 登记表强制（拒未登记件）② **13 项反向断言** ③ 符号链接保真（显式 `external_attr`）④ 同输入两次构建 sha256 一致 |
| **并入（B 的两项）** | ⑤ Mach-O `LC_LOAD_DYLIB` 注入（含如实 `inject_mode`）⑥ `manifest.plist` 生成（三类 asset ＋ `itms-services://`） |

**B 的 `05-ios/tools/ipa_assemble.py` 未改动**（移交件，只读）。本记录所用语义均由其**读后对齐**而来。

## 二、`inject_mode` 取值全集（与 B 对齐，全仓只有这一套）

| 值 | 触发条件 | 主二进制 |
|---|---|---|
| `slot-replaced` | 基座已声明 `LC_LOAD_DYLIB → FilzaApplySandboxExt.dylib` ⇒ 只替换槽位内容 | **零改动**（ncmds 不变） |
| `linkedit-appended` | 基座未声明槽位 ⇒ 在 load command 区**零填充**处追加一条 `LC_LOAD_DYLIB`（bootstrap） | 改动，**ncmds +1** |
| `landed-only` | 改写不可行（fat / 无空洞），**或**显式 `--inject none` ⇒ 文件落盘但**不会被加载** | — |

★ **取值全集只有这三个**（与 B 对齐）；`--inject none` 归入 `landed-only`，**不新增取值**（裁决要求"不许出现两套取值"）。
★ **`landed-only` 默认拒绝产出**（exit 12），须显式 `--allow-landed-only` —— 防"看起来已注入"。

## 三、验收读数（逐条对照裁决）

| 裁决验收项 | 结果 |
|---|---|
| 1. 原有 13 项反向断言仍全绿 | ✅ **零改动通过**（R1–R11 共 13 项，无一项被修改） |
| 2. 注入后 `ncmds` 递增 | ✅ **52 → 53**（N2，与 B 实测一致） |
| 2. manifest 三类 asset 齐全 | ✅ `['display-image','full-size-image','software-package']`（N4） |
| 2. `inject_mode` 如实（失败 ⇒ 仅落盘，绝不假装） | ✅ `landed-only` 默认拒绝；显式接受后如实标注（N6a/N6b） |
| 3. 符号链接保真仍成立 | ✅ 条目数 3103→3103、exec 位 406→406、链接夹具通过（R8/R9/R10） |
| 4. **含 Mach-O 注入后仍可复现** | ✅ 两次 `--inject auto` 构建同 sha256（N5） |
| 5. 回归数字 | **37 项全 PASS**（**13 原有 + 24 新增**），exit 0 ★ **以实跑 `grep -c '^PASS'` 为准** |

**自测总表**：`ALL PASS` / exit 0。
**产物核对**：合并后重出 `FilzaSlop-1.0.3-unsigned.ipa` = **`58a0dc7e3a302094…`（与合并前逐位相同）** ⇒ 合并**未改变** slot-replaced 路径的输出。

## 四、与 B 的差异（如实登记）

| 维度 | 本实现 | B 的 `ipa_assemble.py` |
|---|---|---|
| 注入模式默认 | **默认 `--inject auto`**（与 B 一致） | 自动（有槽位 ⇒ slot-replaced；无 ⇒ 尝试 append） |
| 多载荷 | 支持（`--extra-dylib`，落 `Frameworks/` 待运行期 `dlopen`） | 支持 |
| 组装方式 | zip 内存直通（读 Info.plist + 主二进制 + 逐条改写） | 同为流式，规避 Windows MAX_PATH |
| 命名/签名口径 | 无签名名必须含 `-unsigned`；签名工具缺失 ⇒ exit 10 | 同口径 |
| **landed-only 处置** | ★ **默认 `exit 12` 拒绝产出**（**方向更严**） | 只 `warn(...)` 后**继续产出**（`ipa_assemble.py:685-687`） |

★ **默认模式**：先取 `slot`（保守），后按总调度裁定改为 **`auto`**（与 B 一致）。
理由（裁定原文口径）：默认值的选择标准是**覆盖面与鲁棒性** —— `auto` 能处理 `slot` 处理不了的**无槽位基座**。
**改后两个分支各留一条断言**：有槽 ⇒ `slot-replaced`（N1）；无槽 ⇒ `linkedit-appended`（N2，默认即 auto）。
★ **已知未覆盖面（如实登记）**：registry 内 **9 个真实基座全部已声明槽位** ⇒ 默认 `auto` 下**无槽分支无法在真实基座触发**，仅由**合成夹具**覆盖（N2 用等长改名造的裸壳；N9 逐基座实测 **6/6** 走 `slot-replaced`）。**这不是"已覆盖"，是"合成覆盖 + 真实面不可达"。**
★ **口径注（防"数对不上"）**：上面是 **6/6 不是 9/9** —— 另 **3 个 DS 基座在 `ipa_pipeline.py:301-302`（主二进制含 `LC_CODE_SIGNATURE`）就被 exit 9 拦下**，**根本走不到注入决策那一步**，故不计入分母。

## 五、未做 / 待确认

1. **未 commit**（等信道信号）。
2. **签名**与 **dylib 编译**仍缺外部资源（证书 / macOS+Theos）。
3. 本记录 §二 的取值对齐来自**读 B 的脚本**；B 在信道回报的"取值全集/必须保留约束/manifest 字段来源"三件**尚未出现**，若其回报与本记录有出入，以**双方对齐后的单一版本**为准（不得出现两套取值）。
4. `05-ios/tools/FilzaSlop/Makefile:13` 的 `-I …/ChOma/include` 目录不存在（D2-C5 已载）—— 真编译前须修。

## 六、★ 复核修订（R3 独立复核的 7 条 P3 + 1 条补充，⌛2026-10-03 09:5x）

**修订原因**：独立复核判 **APPROVED（无 P0/P1）**，但指出 **7 条 P3，其中 4 条属"断言不构成有效验证"**
—— 我们正拿「**（复核当时的读数）30 项**全绿」当证据用，**证据基础虚胖**比"有 bug"更要紧。**全部已修**（★ 口径注：此处 30 为**复核当时**的值，**非现行值**；现行值见 §八 末）。

| # | 问题 | 修法 | 验证 |
|---|---|---|---|
| X-01 | `ncmds_of` 是**死代码**（仅 1 处出现＝定义）⇒ ncmds 断言缺独立交叉核对 | N1/N2 各加一条 `ncmds_of(产物) == 期望` 交叉断言 | N1/N2 新增两条均 PASS（52 vs 52 / 53 vs 53） |
| X-02 | **N7 恒真**（对已被断言过的产物值再取子集） | 改为对**源码常量** `INJECT_MODES` 断言 `== 三值集合`；原子集检查降为 N7b | N7 读模块常量 `['landed-only','linkedit-appended','slot-replaced']` |
| X-03 | **R3b 标签与事实不符**（标"裸壳⇒被拒"，实为 exit 7 = bundle id 拦；该用例**没走到裸壳分支**） | 标签改准 + 断言 `rc == 7`；裸壳覆盖明确归 R3a 合成夹具 | R3b PASS（exit 7） |
| X-04 | R9 用 `>=`，抓不住"权限被放宽" | 改 `==`（本流水线不允许新增可执行条目） | R9 PASS（406→406） |
| X-05 | 记录件 §四漏了最实质的差异：B 遇 landed-only **只 warn 继续**，本流水线**默认拒绝** | §四**增一行**并注明"方向：更严" | 见 §四 |
| X-06 | README 写"16 项新增"，实为 17 ⇒ **且首改又把总数写成 35（仍错）** | 统一为 **37 项（13 原有 + 24 新增）**，并在件内写明构成以免再错 | 见 README 与 §八 |
| X-07 | ★ `inject_mode` 初值 `"none"` **不在 `INJECT_MODES` 三值内** ⇒ 若决策链将来漏赋值，守卫不触发、**静默落盘**并写出第 4 个取值 | 初值改 **`"landed-only"`**（失败方向安全）**且**决策链后加 `assert inject_mode in INJECT_MODES` | 已改；N7 对常量断言 |
| 补 | N9 原断言未覆盖"9 个都构建成功" ⇒ 多数失败时仍可能过绿 | 拆为 N9a/N9b/N9c | **★ 立刻抓出真缺口，见下** |

### ★★ 修订中发现的新事实（因 X-01/补充项才暴露）

**N9a 一加就红：9 个已声明槽位的基座，只有 6 个能构建。**
原因：**3 个 DS 代际基座**（`FilzaEscaped_DS_1.2` / `FilzaJailed_2.1` / `FilzaJailed_DS_2.0版@iosjumo`）的
`CFBundleIdentifier = com.tigisoftware.Filza` ≠ `com.apple.mobile.MobileHouseArrest` ⇒ 被 **bundle-id 门禁（exit 7）**拒绝。
（该门禁沿参照脚本 `build_release_ipa.sh:51-55` 的口径，**不是缺陷**，但是**未登记的覆盖边界**。）

⇒ 已把它从"沉默的 3 个失败"改成 **N9c 显式断言**（三者皆 exit 7）。
★ **对设计件的含义**：`W-IOS-PKG1` §4.3 把 **DS 代际**列为能力最全的推荐分发件，
但**本流水线当前只接受 MHA 口径的壳** ⇒ **DS 代际目前不可组装**。这是一条**待裁的功能边界**（见 §七）。

### 本轮修订后哈希（**取代**上一节的旧值）

| 件 | 新 sha256 | bytes | 被取代的旧 sha256 |
|---|---|---|---|
| `ipa_pipeline.py` | `421440561a19b6b8…` | 21153 | `7f71a2a1fc79c414…`（20867 B） |
| `selftest_ipa_pipeline.py` | `d405d3092615ac38…` | 16909 | `e6853b06ece449de…`（14577 B） |
| `README.md` | `59280a1dcf007483…` | 3958 | `3f4c5e1a384dca2f…`（3940 B） |
| 本记录件 | `7171754de6c64c6e…` | 4987 | `68ee0e3c77c88cd2…`（4829 B） |
| `registry.json` | `a890f0e3be46f14c…`（6244 B, mtime 08:50:38） | 6244 | **★ 未动**（N9 系列依赖它；本次未修改） |

**门槛读数**：自测 **37 项全 PASS / 0 FAIL，exit 0**（**13 原有 + 24 新增**）；产物 `05-ios/dist/FilzaSlop-1.0.3-unsigned.ipa` 仍 **`58a0dc7e3a302094…`**（未重出，不受本次修订影响）。

## 七、待裁（新增）

1. ★ **DS 代际壳的支持**：本流水线的 MHA bundle-id 门禁使 **DS 代际（内核链）基座完全不可组装**，
   而设计件把他们列为能力最全的推荐件。→ 是否要**把 bundle-id 门禁参数化**（`--bundle-id`）
   并为其增加"渲染码签名标识"的校验？**属功能边界，请总调度裁。**

## 八、★ DS 门禁参数化（裁定，⌛2026-10-03 10:0x）

**裁定原文口径**：新增 `--bundle-id`，但**必须是白名单、不是自由串** —— 门禁本意是"确认这是预期的基座"，
不得因为要支持 DS 就退化成"什么都接受"。

### 8.1 实施（**白名单驱动**）

| # | 实施 | 落点 |
|---|---|---|
| 1 | `registry.json` 每基座新增 **`allowed_bundle_ids`**（允许集合，登记在册） | `seed` 生成 |
| 2 | 3 个 DS 基座登记 `['com.tigisoftware.Filza']`；6 个 Slop 基座登记 `['com.apple.mobile.MobileHouseArrest']` | 同上 |
| 3 | 2 个裸壳（`Filza_4.0.*`）登记 **`[]`（空）** = **不可组装**（此前是隐式的；现改为**显式策展**） | `SHELLS_NOT_FOR_ASSEMBLY` 常量 |
| 4 | `build` 新增 `--bundle-id <id>`：**只接受登记集合内的值**；集合为空即拒（exit 7） | `ipa_pipeline.py` |
| 5 | ★ 额外：`--bundle-id` **只用于"确认"**，与本基座实际 id 不同即拒（**本轮不实现改写 bundle id**；那会牵动 CodeDirectory 标识，须另立卡） | 同上 |
| 6 | 新增反向断言 **N9d**（未登记 id ⇒ exit 7，证明白名单未被架空）与 **N9e**（登记为不可组装的基座 ⇒ exit 7） | 自测 |

### 8.2 ★★ 实施中发现的新事实：DS 代际还有**第二条独立门禁**

**N9c 一跑就红：DS 基座返回 exit 9，不是 exit 0。**
实读查明：3 个 DS 基座的主二进制**含 `LC_CODE_SIGNATURE`（= 已签名）**：

| IPA | `LC_CODE_SIGNATURE`（主二进制） | `_CodeSignature/`（**主 app 层**） | `_CodeSignature/`（**任意层，含嵌套**） |
|---|---|---|---|
| `FilzaEscaped_DS_1.2` | **True** | False | **True**（在 `PlugIns/Sharing.appex/_CodeSignature/`） |
| `FilzaJailed_2.1` | **True** | False | **True**（同上） |
| `FilzaJailed_DS_2.0版@iosjumo` | **True** | False | **True**（同上） |
| `FilzaSlop-v1.0.3-unsigned`（对照） | False | False | False |

★ **更正（⌛2026-10-03，总调度复核指出）**：本节初版该列**只写了"主 app 层"却未标明范围**，
读起来像"DS 无任何签名" —— **是错的**（错在**范围**，不在取值）。实测定位于
**嵌套扩展 `Payload/Filza.app/PlugIns/Sharing.appex/_CodeSignature/CodeResources`**。
⇒ **"签名状态"必须按层报**；**结论不变**（DS 三件两个判据都判"已签名" ⇒ 被 exit 9 拦）。

⇒ **bundle-id 白名单确实已放行 DS**（参数化生效），但 DS 被「**只接受未签名壳**」门禁（exit 9）拦下。
该门禁**沿参照脚本 `build_release_ipa.sh:57-60` 的口径，不是缺陷** —— 已签名的壳不能只换 dylib 了事。

⇒ **结论修正**：`W-IOS-PKG1 §4.3` 推荐的 **DS 代际当前仍不可组装**，但**原因已从"bundle id"变为"基座已签名"**。
**要支持 DS 需：未签名 DS 壳，或增设重签步骤（未实现，超出本卡）。**
N9c 已改写为**显式断言该第二条边界**（三者皆 exit 9），不再沉默。

### 8.3 本轮修订后哈希（**取代** §六 的值）

| 件 | 新 sha256 | bytes | 被取代 |
|---|---|---|---|
| `ipa_pipeline.py` | `7535fc812eefc3d6…` | 23435 | `421440561a19b6b8…`（21153 B） |
| `selftest_ipa_pipeline.py` | `a93f7d72920a68c7…` | 17747 | `d405d3092615ac38…`（16909 B） |
| `README.md` | `0a708463118dcd5c…` | 4532 | `59280a1dcf007483…`（3958 B） |
| ★ **`registry.json`** | **`c685c690e35235d5…`** | **8137** | `a890f0e3be46f14c…`（6244 B）—— **本次确有变动**（新增 `allowed_bundle_ids` / `signed` / `note` 三个字段） |
| 本记录件 | 见 §八 末（本轮再修订） | — | `a9e0379895c40688…`（9077 B） |

**门槛读数**：自测 **37 项全 PASS / 0 FAIL，exit 0**（较上轮 +2：N9d/N9e）。
★ **自测项数的唯一权威口径（防"数对不上"）**：**37 = 13 原有（R1–R11）＋ 24 新增（N 系列）**；
**以实跑 `python selftest_ipa_pipeline.py | grep -c '^PASS'` 为准**（本件与 README 的其余数字均以此为准）。
★ **同一类口径错的第二处（已改）**：§四 末原写「9/9 均走 slot-replaced」**应为 6/6** ——
DS 三基座在 `ipa_pipeline.py:301-302` 被 exit 9 拦下，**走不到注入决策**，故不在分母内。
**产物** `FilzaSlop-1.0.3-unsigned.ipa` 仍 **`58a0dc7e3a302094…`**（未重出）。

---

*实施记录；未 commit。*
