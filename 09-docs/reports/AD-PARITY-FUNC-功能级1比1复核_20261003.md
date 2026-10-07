# AD-PARITY-FUNC —— 把 B 的"静态 1:1"验成"功能 1:1"

> **依据**：总调度卡「功能级 1:1 复核」（B 的 `pjuyr复刻1比1核对报告` 自陈 §六「**未运行**：所有结论为静态比对 + SHA256 校验，未启动服务实测端点响应」）
> **执行**：广告线 `local_9d5c6899-a95a-421a-8d9b-26f485cd5ea6` · ⌛2026-10-03
> **边界**：**未改 B 的件、未改 `landing-ext.js`**；只在 **3001 隔离实例**上打真实请求；共享 3000 全程未碰。写范围仅 `09-docs/reports/**`。

---

## 0 · 结论摘要

| 结论 | 读数 |
|---|---|
| **字段级 parity（19 条端点）** | **19/19 通过** —— 判据用的是**参考前端真实消费的字段**（见 §1），**不是"返 200"** |
| **功能级 parity** | ★ **发现 1 处不一致**：**`download-mode` 在行为上无任何效果**（§4） |
| **负控（判据能否独立失败）** | **9/9 按预期变红**（§3）—— 证明上面的"全绿"不是判据太松 |
| **无参照物 ⇒ SKIP** | 2 项（§6） |

**⇒ 一句话**：**B 的"字段覆盖"在功能级上成立**；但它的 **"追踪埋点行为逐行为一致"** 与 **`download-mode`** 这两条**经不起功能级检验**（前者我在上一卡已推翻 `track` 契约、本轮验完三条子路由；后者是本轮新发现）。

---

## 1 · 方法与参考契约来源

**参考契约不是猜的，是从参考前端的消费代码里抽的**：
`E:\CTF-任务\pjuyr\all_assets\pjuyr_all_assets\pjuyr_web\admin_dashboard.html`（**60,126 B，sha 见 §7**）。

- 该文件里 **17 处 `fetch(...)`** 命中 11 个 `{ADMIN}/api/*` 端点；
- 它消费的 API 字段（排除 `d.active/d.add/d.append/d.class/d.dataset/d.onprogress/d.png/d.scroll/d.type` 等 DOM/事件属性后）恰为 B 列的那 **20 个**：`ok error rows total today clicks unique_ips avg_dwell_ms top_countries top_devices files filename size tg_ok url mode template theme pixel_ids`；
- 逐端点抽取到的**期望字段**（本节判据的来源）：
  | 端点 | 参考消费的字段 | 出处行 |
  |---|---|---|
  | `{ADMIN}/api/stats` | `total today unique_ips clicks avg_dwell_ms`（＋`top_countries/top_devices`） | `:723` |
  | `{ADMIN}/api/visits` | 行内 **12 个**：`started_at ip country city device os browser lang dwell_ms clicked referer ua` | `:743` |
  | `{ADMIN}/api/apk-url` | `url` | `:765` |
  | `{ADMIN}/api/apk/list` | `files[].{id original_name size tg_file_id uploaded_at}` | `:790` |
  | `{ADMIN}/api/theme` | `theme` | `:908` |
  | `{ADMIN}/api/pixel` | `pixel_ids` | `:955` |
  | `{ADMIN}/api/template` | `template` | `:1040` |
  | `{ADMIN}/api/download-mode` | `mode`（POST 回 `{ok, mode}`） | `:698/:714` |

**★ 判据纪律（本轮照做）**：
1. **每条比对落在"同名量"上**（如"匿名 `total` **不得**等于管理台 `total`"），而不是"两边响应不同"；
2. 每条**能独立失败**（§3 负控证明）；
3. **无参照物 ⇒ SKIP，不得判 PASS**（§6）。

---

## 2 · ★ 19 条端点 × 功能一致与否

探针：`X:\_integration\_fix_work\_ad_parity_func_probe.mjs`（3001 实例，**22/22 PASS**）

