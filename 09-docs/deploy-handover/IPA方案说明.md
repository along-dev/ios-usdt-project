# IPA 方案说明（iOS 载荷投递 · 组装流水线）

> **编制**：架构线 `[D]` ｜ **时刻**：⌛2026-10-07
> **★ 依据**：`09-docs/reports/W-IOS-PKG1-IPA组装流水线设计.md`（设计）· `W-IOS-PKG3-X3合并实施记录.md`（实施）· `05-ios/tools/`（代码现状）· `05-ios/darksword/README.md` / `CHAIN-FLOW.md`
> **★ 不写凭据明文。**

---

## 一、方案架构：两段式

```
A 段（备壳，脚本外）                    B 段（注入，脚本内）
Theos 编译 tweak dylib          →        dylib 放进 Filza 壳 Frameworks/ + 包内手术 + 重打包
```

- **dylib** = `FilzaApplySandboxExt`（Theos 编译的 tweak，5 个 `.m` 源：`Tweak.m`/`MCMBridge.m`/`MCMFilzaIntegration.m`/`PosterBoardFeature.m`/`UpdateChecker.m`）
- **基座** = FilzaSlop（Filza 4.0 改版），主二进制**已预置** `LC_LOAD_DYLIB → FilzaApplySandboxExt.dylib` 载入命令
- 关键：`zip -y`（保符号链接）是 iOS 能否安装的关键；Windows 默认 zip 不保 ⇒ 组装器用 Python `zipfile` 显式设 `external_attr`/symlink 位

---

## 二、基座三代（决定「注入后拿到什么能力」）

| 代 | 件 | 内核链 | 版本门禁 |
|---|---|---|---|
| **第 1/2 代** | DS 变体（FilzaEscaped_DS/FilzaJailed）+ FilzaSlop **≤ v1.0.2** | ✅ 有（`kexploit_opa334`） | **17.0 – 26.0.x**（硬 `exit(1)`） |
| **第 3 代** | FilzaSlop **v1.0.3+** | ❌ 无（走 MCM/MHA 路径） | **无门禁**（dlsym 探测） |
| 裸壳 | Filza_4.0.x（NoUS/Crack） | —（无 dylib 无载入命令） | 只能作备壳输入 |

★ 断点精确在 **v1.0.2 → v1.0.3**（dylib 体积 `886,456 → 470,184` 腰斩；门禁串 `2→0`、`kexploit_opa334` `2→0`）。
★ 选型结论：**要内核链（能力最全）必须选 ≤ v1.0.2 或 DS 变体**；选 v1.1.0+ 即自动放弃内核链。

---

## 三、版本适配：两条正交轴（不是一回事）

| 轴 | 管什么 | 区间 | 依据 |
|---|---|---|---|
| **A · 网页链** | 能否造出注入前提 | coruna **15.2.0–17.2.1** · darksword **18.4–18.6.2** · 空档 17.3–18.3.9 | `chain-router.js:46-74` |
| **B · IPA 代际** | 注入后拿到什么能力 | 第 1/2 代门禁 17.0–26.0.x · 第 3 代无门禁 | `W-IOS-PKG1` §4.2 指纹实测 |

★ 基座 App 本身 `MinimumOSVersion = 7.0`（`Payload/Filza.app/Info.plist`），但**「能装」≠「能投递」**——载荷（coruna/darksword）需要 15.2+ 才有偏移表。

---

## 四、分发规则（设计 · 静态推断，未真机）

| iOS 区间 | 分发件 | 理由 |
|---|---|---|
| **17.0 – 17.2.1** | **DS 变体**（第 1/2 代） | 网页链 coruna ✅ + 内核链门禁内 ✅（能力最全） |
| **18.4 – 18.4.1** | DS 变体 或 Slop-v1.0.0 | darksword ✅ + 门禁内 ✅ |
| 15.2 – 16.x | Slop **第 3 代** | coruna 可跑，但第 1/2 代被门禁拒 |
| 17.3 – 18.3.9 | 任一代（**无链可喂**） | 网页链空档（已裁接受）；工具可用而已 |
| 18.7 – 26.0.x | 第 3 代（DS 也行但无链） | 无链 |

---

## 五、工具链现状（`05-ios/tools/`）

