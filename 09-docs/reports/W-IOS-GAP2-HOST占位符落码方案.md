# W-IOS-GAP2 · `[HOST_PLACEHOLDER]` 落码方案（**待复核，未落码**）

> **性质**：方案件。**未改任何代码**。
> **依据**：`总调度1` 裁定⑩ 解冻（⌛2026-10-03）—— 口径 **(C) 只改 `src_restored/` 一处**，扁平副本内容不动。
> **前置**：`W-IOS-GAP-模板层空目录与HOST占位符-取证与处置.md` §2（事实与三条件）。

---

## 一、范围

| 改 | 不改 |
|---|---|
| `02-backend-node/src_restored/plugins/c2/**`（2 个文件） | `02-backend-node/src/app_dist_*`（**内容一字不动**） |
| `09-docs/reports/**`（本件与判据脚本落点） | `05-ios/_templates/**`（上一卡已交） |
| — | B 的移交件、`contracts.md`、`_manifest.sha256` |

---

## 二、逐处改法（file:line）

### 2.1 `src_restored/plugins/c2/routes/config.js`

| # | 位置 | 现状 | 改法 |
|---|---|---|---|
| 1 | `:10-11`（已存在） | `host` 取出并**已用 `Channel.findOne({domains: host})` 白名单校验** | **复用**，不改 |
| 2 | 新增（`:12` 后） | — | `const scheme = (request.headers['x-forwarded-proto'] \|\| 'http').split(',')[0].trim();` |
| 3 | 新增 | — | ★ **(a) 条件**：`const origin = channel ? \`${scheme}://${host}\` : null;` —— **`!channel` 时 `origin` 为 null，绝不用未校验的 Host 拼 URL** |
| 4 | `:31` | `payload_config:${channelCode \|\| 'global'}:${routeKey}` | ★ **(b) 条件**：追加 `:${host}` 一维 ⇒ `payload_config:${channelCode \|\| 'global'}:${routeKey}:${host}`。**保留 `payload_config:` 前缀**（`:29-30` 的 `invalidateConfigCache` 用 `KEYS payload_config:*` 通配） |
| 5 | `:36` | `getConfigJson(channel \|\| undefined, { userAgent: ua })` | 传入 `origin`：`getConfigJson(channel \|\| undefined, { userAgent: ua }, origin)` |
| 6 | `:52` 附近 | `Cache-Control: public, max-age=300, no-transform` | ★ **(c) 条件**：补 `reply.header('Vary', 'Host')` |

★ **3 号改法带来一处行为变更（须复核确认）**：`!channel`（Host 不在任何渠道域名内）时，
- **现状**：仍返回 `entries[]`（URL 是坏字面量）；
- **改后**：`origin = null` ⇒ `getConfigJson` **响亮失败**，返回 `{unsupported:true, reason:'no_channel_for_host'}`。

理由：Host 未过白名单时**任何**基于它的 URL 都不可信；给坏 URL 不如显式 unsupported。
（该分支现状本来就"必然坏"，故不视为功能回退。）

### 2.2 `src_restored/plugins/c2/services/config-builder.js`

| # | 位置 | 现状 | 改法 |
|---|---|---|---|
| 7 | `:11` | `export async function getConfigJson(channel, device)` | 加第三参 `origin` |
| 8 | 函数入口 | — | **fail-loud 守卫**：`channel` 存在而 `origin` 为空/非法 ⇒ `throw`（**绝不产出带占位符或空 origin 的 URL**）；非法即 `!/^https?:\/\/[^/]+$/` |
| 9 | `:34` | `` url: `http://[HOST_PLACEHOLDER]/details/ch/${channel.code}/corepayload.js` `` | → `` url: `${origin}/details/ch/${channel.code}/corepayload.js` `` |
| 10 | `:40` | `` url: `http://[HOST_PLACEHOLDER]/details/${m.name}.js` `` | → `` url: `${origin}/details/${m.name}.js` `` |

★ 8 号守卫对应项目既有纪律「**残留占位符 ⇒ 响亮失败**」（与 `__C2_ENDPOINT__` 的注入口径同源）。

---

## 三、S-2 怎么改（**从"同步闸"改为"分叉探测器"**，按裁定语）

原 S-2「两份实现签名与返回字段一致」**方向错了** —— 扁平副本已被判**非权威**，断言"相同"会把已知分叉报成红。
改为**两条**：

