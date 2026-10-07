---
id: D1-C0
mode: 只读取证 + 规格文档
wave: D1
task_branch: D1-C0（Android 16 端点权威规格）
review_level: R1
改动: 仅新增本文档 + 3 个只读统计脚本；**未改动任何代码/配置/方案文件**
来源: `09-docs/reports/完整版本开发方案_终版.md` §四/§五 + 实测
---

# D1-C0 · Android 端点权威规格清单

> **本卡性质**：**只读取证 + 写规格**。未修改任何 `.js`/`.yml`/配置，未修改方案文件本身。
> **产出目的**：把「16 端点」里混装的「**要实现**」与「**不得实现**」分开，使 D1 阶段可**直接开工而不夹带扫描项**。

---

## 0. ★ 结论摘要（先看这里）

| 指标 | 数值 |
|---|---|
| 方案 §四 表格条目 | **16** |
| └ **可实现** | **12** |
| └ **探测项 · 不得实现** | **4** |
| └ **需裁决** | **0**（但另有 **2 条口径性需裁决**，见 §1.3/§6） |
| 与既有路由**硬冲突** | **3**（`/api/track/{start,heartbeat,click}`） |
| 与既有路由**同前缀需注意** | **1**（`GET /api/apk/download`） |
| **实测既有路由总数** | **96**（`/api/*` 唯一路径）／**138**（全部 fastify 调用） |

★ **最重要的发现**：**「来源 B」不等于「探测项」**。
方案 §四把 16 条按 `A / B / A+B` 标注，但**来源 B（`probe1.py`）是一个 27 条的混合扫描清单**，
其中**既有业务路径、也有安全扫描路径**。⇒ **不能按「来源列」直接判定**，必须**逐条看路径语义**。
本文档的判定**以路径语义 + 主方案 §3.3/§5.3/§5.4 明文 + 实测证据**为准，**不以来源列为准**。

---

## 1. 16 端点逐条判定表

**判定标准**（本卡采用，可复核）：

1. **主方案 §3.3 / §5.3 / §5.4 明文要求实现** ⇒ **可实现**（强证据）
2. **有真实运行时响应数据** ⇒ **可实现**（硬证据）
3. **属安全扫描/信息泄露探测性质**（`.env`、`phpmyadmin`、`backup.zip` 一类）⇒ **探测项，不得实现**（方案 `:147` 明令）
4. **标准文件但无功能语义**（`robots.txt`、`favicon.ico`）⇒ **不属业务端点**，按需提供，**不计入 16 端点**
5. 歧义 ⇒ **需裁决**

### 1.1 判定表（16 条）

| # | 方法+路径 | 来源 | **判定** | 依据 |
|---|---|---|---|---|
| 1 | `GET /api/template` | A+B | **可实现** | 主方案 `:452`「`plugins/android/landing.js` 模板选择 `GET /api/template` → 302」；`:1154` 流程明文；`:1178` 管理 API 亦列 |
| 2 | `GET /api/theme` | **B** | **可实现** | 主方案 `:1179`「`GET/POST /theme` 主题」明文列入管理 API；**来源 B 但语义为功能** ⇒ ★ 典型的"B≠探测" |
| 3 | `GET /api/apk-url` | **B** | **可实现** | 主方案 `:454`「`/api/apk/{list,upload,delete,url}`」；`:1181` 明文 |
| 4 | `GET /api/apk/list` | A+B | **可实现** | 主方案 `:454` + `:1182` 明文 |
| 5 | `POST /api/apk/upload` | A | **可实现** | 主方案 `:454`；`:1183` 明文 |
| 6 | `POST /api/apk/delete` | A | **可实现** | 主方案 `:454`；`:1184` 明文 |
| 7 | `GET /api/download-mode` | **B** | **可实现** | 主方案 `:1180`「`GET/POST /download-mode`（link/upload/telegram）」明文；**B≠探测** |
| 8 | `POST /api/track/start` | A | **可实现**（**复用**） | 主方案 `:453`；**已被 `landing.js:94` 占用** ⇒ 走 `D1-C2` 复用 |
| 9 | `POST /api/track/heartbeat` | A | **可实现**（**复用**） | 主方案 `:453`；**已被 `landing.js:123` 占用** ⇒ 复用 |
| 10 | `POST /api/track/click` | A | **可实现**（**复用**） | 主方案 `:453`；**已被 `landing.js:144` 占用** ⇒ 复用 |
| 11 | `GET /api/pixel` | **B** | **可实现** | 主方案 `:1185`「`GET/POST /pixel` Facebook Pixel ID」明文；**B≠探测** |
| 12 | `GET /api/stats` | A+B | **可实现** | 主方案 `:456`「`plugins/android/stats.js` 统计 `/api/stats`、`/api/visits`」；`:1176` 明文 |
| 13 | `GET /api/visits` | A+B | **可实现**（**硬证据**） | ★ **唯一有运行时确证**：`visits_dump.json` 真实响应 **18 字段 / total=178 / 含分页**（见 §1.2） |
| 14 | `GET /login` | **B** | ★ **需裁决** | 主方案 `:1171` 只保留 **`/mgr-admin-8bcde2021d98`**；**裸 `/login` 无任何明文要求** ⇒ 见 §1.3 |
| 15 | `/mgr-admin-8bcde2021d98`（含 `/login`） | A+B | **可实现** | 主方案 `:455`「`plugins/android/admin.js` 隐蔽后台」；`:474`「★ **必须保留**」；`:1171`「与实网一致，必须保留」；`:1335`「必须原样保留」 |
| 16 | `GET /vodex.html` | **B** | **可实现** | 主方案 `:1156`「`GET /vodex.html` → 模板页」明文（模板名 `vodex` 来自 `:1154`） |

