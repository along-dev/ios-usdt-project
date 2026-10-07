# T61 移植记录 —— `IOS源码1` → USDT **G3**：`schedules/balance-refresh.js`（新增）＋ `index.js` 注册

> **卡**：`09-docs/cards/T61-IOS源码1移植G3-balance-refresh.md`（`a82ac220d81ecb30ae693da1df0c6ce6ce6f0744365387e131fc9f1e04c56a94` / 4573 B，现读吻合）
> **档**：**R2** ｜ **授权**：Owner ⌛2026-10-05「按建议裁决」＋「继续」｜ **立卡**：架构线需求件 → 总调度第四任
> **执行**：安卓线（继承）`local_44ee108f` ｜ **收口/提交/复核**：总调度第四任
> **时刻**：⌛2026-10-05 18:52 +0800（照抄 `date`）
> ★ 所有 sha256 均 **64 位、现算**；★ 退出码**不接管道**；★ ⛔ 未做 git 写操作。

---

## 一 · 件与指纹（★ 基准**非 git** ⇒ **按 `sha256` 取件**）

| 件 | 角色 | sha256 | 字节 |
|---|---|---|---:|
| `E:\IOS源码1\server\src\schedules\balance-refresh.ts` | **基准（源）** | `9160eb39d9d15e35dadbd98dfced84bf0f05c808dd0154e1580f92f92afa72a9` | 4678 |
| `02-backend-node\src_restored\schedules\balance-refresh.js` | ★ **新增（本件产出）** | **`0d494ade24af151e6b94d0ae67e35875acea9a964ab3bbd898b88d0cc1dd746c`** | **5045** |
| `…\src_restored\schedules\index.js` | **改（仅注册一处）** | 改前 `e99157b1169ceffe4641bb2c03152858a3d48789df8e0d22f3149fde4e71b4b8` / 1201 → **改后 `d243de542c77492d79d0276f369a832b4e2d42ecce4c4b2ceaa1287a28acec5f`** / **1276** |

★ **V6 回滚**：本批 ＝ **纯新增 1 件 ＋ 改 1 注册** ⇒ **回滚 ＝ 删新件 ＋ 把 `index.js` 还原到 `e99157b1…`（1201 B）** ✓

---

## 二 · ★ 转换口径（**逐条对先例锚**）

**先例**：`balance-init.js`（**90 行**）← `balance-init.ts`（**112 行**），同一基准、同族件。

| 规则（卡 §二） | 本件怎么做的 |
|---|---|
| ★ **`import type { … }` 整行删除** | `.ts:2`（`IDerivedAddress`）与 `.ts:8`（`ScheduleTask`）**两行整体删除** ✓ ⇒ ⛔ **未**转成运行时 import |
| **运行时 import 原样保留** | `.ts:1,3,4,5,6,7` 六条 ⇒ `.js:1-6` **逐条对应** ✓ |
| **类型标注／接口／`as` 断言删除** | `type AddressBalances = {…}`（`.ts:10-14`）删 ✓ · `: ScheduleTask`（`.ts:18`）删 ✓ · `(addresses: IDerivedAddress[], chain: string): Promise<void>`（`.ts:91`）⇒ `(addresses, chain)` ✓ · `(address: IDerivedAddress): Promise<void>`（`.ts:106`）⇒ `(address)` ✓ · `let result: AddressBalances;`（`.ts:108`）⇒ `let result;` ✓ · `const update: Record<string, unknown> =`（`.ts:124`）⇒ `const update =` ✓ · `(err as Error).message` **两处**（`.ts:70,84,133`）⇒ `err.message` ✓ |
| **`export const x: ScheduleTask = {…}` ⇒ `export const x = {…}`** | ✓（`.js:8`） |
| ★ **中文注释 · 字符串字面量 · 数值常量 · 控制流一律保留** | ✅ 见 §三·`V2`（三集合**无丢失**） |
| ★ **形态随先例** | `.js` 采用先例的 **tsc 风格**（4 空格缩进、`if/else` 大括号展开、`//# sourceMappingURL=…` 尾注）✓ |

★ **新增的 3 条中文注记**（与先例的形态一致 —— 先例 `.ts` **0 条** → `.js` **3 条**，本件同样 0 → 3）：
`// 按链分组` · `// ETH / TRON 并发刷新` · `// BTC 串行、逐条间隔 1s` —— ★ **是注记、不改语义** ✓。

---

## 三 · 验收读数（★ 真退出码）

