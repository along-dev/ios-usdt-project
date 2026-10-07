# 02-backend-node（gasleak Node 后端）

> **卡 I3-C3**｜基线：本轮实测｜**不得写入凭据明文**

## 职责

gasleak 侧后端服务：**载荷分发**、**归集调度**、**Node→Go 桥接**。
监听端口 **3000**（固定，不得改）。

## ★ 运行目录是 `src_restored`，不是 `src`

| 目录 | 内容 |
|---|---|
| **`src_restored/`** | **实际运行目录** —— 目录树还原版 |
| `src/` | 扁平 dist 版（**改错一份等于没改**） |

镜像为 TypeScript 项目（`src/*.ts` → `tsc` → `dist/*.js`），镜像内**只有 `app/dist`**，
故本工作区装的是 **`dist/` 的 JS**。运行目录以实际启动定论（`ecosystem.config.cjs:4`）。

## ★ 判据中间产物目录（**不在产物内**，勿误认为残留）

下表三个目录**曾经存在于本目录下**，它们是 **`_fix_work` 判据脚本的输出目录参数**
（`syncCorunaPayloads` / `syncDarkswordPayloads` 的第 2 个实参 ⇒ **写入目标**）：

| 目录 | 判据脚本写入点 | 曾含 |
|---|---|---|
| `.verify_tmp_storage` | `verify_entries_coruna.mjs:156` | 15 个 `payloads/*.dat` |
| `.verify_tmp_storage_ds` | `verify_entries_coruna.mjs:199` | 5 个 `payloads/ds_*.dat` |
| `.rt_storage` | `verify_i1c2_runtime.mjs:29/38/72` | 20 个 `payloads/*.dat` |

**要点**：

1. ★ **它们不是产物**：产物根**没有** `payloads/` 目录（载荷模板在 `templates/`），
   且 **`src_restored/`（生产运行目录）对这三个目录名零引用**。
2. ★ **下次跑判据会重建**：执行 `verify_entries_coruna.mjs` / `verify_i1c2_runtime.mjs`
   会在本目录下**重新生成**同名目录，属**预期行为**，**不是新残留**。
3. ⇒ **可安全删除**（已按 R2-C3 清理）；**无需加入排除清单**，
   跑完判据后如不想留存，手工删除即可。

## 关键文件

| 文件 | 作用 |
|---|---|
| `src_restored/app.js` | 服务入口；`:193` 的 `totalWorkers` 与实例守卫 |
| `ecosystem.config.cjs` | PM2 配置；`instances` 默认值（**已与 app.js 同源，漏配退化为单实例**） |
| `src_restored/core/collect-bridge.js` | L2→L4 桥；业务成败用 `code === 0` 判定（**不得用 `r.ok`**） |
| `src_restored/schedules/collect-confirm-task.js` | 归集确认链（有界重试 5 次 + 60s 退避） |
| `src_restored/plugins/api/routes/` | 全部 HTTP 路由（115 条实测） |
| `templates/payloads/` | 载荷模板（构建期从 `build_unified.ps1` 同源产出） |

## ★ 启动

```powershell
# node 不在 PATH —— 必须显式加入（否则 npm ci 的 postinstall 报 'node' 不是内部或外部命令）
$env:PATH = "E:\CTF\runtime\node;" + $env:PATH

npm ci            # 323 包；node_modules 约 3.8 GB，不进产物
npm start         # 脚本用 node --env-file-if-exists=.env
```

★ **app 无 dotenv 加载**（纯读 `process.env`，镜像里靠 pm2 的 `env_file` 注入）
⇒ 必须用 `--env-file-if-exists=.env`，否则**静默用默认值**。

## ★ 归集互斥（重要）

- **占位在 MariaDB（全局共享）**，`inflight` 在**单进程内存**。
- 多实例是本项目**可能的**部署形态；`workders` 漏配时**已修复为退化成单实例**。
- ⇒ 跨进程判断**不能依赖 `inflight` 为空**，那推不出"另一进程不持有占位"。

## 服务依赖

| 依赖 | 端口 |
|---|---|
| MongoDB | 27018 |
| Redis | 16379 |
| MariaDB | 13306 |
| Go 后端 | 8888 |

## ★ TTL（MongoDB 自动过期）—— **静默删除，务必知悉**

★ **本节由 T15（R2）补充**：TTL **早已实现**，此前只是**未在文档中声明**
（`需求文档.md` 的 P2-4 原文写作"未纳入设计"，**该表述不准确**，见下）。

### 哪些集合有 TTL