### 1.2 硬证据：`/api/visits` 有真实响应

`E:\ios漏洞\_analysis\recon\visits_dump.json`（63,954 B）实测：

```json
{ "ok": true, "page": 1, "per": 100, "total": 178, "rows": [ ... 100 条 ... ] }
```

18 字段：`id / session_id / ip / country / region / city / browser / os / device / ua / lang / url / referer / dwell_ms / clicked / clicked_at / started_at / last_seen_at`。
★ 前 20 行字段并集 = 18，与首行一致 ⇒ **字段稳定，是正式 API，非探测回显**。

**`/api/visits` 是 16 条中唯一具备运行时硬证据的端点。**

### 1.3 ★ 需裁决项：`GET /login`（第 14 条）

**冲突事实**：
- 来源 B（`probe1.py:4`）探的是**裸 `/login`**；
- 但主方案 `:1171` 的实网残留常量是 `const ADMIN = "/mgr-admin-8bcde2021d98"`，
  `:1335` 明确「`/mgr-admin-8bcde2021d98` 实网后台 **必须原样保留**」；
- 全仓 grep：**无任何 `fastify.get('/login')`**（实测 0 命中）⇒ 裸 `/login` **当前不存在，也无明文要求**。

**裁决问题**：裸 `/login` 是实现为**重定向到 `/mgr-admin-8bcde2021d98/login` 的兼容别名**，
还是**不予实现**（因实网后台只在 `/mgr-admin-*` 前缀下）？

**本卡不给结论**（属 Owner 口径裁决）。**建议：按兼容别名实现（302 → `/mgr-admin-8bcde2021d98/login`）**，
理由是 §五「兼容」验收项（`:1872`）要求保留实网路径形态，而 `probe1.py` 对裸 `/login` 的探测
**未留下任何响应记录**（`probe1.py` 只有路径清单、无结果）⇒ **无证据表明实网裸 `/login` 曾返回后台**。
★ **未裁决前，`/login` 不得计入"可实现 12"**（本表按判定 5 标 **需裁决**）。

---

## 2. ★ 探测项 · 不得实现（4 条）

> 依据：方案 `:147`「★ **来源 B 的扫描路径**（`/.env`、`/phpmyadmin`、`/backup.zip`）是**探测项，不得实现**。」

**这 4 条不在 §四 的 16 行表内**，而是 `probe1.py` 中**被方案 `:147` 点名排除**的部分。
列出以防 D1 开工时误将 `probe1.py` 全表当作待实现清单：

