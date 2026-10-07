# Filza IPA 在高版本 iOS 上能否使用 —— 结论

> 方法：直接解析 6 个 `FilzaApplySandboxExt.dylib` 的 Mach-O 与字符串表，
> 比 `Filza_IPA_分析报告.md` 更进一层（报告只看了主程序 `minos`，未看 dylib 的内核偏移门禁）。
> **全部静态分析，未真机验证。**

---

## 一、直接回答

**能，而且比两条链覆盖得更宽 —— 但有严格前提。**

`FilzaApplySandboxExt.dylib` 里有一条**明确的内核偏移支持门禁**（三处独立样本一致）：

```
[-] Only supported offset for iOS/iPadOS 17.0 - 26.0.x
```

配套的版本枚举字符串（`hw.cpufamily` / `hw.cpusubtype` 之后，即内核偏移选择表）：

```
16.0  19.0  26.0        ← 表边界/哨兵
17.0  26.1              ← 门禁文字紧邻
17.1  17.4  18.0  18.1  18.4  18.6   ← 实际支持的版本点
```

**解读**：dylib 自带内核偏移表，支持区间标注为 **iOS 17.0 – 26.0.x**，
显式列出的版本点为 **17.0 / 17.1 / 17.4 / 18.0 / 18.1 / 18.4 / 18.6**（及区间上界 26.x）。

**但是** —— 这条门禁属于**第 1/2 代（内核利用链）**。第 3 代（Slop 1.0.3 / 1.2.0）
**没有这条字符串**，因为它们的架构完全不同。

---

## 二、必须区分两条技术路线

| | **第 1/2 代**（DS 系 + Slop 1.0.0） | **第 3 代**（Slop 1.0.3 / 1.2.0） |
|---|---|---|
| 样本 | Escaped_DS_1.2、Jailed_DS_2.0、Jailed_2.1、Slop_1.0.0 | Slop_1.0.3、Slop_1.2.0 |
| 机制 | **内核 R/W + XPF 签名绕过** | **MHA-MCM 身份信任绕过** |
| dylib 大小 | 883K / 918K / 938K / 870K | 470K / 504K |
| 导出符号 | 1080 / 1108 / 1142 / 1 | 1 / 1 |
| 带版本门禁串 | ✅ `17.0 - 26.0.x` | ❌ **无** |
| 读内核 | `kernelcache`、`__dsc_load_file` | 不读 |
| 依赖 LiveContainer | ❌ | ✅ **强依赖** |

### 2.1 第 1/2 代：靠内核偏移表，**版本敏感**

关键证据（`Escaped_DS_1.2` dylib 原文）：

```
/System/Library/Caches/com.apple.kernelcaches/kernelcache     ← 直接读内核缓存
/private/preboot/%s%@                                          ← preboot 路径拼接
/private/preboot/Cryptexes/OS/System/Library/CoreServices/RestoreVersion.plist
                                                               ← iOS 16+ Cryptex 布局
__dsc_load_file / __dsc_load_symbols / _dsc_init_from_path     ← 运行时解析 DSC
_offsets_init                                                  ← 偏移初始化
_objc_msgSend$systemVersion                                    ← 读系统版本做分支
```

**含义**：
- 它**运行时**读 `kernelcache` + `RestoreVersion.plist` 推导内核偏移，
  所以**不写死单一版本** → 这解释了为什么它敢标 `17.0 - 26.0.x`。
- 已含 `/private/preboot/Cryptexes/` 路径 → **至少覆盖 iOS 16+ 的新布局**。
- 但 `RestoreVersion.plist` 只有**部分版本**能推导出正确偏移 →
  所以门禁是「**17.0 – 26.0.x 区间 + 枚举的版本点**」，不是全版本通用。

### 2.2 第 3 代：**不碰内核**，版本无关但**依赖 LiveContainer**

`Slop_1.0.3` / `Slop_1.2.0` 的字符串里**没有任何版本门禁**，取而代之的是：

```
LiveContainer
[LiveContainer] Local Apps / Local App Data / Shared Apps ...
LiveContainer compatibility mode
The process still uses LiveContainer's signed identity.
  It cannot receive MobileHouseArrest access to system app containers.
MHA-MCM class 2 application-data lookup and sandbox extension
MHA-MCM means the MobileHouseArrest identity-trust bypass in MobileContainerManager.
Boundary: no arbitrary /var, Keychain, TCC, root, kernel,
          or app-bundle access is claimed.
```

**含义**：
- **不依赖内核偏移** → 理论上**版本无关**，可跟随系统更新。
- 但**必须运行在 LiveContainer 环境**（或具备 MHA 身份的进程），
  否则字符串明确说拿不到 system app container 的访问权。
- 作者自己划了边界：**不提供 root / 内核 R/W / 任意 /var / Keychain / TCC**。

---

## 三、与两条链的覆盖对比

| iOS | coruna 链 | darksword 链 | Filza dylib 门禁声明 | Filza 实际可用性 |
|---|---|---|---|---|
| 13.0 – 15.1.1 | ✅ | — | ❌ dylib `minos=15.0` | ⚠️ 有链无工具 |
| 15.2 – 17.0 | ✅ | — | 门禁从 **17.0** 起 | ⚠️ **需实测**（`minos` 是 15.0，但偏移表从 17.0 起） |
| **17.0 – 17.2.1** | ✅ | — | ✅ **明确支持** | ✅ |
| 17.3 – 18.3.x | ❌ 链空白 | ❌ 链空白 | ✅ **dylib 支持** | ⚠️ **工具可用但无链喂** |
| **18.4 – 18.4.1** | ❌ | ✅ | ✅ **明确支持** | ✅ |
| 18.5 – 18.6.2 | ❌ | ⚠️ RCE 缺失 | ✅ 含 **18.6** | ⚠️ 工具可用，链不可用 |
| 18.7 – 26.0.x | ❌ | ❌ | ✅ 区间上界 26.0.x | ⚠️ 工具声明支持，**无链** |

