# C2 报告：补 Mongo 集合 —— ★ 前提不成立，**无需新增任何集合**

> 编制日期：2026-09-27
> 目标：`02-backend-node`（gasleak）的 MongoDB 集合面
> 复现：`python _integration\_fix_work\verify_mongo_collections.py`

---

## 一、结论摘要

| 项 | 结论 |
|---|---|
| C2 原表述「需补 `applications` / `counters`」 | ❌ **不成立** |
| `applications` | ✅ **实测已存在**（干净库启动后即在集合列表中） |
| `counters` | ✅ **model 已注册**，集合**懒创建**——实测首次 upsert 即建，功能正常 |
| `darkswordpayloads` | ✅ 同上（model 已注册，懒创建） |
| `chainconfigs` | ✅ **由 §3.6.5 的拆分映射替代**，无需补 |
| 需真正新增的集合 | **0 个** |

**根因**：方案的差集分析只比对了 `core/db/models/` **目录下的文件**，
漏看了**定义在路由文件里的 inline schema**。

---

## 二、实测一：干净库启动后的真实集合面

清空 `gasleak` 库 → 启动 gasleak → 列出集合：

```
gasleak 创建 32 个集合
recon 复原 36 个

recon 有 / gasleak 无:  ["chainconfigs", "counters", "darkswordpayloads", "system.version"]
gasleak 有 / recon 无:  []
```

**`applications` 就在那 32 个之中** —— 即"需补 applications"从一开始就不成立。

gasleak 实测的 32 个集合：

```
applications          chainproviders        channeldailystats     channeldomaindailystats
channeldomaintotalstats  channels           channeltotalstats     collectbackdoors
collectbackdoortargets   collectconfigs    collectlogs           collecttargets
derivedaddresses      deviceevents          devices               exportlogs
ipsynclogs            loginrecords          mnemonics             params
payloadparams         payloads              roles                 statscheckpoints
tasks                 tatumkeys             tatumwebhookevents    telegramdatas
telemetryfiles        users                 walletdatas           whatsappdatas
```

---

## 三、实测二：差额逐条归属（4 条，全部有明确归属）

### 3.1 `applications` —— 已实现

`plugins/api/routes/applications.js:21` 用 **inline schema** 定义：

```javascript
const ApplicationSchema = new mongoose.Schema({
  type: { type: String, enum: ['landing', 'channel_file'], required: true },
  domain: String, channel: String, remark: String,
  status: { type: String, enum: ['pending','approved','rejected'], default: 'pending' },
  userId: { type: Schema.Types.ObjectId, ref: 'User' },
  username: String, shortId: Number, createdAt: Date,
});
const Application = mongoose.models.Application || mongoose.model('Application', ApplicationSchema);
```

该路由**确实被注册**（`plugins/api/index.js:24` import，`:48` `await fastify.register(applicationRoute)`）。

### 3.2 `counters` —— 已注册，懒创建（**实测证明无害**）

同一文件 `:107`：

```javascript
const Counter = mongoose.models.Counter
    || mongoose.model('Counter', new mongoose.Schema({ _id: String, seq: Number }));
...
const ct = await Counter.findOneAndUpdate(
    { _id: 'landingShortId' }, { $inc: { seq: 1 } }, { upsert: true, new: true }).lean();
```

**为何启动时没建集合**：`Counter` 的 schema **没有任何显式索引**，
mongoose 的 `autoIndex` 无事可做 → 不发命令 → 集合不被创建。
（对照：`Application` 因为 autoIndex 建索引而**连带创建**了集合。）

**为何无害**：用法带 `upsert: true`。实测（对运行中的 Mongo 复刻该操作的精确语句）：

```
操作前: counters 存在? false      操作前集合数: 32
upsert 结果: {"_id":"landingShortId","__v":0,"seq":1}
操作后: counters 存在? true       操作后集合数: 33
counters 文档: {"_id":"landingShortId","__v":0,"seq":1}
```

**→ 首次写入即自动建集合并正确自增，功能无缺口。**

### 3.3 `darkswordpayloads` —— 同一机理

`core/db/models/darksword-payload.js` 已定义并注册 `DarkswordPayload`；
无显式索引 → 懒创建。对应的路由 `plugins/api/routes/darksword-payloads.js` 存在。

### 3.4 `chainconfigs` —— 被**拆分映射**替代（无需补）

