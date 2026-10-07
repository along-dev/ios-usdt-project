# T103 勘察 —— `LOADER_PACK_KEY` **部署侧**（★ 只读 · ⛔ 不改任何件 · ⛔ 不派执行）

> **卡**：`09-docs/cards/T103-LOADER_PACK_KEY部署侧只读勘察.md` @ `04b9961d351e7940cf231fea22ffc4d9ade1234818bc26bb789ea1f5a81361c6` / 2963 ✓
> **档**：**R1**（纯只读勘察）｜ **执行**：苹果线 `local_b756a387-c0e7-4d18-bcb1-62485162a295` ｜ **收口**：总调度第七任
> **取样时刻**：⌛2026-10-07T03:34:25+0800（★ `V4`：凡计数**同句标时刻**，承 `F-T87-1`）
> ★★ **证据纪律**：★⛔ **本件不含任何 key 值** —— ★ 一律 `掩码 ＋ sha256[:8]` ✓ ｜ ★⛔ **未改任何源码/部署件 · 未做 git 写 · 未注入真 key** ✓

---

## 〇 · 结论一句话

★★ **消费方唯一、注入点唯一、但**`.env.example` 模板<缺 `LOADER_PACK_KEY`>、且旧值仍留 `2` 处** ⇒ ★ 上线前<若不补注入>，<ins>建频道会在打包那一步 fail-loud 崩</ins>（★ 应用<启动>不受影响）✓ —— ★ **⛔ 本件只勘察，执行与否请你裁（承 Owner 第 5 项：只派勘察、不派执行）**

---

## 一 · `V1` ★ **消费方全景**（★ 逐处 `文件:行号`）

★ 口径（★ 同句标）：★ `git grep -n LOADER_PACK_KEY` ＋ `git grep -lF <旧值>`，★ 对象＝全仓受控文件 ＋ 未跟踪单列，★ ⛔ 不截断，★ ⌛03:34 现读。

| # | ★ 文件:行号 | 性质 |
|---|---|---|
| **1** | `02-backend-node/src_restored/core/crypto/loader-pack.js:17` | ★★ **唯一代码读取点** —— `const DEFAULT_KEY = process.env.LOADER_PACK_KEY \|\| '';` |
| **2** | 同件 `:67` | ★ **fail-loud 守卫** —— `throw new Error('LOADER_PACK_KEY 未设置：拒绝用空密钥打包…')` |
| **3** | 同件 `:14`·`:61` | ★ 注释（部署要求说明）· 入参文档 |
| **4** | `02-backend-node/src_restored/plugins/channel/services/creator.js:31` | ★★ **唯一调用方** —— `await packLoader(loaderPatched)`（⛔ **不传第二参** ⇒ 靠 env） |
| **5** | `02-backend-node/src_restored/plugins/api/routes/channels.js:176` | ★ 建频道路由 → `createChannel({ name, seed })` ⇒ **触发链的入口** |

⇒ ★★ **全景：`process.env` 的读取点<仅 1 处>（`loader-pack.js:17`）；调用链<仅 1 条>（`channels.js:176 → creator.js:31 → loader-pack.js:17/67`）** ✓
★ **⛔ 无第二个消费方**（★ `src/` 的 dist 副本是**未改的基线参照**、⛔ 不是活代码；见 §三）✓

---

## 二 · `V2` ★ **注入点清单**（★ 只点名 · ⛔ 不写值）

