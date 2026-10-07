# AD-LANDINGEXT —— 复核输入包（供**独立复核方**使用）

> **提交方**：广告线 `local_9d5c6899-a95a-421a-8d9b-26f485cd5ea6`
> **提交对象**：总调度 `local_b1a770bf-a016-4adb-973b-293407efa29c`（换届后）
> **性质**：**一页式复核输入包** —— 供被指派的独立复核方直接跑；**本线未自审**。
> ⌛2026-10-03 · 工作区**未提交**

---

## 1 · 复核对象（两件）

| 件 | sha256（全 64 位） | bytes | mtime |
|---|---|---|---|
| `02-backend-node/src_restored/plugins/api/routes/landing-ext.js` | `eb6551771559bb3bd014b8b0c99f1e4714f6d0891cff4c7607be0107bdfb5460` | 14194 | 2026-10-03 11:57:14 |
| `02-backend-node/src_restored/plugins/api/routes/auth.js` | `97db7840b54a818e81717a0e69f0ae3d218ad17f32b7d0daa8a443436ef103fa` | 19528 | 2026-10-03 11:56:20 |

**改前基线**（供 diff 比对）
- `landing-ext.js` 改前 = `fc3fd5234303f6bd8f0bc5f009ac8e32d07afd28aa2ec04113a53e4a8076e623`（＝ `HEAD`，该件已被 `934938a` 提交）
- `auth.js` 改前 = `e25b1ea8b754e065e215f383e9f04f941357abbd15bbe2ec2ee382bb6f75dd92`（＝ `HEAD`，工作树当时与 HEAD 逐位一致）

---

## 2 · 本线改了什么（复核要点）

| 件 | 改动 | 量 |
|---|---|---|
| `auth.js` | **仅 3 处 `export` 关键字**（`isRateLimited` / `incrRateLimit` / `clearRateLimit`），**逻辑与格式零改动** | 3/3 |
| `landing-ext.js` | ① 导入两个 helper ＋ `getRealIP`；② 新增 `/api/track` 常量与字符白名单；③ `/api/stats` 改 `countDocuments`、**只回 `count`** ＋ 更正不符注释；④ `/api/track` **接受无 sid**（合成键 `evt:<type>:<target>`）＋ **限频** ＋ sid 校验 | 66/19 |

**★ 请重点复核的三点**（都是"看起来对、其实可能错"的地方）
1. `auth.js` 是否**真的只加了 `export`**（`git diff` 应只有 3 行）；
2. `/api/track` 的**合成键是否可能被外部放大**（`type`/`target` 的字符白名单是否足够，键空间是否可控）；
3. **限频是否在写库之前**返回（超阈值必须**不落库**），且**复用的是 `auth.js` 的原函数**而非另造一套。

---

## 3 · 可跑命令（原样即可）

**前置**：起 3001 隔离实例（**不碰共享 3000**）——
```bash
powershell -NoProfile -ExecutionPolicy Bypass -File "X:\_integration\_fix_work\_ad_start_3001.ps1"
# 等 ~85s，确认 LISTENING
netstat -ano | grep ":3001 " | grep -c LISTENING     # 期望 1
```

**主断言（A1–A5）**
```bash
cd X:/_integration/_fix_work
AD_PORT=3001 "E:/CTF/runtime/node/node.exe" _ad_landingext_verify.mjs
```
**条件③（加 export 后 auth.js 运行时行为不变）**
```bash
AD_PORT=3001 "E:/CTF/runtime/node/node.exe" _ad_auth_ratelimit_probe.mjs
```
**复核完请停实例**
```bash
# 取 3001 的 PID 后 taskkill，或直接复用 _ad_restart_3001.ps1 的杀进程段
```

---

## 4 · 期望读数（本线实测，供比对）

**A1–A5（`_ad_landingext_verify.mjs`）→ 期望 `6/6 PASS`**

| # | 断言 | 期望读数 |
|---|---|---|
| A1 | 匿名 `GET /api/settings` 无敏感字段名 | `HTTP 200`，`命中=0` |
| A2 | 匿名 `GET /api/stats` **不得含 `total`/`clicks` 键** | `HTTP 200`，响应 **`{"count":500023}`**（两个键**不存在**） |
| A2b | 管理台 `stats` 仍正常（对照） | `HTTP 200`，`total=23 clicks=23` |
| A3 | 匿名 `POST /api/track` 用**模板真实 payload** `{type:"click",target:"download_android"}` ⇒ 写入量 **> 0** | `HTTP 200 {"ok":true}`，**写入量=1**，合成行 `{"sid":"evt:click:download_android","clicked":true}` |
| A4 | 既有 `/api/track/{start,heartbeat,click}` 不得失效 | 三条均 `HTTP 200` |
| A5 | 超阈值 ⇒ **429 且不落库** | 70 次内 **429 出现 10 次**、末次 429、**窗口内写入恰 60**（＝阈值） |