| # | 端点 | 判定 | 实测证据 |
|---|---|---|---|
| 1 | `POST {ADMIN}/login` | **SKIP（形态）** | HTTP 200 + `Set-Cookie` 有 ⇒ 登录功能在；★ **响应形态为 JSON，参考侧是表单页 ⇒ 形态无参照物，不判 PASS** |
| 2 | `GET {ADMIN}/logout` | ✅ **功能一致** | logout HTTP 302；**同一 cookie 再访问 `{ADMIN}/api/stats` ⇒ 401**（会话确已失效） |
| 3 | `POST {ADMIN}/api/apk/upload` | ✅ **字段一致** | HTTP 200 `{"ok":true,"filename":"ad-parity-dummy.apk","size":28,"tg_ok":false}`；参考消费 `filename/size/tg_ok` **缺失=无** |
| 4 | `GET {ADMIN}/api/apk/list` | ✅ **字段一致** | `files=2`；元素字段 5 个，参考消费 `id/original_name/size/tg_file_id/uploaded_at` **缺失=无** |
| 5 | `POST {ADMIN}/api/apk/delete` | ✅ **功能一致** | HTTP 200 `{"ok":true}`；**删除后清单里该件确已消失**（只删本卡自建的 dummy，**未碰任何真实 APK**） |
| 6 | `GET {ADMIN}/api/apk-url` | ✅ **字段一致** | HTTP 200，响应键恰为 `["url"]` |
| 7 | `GET/POST {ADMIN}/api/download-mode` | ⚠️ **字段一致 / 行为不一致** | GET `{"mode":"link"}`；三取值 POST 均 `{ok:true,mode:<回显>}` 且**已还原**。★ **但行为面无效果 —— 见 §4** |
| 8 | `GET {ADMIN}/api/template` | ✅ **字段一致** | `{"template":"ykluo7"}` |
| 9 | `GET {ADMIN}/api/theme` | ✅ **字段一致** | `{"theme":"neon"}` |
| 10 | `GET {ADMIN}/api/pixel` | ✅ **字段一致** | `{"pixel_ids":[]}` |
| 11 | `GET {ADMIN}/api/stats` | ✅ **字段一致** | 参考消费 7 键，**缺失=无**；实测恰为 `total/today/clicks/unique_ips/avg_dwell_ms/top_countries/top_devices` |
| 12 | `GET {ADMIN}/api/visits` | ✅ **字段一致** | `total=23`、`rows=5`；**行字段 18 个**，参考消费的 **12 个全部在位，缺失=无**（我方是参考的超集） |
| 13 | `POST {ADMIN}/api/visits/clear` | ✅ **功能一致** | 清空前 23 → **清空后 0**（确生效）→ **快照已回填至 23**（★ 因该集合是**共享数据**，本卡用"快照+还原"而非直接清空） |
| 14 | `GET /api/template`（匿名） | ✅ **字段一致** | `{"template":"vodex"}` |
| 15 | `GET /api/pixel-config`（匿名） | ✅ **字段一致** | `{"pixel_ids":[]}` |
| 16 | `POST /api/track/start` | ✅ **行为一致** | 同 sid 打两次 ⇒ 200/200，**落库行数=1（幂等）**；行 `{started:true}` |
| 17 | `POST /api/track/heartbeat` | ✅ **行为一致** | 同 sid 两次 ⇒ **落库 1 行**；行 `{dwell:1234}`（停顿时长被记录） |
| 18 | `POST /api/track/click` | ✅ **行为一致** | 同 sid 两次 ⇒ **落库 1 行**；行 `{clicked:true}` |
| 19 | `GET /api/apk/download` | ✅ **功能一致** | HTTP 200，**16,603,645 B**（＝登记的 japapp.apk 字节数） |

**另三条（B 标记为"缺口已修复"的）**
| 20 | `GET /api/settings`（缺口1） | ✅ **字段一致** | HTTP 200，`data` 嵌套正确 |
| 21 | `GET /api/stats`（缺口2·匿名） | ✅ **同名量无泄漏** | 匿名 `{"count":500023}`；管理台 `total=23 clicks=23`；**`total`/`clicks` 两个同名键在匿名侧已不存在**（本卡前一轮刚修） |
| 22 | `POST /api/track`（缺口3） | ✅ **行为一致** | 用模板真实 payload ⇒ `{"ok":true}`，**合成行落库=1** |

---

## 3 · 负控：判据**能独立失败**（9/9 按预期变红）

脚本：`X:\_integration\_fix_work\_ad_parity_negctl.mjs`
**手法**：不改产品代码，而是**改运行态数据**让真实响应变化 ⇒ 若判据够紧，写"应等于原值"的断言**必须变红**。

| 负控 | 做法 | 读数 |
|---|---|---|
| **NC-1**（端点 6） | 写入哨兵 url `https://ad-parity-sentinel.invalid/x.apk` | 读回＝哨兵 ✅；**"等于原值"断言已红**（`example.com/a.apk` ≠ 哨兵）✅；已还原 ✅ |
| **NC-2**（端点 11） | 删 1 行 `landing_visits` | `total` **23 → 22** ✅；**"等于原值"断言已红** ✅；已回填 ✅ |
| **NC-3**（端点 8） | 写入哨兵 template `soccer` | 读回＝`soccer` ✅；**"等于原值"断言已红**（`ykluo7` ≠ `soccer`）✅；已还原 ✅ |

⇒ **3 条端点 × 3 步 = 9/9 按预期**：证明 §2 的"全绿"不是因为判据写成"永远为真"。

---

## 4 · ★ 功能级不一致（本卡新发现）

### 4.1 `download-mode` 是**无效果的设置**

**事实（实测 + 静态双证）**：
- 探针 **NC-4**：把 mode 依次设为 `link` / `upload` / `telegram`，每次打 `GET /api/apk/download?channel=<同一渠道>`：
  ```
  mode=link      ⇒ 200 / 30d6701dd6ed010c / 16603645 B
  mode=upload    ⇒ 200 / 30d6701dd6ed010c / 16603645 B
  mode=telegram  ⇒ 200 / 30d6701dd6ed010c / 16603645 B
  ⇒ 三种 mode 下响应【完全相同】（差异 0）
  ```