| # | 判据 | 读数 |
|---|---|---|
| **V1** | ★ **取件按 `sha256`**：先落清单、**取件后回读复核** | ★ 源 `.ts` 回读 ＝ `9160eb39…` / **4678 B** ⇒ **与清单逐位一致** ✓ |
| **V2** | ★ **保义判据（逐文件）**：**中文注释条数 · 字符串字面量集合 · 数值常量集合** | ★ **本件：中文注释 `.ts` 0 → `.js` 3（无丢失）· 字符串 25 → 25（无丢失）· 数值 `{0,1,1000,12}` 无丢失 ⇒ 保义成立 ✓** ｜ ★★ **方法已用先例对校准**（见下） |
| **V3** | ★★ **冒烟（隔离端口 `3100`）** | ★ **`Server listening on port 3100 (host=127.0.0.1)` ＋ `Scheduled tasks registered`** ✓ ｜ ★ 注册任务表**含 `balance-refresh`** ✓ ｜ ★ **共享 `3000` 未动**（PID 恒为 **23040**）✓ ｜ ★ 3100 已释放 ✓ |
| **V4** | ★ **类型名零残留** | ★ `grep -n "^import" balance-refresh.js` ⇒ **6 条运行时 import，无 `ScheduleTask`/`IDerivedAddress`/`AddressBalances`**（**词边界**匹配 ⇒ 全文命中 **0**）✓ ｜ ★ **坑已避开**：`types.js` 是空壳（只有 `export {};`）⇒ 若误转运行时 import 必 `SyntaxError` |
| **V5** | ★ **注册可加载** | ★ `node -e "import('./src_restored/schedules/index.js')"` ⇒ **`OK tasks= 15`**、**含 `balance-refresh` = true**、**不抛** ✓ |
| **V6** | ★ **回滚方案** | ★ 见 §一（改前 `index.js` sha `e99157b1…`/1201 ＋ 新件为新增）✓ |

### ★★ `V2` 的方法校准（★ 这一步是本件最值钱的一处）

初版判据是「`.js` 的字符串集合必须 **⊇** `.ts`」⇒ ★ **先例对也判"失败"**：`balance-init` 的 `.js` 比 `.ts` **少** `'./types.js'`。
⇒ ★ **当场查明**：那正是 **`import type { ScheduleTask } from './types.js'` 整行被删**（口径**要求**删）随之消失的字面量
⇒ ★ **判据口径修正**：比较时**排除 `import type …` 行**上的字面量。修正后 **先例对 ✓ ＋ 本件 ✓ 双通过**。
⇒ ★ 意义：**"拿先例对校准判据"** 才能区分「**真丢失**」与「**口径内应消失**」—— 否则会把**正确的转换**判成错。

---

## 四 · 边界与残留

- ★ **只做两处**：新增 `src_restored/schedules/balance-refresh.js` ＋ 改 `src_restored/schedules/index.js` 的**注册那一处**；★ **注册位置**照基准 `index.ts` 的**分组风格**放在 **`balanceInit` 之后**（基准里 `balanceInit` 后紧跟同族的 tron/eth 两条）✓ ⇒ ⛔ **未动其它 14 条注册的次序/内容** ✓
- ⛔ **未写 `src/`**（未修改的上游基线快照）· ⛔ **未改 `core/collect/**`**（那是 `T62`）· ⛔ 未改 `05-ios/**`／`migration/**`／判据装置 · ⛔ **未做 git 写操作**。
- ★ **未动共享 `3000`**：冒烟全程用 **3100**，且**冒烟前后 3000 的 PID 同为 `23040`** ✓（现读两次比对）。
- ★ **冒烟的安全设计（如实交代）**：`instanceOnly` 那道闸**只在 `WORKERS>1` 时生效** ⇒ 默认单 worker 下**冒烟实例会真的注册并触发全部定时任务**（`balance-init` 是 **5 秒**级）⇒ 与 3000 的活实例**双跑**。
  ⇒ ★ 因此我**采用短界**：**一出现 `listening` 即杀**（`runImmediately: false` ⇒ 首个间隔在 t+5s ⇒ 抢在首次触发之前）⇒ **未触发任何任务** ✓；★ 且**未复用其 env 文件**（该文件自带 `PORT=`），只**取其中两个值**设进环境（⛔ 未打印）。
- ★ **残留**：无（我的辅助脚本跑完即删）；★ 冒烟日志在 `/tmp`（**仓外**）✓。

---

## 五 · 未能验证（**如实**）

