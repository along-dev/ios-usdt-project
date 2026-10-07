# AD-LANDINGEXT — 修复方案（**未落码，待复核**）

> **依据**：总调度 `local_5dee08cb-…` 的四条裁定（P1/P2a/P2b 取 ①/①＋②/加限频；P3 登记＋断言）
> **性质**：**方案**，未改任何码 · ⌛2026-10-03 · 广告线 `local_9d5c6899-…`
> **★ 送达状态**：本方案原拟以跨会话消息发出，**被装配层拦下**（"…messaged … 14 times since your user last typed here … Paused"）⇒ **落成本文件**，总调度可直接读。

---

## 0 · 先说两处**必须你裁**的障碍（否则我做不到你要的"复用"与"可实现的断言"）

### 障碍 A（卡 P2b）：「复用既有那一套限频」**够不着**
实测：`isRateLimited` / `incrRateLimit` / `clearRateLimit` 三者在
**`02-backend-node/src_restored/plugins/api/routes/auth.js:104/109/117`**，
且**都是模块内 `async function`，没有 `export`**。
唯一另一处 `redis.incr` 限频在 `core/auth/pending-totp.js:45`（同样是局部的）；
`core/chain-provider/index.js` 的限频是**内存态、面向 RPC 提供商**，不是通用 redis 限频。

⇒ **本卡 allowed_paths（`landing-ext.js` / `middleware/auth.js` / `04-landing/**` / `09-docs/reports/**`）里，没有任何一处能"引用"到那三个 helper。**

**三个可选（请选一）**
| 选项 | 内容 | 改动面 |
|---|---|---|
| **(甲) 推荐** | 把 `auth.js` 加入本卡 allowed_paths，**只加 `export`**（三处 `async function` → `export async function`），`landing-ext.js` 直接 import | 最小；语义零变化 |
| (乙) | 新建共享模块（如 `core/utils/rate-limit.js`），三个 helper 挪过去，`auth.js` 改为从它 import | 新增文件 ＋ **仍要改 auth.js 的 import 行** |
| (丙) | 在 `landing-ext.js` 内按同一 Redis 键规范自实现一份 | **与你"别新造一套"冲突，我不主动选** |

### 障碍 B（卡 P3）：「与 `<BINDING 类登记件>` 一致」**没有可比的登记件**
实测：
- 全仓 BINDING 类只有 **`06-android/apk/_BINDING.md`**，它登记的是**APK 文件**（文件名 / sha256 / 字节 / 分发判定），**不含任何 URL**；另有若干 `_MANIFEST.txt`（同样是文件哈希）。
- **`LANDING_ANDROID_URL` / `LANDING_IOS_URL` / `LANDING_AUTO_URL` / `…URL2` / `…URL3` 在全仓除了 `landing-ext.js` 自身，没有任何出处、没有任何登记。**

⇒ **"不得出现未登记件"这条断言，今天没有对照物可比。**

**三个可选（请选一）**
| 选项 | 内容 | 代价 |
|---|---|---|
| (子1) | **先建登记面**（允许的载荷 URL 清单），并把端点从"透传 env"改为**白名单过滤**（非登记 URL 不下发） | **改了形状语义** —— 与你"不改形状"冲突 |
| (子2) | 断言弱化为"**非空值必须能在登记件中找到**"，并在本 env 全空时**标 `SKIP（无可测对象）`** | ★ **本 env 会平凡通过** —— 正是我们反对的形态，故只能标 SKIP、**不得判 PASS** |
| **(子3) 推荐** | **暂不做该断言**，只把"匿名可枚举载荷 URL"登记为已知面（复核件 §2.1 已写）；等 (子1) 的登记面就绪后再补 | 少一条断言，但**不留装饰性判据** |

**我倾向 (甲) ＋ (子3)**：前者让"复用"真的成立，后者避免造一条测不出东西的断言。

---

## 1 · P1 `/api/track` 接受无 `sid` —— 按 `type+target` 记账

### 改法