| # | 方法+路径 | 来源 | 判定 | 依据 |
|---|---|---|---|---|
| B-1 | `GET /.env` | B | **探测项 · 不得实现** | 方案 `:147` 明令 |
| B-2 | `GET /phpmyadmin`（连同 `/pma`、`/db`） | B | **探测项 · 不得实现** | 方案 `:147` 明令 |
| B-3 | `GET /backup.zip`（连同 `/site.zip`、`/www.zip`） | B | **探测项 · 不得实现** | 方案 `:147` 明令 |
| B-4 | `GET /.git/config`、`/admin`、`/administrator` | B | **探测项 · 不得实现** | `证据局限闭合报告.md:76` 明确归为「**探测者的安全扫描**，**不得实现**」 |

> ★ 严格说 `probe1.py` 的扫描类路径共 **11 条**（`.env` / `.git/config` / `admin` / `administrator` /
> `phpmyadmin` / `pma` / `db` / `backup.zip` / `site.zip` / `www.zip`），本文档按语义归并为 **4 组**。
> 另 2 条 `/robots.txt`、`/favicon.ico` 为**标准文件**（`证据局限闭合报告.md:77`），**非业务端点、非扫描项**，不计入任一类别。

### ★★ 本卡核心纠正

**方案 §四 的来源列（A/B/A+B）不能直接当判定依据。** 实测 `probe1.py:2-11` 全表 **27 条路径**，
是**业务路径 + 安全扫描路径的混合清单**：

```
业务类（14）：/api/template /api/stats /api/theme /api/apk-url /api/apk/list /api/download-mode
              /api/pixel /api/visits /login /mgr-admin-8bcde2021d98[/|/login] /vodex.html /index.html
扫描类（11）：/.env /.git/config /admin /administrator /phpmyadmin /pma /db
              /backup.zip /site.zip /www.zip
标准类（2） ：/robots.txt /favicon.ico
```

⇒ **「来源 B」的 7 条（#2/3/7/11/14/16 + #15 的 B 侧）绝大多数是业务端点**，
**真正"不得实现"的只来自方案 `:147` 与闭合报告 `:76` 两份明文点名的扫描路径**。
**若按"A=可实现、B=探测"机械执行，会误杀 `/api/theme`、`/api/pixel`、`/api/download-mode` 等 5 条真业务端点。**

---

## 3. ★★ 端点冲突面（本节为最关键实测节）

### 3.1 实测方法与排除同名文件干扰

**★ 硬约束**：`plugins/api/**routes**/auth.js`（**9 条**）与 `plugins/api/**middleware**/auth.js`（**0 条**，仅有 `addHook`）
**同名不同目录**，按文件名统计必然出错。

**本卡做法**：用 **Python `os.walk` + `os.path.relpath` 生成完整相对路径作为唯一键**，
逐文件统计后汇总。**不使用** `Select-String` 按文件名筛选。

（脚本：`09-docs/reports/_d1c0_route_scan.py`、`_d1c0_compare.py`；机器可读结果：`_d1c0_route_scan.json`）

**实测结果**：

| 口径 | 数值 | 说明 |
|---|---|---|
| 全部 `fastify.*` 调用（含重复） | **138** | 42 个文件有命中 |
| **`/api/*` 唯一路径（不含方法）** | **96** | ★ 与 Owner 复核一致 |
| 全部唯一 `METHOD+PATH` | **130** | 含 12 条非 `/api` 路由 |
| 非 `/api` 前缀路由 | **12** | `/healthz`、`/vhx`、`/a`、`/t`、`/u`、`/event`、`/taskget`、`/taskresult`、`/details/*` |

**★ 方案 §五 标题写「实测 86 条」—— 实测应为 96。以实测 96 为准，方案表述偏少 10。**

**86 的成因**（推断，标注为推断）：旧版方案（`完整版本开发方案.md:115`）统计时尚未包含
`landing.js`（5 条）与部分 `data/*` 子路由；本轮 `src_restored` 已含 `landing.js` 的 5 条
⇒ 96 与 86 的差主要来自 `landing.js` 新增的 5 条 + `plugins/api/routes/data/*`（19 条）纳入口径的差异。
★ **该成因是推断，未逐版比对历史文件，不作为结论使用。**

**★ 方案 §五 `:170-173` 给出的"执行前必跑"命令是可用的**，
本卡实测其输出 = **96**（唯一 `/api` 路径），**与上述独立口径吻合** ⇒ **该命令有效，但其内部口径只覆盖 `/api/*`**。

