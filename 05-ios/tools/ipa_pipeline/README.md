# IPA 组装流水线（W-IOS-PKG · X-3 合并版）

参数化：**〈外壳 × dylib 代际〉**，不预设某一代；签名段可插拔。

> **X-3 合并**（Owner 授权，2026-10-03）：以本目录 `ipa_pipeline.py` 为骨架，
> 并入参照终端 B `05-ios/tools/ipa_assemble.py` 的两项能力 ——
> ① Mach-O `LC_LOAD_DYLIB` 注入；② `manifest.plist` 生成。
> 骨架原有四项**不变**：登记表强制 / 反向断言 / 符号链接保真（`external_attr`）/ 可复现。

## 用法

```bash
python ipa_pipeline.py seed                       # 刷新 registry.json
python ipa_pipeline.py verify --ipa <ipa>         # 校验产物
python selftest_ipa_pipeline.py                   # 自测：共 37 项（13 原有 + 24 新增）—— 以实跑 `grep -c '^PASS'` 为准

# 组装（默认 slot 模式；无签名产出名必须含 -unsigned）
python ipa_pipeline.py build \
  --base-shell 05-ios/reference/ipa/FilzaSlop-v1.0.3-unsigned.ipa \
  --dylib      05-ios/dist/inputs/FilzaApplySandboxExt-v1.0.3.dylib \
  --version    1.0.3 \
  --manifest-url https://<cdn>/ipa/FilzaSlop-1.0.3-unsigned.ipa \
  --icon57-url   https://<cdn>/ipa/i57.png \
  --icon512-url  https://<cdn>/ipa/i512.png --title FilzaSlop
```

## `inject_mode`（取值全集 —— 与 B 对齐，全仓只有这一套）

| 值 | 含义 | 主二进制 |
|---|---|---|
| `slot-replaced` | 基座已声明 `LC_LOAD_DYLIB → FilzaApplySandboxExt.dylib` ⇒ 只替换该槽位内容 | **零改动**（ncmds 不变） |
| `linkedit-appended` | 基座未声明槽位 ⇒ 在 load command 区零填充处**追加**一条 `LC_LOAD_DYLIB`（bootstrap） | 改动，**ncmds +1** |
| `landed-only` | 两种改写都不可行（fat / 无空洞），或显式 `--inject none` ⇒ **文件已落盘但不会被加载** | — |

`--inject {slot,append,auto,none}`，**默认 `auto`**（与 B 一致：有槽位⇒`slot-replaced`，无槽位⇒尝试 `linkedit-appended`）。
★ `slot`/`append` 为**强制模式**：与基座不匹配即拒绝（exit 8）。
★ `landed-only` **不等于已注入** ⇒ 默认**拒绝产出**（exit 12），须显式 `--allow-landed-only`。
★ **取值全集只有上表三个**（与 B 对齐）；`--inject none` 归入 `landed-only`，**不新增取值**。
★ **已知未覆盖面**：当前 9 个真实基座**全部**已声明槽位 ⇒ 默认 `auto` 下**无槽分支无法在真实基座触发**（仅由合成夹具覆盖，见自测 N2/N9）。
★ **已知功能边界（DS 代际）**：3 个 **DS 代际**基座（`FilzaEscaped_DS_1.2` / `FilzaJailed_2.1` / `FilzaJailed_DS_2.0`）
  bundle-id 白名单**已放行**（登记为其 `com.tigisoftware.Filza`），但它们的主二进制**含 `LC_CODE_SIGNATURE`（已签名）**
  ⇒ 被「**只接受未签名壳**」门禁拦下（**exit 9**）。**要组装 DS 代际需未签名壳或增设重签步骤**（未实现）。

## 硬约束（违反即拒绝）

| # | 规则 | 退出码 |
|---|---|---|
| 1 | 外壳 / dylib sha256 必须在 `registry.json` 登记（`--allow-unregistered` 可豁免并记入 manifest） | 3 / 4 |
| 2 | ★ **bundle-id 白名单**：`--bundle-id` 取值必须命中 `registry.json` 中**该基座声明的允许集合**（不接受命令行任意值）；集合为空 = 该基座登记为**不可组装** | 7 |
| 3 | 外壳必须未签名（无 `_CodeSignature/`、无 `LC_CODE_SIGNATURE`） | 9 |
| 4 | 模式与基座不匹配（`slot` 遇裸壳 / `append` 遇有槽位壳）⇒ 拒绝 | 8 |
| 5 | 无签名产出名必须含 `-unsigned` | 5 |
| 6 | 签名工具不可用 ⇒ **显式失败**，绝不静默跳过 | 10 / 11 |
| 7 | 注入不可行（`landed-only`）未显式接受 ⇒ 拒绝 | 12 |

## 保证

- **保真**：`create_system` / `external_attr` / `date_time` / 条目顺序逐条沿用 ⇒ 符号链接与权限位不丢。
- **可复现**：同输入两次构建 ⇒ 同 sha256（**含 Mach-O 注入后仍成立**）。
- **不落地解包**：全程 zip 内存直通（规避 Windows MAX_PATH 260）。
- **可追溯**：`<out>.ipa.manifest.json` 记 version / inject_mode / 两个输入件 sha256 / 产物 sha256 / OTA 入口。

## 外部依赖（未做）

- **签名**：需 macOS 或带 p12 的签名工具（`IPA_SIGN_TOOL`，默认 `zsign`）。
- **编译 dylib**：需 macOS + Theos（`05-ios/tools/FilzaSlop/Makefile:13` 的 `-I …/ChOma/include` 目录不存在，实现前须先修）。
- 本流水线**不产生 dylib**，只做「外壳 + 已有 dylib → IPA (+ manifest.plist)」的组装。