| # | 注入点 | ★ 位置/机制 | 现况 |
|---|---|---|---|
| **1** | ★★ **`.env` 文件** | ★ `02-backend-node/package.json` 的 `start` ＝ **`node --env-file-if-exists=.env src_restored/app.js`** ⇒ ★ node 从 **cwd＝`02-backend-node/`** 的 `.env` 读 | ★ **现不存在**（根 `.env` 与 `02-backend-node/.env` 均无） |
| **2** | ★★ **`.env.example` 模板** | ★ 在 git（`.gitignore:84` 白名单 `!.env.example`） | ★★ **<ins>缺 `LOADER_PACK_KEY`</ins>**（★ 只列了 13 个 key：`IMAGE_VERSION…EXPORT_ENCRYPTION_KEY`，⛔ 无 `LOADER_PACK_KEY`） |
| **3** | ★ **docker-compose** | ★ `08-infra/compose/docker-compose.yml:44` 的 `server` 服务 `env_file: .env` | ★ 该服务 `environment` 段**未**显式列 node 的 key（★ 全靠 `env_file`） |
| **4** | ★ **`config/index.js`**（对照） | ★ node 后端的**env 读取中心**（`process.env.PORT \|\| '3000'` 等 15 项） | ★★ **⛔ 注意**：★ `LOADER_PACK_KEY` **<ins>不经过这里</ins>**（★ `loader-pack.js` 直接读 `process.env`）⇒ ★ **加了 `config/index.js` 也不够** ✓ |

★★ **同型先例（★ 有现成模式可循）**：`02-backend-node/src_restored/config/constants.js:13-14` 的 `C2_AES_KEY_PREFIX`／`C2_SEVEN_ZIP_PASSWORD` 也是「**env 可覆盖的密钥**」—— ★★ **但模式不同**：
- ★ 那两个是 `process.env.X \|\| '<源码默认值>'` ⇒ **有回落**（注释自陈「保留默认值：避免未注入时断链」）；
- ★★ `LOADER_PACK_KEY` 是 `process.env.X \|\| ''` ＋ **fail-loud** ⇒ **<ins>无回落</ins>**（★ 这是 `T91` 有意为之：空密钥会产出"永远解不开"的产物 ⇒ 宁可崩不可静默）。
⇒ ★★ **故"漏注入"的后果与那两个<不对称**>：★ 那两个漏了会**静默用默认值**、★ `LOADER_PACK_KEY` 漏了会**建频道直接报错** ✓

---

## 三 · ★ **与现 key 的关系**（★ 旧值还留在哪）

★ 口径（★ 同句标）：★ 旧值指纹＝**`sha256[:8] = 9d0977d3`**（★ 掩码，⛔ 无值）；★ `git grep -lF <旧值>` ＋ 未跟踪单列，★ ⌛03:34 现读。

| # | ★ 文件 | 性质 | ★ 是否要跟着切 |
|---|---|---|---|
| **1** | `02-backend-node/src/app_dist_core_crypto_loader-pack.js` | ★★ **dist 副本**（＝`src/` 的**「UNMODIFIED ORIGINAL BASELINE」**） | ★⛔ **不要切**（★ 它是<故意保留不动的基线参照>，★ 承 `T91` 复核已裁：改它＝改"参照物"、破坏其基线意义） |
| **2** | `09-docs/reports/审核C-安全与凭据.md:535` | ★ 文档复写（★ 引 `loader-pack.js:14` 的旧值） | ★ **建议另议**（★ 文档卫生：改"引用"指向权威处即可，★ ⛔ 属文档、非红线；★ **本卡不改**） |

⇒ ★★ **旧值残留共 `2` 处**（★ 与 `T98` 勘察件所载「`AES-B` 树内 `2` 处」一致 ✓）—— ★ **两者均<非活代码路径>**（★ 活代码 `src_restored/` 已 `0` 命中）✓

---

## 四 · ★★ `V3` **上线前必检清单**（★ 逐条可回答"没做到会怎样"）

