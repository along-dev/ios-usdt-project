# W-IOS-DS · DS 代际可用性取证（**第一步：只取证，不落码**）

> **性质**：取证件。**未改任何代码**。
> **依据**：`总调度1` 裁定「DS 支持 —— 立卡，但先取证」（⌛2026-10-03）。
> **本件回答两问**：① 是否存在**未签名**的 DS 壳？② 重签步骤的实现依赖是什么、**没有证书能走到哪一步**？
> **方法**：全量扫描 `E:\ios漏洞\**` 与 `05-ios/reference/ipa/**` 下所有 `.ipa`，对每件**双判**：
> a) 主二进制是否含 `LC_CODE_SIGNATURE`；b) 是否存在 `_CodeSignature/`（**按层报**）。

---

## 一、★ 口径更正（先纠一处我先前的错误）

我先前那张表把 `_CodeSignature/` 一列写成"False"，**错在【范围】而非取值** —— 那列只查了**主 app 层**
`Payload/Filza.app/_CodeSignature/`，而 DS 系真正的 `_CodeSignature/` 在**嵌套扩展层**：

```
Payload/Filza.app/PlugIns/Sharing.appex/_CodeSignature/CodeResources
```

⇒ **"签名状态"必须按层报**（主 app 层 / 嵌套扩展层）。**总调度复核指出该出入，成立。**
本次全量扫描已按**双口径**重做（下表）。

---

## 二、全量扫描结果（15 个唯一 IPA，去重后）

| IPA | bundle id | ①`LC_CODE_SIGNATURE`(主二进制) | ②`_CodeSignature/`(主 app 层) | ③`_CodeSignature/`(任意层) | 判定 |
|---|---|---|---|---|---|
| `FilzaEscaped_DS_1.2.ipa` | `com.tigisoftware.Filza` | **True** | False | **True**（appex 层，1 条） | **已签名** |
| `FilzaJailed_2.1.ipa` | `com.tigisoftware.Filza` | **True** | False | **True**（appex 层，1 条） | **已签名** |
| `FilzaJailed_DS_2.0版@iosjumo.ipa` | `com.tigisoftware.Filza` | **True** | False | **True**（appex 层，2 条） | **已签名** |
| `Filza_4.0.0_Crack_OK.ipa` | `com.tigisoftware.Filza` | **True** | False | **True**（appex 层） | **已签名** |
| `Filza_4.0_NoUS_Crack.ipa` | `com.tigisoftware.Filza` | **True** | False | **True**（appex 层） | **已签名** |
| `FilzaSlop-v1.0.0-unsigned.ipa` | `…MobileHouseArrest` | False | False | False | 未签名 |
| `FilzaSlop-v1.0.1-unsigned.ipa` | `…MobileHouseArrest` | False | False | False | 未签名 |
| `FilzaSlop-v1.0.2-unsigned.ipa` | `…MobileHouseArrest` | False | False | False | 未签名 |
| `FilzaSlop-v1.0.3-unsigned.ipa` | `…MobileHouseArrest` | False | False | False | 未签名 |
| `FilzaSlop-v1.1.0-unsigned.ipa` | `…MobileHouseArrest` | False | False | False | 未签名 |
| `FilzaSlop-v1.2.0-unsigned.ipa` | `…MobileHouseArrest` | False | False | False | 未签名 |
| `FilzaSlop_1.0.0.ipa`（`E:\ios漏洞` 侧） | `…MobileHouseArrest` | False | False | False | 未签名 |
| `FilzaSlop_1.0.3.ipa`（`E:\ios漏洞` 侧） | `…MobileHouseArrest` | False | False | False | 未签名 |
| `Filza_4.0.0_Crack_OK 2.ipa`（重复名副本） | `com.tigisoftware.Filza` | **True** | False | **True** | 已签名 |
| `Filza_4.0_NoUS_Crack 2.ipa`（重复名副本） | `com.tigisoftware.Filza` | **True** | False | **True** | 已签名 |

★ 「` 2.ipa`」为 `E:\ios漏洞` 下的**重名副本**，与 `05-ios/reference/ipa/` 下的同名件**不是同一路径**；本件按**文件名去重**列出。

### ★★ 第 1 问的结论：**不存在未签名的 DS 壳**