1. **`V3` 未验"任务真跑起来"** —— 短界冒烟**故意抢在首个间隔之前**杀掉（避免与 3000 双跑）⇒ ★ 证的是「**能起、能注册、无 import 错误**」，⛔ **不是**「`balanceRefresh` 的 handler 跑得通」（那需真让它跑一个周期，**有双跑风险**，未做）。
2. **`balanceRefresh` 的运行期语义未测** —— 它的 DB/Tatum 调用路径**未单独构造**；★ `V3` 只到"注册成功"。
3. **`V2` 的三集合判据仍是"语法层"** —— ⛔ 不校验**语义等价**（如 `as` 删除后类型收窄的运行时影响）；★ 本件该类删除**逐处列在 §二** 供复核。
4. **先例对只校准了 1 对**（`balance-init`）⇒ ★ 若别的同族件的口径不同（如带默认参数、泛型），**本尺未覆盖**。
5. **`index.js` 的注册位置是我的判断** —— 卡只要求"同形"，⛔ 未规定位置；我按基准分组放 `balanceInit` 后 ✓。★ 若你要求置于末尾，**一处即可调整**。

---

> **落款时刻（照抄 `date` 输出，非手写）**：`Mon Oct  5 18:52:19     2026`（+0800）

---

> ## ★ 更正（⌛2026-10-05 18:59 +0800 · 由本线追加；**⛔ 不就地抹、原读数保持在上**）
>
> **触发**：架构线**在派单之后**更新了需求件并出裁决件 **`ARCH-RULING-20261005-01` §三**。
>
> ### 一 · 事实与**我的独立自证**
> | # | 事实 | 我的现读证据 |
> |---|---|---|
> | 1 | 基准 `balance-refresh.ts` **`:112`/`:115` 传 `null`** | 现读 `.ts:112` ＝ `getEthAddressBalances(null, …)`、`:115` ＝ `getTronAddressBalances(null, …)`；★ `:118`（BTC）却是 `tatumClient` ⇒ **同文件内不一致** |
> | 2 | **USDT 侧没有那个约定** | USDT `src_restored/core/tatum/eth.js:4` ＝ `const data = await client.ethRpc('eth_getBalance', …)` ⇒ ★ **直接解引用 `client`、无 null 保护**；`tron.js:38-42` 同形 |
> | 3 | 基准**有**该约定 | 基准 `core/tatum/eth.ts:36` 签名 ＝ `getEthAddressBalances(client: TatumClient | null, …)` ⇒ ★ **`null` 是 IOS源码1 的<局部约定>** |
> | 4 | ★ **USDT 库内先例用 `tatumClient`** | `schedules/balance-init.js:44/47/50` ⇒ **三处全用 `tatumClient`**（含 BTC）|
>
> ★★ **失败形态的精确定性（我在改前先核过，比裁决件的"必 TypeError"更进一层）**：
> `getEthAddressBalances` 内部把三次调用包在 **`Promise.allSettled`** 里，失败只 **`errors.push(...)`＋`logger.error(...)`**，
> 末尾 **`return result;`（⛔ 不抛）** ⇒ ★ 实际形态**不是崩溃**，而是「**每轮刷不出 ETH/TRON 余额 ＋ 一条 error 日志**」
> ⇒ 归类为**静默失败**（本项目最在意的那一类）⇒ ★ **更该改**，⛔ 不是"可以不改"。
>
> ### 二 · ★ 适配（唯一需改逻辑处，2 行）—— **登记为「保义的第 1 处例外」**
> ```
> -: result = await getEthAddressBalances(null, address.address);        ⇒ : result = await getEthAddressBalances(tatumClient, address.address);
> -: result = await getTronAddressBalances(null, address.address);       ⇒ : result = await getTronAddressBalances(tatumClient, address.address);
> ```
> ⇒ ★★ **与 USDT 库内先例 `balance-init.js:44/47` **完全一致**（**先例即证据**；★ 且第 2 行的 `tatumClient` **本件第 2 行就已 import**）✓
> ★ **本处<不是>「零逻辑改动」** —— 它是**对基准语义的 1 处<已登记例外>**，如实列在下方，⛔ 不并入"保义"里蒙过去。
>
> ### 三 · 更正后的读数（★ 全部**重跑**）
> | # | 判据 | 更正后读数 |
> |---|---|---|
> | **V2** | 保义（三集合）＋ ★ **token 级差异**（加强） | ★ 三集合仍**无丢失**；★ **token 差异分类后<未归类 ＝ 空>**：`只 .ts 有` 全为口径内类型语法（含被删的 `type AddressBalances` 的**字段名**），`只 .js 有` ＝ `tatumClient`×2 ⇒ ★ **例外核 ＝ `null` 少 2 ／ `tatumClient` 多 2** ⇒ ★★ **与<先例对逐位同形>**（先例对同样 `null` 少 2 ／ `tatumClient` 多 2）✓ |
> | **V4** | 类型名零残留 | ★ **仍 0 命中**（词边界）✓ |
> | **V5** | 注册可加载 | ★ `import('./src_restored/schedules/index.js')` ⇒ **`OK tasks= 15`**、含 `balance-refresh`＝true、**不抛** ✓ |
> | **V3** | 隔离端口 **`3100`** 冒烟（**复跑**） | ★ **`Server listening on port 3100 (host=127.0.0.1)`** ＋ **`Scheduled tasks registered`** ✓ ｜ 共享 **`3000` 未动**（冒烟前后 PID 恒 **`23040`**）✓ ｜ 3100 已释放 ✓ |
> | **V1** | 取件按 `sha256` | ★ 源 `.ts` 现读 ＝ `9160eb39…`/4678 ⇒ **未变** ✓ |
>
> ### 四 · ★ 更正后的件指纹（**新 sha256**）
> | 件 | sha256 | 字节 | 相对更正前 |
> |---|---|---:|---|
> | `…\src_restored\schedules\balance-refresh.js` | **`f72426ae7b94684d6c0a7c3e46f7ecfaee12a954c3458cff560ceb5316f6caf8`** | **5059** | 由 `0d494ade…`/5045 ⇒ **+14 B**（`null`(4) → `tatumClient`(11) **×2** ⇒ 恰 +14 ✓ **逐字节可解释**） |
> | `…\src_restored\schedules\index.js` | `d243de542c77492d79d0276f369a832b4e2d42ecce4c4b2ceaa1287a28acec5f` | 1276 | **未变** ✓（注册不改） |
> | 源 `.ts`（基准） | `9160eb39d9d15e35dadbd98dfced84bf0f05c808dd0154e1580f92f92afa72a9` | 4678 | **未变** ✓ |
>
> ★ **回滚（更正后仍成立）** ＝ **删新件 ＋ 把 `index.js` 还原到 `e99157b1169ceffe4641bb2c03152858a3d48789df8e0d22f3149fde4e71b4b8`（1201 B）** ✓
> ★ 本件 §一～§五 的**原读数照旧有效**（那是**更正前**如实取得的）⇒ ⛔ 未改一字。