**条件③（`_ad_auth_ratelimit_probe.mjs`）→ 期望 `PASS`**
```
用伪造 IP 10.99.99.99（键 ratelimit:login:10.99.99.99）连发 12 次错误口令：
  第 1–10 次：HTTP 401
  第 11–12 次：HTTP 429
  计数器终值 = 10（= RL_LOGIN_MAX）
```
> ★ 该探针**故意用伪造 IP**：`getRealIP` 认 `cf-connecting-ip > x-real-ip > x-forwarded-for`。若**不隔离**，会打满 **3000/3001 共用**的 `ratelimit:login:127.0.0.1` ⇒ **打断其他线登录 900 秒**。复核时**请勿改用真实 IP**。

---

## 5 · 已知缺口（复核时**不要**当成本次引入）

1. **`/api/track` 的合成行会计入管理台 `total`/`clicks`** —— 管理台用 `countDocuments({})` / `countDocuments({clicked:true})`，合成行（`evt:*`）也在 `landing_visits` 里。**诚实客户端下 ≤ 十余条**（`type` 2 种、`target` 取值族固定）；★ **服务端原未设基数上限**（**已由本批 AD-01 修复**：白名单收窄后由服务端保证有界）。已按总调度裁定 **取 (i) 接受并登记**。
2. **P3 的"载荷 URL 必须与登记件一致"断言未做** —— 因**对照登记件不存在**（BINDING 类只登 APK 文件；`LANDING_*_URL` 全仓除 `landing-ext.js` 自身外无任何出处）。总调度取 **(子3)**：暂不做装饰性断言，改为**登记待建件**（见 `AD-LANDINGEXT-修复方案_20261003.md` §8）。
3. **`download-mode` 无行为效果** —— 本轮复核发现，**已登记为缺口 `G-27`（需 Owner 裁决）**，**不是本次改动引入**。
4. **限频阈值 60 次/60 秒** 是本线选的值（理由：模板单页生命周期最多 ~6 次 track），**未经 Owner 确认** —— 若复核方认为不合适，请指出。

---

## 6 · 边界（复核时请遵守）

- **不要改** `landing-ext.js` / `auth.js`（**先出结论**，要改由总调度裁定后另行安排）；
- 用 **3001 隔离实例**，**不要碰共享 3000**；
- `_ad_*` 脚本在仓库外 `X:\_integration\_fix_work\`，**不要落进产物**；
- 探针会**写库**（`landing_visits` 的 `evt:*` / `parity-*` 行）并在结束时自清；若中途失败，请手工清 `sid` 以 `evt:` 开头的行。

---

## 7 · ★ **Revision 2**（AD-01/02/03/04/05 修复后 · **待复验**）

> **本件 §1 的哈希是已复核的 Revision 1；本节才是当前待复验的 Revision 2。**

### 7.1 新哈希（Revision 2）

| 件 | sha256（全 64 位） | bytes | mtime |
|---|---|---|---|
| `landing-ext.js` | **`e8952d39664ead006f5dab6af42895cc307b7727ca8036922a6748ec1cde26e8`** | **18026** | 2026-10-03 18:42:56 |
| `auth.js` | `97db7840b54a818e81717a0e69f0ae3d218ad17f32b7d0daa8a443436ef103fa`（**未变** —— 本批未碰它） | 19528 | 2026-10-03 11:56:20 |

改动量：`landing-ext.js` **129/20**（累计）· `auth.js` **3/3**（仍仅 3 处 `export`）

### 7.2 五条修复逐条

| 复核意见 | 本批处置 |
|---|---|
| **AD-01（P2）** 合成键基数无上限 | **收窄到模板真实取值族白名单**：`type ∈ {click, download}`；`target ∈ {download_<4 platform>, <4 platform>, copy_download, contact_<服务端配置>, share_<3 channel>, share_copy}`。白名单外**归 `other` 并告警留痕**（不丢弃）。⇒ 合成键上限 ≈ **24 种** |
| **AD-02（P3）** 限频键可伪造 | ★ **复核意见给的"改用 `request.ip`"在本仓不成立**（见 7.4），故取它给的另一条路：**默认只用 socket 地址**；仅当 socket 地址在 `LANDING_TRUSTED_PROXIES` 白名单内才信任 `getRealIP()`（CF/XFF 类头） |
| **AD-03（P3）** 阈值不可配 ＋ 无打点 | 阈值改 `LANDING_TRACK_RATE_MAX` / `LANDING_TRACK_RATE_WINDOW`（**默认仍 60/60s，未改行为**）；429 时 `logger.warn({rlKey,max,windowSec})` 打点 |
| **AD-04（P3）** 计数语义 | **不改行为**，仅在注释写明：计数器统计**尝试数**、且**只在通过校验之后 +1** ⇒ `sid_invalid` 的 400 **不消耗配额**（已登记） |
| **AD-05（P3）** 措辞 | §5.1 已改为「**诚实客户端下 ≤ 十余条；服务端原未设基数上限（已由本批 AD-01 修复）**」 |

### 7.3 自证读数（3001 隔离实例实测）

**★ 强制回归（总调度点名）** —— 模板 `main.js` 的 6 处 `track()` 共 **14 个 (type,target)** 全部命中白名单、**无一条落入 `other`**：
```
PASS  REG-6  模板 6 处调用共 14 个 (type,target) 全在白名单内
      用例覆盖 :145/:146/:168/:196/:254/:268（4 platform × 2 + copy_download + contact_custom + 3 share + share_copy）