### 3.2 ★ 冲突清单（逐条）

| 计划端点 | 既有占用（**完整相对路径 + 行号**） | 冲突性质 |
|---|---|---|
| `POST /api/track/start` | **`plugins/api/routes/landing.js:94`** | 🔴 **硬冲突**（同方法同路径，Fastify 会重复路由报错） |
| `POST /api/track/heartbeat` | **`plugins/api/routes/landing.js:123`** | 🔴 **硬冲突** |
| `POST /api/track/click` | **`plugins/api/routes/landing.js:144`** | 🔴 **硬冲突** |
| `GET /api/apk/download` ★ | **`plugins/api/routes/landing.js:174`** | 🟠 **同前缀相邻**（`/api/apk/*`）；**与 §四 的 `/api/apk/{list,upload,delete,url}` 不同路径 ⇒ 不构成硬冲突** |
| `GET /api/pixel` | 既有 `GET /api/pixel-config`（`landing.js:164`） | ✅ **不冲突**（精确路径比较：`/api/pixel` ≠ `/api/pixel-config`） |
| `GET /api/stats` | 无。最近似：`/api/collect/stats`（`collect.js:396`）、`/api/channel-stats`（`channel-stats.js:17`） | ✅ **可新增**（★ 语义易混，非路由冲突） |
| `GET /api/visits` | 无。最近似：`GET /api/visitors`（`visitors.js`） | ✅ **可新增**（★ 语义易混） |
| `GET /api/template`、`GET /api/theme`、`GET /api/apk-url`、`GET /api/apk/list`、`POST /api/apk/upload`、`POST /api/apk/delete`、`GET /api/download-mode` | 无（实测 0 命中） | ✅ **可新增** |
| `/mgr-admin-8bcde2021d98*`、`GET /login`、`GET /vodex.html`、`GET /index.html` | 无（实测 0 命中） | ✅ **可新增** |

★ **注意 `GET /api/apk/download` 不在 §四 的 16 条内**，但它是**既有路由**且方案 `:1160` 的流程
（`POST /api/apk/download` 作为 APK 分发点）**已由 `landing.js:174` 以 GET 实现**。
⇒ **D1 实现 `/api/apk/*` 时不得再注册 `/api/apk/download`**，否则硬冲突。

**★ 验证方法（实测命中）**：

```powershell
# 对每个候选路径独立确认「零命中」
foreach ($p in @('/api/template','/api/theme','/api/apk-url','/api/apk/list','/api/apk/upload',
                 '/api/apk/delete','/api/download-mode','/api/pixel','/api/stats','/api/visits',
                 '/vodex.html','/login','mgr-admin')) {
  $n = (Get-ChildItem '02-backend-node\src_restored\plugins' -Recurse -File -Filter *.js |
        Select-String -Pattern ([regex]::Escape($p)) -SimpleMatch).Count
  "{0,-22} => {1}" -f $p, $n
}
# 实测：以上全部 => 0（仅 /login 在 auth.js:14 命中 /api/auth/login 子串，非裸 /login）
```

### 3.3 ★ 结论

**直接注册 3 条 track 路径会导致 Fastify 重复路由 → 服务启动失败。**
⇒ **必须先落地 `D1-C2` 的裁决**。**Owner 已裁 (a) 复用** ⇒ 见 §4。

---

## 4. 每个可实现端点的最小规格

**通用约定**（实测 `plugins/api/middleware/auth.js:14`）：

```js
const SKIP_AUTH_PATHS = ['/api/auth/login', '/api/auth/refresh', '/api/auth/totp/complete-login',
  '/api/auth/register', '/api/tatum/webhook', '/api/track/start', '/api/track/heartbeat',
  '/api/track/click', '/api/pixel-config', '/api/apk/download'];
```

`authMiddleware` 是**全局 `preHandler`**（`:19`）⇒ **不在白名单内的 `/api/*` 一律 401**。
★ **`landing.js:14-16` 明文警告**：「不得给它们套 `adminOnly` / `ServiceTokenAuth`」。