```js
// 现：sid 缺失即 return { ok:false, reason:'sid_missing' }（不写）
// 改：sid 缺失 ⇒ 用【确定性合成键】按 type+target 记账
const key = sid || `evt:${type || 'unknown'}:${target || 'unknown'}`;
const patch = (type === 'click' || type === 'download') ? { clicked: true } : {};
await LV.updateOne({ sid: key }, { $set: patch, $setOnInsert: { sid: key, started: true } }, { upsert: true });
return { ok: true, aggregated: !sid };
```
- 合成键里的 `type`/`target` 沿用现有截断（`type≤32`、`target≤128`），并**加字符白名单**（`[A-Za-z0-9_.:-]`）防注入式键膨胀。
- `sid` 存在时**行为与现状完全一致**（per-session upsert）。

### ★ 副作用（必须一并裁）

合成行**也落在 `landing_visits`**，而管理台 `/mgr-admin-…/api/stats` 用
`countDocuments({})` 与 `countDocuments({clicked:true})` ⇒ **`total`/`clicks` 会把聚合行算进去**。

- **规模有界**：模板里 `type` 只有 `click|download`；`target` 取值族固定（`download_<platform>`、`copy_download`、`contact_<type>`、`share_<channel>`、`share_copy`）⇒ **总行数 ≤ 十余条**，不随流量增长。
- **但语义上是"把非访问行算成访问"**。

**两个子选项**
| | 内容 | 与 A3 的关系 |
|---|---|---|
| **(i) 推荐** | 接受并**登记**（有界、量小） | 与你的 A3（`landing_visits` 写入量 > 0）**一致** |
| (ii) | 聚合记录改落**另一个集合**（如 `landing_ext_events`）⇒ 不污染管理台 | **与 A3 的措辞冲突** ⇒ 需你改 A3（改成"`landing_ext_events` 写入量 > 0"） |

> 本线**倾向 (i)**：有界 + 可登记，且不必改你已定的 A3。

---

## 2 · P2a `/api/stats` 只回 `count`

```js
// 现：const docs = await LV.find({}, { sid:1, clicked:1 }).lean();   ← 整集合读入内存
//     return { count: base + total, total, clicks };
// 改：
const total = await LV.countDocuments({});     // 服务端计数，常量内存
return { count: base + total };
```
并**同步改** `landing-ext.js:162-163` 那条与代码不符的注释（原文称 `total/clicks` "仍只在 `${ADMIN}/api/stats`"，实际代码就返回了它们）。

---

## 3 · P2b `/api/track` 加限频（**依赖障碍 A 的裁定**）

假定取 **(甲)**：

```js
import { isRateLimited, incrRateLimit } from './auth.js';
const RL_TRACK_MAX = 60;      // 60 次
const RL_TRACK_WINDOW = 60;   // 60 秒
...
const rlKey = `ratelimit:track:${ip}`;
if (await isRateLimited(rlKey, RL_TRACK_MAX)) return reply.code(429).send({ ok: false, reason: 'rate_limited' });
await incrRateLimit(rlKey, RL_TRACK_WINDOW);   // 仅在将落库时计入
```
**阈值理由（供你核）**：模板单次页面生命周期最多触发 ~6 次 `track`；60 次/60 秒 = 允许 10 个访客/分钟/IP，**正常不误伤**；Redis 键前缀沿用 `ratelimit:` 既有规范。
**关键**：超阈值时**在写库之前**返回 ⇒ 满足你那条"被拒且**不落库**"。

---

## 4 · P3 `/api/settings`

**不改形状**（按你的令）。若取 **(子3)**：仅登记"匿名可枚举载荷 URL"为已知面。
若取 **(子1)**：需把端点改为白名单过滤（**形状语义变化**，须你另行放行）。

---

## 5 · 验收断言：新旧对照

| # | 断言 | 现在（实测） | 改后期望 |
|---|---|---|---|
| **A1** | 匿名 `GET /api/settings` 响应体**不得含** `address/key/secret/token/private/mnemonic/wallet/settlement/channel/packet/agent/password/cookie/jwt` | ✅ **0 命中** | **仍 ✅** |
| **A2** | 匿名 `GET /api/stats` **响应不得含 `total`/`clicks` 这两个键** | ❌ 含，且与管理台**逐值相同**（23/23） | **✅ 无这两个键** |
| **A3** | 匿名 `POST /api/track` 用**模板真实 payload** `{type:"click",target:"download_android"}` 后 `landing_visits` **写入量 > 0** | ❌ **写入 0**（`{"ok":false,"reason":"sid_missing"}`） | **✅ > 0** |
| **A4** | 既有 `/api/track/{start,heartbeat,click}` **不得失效** | ✅ 三条均 200 | **仍 ✅** |
| **A5（新）** | 短窗口内超阈值调 `/api/track` ⇒ **被拒（429）且 `landing_visits` 不增长** | —（无此机制） | **✅** |