### 3.1 一个重要发现：Filza 的覆盖比两条链**更宽**

门禁写的是 **17.0 – 26.0.x**，而两条链合起来只到 18.6.2（且 18.5+ 残缺）。

也就是说：
- **17.3 – 18.3.x 这段"链空白区"，Filza 的 dylib 声明支持** ——
  但**没有链能在这段拿到注入前提**，所以工具再强也喂不进去。
- **18.7 – 26.0.x** 同理：Filza 声明支持，但两条链都不覆盖。

**结论**：Filza 的版本能力**不是瓶颈**，**瓶颈在链**。

### 3.2 `minos` 与门禁的**矛盾**需要实测

| 项 | 值 | 含义 |
|---|---|---|
| Mach-O `minos` | **15.0.0** | 声明最低 iOS 15 |
| 内核偏移门禁 | **17.0 – 26.0.x** | 声明偏移只覆盖 17.0 起 |

两者冲突区间是 **15.0 – 16.x**：
dylib **能加载**（minos 允许），但**偏移表不覆盖** → 内核利用会失败。

**我倾向**：15.0–16.x 上 dylib 能跑但 `kexploit` 失败（会打印
`[-] Only supported offset...` 然后降级或退出）。**这需要真机确认。**

---

## 四、还有一个硬约束：签名

| 项 | 状态 |
|---|---|
| `_CodeSignature/CodeResources` | ❌ 全部缺失（除内嵌 Sharing.appex） |
| `embedded.mobileprovision` | ❌ Slop 三个无；其余 5 个共用的**已于 2023-10-30 过期** |
| 证书 | Team `83R2LKVFAQ`，`application-identifier = 83R2LKVFAQ.com.*`（通配） |
| `get-task-allow` | `true`（允许调试器附加） |

**含义**：这些包**在高版本 iOS 上无法直接安装**——
高版本对签名校验更严，过期 profile + 无 `_CodeSignature` 会被拒。
必须经**越狱/漏洞链提权后侧载**，而侧载正是需要链的原因。

---

## 五、最终结论

### 5.1 直接回答"能不能用到高版本"

| 问题 | 答案 |
|---|---|
| dylib 自身支持到多高？ | **iOS 26.0.x**（门禁声明），枚举点含 18.6 |
| 高版本能用吗？ | **能，但有前提** |
| 前提是什么？ | 1. 必须**先经漏洞链提权**才能装上（签名已过期）<br>2. **17.0 以下偏移表不覆盖**，15.0–16.x 大概率 `kexploit` 失败<br>3. 第 3 代还需要 **LiveContainer 环境** |
| 比两条链覆盖宽吗？ | **宽得多**（Filza 到 26.0.x，链只到 18.6.2） |
| 那为什么不能直接用？ | **瓶颈在链不在工具** —— 17.3–18.3.x、18.7+ 没有链能把 Filza 送进去 |

### 5.2 实操建议

| 目标版本 | 建议 |
|---|---|
| 15.2 – 17.2.1 | ✅ 用 coruna 链 + DS 系 Filza（门禁覆盖 17.0+；15.2–16.x 需实测） |
| **18.4 – 18.4.1** | ✅ **最佳组合**：darksword 全链 + Filza（门禁明确含 18.4） |
| 18.5 – 18.6.2 | ⚠️ Filza 声明支持 18.6，但**链的 RCE 模块是 85 字节存根** → 喂不进去 |
| 17.3 – 18.3.x | ❌ **链空白**，Filza 再新也没用 |
| 18.7 – 26.0.x | ❌ **链不支持**，Filza 声明支持也无从注入 |

### 5.3 一句话

> **Filza 的版本能力覆盖到 iOS 26.0.x，比两条链宽；
> 但它必须先被链送进设备，而链只覆盖 15.2–17.2.1 与 18.4–18.4.1。
> 所以"能不能用到高版本"的真正答案是：工具能，链不能。**

---

## 六、证据局限

1. **未真机验证**。门禁字符串是**声明**，不是已确认行为。
2. `17.0 - 26.0.x` 中的 **26.0.x** 指 iOS 26（即 2025 年后的新命名），
   与 SDK `26.2.0` / `26.5.0` 呼应，但**该版本号体系与链的偏移表未对齐**。
3. 版本枚举串 `17.0 17.1 17.4 18.0 18.1 18.4 18.6` 是从**二进制相邻字节**提取，
   可能包含非版本用途的数字，**顺序与归属需反汇编确认**。
4. `minos=15.0.0` 与门禁 `17.0+` 的矛盾**未解决**，需真机测 15.0–16.x。
5. Slop 1.0.3 / 1.2.0 符号被大量 strip（167/179 个），
   其"版本无关"结论主要基于**缺少门禁字符串 + 依赖 LiveContainer** 的推断。
6. `Boundary:` 那段是**作者自述**，未经独立验证。