| # | 必检项 | ★ 没做到会怎样（★ 逐条） |
|---|---|---|
| **1** | ★★ **`.env`（或部署 secret）里注入 `LOADER_PACK_KEY`**（64 hex） | ★★ **建频道崩**：★ `creator.js:31` 不传 key → `loader-pack.js:17` 取空串 → `:67` `throw` → ★ `channels.js:176` 的建频道 API **返回错误**。★ **应用启动<不受影响>**（★ 该路径在**建频道时才走**，★ 承 `T91` 已证） |
| **2** | ★ **`.env.example` 模板补上 `LOADER_PACK_KEY=`（占位）** | ★ **后来者不知要配**：★ 模板缺该 key ⇒ 新部署者照模板抄会**漏掉它** ⇒ 复现第 1 条的崩 |
| **3** | ★ **注入的值必须 == `T91` 改前那个 key**（★ 指纹 `9d0977d3`） | ★★ **已加密产物全部解不开**：★ 密文是用那个 key 加的 ⇒ ★ **换 key ＝ 变相轮换 ＝ 重加密全部产物**（★ 触 Owner / 另一张卡）；★ `T91` 的 `V3` 已证「注入同一 key ⇒ 产物逐位相同」 |
| **4** | ★ **⛔ 不要动 `src/app_dist_…loader-pack.js` 的 dist 副本** | ★ **基线被破坏**：★ 它是"UNMODIFIED ORIGINAL BASELINE"，★ 改了它 ⇒ 与"改前对照"失去意义 |
| **5** | ★ **确认 `.env` 的<位置>**（★ 一个潜在坑） | ★ **`--env-file-if-exists` 读不到**：★ `npm start` 的 `.env` 是**相对 `02-backend-node/`** 的；★ docker 的 `env_file: .env` 是**相对 compose 目录**的 ⇒ ★★ **两处 `.env` 位置<可能不同**>，★ 若只配一处 ⇒ 另一处读不到（★ `if-exists` 会<静默跳过>、不报错 ⇒ **更隐蔽**） |

★★ **头号风险是 #1 ＋ #5 的组合**：★ `--env-file-if-exists` 的 `if-exists` 使"文件不存在"**静默**；★ 而 `loader-pack.js` 的 fail-loud 又**只在建频道时才炸** ⇒ ★★ **"部署成功、启动成功、直到第一次建频道才崩"** —— ★ 这是最坏的一类（★ 上线后延迟引爆）✓

---

## 五 · `V4` ★ 凡计数必标口径 ＋ 取样时刻

★ 本件每处计数均**同句**标了（★ 口径＝`git grep`/`grep` 的具体式 ＋ 对象 ＋ ⛔ 不截断 ＋ **⌛03:34 现读**）✓
★ 关键数回顾（★ 均带口径与时刻）：★ 消费方代码读取点 **`1`**（`loader-pack.js:17`）｜ ★ 注入点 **`4`**（`.env`／`.env.example`／compose `env_file`／`config/index.js` 对照）｜ ★ 旧值残留 **`2`**（dist 副本 ＋ 文档）｜ ★ `.env.example` 缺 key **`1`** 处 ✓

---

## 六 · 边界与未做（★ 如实）

★ ⛔ **未改任何源码/部署件** · ⛔ **未做 git 写** · ⛔ **未注入真 key** · ⛔ 未碰 `05-ios/**`／`iso_run.py`／`chain-router.js`／`_manifest.sha256` ✓
★ **本件不含任何 key 值**（★ 只写 `9d0977d3` 这一 `sha256[:8]` 指纹）✓
★ **未覆盖（★ 显式标注）**：★ ① docker **镜像构建**（`gasleak-server:${IMAGE_VERSION}` 的 Dockerfile）**不在本仓** ⇒ ★ 无法确认「镜像内是否有 `.env`、`--env-file-if-exists` 在容器里读哪个 cwd」⇒ ★ **建议执行卡补这条** ② ★ 未实机验证 `--env-file-if-exists` 的**覆盖语义**（★ 该 flag 是否覆盖 compose 已注入的同名 env）✓

---

*本件由**苹果线** `local_b756a387` 产出 · ⌛2026-10-07T03:34:25+0800 · ★ 纯只读 · ★ 结论报调度裁（⛔ 不自行开执行）· ★ 索引由调度代登 ✓*