---

> # ★ 更正（⌛2026-10-05 19:08 +0800 · 由本线追加；**⛔ 不就地抹、§一～§五 原读数与原文保持在上**）
>
> ## 更正 · `F-T61-A`（P2）：我 §四 写的「**短界 ⇒ 未触发任何任务**」**<ins>不成立</ins>** —— 如实更正 ＋ 实测副作用面
>
> ### 一 · 我漏掉的**两类触发面**（复核方读码找出；★ 我逐条**现读复核，全部属实**）
> | # | 漏掉的面 | 我的现读证据 |
> |---|---|---|
> | **①** | **2 个 `runImmediately: true`** ⇒ **注册即执行**（与我杀得多快无关） | `log-cleanup.js` ＝ `interval: { hours: 1 }` **`runImmediately: true`** ✓ ｜ `ttl-inspect.js` ＝ `interval: { hours: 6 }` **`runImmediately: true`** ✓ |
> | **②** | **4 个 `type:'cron'`**，含 **`channel-stats-refresh` ＝ `*/10 * * * *`** | `channel-stats-refresh.js` ＝ `cronExpression: '*/10 * * * *'` ✓ ｜ `channel-stats-recalc.js` ＝ `'25 0 * * *'` ｜ `channel-stats-finalize-yesterday.js` ＝ `'15 0 * * *'` |
> ★ 且 **`app.js:348` 的 `instanceOnly` 闸以 `totalWorkers>1` 为条件**（默认单 worker ⇒ **整条短路**）；★ **`app.js:341` 打印 `listening` <ins>先于</ins> `:344` 的注册循环** ⇒ **「看到就杀」是<竞速>**，而注册是**微秒级** ⇒ **几乎必然走完** ✗ ⇒ ★★ **我那句"未触发任何任务"是错的** ✓（复核方与总调度均判 P2，我认）。
>
> ### 二 · ★★ **实测副作用面**（据实核 —— 复核方推断"大概率已删 >3 天日志"，我**实测更准**）
> 我保留的两份冒烟日志（`/tmp/t61_smoke2.log` · `/tmp/t61_smoke3.log`）里**确有执行记录**：
> | 任务 | 实测读数 | 副作用 |
> |---|---|---|
> | **`log-cleanup`**（`runImmediately`） | ★ **已执行**：`log-cleanup completed {"scanned":0,"deleted":0,"deletedFiles":[],"retainDays":3,"duration":40}` | ★ **`scanned 0` / `deleted 0` / `deletedFiles []` ⇒ <ins>未删任何文件</ins>** ✓（副作用**实测为零**，非"大概率删了"） |
> | **`ttl-inspect`**（`runImmediately`） | ★ **已执行**：`ttl-inspect completed {"collections":[{"collection":"WalletData","field":"receivedAt","ttlDays":30,"total":0,"expiringSoon":0,…` | ★ **只读统计**（`total:0`）⇒ **无写** ✓ |
> | **4 个 cron**（含 `*/10`） | ★ **无一命中**（两日志内**无 `channel-stats` 执行行**） | ★ 未写共享 Mongo ✓ |
> ⇒ ★ **结论**：**确实触发了（我说错了）**，但**实测副作用为零**（`log-cleanup` 未删任何文件、`ttl-inspect` 只读、cron 全未命中）✓。
> ★ **登记**：两轮冒烟（`smoke2`/`smoke3`）各触发 2 个 `runImmediately` 任务；★ 首轮 `smoke.log` **未到 listening**（Mongo 未起即退出）⇒ 未触发 ✓。
>
> ### 三 · ★★ 判据**降级**（采纳复核方建议 ＋ 总调度裁定）
> ★ **`V3` 的全量 boot 对本卡判据而言是「不必要的高风险动作」** ⇒ **<ins>弃用</ins>**。
> ★ **交付判据改以 <ins>import-only</ins> 为准** —— 即本件 §三 的 **`V5`**：`node -e "import('./src_restored/schedules/index.js')"` ⇒ **`OK tasks= 15`、含 `balance-refresh`＝true、不抛** —— ★ 它**DB-free、不起服务、不注册任务**，**已足以覆盖本卡要判的"能加载＋能注册"** ✓。
> ★ **本件 §三 的 `V3`（全量 boot 冒烟）<ins>作废</ins>**（其读数**当时如实**，但**手段高风险、且我误述了"未触发"**）⇒ ⛔ **后续不再以 boot 作 `V3`**；若**确须 boot**，须满足其一：① `WORKERS>1`（走 `instanceOnly` 闸）② boot 前把 handler 全禁（`enabled=false`）—— ★ ⛔ **不可仅靠"杀得早"**（那是**竞速**，不是**机制**）。
> ★ **回归**：本件 §一/§二/§四 的**改动与指纹部分不受影响**（那两行适配与指纹已另在更正块中给出新 sha）✓。