| # | 断言 | 判红条件 | 性质 |
|---|---|---|---|
| **S-2a** | **对 `src_restored/` 单一实现的自洽性**：`getConfigJson` 形参个数 == 3（`channel, device, origin`）**且**返回对象含 `settings` / `chain` / `chainReach` / `core` / `entries` 五键 | 签名或字段集**漂移** | **自洽闸** |
| **S-2b** | ★ **分叉登记性断言**：`KNOWN_DIVERGENCES`（见下）中**每一条已知分叉仍然成立** | 某条分叉**消失**（说明有人同步/删改了扁平副本却未重新裁决）⇒ 报红并提示"需重新裁决" | **分叉探测器** |

**`KNOWN_DIVERGENCES`（登记表，随方案落 `09-docs/reports/`）** —— 当前两条：

| id | 分叉点 | 源（`src_restored/`） | 扁平副本（`src/app_dist_*`） | 裁 |
|---|---|---|---|---|
| D1 | `getConfigJson` 形参个数 | 3（本次改后） | 1 | 扁平副本**非权威**（`src/README-NONAUTHORITATIVE.md`，广告线在写） |
| D2 | 返回字段集 | 含 `chain`/`chainReach` + 选链过滤 | 无 | 同上 |

★ **方向说明**：S-2b 断言的是「**确实分叉**」，而非「应当相同」。**这是把已知事实变成可机检的登记**，
而不是把分叉当缺陷去消灭 —— 与"扁平副本非权威"的裁定一致。
★ 若将来要在扁平副本上补选链，S-2b 会先报红（"分叉消失/改变"）⇒ 强制先裁决再改，**不会静默同步**。

---

## 四、反向断言（判据，实现后随件交付）

| # | 断言 | 期望 |
|---|---|---|
| R-1 | `src_restored/` 的 `config-builder.js` 中 `HOST_PLACEHOLDER` 命中数 | **0** |
| R-2 | 扁平副本 `app_dist_…config-builder.js` 中 `HOST_PLACEHOLDER` 命中数 | **2**（★ 登记为**已知分叉**，不是"漏改"） |
| R-3 | `routes/config.js` 的 `cacheKey` 含 `host` 维度 | 命中 |
| R-4 | `routes/config.js` 有 `Vary` / `Host` | 命中 |
| R-5 | `!channel` 分支**不构造** origin（源码级） | 命中（`channel ? … : null`） |
| R-6 | `config-builder.js` 的 fail-loud 守卫在位 | 命中 |
| R-7 | S-2a / S-2b | 均绿 |
| **R-8** | ★ **行为级（需启服务，本次不做）**：`Host: <已登记域名>` ⇒ 响应 URL 的 host 与该 Host 一致；`Host: evil.test` ⇒ 响应中**不出现** `evil.test`；同 channel 的两个域名 ⇒ **各自正确**（不串味） | **待授权后做** |

★ **R-8 的诚实说明**：本卡**不得启服务**（未授权），故 R-1…R-7 是**静态判据**；
**行为级证据缺失**将**如实登记为未覆盖面**，不得以"静态绿"冒充"端到端已验"。

---

## 五、不改的东西（明确登记）

| 对象 | 处置 |
|---|---|
| `src/app_dist_plugins_c2_services_config-builder.js`（`:18,24`） | **内容不动**；由广告线的 `src/README-NONAUTHORITATIVE.md` 统一声明"非权威、勿以它为准" |
| `src/app_dist_plugins_c2_routes_config.js`（`:16` 缓存键无 host） | **内容不动**（同上） |

---

## 六、风险与未覆盖面

1. **`!channel` 行为变更**（见 2.1 的 3 号）—— 请复核确认这是否符合预期。
2. **缓存键加 host 会使缓存条目按域名分裂**（`Channel.domains` 是数组 ⇒ 多域名同渠道是受支持场景）⇒ 这是**必要代价**，否则 A 域名配置被 B 域名命中。
3. **多域名同渠道**下，同一 channel 会有 N 份缓存；`invalidateConfigCache` 用 `KEYS payload_config:*` 通配 ⇒ **仍能全清**，不受影响。
4. **行为级未验**（R-8 需启服务）⇒ 登记为未覆盖面。
5. 本方案**未落码**；改动将来**单独一批**提交，不混入批 4。

## 六、★ 落码实施记录（⌛2026-10-03 10:0x）

**已按放行口径落码**，并落实总调度追加的两条：

| 追加要求 | 实施 |
|---|---|
| **`!channel` 的"响亮 unsupported"须记日志（WARN、含 host、不含 body/凭据）** | `routes/config.js`：`logger.warn({ host }, 'Config request: host not in any channel allowlist -> unsupported')` |
| ★ **`scheme` 收敛为白名单**（`x-forwarded-proto` 可伪造） | 只接受 `http`/`https`，**其余一律回落 `http` 并 `logger.warn`** ⇒ 阻断 `javascript://`、`file://` 之类混入下发的 URL |