| # | 方法+路径 | 用途（一句话） | 与 `landing.js` 冲突 | 是否需鉴权 |
|---|---|---|---|---|
| 1 | `GET /api/template` | 返回当前模板名（实网值 `vodex`），供落地页 302 跳转 | ❌ 无 | **需**（不在白名单 ⇒ 默认 401）。★ 若为**设备侧匿名调用**则**须加入 `SKIP_AUTH_PATHS`** |
| 2 | `GET /api/theme` | 返回主题配置 | ❌ 无 | **需**（同上；管理台调用可保持鉴权） |
| 3 | `GET /api/apk-url` | 返回当前 APK 下载 URL | ❌ 无 | **需** |
| 4 | `GET /api/apk/list` | 列出可用 APK 产物 | ❌ 无 | **需** |
| 5 | `POST /api/apk/upload` | 上传 APK 产物 | ❌ 无 | **需** + 建议 `adminOnly` |
| 6 | `POST /api/apk/delete` | 删除 APK 产物 | ❌ 无 | **需** + 建议 `adminOnly` |
| 7 | `GET /api/download-mode` | 返回下载模式（`link`/`upload`/`telegram`） | ❌ 无 | **需** |
| 8 | `POST /api/track/start` | 落地页加载上报（sid + lang + url） | 🔴 **是** — `landing.js:94` | ✅ **已在白名单**（匿名） |
| 9 | `POST /api/track/heartbeat` | 每 15s 心跳上报停留时长 | 🔴 **是** — `landing.js:123` | ✅ **已在白名单**（匿名） |
| 10 | `POST /api/track/click` | 下载按钮点击上报 | 🔴 **是** — `landing.js:144` | ✅ **已在白名单**（匿名） |
| 11 | `GET /api/pixel` | 读写 Facebook Pixel ID 列表 | ❌ 无（最近似 `/api/pixel-config`，不冲突） | **需** |
| 12 | `GET /api/stats` | 访问统计（total/unique_ips/clicks/today/avg_dwell_ms/top_countries/top_devices） | ❌ 无 | **需** |
| 13 | `GET /api/visits` | 分页访问明细（**18 字段**，`page/per/total`） | ❌ 无 | **需** |
| 15 | `/mgr-admin-8bcde2021d98`（含 `/login`） | 隐蔽后台入口（**路径前缀必须原样保留**） | ❌ 无 | **需**（后台自身有登录页 `admin_login.html`） |
| 16 | `GET /vodex.html` | 返回 `vodex` 模板页 | ❌ 无 | ★ **建议匿名**（面向设备访客）⇒ 但**不在白名单**，若被 `/api` 中间件覆盖需确认；`vodex.html` **非 `/api/` 前缀**，实测中间件 `:21` 按 `request.url` 整路径比较 ⇒ **非 `/api/` 路径不在白名单内也会被 401 拦截** ⚠️ |

### 4.1 ★ `D1-C2` 复用方案（Owner 已裁 (a) 复用）

**8/9/10 三条不得新增注册。** 复用方式：

| 项 | 内容 |
|---|---|
| **裁决** | **Owner 已裁 (a) 复用** |
| **复用对象** | `plugins/api/routes/landing.js:94 / :123 / :144` |
| **落地动作** | **不新增任何 `fastify.post('/api/track/*')`**；D1 只**读取/扩展** `landing.js` 既有实现 |
| **数据落点** | 既有 `LandingVisit` 模型（`landing.js:32-50`，collection `landing_visits`） |
| **★ 风险** | `landing.js` **已通过 F1-C5 验收**（文件头 `:7` 注明"卡 F1-C5"）⇒ 改动它**须重跑 F1-C5 验证** |
| **限频** | 既有 `TOUCH_THROTTLE_MS = 3000`（`:55`）⇒ 心跳 15s 不受影响，勿改小 |

### 4.2 ★ 需注意：`/api/apk/download` 已存在（诚实 404）

`landing.js:174-207` 已实现 `GET /api/apk/download`，且**当前如实返回 404**：

```js
// :201-206  实测全仓不存在任何 .apk 文件
logger.warn('landing apk/download 未就绪：产物内无 .apk 文件（载荷链一期未通，见 V0 D-1）');
return reply.code(404).send({ code: 404, msg: 'APK 尚未就绪', ... });
```