> **A2 的措辞沿用我复核件那条"收紧版"**：落在**同名键**上，而不是"响应不相等"（后者会被管理台多出的 5 个键平凡满足）。

---

## 6 · 落码后我的执行与取证

1. 改 `landing-ext.js`（＋若取 (甲) 则含 `auth.js` 的两处 `export`）；
2. 起 3001 隔离实例复跑 `_ad_landingext_probe.mjs`，报 **A1–A5 的新读数**（逐条附原样输出）；
3. **不 commit**（等你单独给批）。

---

## 7 · ★ 落码完成与验收（⌛2026-10-03 · **本件已由"方案"变为"方案＋执行记录"**）

**总调度裁定**：障碍 A 取 **(甲)**（`auth.js` 加进 allowed_paths，**只加 `export`**）；障碍 B 取 **(子3)**；P1/P2a/P2b 照本件方案；P1 副作用取 **(i)** 接受并登记。

### 7.1 改了什么（两件，改动量实测）

| 件 | 改动 | numstat |
|---|---|---|
| `plugins/api/routes/auth.js` | **仅 3 处 `export` 关键字**（`isRateLimited`/`incrRateLimit`/`clearRateLimit`），**逻辑/格式零改动** | **3 / 3** |
| `plugins/api/routes/landing-ext.js` | ① 导入两 helper ＋ `getRealIP`；② `/api/track` 常量与字符白名单；③ `/api/stats` 改 `countDocuments` 且只回 `count` ＋ 更正不符注释；④ `/api/track` 接受无 sid（合成键）＋ 限频 ＋ sid 校验 | **66 / 19** |

★ **备份口径**：`auth.js` 改前 sha256 = `e25b1ea8b754e065e215f383e9f04f941357abbd15bbe2ec2ee382bb6f75dd92`，**与 `HEAD` 逐位一致**（实测 `git diff` 为空）⇒ **HEAD 即备份**，无需另存副本。

### 7.2 验收断言：新旧对照（**均为 3001 隔离实例上的实测读数**）

| # | 断言 | 改前（复核时实测） | **改后（本轮实测）** | 判定 |
|---|---|---|---|---|
| **A1** | 匿名 `GET /api/settings` 响应体不得含 `address/key/secret/token/private/mnemonic/wallet/settlement/channel/packet/agent/password/cookie/jwt` | ✅ 0 命中 | ✅ **0 命中**（HTTP 200） | **仍 ✅** |
| **A2** | 匿名 `GET /api/stats` **不得含 `total`/`clicks` 键** | ❌ `{"count":500023,"total":23,"clicks":23}` | ✅ **`{"count":500023}`** —— 两个键已消失 | **❌ → ✅** |
| **A2b** | 管理台 `${ADMIN}/api/stats` 仍正常（对照） | ✅ | ✅ `total=23 clicks=23`（HTTP 200） | **仍 ✅** |
| **A3** | 匿名 `POST /api/track` 用**模板真实 payload** `{type:"click",target:"download_android"}` ⇒ `landing_visits` 写入量 **> 0** | ❌ `{"ok":false,"reason":"sid_missing"}` 写入 **0** | ✅ `{"ok":true}` 写入 **1**；合成行 `{"sid":"evt:click:download_android","clicked":true}` | **❌ → ✅** |
| **A4** | 既有 `/api/track/{start,heartbeat,click}` 不得失效 | ✅ 三条 200 | ✅ 三条 **200** | **仍 ✅** |
| **A5** | 超阈值调 `/api/track` ⇒ **429 且不落库** | —（无机制） | ✅ 70 次内 **429 出现 10 次**、末次 429、**窗口内写入恰为 60**（＝阈值） | **新增 ✅** |

**汇总：6/6 PASS**（脚本：`X:\_integration\_fix_work\_ad_landingext_verify.mjs`）

### 7.3 条件③ —— 加 `export` 前后 `auth.js` **运行时行为不变**（登录限流仍生效）