| 工具 | 作用 | 状态 |
|---|---|---|
| `ipa_pipeline.py` | 骨架：`seed`/`build`/`verify`；登记表强制（拒未登记件）+ 13 项反向断言 + 符号链接保真 + 可复现（同输入两次同 sha） | ✅ 已实现 |
| `ipa_assemble.py` | Mach-O `LC_LOAD_DYLIB` 注入（`inject_mode`：`slot-replaced`/`linkedit-appended`/`landed-only`）+ `manifest.plist` 生成 | ✅ 已并入 pipeline |
| `resolve_payload_set.py` | iOS 版本 → 载荷集合（与 chain-router 同源） | ✅ |
| `delivery_router.py` | 平台分流（iOS/Android/桌面） | ✅ |
| `make_mobileconfig.py` | 企业签名 OTA 描述文件 | ✅ |
| `registry.json` | 11 外壳 × 9 dylib 登记（按 sha256） | ✅ |

★ `inject_mode` 三个取值：`slot-replaced`（基座有槽位，零改动）· `linkedit-appended`（无槽位，ncmds+1）· `landed-only`（落盘不加载，**默认 exit 12 拒绝**）。
★ 产物：`05-ios/dist/FilzaSlop-1.0.3-unsigned.ipa` + `.manifest.json`。

---

## 六、★ 三个阻断项（方案未闭环）

| 阻断 | 现状 | 要什么 |
|---|---|---|
| **签名** | 11 件**全部 unsigned** ⇒ 不能 OTA，只能侧载（AltStore/Sideloadly/LiveContainer） | 付费 Apple 证书（.p12）+ bundle id 必须 `com.apple.mobile.MobileHouseArrest`（免费账号签不了，报 9400/9401） |
| **dylib 编译** | 本机无 Theos/clang/iOS SDK；且 `Makefile:13` 的 `-I` 路径缺失（ChOma 无 include/） | macOS + Theos |
| **真机验证** | 全部静态分析 + 包内指纹 | 真机 17.0 / 17.2.1 / 18.4 / 18.4.1 各 ≥1 台（+ 17.3 对照） |

---

## 七、投放端（设计 · 未实现）

IPA 端点**同构 APK 侧**（隐藏前缀 `mgr-admin-8bcde2021d98` 逐字符保留）：

| 端点 | 方法 | 用途 |
|---|---|---|
| `/mgr-admin-8bcde2021d98/api/ipa/upload` | POST | 上传已签名 IPA |
| `/mgr-admin-8bcde2021d98/api/ipa/list` | GET | 列表（version/bundle id/iOS 区间） |
| `/mgr-admin-8bcde2021d98/api/ipa/delete` | POST | 删除 |
| `/mgr-admin-8bcde2021d98/api/ipa-url` | GET | 按 UA/版本返回 IPA 直链 |
| `/mgr-admin-8bcde2021d98/api/ipa/manifest.plist` | GET | 动态生成 OTA manifest |
| `/mgr-admin-8bcde2021d98/api/ipa/route` | GET | 版本→分发件 判决（诊断） |

**OTA 链路**：`落地页 → itms-services://?action=download-manifest&url=… → manifest.plist → IPA 直链 → iOS 校验签名 → 安装`。
★ 独立判决器 `pickIpa(ua)`（⛔ 不复用 `chain-router.pickChain`，它管网页链）。

---

## 八、实现顺序建议（承 W-IOS-PKG1 §8）

1. **不依赖签名**（可立即做）：§七端点契约 + 判决器 + 外部资源清单文档化。
2. **依赖外机器**：macOS + Theos → 修 `Makefile:13` 的 `-I` → 编译 dylib（A 段）。
3. **依赖证书**：签名（F 段）→ 打通 OTA → 真机验证。
4. **决策点**：参考件选 v1.2.0（无内核链）还是 v1.0.0/DS（含内核链）。

---

## 九、证据局限（必须随件知悉）

1. 全部为**静态分析 + 包内指纹**，未编译、未签名、未真机。
2. 「代际判定」依据字符串指纹（`kexploit_opa334`/门禁串/`container_query_create`/`MobileHouseArrest`），若上游符号剥离/加密可能漏判（但四 marker 同现同消 + 体积差交叉一致）。
3. §四分发映射来自 `版本支持终版.md`（自述"未真机验证"）。

---

> **落款时刻**：⌛2026-10-07（架构线 `[D]`）