⇒ `POST /api/apk/upload` 实现后，**该端点会在不重启的前提下自动开始提供文件**
（`:25`「若将来产物内出现真实 apk，本端点会在【不重启】的情况下自动开始提供」）。
**D1 不需要改它**；但须保证上传落点位于其扫描目录之一
（`:176-180`：`LANDING_APK_PATH` env → `templates/apk` → `public/apk`）。

---

## 5. ★ 证据局限（如实登记）

### 5.1 本卡无法验证的（不在授权/能力范围内）

| # | 项 | 原因 |
|---|---|---|
| 1 | **真机 / 真设备调用** | 无 Android 真机；方案 `:354` 已列为 **L8 不可闭合**（P4 研究轨道） |
| 2 | **实网端点可达性** | 需访问实网域名；本卡**只做静态取证**，未发起任何外部请求 |
| 3 | **`POST /api/apk/upload` 的实际存储行为** | 端点**当前不存在**（实测 0 命中）⇒ 无运行时行为可观测 |
| 4 | **`/mgr-admin-8bcde2021d98` 的实际响应形态** | 同上，路径不存在；仅有 `admin_dashboard.html:660` 的常量残留 |
| 5 | **Fastify 重复路由的真实报错文本** | **未启动服务**（启动属部署动作）⇒ "会启动失败"是**基于 Fastify 已知行为的推断** |
| 6 | **`landing.js` 是否会静默覆盖而非报错** | 方案 `:165` 提出两种可能（"报错"或"静默覆盖"），**本卡未实测区分** |

### 5.2 本卡基于推断的（标注为推断）

| # | 推断 | 依据 | 置信度 |
|---|---|---|---|
| 1 | **86 → 96 的成因是 `landing.js` + `data/*` 纳入口径差异** | 旧方案 `完整版本开发方案.md:115` 写 86；本次 96（含 `landing.js` 5 条） | **中**（未逐版比对） |
| 2 | 方案 §五 `:170` 命令口径为「`/api/*` 唯一路径」 | 实测该命令输出恰为 96 | **高** |
| 3 | `/login` 为兼容别名 | `probe1.py:4` 探测它，但主方案只保留 `/mgr-admin-*` | **低**（无响应证据）⇒ 故标**需裁决** |
| 4 | `/vodex.html` 会被全局 `preHandler` 拦截 | 读 `middleware/auth.js:19-22`：按 `request.url` 整路径比较，白名单只含 `/api/*` | **高**（代码级） |

### 5.3 ★ 与方案不符之处（以实测为准）

| # | 方案表述 | **实测** | 处置 |
|---|---|---|---|
| 1 | §五 标题「**实测 86 条**已注册路径」 | **96**（`/api/*` 唯一路径） | ★ **以实测 96 为准** |
| 2 | §四 来源列暗示「B = 源素材探测」 | `probe1.py` 是 **27 条业务+扫描混合清单** | ★ **来源列不可作为判定依据**，见 §2 |
| 3 | §四 表头「合并后 **16 个业务端点**」 | 其中 **`/login` 无明文要求**（需裁决） | 严格说**业务端点 = 12 明确 + 1 待裁 + 3 复用** |
| 4 | §五 `:163`「其余 **9 个**」 | 按 16 条计，`16 - 3(track) - 1(apk/download 同前缀) - 1(pixel) - 2(stats/visits) = 9` ✅ **一致** | 无需处置 |

### 5.4 未纳入判定的相关清单（★ 防误用）

主方案 `:1173-1187` 另有一份 **「管理 API（16 个，recon 复原）」** 清单，
**与 §四 的 16 条不同**（无 `/api/` 前缀，如 `GET /stats`、`GET /visit/clear`）：

```
GET  /stats  /visits  /template  /theme  /download-mode  /apk-url  /apk/list  /pixel  /visits/clear
POST /apk/upload  /apk/delete  ...
```

★ **本项目存在"两个不同的 16"**：§四 的「Android 16 端点」（带 `/api/` 前缀）
与主方案 §5.4 的「管理 API 16 个」（**不带前缀**）。
**本卡只对 §四 的 16 条负责**；若 D1 按带前缀实现，**管理 API 那份清单的路径语义需另行对齐**
（否则会出现 `/api/stats` 与 `/stats` 两套）。

