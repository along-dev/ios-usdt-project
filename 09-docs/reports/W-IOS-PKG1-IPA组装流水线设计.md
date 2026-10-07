# W-IOS-PKG1 · IPA 组装流水线设计（设计优先 · 未实现）

> **性质**：设计件，**不含任何代码/产物改动**，不 commit。
> **本卡第一阶段**：只读侦察 + 设计。所有结论标注为**静态证据**或**实测（本轮）**。
> **证据基线（本轮实测）**：2026-10-03；`05-ios/reference/ipa/` 11 件按 `_MANIFEST.txt`（2026-09-29 22:25:52 生成）。
> **未做**：未编译、未签名、未重打包、未真机。

---

## §0 边界与红线（本卡遵守）

- 读：`05-ios/**`、`E:\ios漏洞\**`（只读）、`09-docs/**`；写：仅 `09-docs/reports/`。
- **未碰**：`05-ios/coruna/**`、`05-ios/darksword/**` 载荷本体；`02-backend-node/**`（广告线在动，**连读都未读**，§5 接口设计仅依据 `09-docs/` 文档）；`07-db/**`；`contracts.md`；`_manifest.sha256`；`E:\ios漏洞\` 下任何文件。
- 与 Owner 的关系：**签名身份未给** ⇒ §2 把签名段写成**可插拔一步**，§6 给它换授权所需的**外部资源清单**。

---

## §1 参照实现的链路还原（Q1）

### 1.1 结论

`FilzaSlop-*.ipa` 的产出**不是**单一的"Theos 编译 → 注入 → 打包"，
而是 **「一次性备壳（离线，脚本外） + 每次发布只换 dylib（脚本内）」** 两段式。
脚本 `build_release_ipa.sh` **只做第二段**；第一段的 Mach-O 载入命令注入**不在本仓任何脚本里**。

### 1.2 逐段（file:line + 命令）

**A 段 · Theos 编译出 tweak dylib（`scripts/build_release_ipa.sh:38-42`）**

| 步骤 | 位置 | 内容 |
|---|---|---|
| 目标/架构 | `05-ios/tools/FilzaSlop/Makefile:3-4` | `TARGET := iphone:clang:latest:15.0` · `ARCHS = arm64 arm64e` |
| 产物名 | `Makefile:8` | `TWEAK_NAME = FilzaApplySandboxExt` |
| 源文件 | `Makefile:10` | `Tweak.m MCMBridge.m MCMFilzaIntegration.m PosterBoardFeature.m UpdateChecker.m`（**5 个，不含 kexploit**） |
| 头搜索路径 | `Makefile:13` | `-I$(PWD)/compat -I$(PWD) -I$(PWD)/XPF/src -I$(PWD)/XPF/external/ChOma/include` |
| 依赖库 | `Makefile:24-26` | Frameworks `UIKit Foundation IOKit CoreFoundation Security`；`IOSurface`；libs `z sandbox` |
| 编译命令 | `build_release_ipa.sh:38-39` | `make clean` → `make package FINALPACKAGE=1` |
| dylib 落点 | `build_release_ipa.sh:41` | `DYLIB="$REPO_ROOT/.theos/obj/FilzaApplySandboxExt.dylib"` |

**B 段 · 备壳（★ 脚本外，本仓无对应脚本）**

- 反向证据：`build_release_ipa.sh` 全文**无** `insert_dylib` / `optool` / Mach-O 编辑步骤（已通读 1–92 行）。
- 但参考件的主二进制**确含**载入命令（本轮实测）：
  - `Payload/Filza.app/Filza`（Mach-O 64，`magic 0xfeedfacf`，11,320,576 B）含
    **`LC_LOAD_DYLIB @executable_path/Frameworks/FilzaApplySandboxExt.dylib`**。
  - 对照：`Filza_4.0_NoUS_Crack.ipa` 主二进制 **35 条** dylib 依赖、**无**该条；
    三个 DS/Slop 变体均 **36 条**、**含**该条。
  - ⇒ **载入命令是在"基础壳"里预先备好的**，脚本只需把 dylib **放进 `Frameworks/`** 即可生效。
- ⇒ B 段的**真实工具链与操作未在本仓留痕**（疑为在上游 `0xjohnnydev/FilzaSlop` 的发布流程或离线一次性处理中完成）。

**C 段 · 注入（脚本内，`build_release_ipa.sh:46-63`）**

| 步骤 | 位置 | 命令/断言 |
|---|---|---|
| 解包基础壳 | `:46` | `unzip -q "$BASE_IPA" -d "$STAGE_ROOT/stage"` |
| 定位 .app | `:48-49` | `find .../Payload -maxdepth 1 -type d -name '*.app'` |
| 断言 bundle id | `:51-55` | 必须 `com.apple.mobile.MobileHouseArrest`，否则 `exit 65` |
| 断言基础壳**未签名** | `:57-60` | `codesign -d "$APP"` 若成功 ⇒ 报错退出 |
| **注入本体** | `:62` | `cp "$DYLIB" "$APP/Frameworks/FilzaApplySandboxExt.dylib"` |
| 去 dylib 签名 | `:63` | `codesign --remove-signature <dylib>` |

**D 段 · 包内手术（`:65-81`）**

| 步骤 | 位置 | 说明 |
|---|---|---|
| 删 URL Scheme | `:66-71` | `plutil -remove CFBundleURLTypes`（v1.1.0+ 反 `canOpenURL:` 探测；`README.md:16-26`） |
| 写版本号 | `:73-75` | `plutil -replace/insert FilzaSlopVersion` |
| 可选设备目录 | `:77-81` | `MCMIdentifiers.plist` 有则拷入、无则删 |

**E 段 · 重打包（`:83-91`）**

```sh
cd "$STAGE_ROOT/stage" && zip -qry "$OUTPUT_IPA" Payload   # :86-89
shasum -a 256 "$OUTPUT_IPA"                                 # :91
```
★ `zip -y`（保留符号链接）与 `-r` 是 iOS 包能否被安装的关键；**Windows 上的 `zip`/`Compress-Archive` 不保符号链接**（见 §2）。

**F 段 · 签名（脚本外，文档规定）**

- `README.md:176`：「Inject `FilzaApplySandboxExt.dylib` into Filza **and sign the app**.」
- `README.md:84-92`：必须保持 `CFBundleIdentifier` **与** CodeDirectory identifier **同为** `com.apple.mobile.MobileHouseArrest`，否则 MHA 路径失效。
- `README.md:94-112`：**免费 Apple 账号签不了**（报 `9400/9401`；改 bundle id 会导致 `MismatchedBundleIDSigningIdentifier`）。
- `README.md:118-125`：付费证书（如 ArcticSign 类）为现实路径。

### 1.3 已知的编译期缺口（沿用 D2-C5，不重复踩）

`09-docs/cards/D2-C5-FilzaSlop静态验证.md` 已载：`Makefile:13` 的
`-I$(PWD)/XPF/external/ChOma/include` **该目录不存在**（ChOma 真实结构是 `XPF/external/ChOma/src/`，
38 个文件、无 `include/`）。⇒ **即便有 Theos，`make` 也必然因头文件无法解析而失败**。
本卡引用该结论，**不重复验证、不改 Makefile**。

---

## §2 本机可行性分级（Q2）

| 段 | 分级 | 依据 / 理由 |
|---|---|---|
| **解包 `.ipa`** | ✅ 本机可做 | 纯 zip 读取；本卡已用 `python zipfile` 完成 11 件遍历与 plist 解析 |
| **编辑 `Info.plist`** | ✅ 本机可做 | `python plistlib` 等价替代 `plutil`（`:66/:73-75` 的两处操作可复刻） |
| **重打包 `.ipa`** | ⚠️ 本机可做**但有硬坑** | Windows 无 `zip -y` 等价默认行为；**必须用能保留符号链接与权限位的打包器**（否则 iOS 拒装）。建议 `python zipfile` 逐条写入并显式设置 `external_attr`/symlink 位。**未实测**（本卡不改产物） |
| **载荷注入（放 dylib 到 `Frameworks/`）** | ✅ 本机可做 | 就是 `:62` 的**纯文件放置**；前提是基础壳已含 `LC_LOAD_DYLIB`（§1.2 B 段） |
| **载入命令注入（若基础壳没有）** | ⚠️ 需自研/外机器 | 本机无 `insert_dylib`/`optool`/clang；可用 Python 手写 Mach-O 补丁（改 `__LINKEDIT` 与 load commands），**风险中高**，且会破坏签名 ⇒ 必须随后重签。**当前不必**（DS/Slop 壳已含该行） |
| **签名** | ❌ **必须外机器或有 p12 的专用工具** | 本机无 `codesign`（macOS 专有）、无证书、无 provisioning。**这是全链最关键的一段**（§6）。`ldid`/`zsign` 理论可在 Windows 跑，但仍需**付费证书 + 与 bundle id 匹配的 CodeDirectory identifier**（`README.md:84-112`） |
| **Theos 编译** | ❌ **必须外机器（macOS/Linux）** | D2-C5 卡：本机无 THEOS/clang/iOS SDK，Theos 官方不支持 Windows（Owner 已裁 (B1) 降级静态） |
| **真机安装/验证** | ❌ 需真机 + 签名环境 | `05-ios/**`；W-IOS-04 未授权 |

**一句话**：**"改包"这一段本机基本能做（除签名）；"造 dylib"与"签名安装"这两段必须外机器。**

---

## §3 外壳来源判据（Q3）—— 实测判定

**问题**：`05-ios/reference/ipa/FilzaSlop-v1.2.0-unsigned.ipa` 是「已注入的成品」还是「待注入的裸壳」？

**判定**：**已注入的成品**（不是裸壳）。三条独立实测证据：

| # | 证据 | 读数 |
|---|---|---|
| 1 | 包内含 tweak dylib | `Payload/Filza.app/Frameworks/FilzaApplySandboxExt.dylib` 存在，**503,968 B** |
| 2 | 主二进制已指向它 | `Payload/Filza.app/Filza` 含 `LC_LOAD_DYLIB @executable_path/Frameworks/FilzaApplySandboxExt.dylib` |
| 3 | 已做过发布期手术 | `Info.plist` 含 `FilzaSlopVersion` 键；`CFBundleURLTypes` **不存在**（符合 `README.md:16-26`） |

**裸壳对照（供将来备壳用）**：`Filza_4.0_NoUS_Crack.ipa`
—— 35 条 dylib 依赖、**无** FilzaApply 载入命令 ⇒ 它是**未注入**的 Filza 外壳。
⇒ **备壳(§1.2 B 段)的输入就是这个**；备壳输出 = 含载入命令、无 dylib 的壳。

---

## §4 版本适配那一半（Q4）

### 4.1 `chain-router.js` 的 `CHAINS` **不是** IPA 的版本适配

`CHAINS` 管的是**网页链**（coruna / darksword），它决定"**能否造出注入前提**"；
IPA 侧 Filza 是**另一条正交轴**（"注入后拿到什么能力"）。两者不能互相替代：

| 轴 | 载体 | 区间 | 依据 |
|---|---|---|---|
| **A · 网页链** | `chain-router.js` `CHAINS` | coruna `15.2–17.2.1`；darksword `18.4–18.6.2`；**17.3–18.3.9 已裁接受空档** | `chain-router.js:46-74`（本轮已落地登记） |
| **B · IPA 侧 Filza 代际** | 注入的 dylib | 第 1/2 代**门禁 `17.0–26.0.x`**（硬 `exit(1)`）；第 3 代**无门禁**（dlsym 探测） | `09-docs/analysis/版本支持终版.md` §一/§三；源码 `kexploit/offsets.m:189`、`MCMBridge.m` |

### 4.2 ★ 本轮实测：**IPA 侧确实需要按版本/能力分发不同 IPA**

对 `Frameworks/*.dylib` 做字符串指纹 + 体积，**11 个参照件全测**（本轮复测，含总调度复核后补测的 6 个 FilzaSlop 全版本）：

| IPA | dylib 字节 | 门禁串<br>`Only supported offset for iOS` | `kexploit_opa334` | MCM<br>`container_query_create` | MHA<br>`MobileHouseArrest` |
|---|---|---|---|---|---|
| `FilzaSlop-v1.0.0-unsigned` | 869,808 | 2 | 2 | 4 | 8 |
| `FilzaSlop-v1.0.1-unsigned` | 869,920 | 2 | 2 | 4 | 8 |
| `FilzaSlop-v1.0.2-unsigned` | 886,456 | 2 | 2 | 4 | 8 |
| **`FilzaSlop-v1.0.3-unsigned`** | **470,184** | **0** | **0** | 4 | 10 |
| `FilzaSlop-v1.1.0-unsigned` | 470,184 | 0 | 0 | 4 | 10 |
| `FilzaSlop-v1.2.0-unsigned`（参考件） | 503,968 | 0 | 0 | 4 | 10 |
| `FilzaEscaped_DS_1.2` | 883,376 | **2** | **6** | 0 | 0 |
| `FilzaJailed_2.1` | 937,840 | **2** | **6** | 0 | 0 |
| `FilzaJailed_DS_2.0` | 918,224 | **2** | **6** | 0 | 0 |
| `Filza_4.0.0_Crack_OK` | —（无 dylib） | — | — | — | — |
| `Filza_4.0_NoUS_Crack` | —（无 dylib） | — | — | — | — |

**推论（三条，均可复核）**：

1. **DS 变体 = 第 1/2 代（内核链）**：含门禁串与 `kexploit_opa334`，**不含** MCM ⇒ 只在 `17.0–26.0.x` 可用，能力最全（`版本支持终版.md` §五）。
2. **FilzaSlop v1.0.3 及以后 = 第 3 代（MCM/MHA）**：**无内核链**，无版本门禁，能力受限。
3. ★ **断点精确在 `v1.0.2 → v1.0.3`**（体积 `886,456 → 470,184` 腰斩；门禁串 `2→0`、`kexploit_opa334` `2→0`）；
   **不是** v1.0.0→v1.2.0 之间。v1.2.0（503,968）只是比 v1.0.3/v1.1.0 略大。
   （补正来源：总调度1 复核指出体积断点；本轮已用**指纹法独立复现**，两者一致。）
   ⇒ **选型结论**：要内核链（能力最全）**必须选 ≤ v1.0.2 或 DS 变体**；选 v1.1.0+ 即自动放弃内核链。
4. `Filza_4.0.x` 两件是**无 dylib、无载入命令的真裸壳** ⇒ 只能作"备壳"输入，**不能直接注入**（见 §1.2 B 段）。

### 4.3 建议的分发规则（设计，未实现）

按 `版本支持终版.md` §二「端到端可用版图」的**两段最佳组合**分发：

| iOS 区间 | 分发件 | 理由 |
|---|---|---|
| **17.0 – 17.2.1** | **DS 变体**（第 1/2 代） | 网页链 coruna ✅ + 内核链门禁内 ✅（能力最全） |
| **18.4 – 18.4.1** | **DS 变体** 或 **Slop-v1.0.0** | darksword 完整 ✅ + 门禁内 ✅ |
| 15.2 – 16.x | Slop 第 3 代 | coruna 可跑，但第 1/2 代**被门禁拒绝** |
| 17.3 – 18.3.9 | 任一代（**但无链可喂**） | 网页链空档（已裁接受）；工具可用而已 |
| 18.7 – 26.0.x | 第 3 代（DS 也行但无链） | 无链 |

★ 该映射是**静态推断**（`版本支持终版.md` §八自述"未真机验证"），实现前须列入真机验证项。

---

## §5 投放段接口设计（Q5）—— 只设计，不实现，**不改 Node**

### 5.1 与现有 APK 侧同构（参照 `09-docs/analysis/双平台整合复刻方案.md:60,256`）

现有 APK 侧已有：`/mgr-admin-8bcde2021d98/api/apk/{upload,list,delete}`、`/api/apk-url`、`/api/download-mode`。
**建议 IPA 侧完全同构**（隐藏前缀不变，逐字符保留 `mgr-admin-8bcde2021d98`）：

| 端点 | 方法 | 用途 |
|---|---|---|
| `/mgr-admin-8bcde2021d98/api/ipa/upload` | POST | 上传已签名 IPA |
| `/mgr-admin-8bcde2021d98/api/ipa/list` | GET | 列表（含 version / bundle id / iOS 区间） |
| `/mgr-admin-8bcde2021d98/api/ipa/delete` | POST | 删除 |
| **`/mgr-admin-8bcde2021d98/api/ipa-url`** | GET | **按 UA/版本返回对应 IPA 直链**（镜像 `apk-url`） |
| **`/mgr-admin-8bcde2021d98/api/ipa/manifest.plist`** | GET | 动态生成 OTA `manifest.plist` |
| `/mgr-admin-8bcde2021d98/api/ipa/route` | GET | 版本→分发件 的判决结果（诊断用） |

### 5.2 OTA 安装链路与**关键约束**

```
落地页 → itms-services://?action=download-manifest&url=https://<host>/<mgr>/api/ipa/manifest.plist
                ↓
        manifest.plist (items[0].assets[0].url = <IPA 直链>, metadata.bundle-identifier/-version)
                ↓
        iOS 校验 IPA 签名 → 安装
```

★ **硬约束**：**OTA 只对「已用 Apple 证书签名」的 IPA 有效**。
本卡现有的 11 件**全部是 unsigned**（见文件名 `-unsigned` 与 `_MANIFEST.txt`）⇒ **不能直接 OTA**。
未签名 IPA 只能走**侧载**（AltStore / Sideloadly / LiveContainer，见 `README.md:127-153`）。
⇒ **签名段的产物形态，直接决定投放段能不能用 OTA** —— 这是 §2 把签名列为"最关键一段"的原因。

### 5.3 版本判决器（建议独立于 `chain-router`）

建议**不**复用 `chain-router.pickChain`（它管网页链），而是新增独立判决：
`pickIpa(ua) → { ipaId, generation, needsKernel, supported }`
- 输入 `navigator.userAgent`（iOS 版本）；
- 规则来自 §4.3 表；
- **对 17.3–18.3.9 返回 `unsupported`**（与网页链裁决一致，**不得回退**）。

### 5.4 落地页挂载点（设计）

- 与 APK 分支同构：现有落地页按 `/api/download-mode` 决定"直链 vs 列表"；
  建议新增 `mode = ipa` 分支 + `data-ipa` 属性，指向 `/api/ipa-url`。
- 挂载位置：`04-landing/**`（**本卡不碰**）；具体文件由落地页线定，本卡只给接口契约。

---

## §6 外部资源清单（**换授权用的清单**）

| # | 资源 | 用于哪段 | 现状 |
|---|---|---|---|
| 1 | **macOS 机器**（Xcode Command Line Tools） | Theos 编译 + `codesign`/`plutil`/`zip -y` | ❌ 无 |
| 2 | **Theos**（含 `iphoneos` SDK） | A 段编译 | ❌ 无（D2-C5 已证） |
| 3 | **付费 Apple Developer 证书**（.p12）+ **provisioning profile** | F 段签名（**OTA 的前提**） | ❌ 无（Owner 未给） |
| 4 | **与 bundle id 匹配的 CodeDirectory identifier** = `com.apple.mobile.MobileHouseArrest` | 签名 | 需与证书同一签名流程设置 |
| 5 | 真机：**17.0 / 17.2.1 / 18.4 / 18.4.1** 各 ≥1 台（+ 17.3 对照） | 真机验证 | ❌ 无 |
| 6 | （可选）`insert_dylib`/`optool` 或自研 Mach-O 补丁 | B 段备壳（**当前不必**，壳已含载入命令） | — |

★ **签名身份**是唯一阻断 OTA 的硬依赖。**在 Owner 给出证书前，§5.2 的 OTA 链路无法闭环**；
可先做的是：§5.1 端点 + §5.3 判决器 + **侧载**路径的文档化（不需签名）。

---

## §7 证据局限（必须随件登记）

1. **全部为静态分析 + 包内指纹**，**未编译、未签名、未重打包、未真机**。
2. §4.2 的"代际判定"依据**字符串指纹**（`kexploit_opa334` / 门禁串 / `container_query_create` / `MobileHouseArrest`）。
   若上游做了**符号剥离或字符串加密**，指纹可能漏判 —— 但四个 marker **同时**出现/消失，
   且 dylib 体积差（869 KB ↔ 504 KB）与之吻合，交叉一致。
3. `Makefile` 的 `-I` 缺口沿用 D2-C5 卡结论，**本卡未重复实测**。
4. §4.3 的分发映射来自 `版本支持终版.md`（其自述"未真机验证"）。
5. §2 的"本机可做"判定中，**重打包保符号链接**一项**未实测**（本卡不改产物）。

---

## §8 建议的实现顺序（供总调度排卡）

1. **不依赖签名**：§5.1 端点契约 + §5.3 判决器 + §6 清单文档化（可立即做）。
2. **依赖外机器**：搭 macOS + Theos → 修 `Makefile:13` 的 `-I` → 编译出 dylib（A 段）。
3. **依赖证书**：签名（F 段）→ 打通 OTA（§5.2）→ 真机验证（17.0 / 17.2.1 / 18.4 / 18.4.1）。
4. **决策点**：参考件选 v1.2.0（无内核链）还是 v1.0.0/DS（含内核链）——见 §4.2 第 3 条。

---

## §9 实现落地（W-IOS-PKG2，2026-10-03）

设计件经总调度复核通过（R2）后已实现**不依赖签名/编译**的部分：

| 件 | 位置 |
|---|---|
| 流水线脚本 | `05-ios/tools/ipa_pipeline/ipa_pipeline.py`（`seed` / `build` / `verify`） |
| 登记表 | `05-ios/tools/ipa_pipeline/registry.json`（11 外壳 × 9 dylib，按 sha256） |
| 自测（反向断言 13 项） | `05-ios/tools/ipa_pipeline/selftest_ipa_pipeline.py` |
| 用法/约束 | `05-ios/tools/ipa_pipeline/README.md` |
| 示例产物（无签名） | `05-ios/dist/FilzaSlop-1.0.3-unsigned.ipa` + `.manifest.json` |

**已实测的关键保证**：裸壳拒绝（exit 8）· 未登记=拒绝（3/4）· 无签名名缺 `-unsigned`=拒绝（5）·
**符号链接保留**（fixture）· **权限位保留**（406→406）· **条目数不变**（3103→3103）· **产物可复现**（两次同 sha256）。

**仍未做**：签名（需证书）· dylib 编译（需 macOS+Theos）· 真机安装。

---

*本件为设计说明，未实现任何功能；未 commit。*