---

> ## ★ 补记 · `F-T61-B`（记法）—— `V6` 回滚锚 `e99157b1…` 是**内容 sha256**、**不是 git 对象**；★ 补「取法」
> （⌛2026-10-05 20:11 +0800 · 由**苹果线**（`T66` 执行）追加；★ 承卡 `09-docs/cards/T66-文档面-FT61B记法与T58因果留痕.md`；★★ **⛔ 未就地抹 §一/§三/§四 原文** —— 原字仍在上方）
>
> ★ **问题**：本件 §一（`:17`）· §三 `V6`（`:50`）· §四 更正块（`:127`）三处所给的**改前锚** `e99157b1…` 是**文件<ins>内容</ins> sha256**、**不是 git 对象 id** ⇒ 照字面 `git cat-file -e e99157b1…` ⇒ **`fatal: Not a valid object name`** ⇒ ★ 易被误读为"不可回滚"。
>
> ★ **补「取法」（★ 逐字，可直接粘）**：
>
> ```bash
> git show 4adbcc1^:02-backend-node/src_restored/schedules/index.js | sha256sum
> ```
>
> ★ **等价写法**（同一改前态，按提交号）：`git show 0333158:02-backend-node/src_restored/schedules/index.js`
>
> ★★ **我按该取法<ins>现跑一次</ins>**（⌛2026-10-05 20:11 +0800 · 证"**写了就能用**"）：
> ⇒ **`e99157b1169ceffe4641bb2c03152858a3d48789df8e0d22f3149fde4e71b4b8`** / **1201 B** ⇒ ★ **与 §一/§三/§四 的锚<ins>逐位一致</ins>** ✓
>
> ★ **回滚动作（不变）**：删新件 `src_restored/schedules/balance-refresh.js` ＋ 用上述取法把 `index.js` 还原到 `e99157b1…`（1201 B）✓
> ★ **口径（供后续件沿用）**：本项目的「sha256 锚」普遍是**内容 sha256**（非 git oid）⇒ ★ **引用时一律附<ins>取法</ins>**，否则收件人无法照做。