```

**AD-01 验收（键种数不随 N 增长）**
```
连发 150 次伪造 target（type 用合法值 click）⇒ 落库合成键 1 行 · **种数 = 1** · 含 evil_ 的键 = 0
键集合 = evt:click:other
```

**AD-02 验收（伪造 IP 不能突破限频）**
```
每请求换一个伪造 X-Real-IP / cf-connecting-ip，共 80 次 ⇒ **429 出现 20 次**（阈值 60）
⇒ 伪造头不再换来新配额
```

**A1–A5 回归：6/6 PASS**（A5 已改为"每请求独立 sid"，故"放行条数"可测）
```
A1 命中=0 · A2 匿名={"count":500024}（无 total/clicks）· A2b 管理台正常
A3 模板真实 payload ⇒ 落库 1 · A4 三条子路由均 200
A5 429 次数=10 末次 429 **窗口内落库=60**（恰为阈值）
```

脚本：`_ad_landingext_delta.mjs`（delta，4/4）· `_ad_landingext_verify.mjs`（A1–A5，6/6）

### 7.4 ★ 对复核意见的一处更正（前提核实）

复核意见 AD-02 给的首选是"改用不可伪造来源（`request.ip`）"。**在本仓不成立**：
`02-backend-node/src_restored/app.js:28` 设了 **`trustProxy: true`** ⇒ Fastify 的 `request.ip` **同样取自 `X-Forwarded-For`**，一样可伪造。
故本批取意见里的**另一条路**（可信代理白名单），并把默认设为**只用 socket 地址**（最保守）。
⇒ 部署在 nginx 之后时，把 nginx 地址写进 `LANDING_TRUSTED_PROXIES` 即可恢复"按真实客户端限频"。

**请复验方一并核这一点**（`app.js:28` 的 `trustProxy` 是否确实为 `true`）。

---

## 8 · ★★ **Revision 3**（D-01/02/03 修复后 · **待复验 delta**）

> §1 = 已复核的 Rev 1；§7 = Rev 2（已复验，**CHANGES_REQUIRED**）；**本节 = 当前待复验的 Rev 3**。

### 8.1 新哈希（Revision 3）

| 件 | sha256（全 64 位） | bytes | mtime |
|---|---|---|---|
| `landing-ext.js` | **`40f3416ba41fb48fdcae237c2c85ba51f072c563e51c30b02547c8b051a22cef`** | **21757** | 2026-10-03 19:17:20 |
| `auth.js` | `97db7840b54a818e81717a0e69f0ae3d218ad17f32b7d0daa8a443436ef103fa`（**未变**） | 19528 | 2026-10-03 11:56:20 |

改动量（累计）：`landing-ext.js` **205/20** · `auth.js` **3/3**（仍仅 3 处 `export`）

### 8.2 三条逐条

| 意见 | 本批处置 |
|---|---|
| **D-01（P2）· 代码侧 —— 加启动自检** | ① **启动期**：白名单为空 ⇒ 打 **ERROR**（模块加载时执行一次）；② **运行期**：**首次**收到带 `cf-connecting-ip` / `x-real-ip` / `x-forwarded-for` 的请求而白名单仍为空 ⇒ 打**一次** ERROR，文案含「限频将对**全站**生效（60 次/60 秒/全站），遥测会静默丢失」 |
| **D-01 · 部署侧** | ★ **登记为部署项，尚未设置**（见 8.4）—— 设变量属改运行环境，**待总调度授权** |
| **D-02（P3）** 守卫固化 | **REG-6 已并入正式判据件** `_ad_landingext_verify.mjs`：枚举模板 6 处 `track()` 的 **14 个 (type,target)**，断言 **REG-6a 键数=14** ＋ **REG-6b 落入 `other` 的键数=0** |
| **D-03（P3）** IP 格式校验 | 白名单逐条校验：**非 IP 字面量**、或 **`0.0.0.0` / `::` 通配** ⇒ 打 ERROR 并**忽略该条**（防误填把伪造面重新打开）；同时把 `::ffff:127.0.0.1` 归一化为 `127.0.0.1` 再比对 |

### 8.3 自证读数（3001 隔离实例实测）

**D-01① 启动期 ERROR**（实测已打出）
```
[19:13:04.617] [system] ERROR landing-ext：LANDING_TRUSTED_PROXIES 为空 ⇒ /api/track 的限频按【socket 地址】计；
  若 Node 在反向代理（nginx / _gva_proxy.cjs）之后，socket 恒为 127.0.0.1 ⇒ 限频将对**全站**生效…