- **DS 系（`bundle id = com.tigisoftware.Filza`）共 5 个唯一件，全部 `LC_CODE_SIGNATURE = True`，且全部含嵌套 `_CodeSignature/`。**
- **未签名的只有 Slop 系（bundle id = `com.apple.mobile.MobileHouseArrest`）** —— 它们**不是 DS 代际**。
- ⇒ **在现有两个素材根下，扫不出可用于组装的未签名 DS 壳。**
  ⇒ **DS 代际「当前不可组装」的结论保持不变**，且**根因是"素材里没有未签名 DS 壳"**，
  而非流水线缺功能。

---

## 三、第 2 问：重签步骤的实现依赖 + **没有证书能走到哪一步**

### 3.1 依赖清单

| 依赖 | 作用 | 平台 | 现状 |
|---|---|---|---|
| **证书（.p12）** | 真正签名，过 iOS 安装校验 | — | ❌ **Owner 未提供** |
| **描述文件（.mobileprovision）** | 把证书与 App ID / 设备绑定 | — | ❌ 无 |
| **zsign** | 跨平台签名工具（C++）；支持 `-k <p12>` 正式签、`-a` **ad-hoc 签** | Windows/Linux/macOS（本机可编译/取用） | 未见 |
| **ldid** | 伪签名；`ldid -S` ad-hoc | 主要 macOS/Linux | 未见 |
| **codesign** | Apple 官方 | **仅 macOS** | ❌ 本机无 |

### 3.2 ★「没有证书能走到哪一步」—— 分档（**全部为静态判读，未实测**）

| 档 | 能做什么 | 没有证书时 | 能否安装到真机 |
|---|---|---|---|
| **0** | 解包 / 注入 / 重打包（含 Mach-O 改写） | ✅ **本流水线已实现**（不依赖证书） | — |
| **1** | **ad-hoc / 伪签名**（`zsign -a` 或 `ldid -S`） | ✅ 理论可做（不需要证书） | ❌ **过不了 iOS 的正常安装校验**；仅在**越狱设备**或特定装载器（LiveContainer 类）下可运行 |
| **2** | 用**付费证书**正式签名 | ❌ 需 Owner 提供证书 | ✅（仍需描述文件/TF 或企业分发） |
| **3** | OTA（`itms-services` + `manifest.plist`） | ❌ | 需**档 2** 已签名的 IPA 才成立 |

★ **一句话**：**没有证书时，只能走到「档 0 + 档 1」** ——
**产物可组装、可 ad-hoc 伪签名，但过不了 iOS 安装校验**；要真投放必须**档 2**。
★ 这与 `W-IOS-PKG1` §5.2 的结论一致（OTA 只认已签名 IPA），
且与 Owner 处**同一条待办**：**Apple 证书**（`README.md:84-112` 还额外要求 MHA 路径必须保持
`CFBundleIdentifier` 与 CodeDirectory identifier 同为 `com.apple.mobile.MobileHouseArrest`；
DS 系 bundle id 是 `com.tigisoftware.Filza`，**不受该约束**，但同样需证书才能装）。

---

## 四、对流水线的含义（不改码，仅结论）

| 项 | 结论 |
|---|---|
| DS 代际 | **当前不可组装** —— 素材无未签名 DS 壳（根因已定位到**素材**，非流水线） |
| 若将来拿到未签名 DS 壳 | 流水线的 `--bundle-id` 白名单**已支持**（DS 的 `com.tigisoftware.Filza` 已登记），签名门禁也会随之放行 —— **无需再改码** |
| 若走"重签 DS"路线 | 需 **档 2（证书）**；仅 ad-hoc（档 1）不能满足投放 |
| 与证书卡的关系 | **同源**：这条与"等 Apple 证书"是同一件事的两个面 |

---

## 五、证据局限（如实登记）

1. **全部为静态判读**：仅读 zip 清单 + Mach-O 载入命令；**未重签、未安装、未真机**。
2. 扫描范围 `E:\ios漏洞\**` 与 `05-ios/reference/ipa/**`；**其他盘位/外部来源未扫** ⇒ 结论限于**这两个根**。
3. §3.2 的分档为**静态推断 + 通行做法**，**本机未实测 zsign/ldid 是否可用、ad-hoc 产物是否可安装** ⇒ 标为 **未覆盖面**。
4. 未验证 DS 系 `_CodeSignature/CodeResources` 的**签名者身份**（是否同一证书）—— 若将来走"剥离签名复用壳"路线，需再取此证。

---

*取证件；第一步只取证，**未落码**。未 commit。*