| 集合 | 过期字段 | TTL | 定义处（`src_restored/`） |
|---|---|---|---|
| **`WalletData`** | `receivedAt` | **30 天** | `core/db/models/wallet-data.js:16` |
| **`device-event`**（`DeviceEvent`）| `createdAt` | **30 天** | `core/db/models/device-event.js:10` |
| `Task` | `createdAt` | **90 天** | `core/db/models/task.js:20` |

均为 MongoDB TTL 索引：`index({ <字段>: 1 }, { expireAfterSeconds: 30 * 24 * 3600 })`
（即 `2592000` 秒）。集中常量见 `config/constants.js:14` 的 `EVENT_TTL_DAYS: 30`。

### TTL 的行为 —— ★ **静默删除**

**TTL 由 mongod 的后台线程执行**（默认约每 60 秒一轮），
**不经过应用层** ⇒ **没有告警、没有日志、没有通知**。
应用侧**不会**收到任何回调，删除动作**在 Node 日志中零痕迹**。

★ 这是 **TTL 的固有行为，不是缺陷**。缺陷在于**我们此前没有观测它**。

### 运维含义（★ 重要）

1. ★★ **凭证超期后不可追溯**：`WalletData` 超过 30 天后被 mongod 直接删除，
   该凭证**无法恢复、无法审计、无法回溯**。若某设备长期离线，
   其早期上报的凭证会在**重新上线之前**就已消失。
2. ★ **dead-letter / 未同步数据同样会被清理**：TTL 只看字段时间，
   **不区分状态** ⇒ 尚未同步、待处理的记录也会一并删除。
3. ★ **删除时间不精确**：mongod 后台线程约每 60 秒扫描一次，
   实际删除时刻比 `字段时间 + TTL` **晚最多约 1 分钟**（且高负载下更晚）。

### ★ 可观测性（T15 新增）

- **定时巡检**：`src_restored/schedules/ttl-inspect.js`
  任务名 **`ttl-inspect`**，**每 6 小时**执行一次（`runImmediately: true`）。
  统计每个集合「即将进入 TTL 窗口」的条数与最老记录年龄，
  并以 **`logger.warn`** 记录（字段：`collection` / `expiringSoon` /
  `oldestAgeDays` / `ttlDays` / `total` / `overdue`）。
  ⇒ **让"静默消失"在日志中可见**。
- **只读端点**：`GET /api/dashboard/ttl-status`（需鉴权，无 token 返回 401）。
  返回各集合的 `total` / `expiringSoon` / `overdue` / `oldestAgeDays`，
  并附 `limitation` 字段如实声明"已删除的不可追溯"。
- ★ **本巡检只读**：仅 `countDocuments` + `findOne`，
  **不删除任何数据、不修改任何 TTL 索引数值**。

## ★ §5.2.4 的处置：**确认由潜客兜底**（T20）

**`需求文档.md:207`（§5.2.4）原文**：

> `| 5.2.4 | 补 bsc collector（或确认由潜客兜底） | 二期 |`

**★ 本轮（T20）选择"确认由潜客兜底"路径，【不新建 bsc collector】。**

### 依据

1. ★ **`src_restored` 全树无 bsc collector** —— 全树搜 `bsc`/`binance`/`bep20`
   **零业务命中**（仅 `templates/` 下混淆 JS 的二进制噪声）。
2. ★ **BTC 归集由潜客侧 `Sk()` 处理**（见 N-6 / N-7 的既有裁决）。
3. ★ **`需求文档.md:90-91` 已写明原因**：

   > （默认 gasleak 执行；**bsc 由潜客兜底**，因 gasleak `derived-address.chain`
   > 枚举实测为 `['eth','tron','btc']`，**不含 bsc**）。

4. ★ **`需求文档.md:449`（C6）** 同口径：「gasleak 是否需补 bsc collector
   ⇒ 由 §2.3 决策（**当前由潜客兜底**）」。

⇒ **gasleak 侧不承担 bsc 归集**；`collect_lock.go` 的 `chain` 词表亦**不含 bsc**
（词表外一律拒绝，**单一事实来源**）。本条**不是能力缺口，是已裁决的边界**。

## 相关契约

- **C-2**（`/app/*` 三端点）：响应恒 HTTP 200，**成败看 body 的 `code`**；
  `collect-lock` 冲突为 **HTTP 409**。
- **C-3**（`entries` 项数）：coruna 恰 15、darksword 恰 5。
- **C-4**（`srcDir`）：指向复制进 `02-backend-node/templates/` 的副本（只复制不移动）。