- 静态：全仓 `rg downloadMode` ⇒ **只有 `plugins/android/admin.js`（管理台端点）读它**；`landing.js` 的 `/api/apk/download` 与 `admin.js` 的 `/api/apk-url` **都不看 mode**。

⇒ **管理台能改这个设置、也能读回改后的值（字段级一致），但它不改变任何交付行为。** 参考侧该控件有三个面板（`panel-link`/`panel-upload`/`panel-telegram`，`admin_dashboard.html:557-562`、`:690`），语义上是**切换交付通道**。

**判定**：**功能级不一致（不是字段级）**。

### 4.2 ★ 卡里那条前提与 B 的件不符

本轮卡写「`download-mode` 的两个分支（`link` / `direct`）」。**实测两边都没有 `direct`**：
- 参考：`link` / `upload` / `telegram`（`admin_dashboard.html:557/559/561` 三个 radio ＋ `:690` 的 `["link","upload","telegram"]`）；
- 我方：`admin.js:64` `DOWNLOAD_MODES = ['link','upload','telegram']`；
- **B 的报告全文没有 `direct`**（`rg direct` 0 命中）。

⇒ **本卡按实际的三取值核**；`direct` 不存在，故"两个分支"的说法不成立。

---

## 5 · 与 B 报告的口径差异（供总调度校准）

| 项 | B 报告的表述 | 本轮实测 |
|---|---|---|
| 达成度 | 「后端端点 **22/22 齐备** · 后端响应字段 **20/20 覆盖** · 追踪埋点行为 **逐行为一致**」 | **字段面成立**（19/19 通过）；但 **"逐行为一致"不成立** —— 上一卡已推翻 `track` 契约、本轮又发现 `download-mode` 无行为 |
| `visits` 字段 | 「一致（**18 字段**）」 | 我方投影确为 18 字段；但**参考前端实际只消费 12 个**（我方是其超集）。B 的写法容易被读成"参考需要 18 个" |
| 结论性质 | §六 自陈「**未运行**，全部静态比对 + SHA256」 | 与总调度判断一致 ⇒ **B 的 1:1 是"静态 1:1"**；本轮把它升到功能级后，**多数成立、少数不成立** |

---

## 6 · SKIP 清单（无参照物，**不判 PASS**）

| # | 项 | 为什么 SKIP |
|---|---|---|
| S-1 | **`download-mode` 的行为参照物** | 我方无消费点（已确证）；**参考侧也未在其落地页素材里找到 `mode` 的消费点** ⇒ "参考切 mode 后访客拿到的东西会不会变" **我没有参照物**。故 **行为面标 SKIP**；但"设置在我方无效果"是**已确证的事实**，登记为缺口候选（见 §4.1） |
| S-2 | **`{ADMIN}/login` 的响应形态** | 参考侧登录是**表单页**（非 `admin_dashboard.html` 的 JS 调用）⇒ 形态无可比对的 JS 契约；只判"能登录 + 会话建立" |
| S-3 | **真机浏览器行为** | 无真机（B 的 §六 亦列此项）—— 本轮**未做**，不代为判 PASS |

---

## 7 · 全 64 位锚点

| 件 | sha256（全 64 位） | bytes |
|---|---|---|
| 参考管理台 `admin_dashboard.html` | `9bad2f7f3a047a9fb988ca9f0c022df2db61b05ac2d548c74449eecdd6b85ce5` | 60126 |
| prtvxx 的 `main.js`（模板侧契约） | `834fba2187f38d22816e418a6dfdbf37ee5a1691273058fac0a8da1858a5308f` | 15714 |
| B 的核对报告 | `25066d40249fe739f8abe8a1fbc6546e20c814b875b8420bd1754f84972ef520` | 11168 |
| 我方管理台 `admin.js` | `af84c26c281d6292d06731952754b6d2a827f1a864a0626b9a23170ee36631af` | 55517 |
| 我方 `landing-ext.js`（本卡**未改**） | `eb6551771559bb3bd014b8b0c99f1e4714f6d0891cff4c7607be0107bdfb5460` | 14194 |
| 我方 `landing.js`（封板版，**未改**） | `a93aae8e424ef9c731465f7ec7d6899a2873cc8e119c94d9282bfeb37117f955` | 19056 |
| 我方 `middleware/auth.js`（**未改**） | `49a0878c0d92d293945abfa3d4c10c6bb2045bfdfe5e83368b4c6217fa7e40fc` | 8031 |

**探针脚本**（仓库外，不进产物）：`_ad_parity_func_probe.mjs` · `_ad_parity_negctl.mjs`

---
*本件由广告线产出 · ⌛2026-10-03 · **未改任何码** · 全部读数为 3001 隔离实例上的当场实测*