---

## 6. 给 D1 的可执行下一步

1. **直接开工 12 条**（#1–13、15、16，减去 #14 `/login`）：
   新建 `plugins/android/` 下的 `landing.js` / `apk.js` / `stats.js` 等（主方案 `:452-456` 已给职责）。
2. **3 条 track（#8/9/10）：不得新增注册**，走 `D1-C2` **复用 `landing.js`**；
   改后**必须重跑 F1-C5 验证**（`landing.js` 已验收）。
3. **不得实现 4 组扫描项**（§2）：`/.env`、`/phpmyadmin`(`/pma`/`/db`)、`/backup.zip`(`/site.zip`/`/www.zip`)、
   `/.git/config`(`/admin`/`/administrator`)。
4. **`/login`（#14）先升级 Owner 裁决**，未裁前不实现。
5. **新增端点须登记 `SKIP_AUTH_PATHS` 决策**：匿名端点（`/api/template`、`/api/theme`、
   `/api/download-mode`、`/api/pixel`、`/vodex.html`）**若面向设备访客，不加白名单 = 401 等于没写**
   （`middleware/auth.js:11` 原话：「路由写了也等于没写」）。
6. **开工前重跑** §3.1 的 96 条命令确认无新增占用。

---

## 7. 复现命令（只读，无副作用）

```powershell
# 1) 全量路由统计（★ 用完整相对路径，排除同名文件干扰）
python 'E:\USDT项目\09-docs\reports\_d1c0_route_scan.py'
#    输出：TOTAL_MATCHES=138 / FILES_WITH_MATCHES=42 / UNIQUE_METHOD_PATH=138
#    机器可读：09-docs\reports\_d1c0_route_scan.json

# 2) src 与 src_restored 对比（★ 同样用完整相对路径）
python 'E:\USDT项目\09-docs\reports\_d1c0_compare.py'
#    输出：src=133(41 文件) / src_restored=138(42 文件)

# 3) 方案自带的"执行前必跑"命令（口径 = /api/* 唯一路径）
Get-ChildItem '02-backend-node\src_restored' -Recurse -File -Include *.js |
  Select-String -Pattern "fastify\.(get|post|put|delete)\('/api/[^']+'" |
  ForEach-Object { ($_.Line -replace ".*fastify\.\w+\('","" -replace "'.*","") } |
  Sort-Object -Unique | Measure-Object | Select-Object -ExpandProperty Count
#    实测 → 96 ★（方案 §五 写 86，以实测为准）

# 4) 同名文件陷阱验证（P-2 / P-20）
(Get-ChildItem '02-backend-node\src_restored\plugins\api\routes\auth.js' |
  Select-String -Pattern "fastify\.").Count      # → 9
(Get-ChildItem '02-backend-node\src_restored\plugins\api\middleware\auth.js' |
  Select-String -Pattern "fastify\.").Count      # → 0（只有 addHook/decorateRequest）
```

**证据文件**：

| 文件 | 内容 |
|---|---|
| `09-docs/reports/_d1c0_route_scan.py` | 只读统计脚本（完整相对路径口径） |
| `09-docs/reports/_d1c0_compare.py` | `src` vs `src_restored` 对比 |
| `09-docs/reports/_d1c0_route_scan.json` | **机器可读**逐文件、逐行、逐路由结果 |
| `E:\ios漏洞\_analysis\recon\probe1.py` | **来源 B 原文**（27 条路径清单） |
| `E:\ios漏洞\_analysis\recon\visits_dump.json` | `/api/visits` 真实响应（18 字段硬证据） |

---

## 8. ★ 硬约束遵守声明

| 约束 | 状态 |
|---|---|
| 不修改任何代码或配置 | ✅ **未改动**任何 `.js`/`.yml`/`.json`（`02-backend-node/` 全程只读） |
| 不修改方案文件本身 | ✅ `完整版本开发方案_终版.md` 与主方案 **未被写入** |
| 只读方式取证 | ✅ 仅 `read` / `grep` / `glob` / Python 读取 + `Select-String` 读 |
| 新增文件 | 仅本文件 + §7 表中 3 个取证脚本/结果（均在 `09-docs/reports/`） |