**实际改动**（`src_restored/` 2 文件，`src/app_dist_*` **一字未动**）：

| 文件 | 改动 |
|---|---|
| `routes/config.js` | ① host 未命中的日志由 `info` 改 **WARN 并带 host**；② 新增 **scheme 白名单**；③ 新增 **`origin = channel ? \`${scheme}://${host}\` : null`**；④ `cacheKey` 追加 **`:${host}`**（保留 `payload_config:` 前缀）；⑤ `getConfigJson(..., origin)` 下传；⑥ 补 **`Vary: Host`** |
| `services/config-builder.js` | ⑦ 形参加 `origin`；⑧ `!channel` ⇒ **`{unsupported:true, reason:'no_channel_for_host'}`**（不再产出任何 URL）；⑨ **fail-loud 守卫**（origin 缺失/非法即 `throw`）；⑩ `:34`/`:40` 改 `${origin}`；并移除因守卫而变成死分支的 `core: channel ? … : null` |

**判据实跑**（`09-docs/reports/verify_w_ios_gap2_host.py`）：**14 项全 PASS + R-8 SKIP**，exit 0。

| # | 结果 |
|---|---|
| R-1 源侧 `HOST_PLACEHOLDER` = 0 | ✅ |
| R-2 扁平副本仍 = 2（**已知分叉**，非漏改） | ✅ |
| R-3 缓存键含 host | ✅ |
| R-4 `Vary: Host` | ✅ |
| R-5 `!channel` 不构造 origin | ✅ |
| R-6 fail-loud 守卫 | ✅ |
| R-9 `scheme` 白名单 {http,https} | ✅（追加要求） |
| R-10 `!channel` ⇒ unsupported（源产出 reason，路由透传） | ✅ |
| R-11 未命中记 WARN 且只带 host | ✅（追加要求） |
| **S-2a-1** 形参 == 3 | ✅ `['channel','device','origin']` |
| **S-2a-2** 返回五键 | ✅ `['settings','chain','chainReach','core','entries']` |
| **S-2b-D1/D2/D3** 已知分叉仍成立 | ✅（源 3 参 vs 扁平 1 参；chainReach 源有扁平无；扁平路由键无 host） |
| **R-8 行为级** | **SKIP —— 未覆盖面**（需启服务，本卡未授权） |

★ **R-8 明确不判 PASS**：真实响应里 host 是否正确、伪造 Host 是否被拒、同渠道多域名是否串味，
**需启服务**；本卡未授权 ⇒ **如实登记为未覆盖面**，不以静态绿冒充端到端已验。
（总调度已将其排入"待窗口期端到端验证"清单。）

**未做**：不改 `src/app_dist_*`（内容一字未动，`git diff` 为空）；不动 `_templates/**`；**不 commit**（缺口2 单独留批）。

### 6.1 ★ 复核意见处置（⌛2026-10-03）

| # | 意见 | 处置 |
|---|---|---|
| **Y-03（P3）** | 运行期只信 `registry.json`，`SHELLS_NOT_FOR_ASSEMBLY` **只在 seed 期强制** ⇒ 手改 registry 即可放行裸壳 | ✅ **取选项①：运行期再校验一次**（`ipa_pipeline.py` 在 bundle-id 白名单之前，按 `shell_entry["id"] in SHELLS_NOT_FOR_ASSEMBLY` 二次拒绝）—— **不依赖"别手改 registry"这类纪律** |
| **Z-02（P3）** | `verify_w_ios_gap2_host.py` 三条断言**比其标签弱**（R-3 用 `or` 全文找 `${host}`；R-4 只查两个子串；S-2a-2 全文找五键名） | ✅ 三条**已收紧**：R-3 **锚定 `const cacheKey` 那一行**且**去掉 `or`**；R-4 断言**整句** `reply.header('Vary', 'Host')`；S-2a-2 **限定在 `return { … }` 块内** |
| **Z-01（P3）** | R-6 守卫正则 `/^https?:\/\/[^/]+$/` **放行主机部分的空格与换行**（`http://a b`、`http://a\nb` 均 match） | ⏸ **仅登记，本轮不改**。**当前不可达**（`origin` 仅在 channel 命中后、由**已登记域名**拼出）。★ **登记为「依赖上游不变量」**，并附复核方的诚实标注：**「Node 拒 header 内 CR/LF 这一前提未实测」** |

---

*方案件；待复核放行后方可落码。未 commit。*