```

**D-01② 运行期 ERROR**（发一个带 `X-Forwarded-For: 203.0.113.9` 的请求后，实测已打出）
```
[19:15:10.624] [api] ERROR landing-ext：收到带 X-Forwarded-For 类头的请求，但 LANDING_TRUSTED_PROXIES 为空
  ⇒ 限频将对全站生效（60 次/60 秒/全站），遥测会静默丢失 {"socket":"127.0.0.1","xff":"203.0.113.9"}
```

**★ D-02 验收：把白名单改窄 ⇒ 断言必红（已实测演示）**
把 `TRACK_SHARE_CHANNELS` 临时改为 `['whatsapp','facebook']`（去掉 `telegram`）后重启：
```
FAIL  REG-6b  落入 `other` 的键数应 = 0  | other 键 = evt:click:other
（同轮 REG-6a 仍 PASS —— 因为塌进 other 的键仍是"一种"，**这正是 REG-6b 不可省的原因**）
=== 汇总 7/8 PASS ===   失败：REG-6b
```
**还原后复跑 ⇒ 8/8 PASS**（`share_telegram` 回到白名单，other=无）

**verify 全绿（8/8）**：A1 · A2 · A2b · A3 · A4 · A5 · **REG-6a（14 种）** · **REG-6b（other=0）**
**delta 4/4**：REG-6 · AD-01（150 次伪造 ⇒ 键种数 **1**、无 `evil_` 键）· AD-02（伪造 IP 轮换 80 次 ⇒ **仍 429×20**）· A1–A5 回归

脚本：`_ad_landingext_verify.mjs`（含固化后的 REG-6） · `_ad_landingext_delta.mjs`

### 8.4 ★ 部署项（**尚未设置 —— 待总调度授权**）

| 项 | 内容 |
|---|---|
| **变量** | `LANDING_TRUSTED_PROXIES=127.0.0.1` |
| **写到哪** | 启动 3000 的那份 env（**树外**）：`X:\_integration\_fix_work\_i1c3_ws\.env` |
| **为什么** | 无论 nginx 还是 `_gva_proxy.cjs`，Node 都在**本地代理之后** ⇒ socket 恒为 `127.0.0.1` ⇒ **不设它则全站共用一个限频桶**（60 次/60 秒/全站） |
| **为何我未设** | 改的是**运行环境**，按总调度要求**须其授权后**再动 |
| **设定后应验** | 重启 3000 ⇒ 日志里**不再**出现 8.3 那两条 ERROR；且「带不同 `X-Forwarded-For` 的请求」应落在**不同**限频桶 |

---
*本件由广告线产出 · ⌛2026-10-03 · **Revision 3 工作区未提交***