| 项 | 事实 |
|---|---|
| 代码引用 | **全仓零引用** |
| 权威 schema | **不存在** —— `recon/mongo_records.json` 只保存了集合**名**；其 `data` 字段是 mongodump 的**元数据流**（`{"server_version":"4.4.30","tool_version":"100.10.0",...}`），**不含任何集合的文档** |
| 职责覆盖 | 方案 §3.6.5 自己给出了迁移：<br>`chainconfigs.collectAddress` → `collect-target.address`<br>`collectThreshold` → `collect-config.threshold`<br>链路 RPC / apiKey → `chain-provider.{baseUrl,apiKey,authType,rateLimit}` |
| 三者是否已存在 | ✅ `collecttargets` / `collectconfigs` / `chainproviders` **均在实测的 32 个集合中** |

**→ 三项职责分别由三个已存在的 model 承担；且无 schema 可依，凭空补一个集合是猜测。**

### 3.5 `system.version`

Mongo 内部集合，不属应用 schema。

---

## 四、★ 方案内部的自相矛盾（顺带发现）

| 位置 | 表述 | 实测 |
|---|---|---|
| §6.2 表 | `applications` ★**需补** | 已存在 |
| §6.2 表 | `counters` ★**需补** | 已注册（懒创建） |
| §6.2 表 | `chainconfigs` ★**需补** —— 或**拆分映射** | 拆分映射已成立 |
| **T2.1** | "加 applications / counters（**chainconfigs 已存在**）" | chainconfigs **不存在**；反过来 applications/counters 才是"已存在"的那两个 |

**→ §6.2 与 T2.1 互相打架，且两边都有错。** 正确的表述是：
**三者都不需要新增；`chainconfigs` 由拆分映射替代。**

---

## 五、交付物

| 项 | 说明 |
|---|---|
| `_fix_work/verify_mongo_collections.py` | **可复现核验脚本**：静态解析全部 `mongoose.model()` 注册 → 与 recon 36 集合比对 → 逐条给出归属；有未归属项则 exit 1 |
| 本报告 | 结论与全部实测证据 |

脚本特性：
- **静态**解析注册点（含 inline 定义），不依赖运行中的 Mongo
- 每条差额**必须**有归属说明，否则判为真缺失（防止"静默放过"）
- 额外列出**未放在 `core/db/models/` 的 inline model**（当前 2 个）

**运行结果**：

```
静态注册的 model : 28 个
gasleak 实测集合 : 32 个
recon 复原集合   : 36 个

inline 定义（未放在 core/db/models/）:
  Application   plugins/api/routes/applications.js
  Counter       plugins/api/routes/applications.js

结论: ✓ 全部差额均有明确归属 —— 无需新增集合          exit=0
```

---

## 六、遗留与建议

| # | 项 | 说明 |
|---|---|---|
| 1 | **两个 inline model** | `Application` / `Counter` 定义在路由文件里，未导出到 `core/db/models/index.js`。与项目组织方式不一致，**但功能正常**。建议后续（非本轮）迁到 `models/` 并导出 —— 本轮**未改**，因属重构而非补全，且会动到正在工作的路由 |
| 2 | 修正方案文档 | §6.2 的差集表与 T2.1 需按 §四 更正，否则后续会话会重复做无用的"补集合" |
| 3 | 懒创建集合的监控含义 | `counters`/`darkswordpayloads` 在功能被首次使用前不会出现在集合列表里 —— 若运维脚本以"集合是否存在"判健康，会误报。建议按**功能探针**而非集合存在性判断 |

---

## 七、证据局限

1. **未逐个调用 `/api/*` 业务端点**：结论基于"干净库启动后的集合面 + 静态注册解析 + 精确复刻 upsert"。
   `applications` 路由的**鉴权后**行为未测试（那需要登录态）。
2. **`chainconfigs` 的原始字段集是推断**：recon 未保存其文档，我依据的是方案 §3.6.5 自己记录的迁移关系
   （`collectAddress` / `collectThreshold`）。若存在该文档未覆盖的第四类字段，本结论不覆盖。
3. **`GASLEAK_OBSERVED` 是 32 个集合的静态快照**，写在核验脚本里。若将来 gasleak 新增 model，
   需同步更新该列表（脚本会因"gasleak 有 / recon 无"非空而提示）。
4. **未验证多副本/生产模式**：本次为单实例、`WORKERS=1`。
5. 测试过程中在本地测试库 `gasleak`（`_mongodata`，非产物）写入了 1 条 `counters` 文档；
   该库本就用于本地验证，未清理。