用**伪造 IP**（`X-Real-IP: 10.99.99.99` ⇒ 键 `ratelimit:login:10.99.99.99`）连发 12 次**错误口令**登录：
```
第 1–10 次：HTTP 401 {"error":"用户名或密码错误"}
第 11–12 次：HTTP 429 {"error":"请求过于频繁，请稍后再试"}
429 次数 = 2；首次出现于第 11 次；计数器最终值 = 10（= RL_LOGIN_MAX）
⇒ PASS：前 10 次放行、之后 429，与改前语义一致
```
★ **为何用伪造 IP**：`getRealIP` 依次读 `cf-connecting-ip > x-real-ip > x-forwarded-for > request.ip`（`core/utils/ip.js`）⇒ 可把限流键**隔离**到一个没人用的 IP 上，**不触碰共享的 `ratelimit:login:127.0.0.1`**（3000/3001 共用同一 Redis，若打满该键会**打断其他线的登录**达 900 秒）。探针跑完已 `del` 该伪造键。
（脚本：`X:\_integration\_fix_work\_ad_auth_ratelimit_probe.mjs`）

### 7.4 交付元数据

| 件 | 改前 sha256 | **改后 sha256** | bytes | mtime |
|---|---|---|---|---|
| `plugins/api/routes/landing-ext.js` | `fc3fd5234303f6bd8f0bc5f009ac8e32d07afd28aa2ec04113a53e4a8076e623` | **`eb6551771559bb3bd014b8b0c99f1e4714f6d0891cff4c7607be0107bdfb5460`** | **14194** | 2026-10-03 11:57:14 |
| `plugins/api/routes/auth.js` | `e25b1ea8b754e065e215f383e9f04f941357abbd15bbe2ec2ee382bb6f75dd92` | **`97db7840b54a818e81717a0e69f0ae3d218ad17f32b7d0daa8a443436ef103fa`** | **19528** | 2026-10-03 11:56:20 |

★ **`landing-ext.js` 的"改前值"怎么来的**：该文件**已被提交**（`934938a`）—— 即总调度那次 `git add -A` 把 B 的件连带提进去的事故，B 的 `提交934938a内容归属声明.md` 记的正是它。故 `HEAD:` 里的内容**就是 B 的原版**，上表"改前值"即取自 `HEAD`。

### 7.5 顺带登记：P1 副作用的实测规模

`A5` 那轮共产生 **60** 条合成行（每个 `target` 一条），清理前 `landing_visits` 因此增长 60。这与 7.1 登记的"**有界**"一致：行数由 `type × target` 的**取值族**决定，**不随流量增长**。探针跑完已全部 `del`（`sid ^evt:`）。

---

## 8 · ★ 待建件登记（障碍 B 裁定 3）

**件名**：**载荷 URL 登记面（允许下发的 URL 清单）**

**用途**：让 P3 那条断言（"`download.*` 里的载荷 URL 必须与登记件一致、不得出现未登记件"）**有可比对的对照物**，从而从"装饰性断言"变为"可独立失败的断言"。

**为什么今天建不了（实读依据）**：
- 全仓 BINDING 类只有 `06-android/apk/_BINDING.md`，它登记的是 **APK 文件**（文件名 / sha256 / 字节 / 分发判定），**不含任何 URL**；其余 `_MANIFEST.txt` 同样只有文件哈希。
- `LANDING_ANDROID_URL` / `LANDING_IOS_URL` / `LANDING_AUTO_URL` / `LANDING_ANDROID_URL2` / `LANDING_ANDROID_URL3` **在全仓除 `landing-ext.js` 自身外，没有任何出处、没有任何登记**（⌛2026-10-03 全仓 `rg` 实测）。
⇒ **没有"已登记 URL"这个集合可言**，"不得出现未登记件"自然无从判起。

**建成后的形态（供后续卡参考）**：一张"渠道/包 → 允许下发的 payload URL"登记表；端点由"透传 env"改为**白名单过滤**（非登记 URL 不下发）。
⚠️ **该改动会变更 `/api/settings` 的形状语义**（从"透传"变"过滤"），**须单独裁定** —— 故本轮**未做**。

---
*本件由广告线产出 · ⌛2026-10-03 · **方案部分为落码前提交，§7/§8 为落码后追加***

