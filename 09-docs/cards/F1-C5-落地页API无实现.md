---
id: F1-C5
mode: 实施
wave: 2
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  触 04-landing 与 02-backend-node 的契约边界（D 线：落地页→Node:3000）。
  属【前端调用、后端无实现】的验收盲区，非资金路径 ⇒ R2。
  ★ 但本卡【必须先裁决归属】—— 见「停靠点 1」；本卡已按 (a1) Node 侧实现编写。
来源: 09-docs/reports/全量审核报告_独立复核版.md §三 P0-B + 需求文档 §3.1 新增验收项 1.9
base:
  - path: 04-landing\runtime\landing-runtime.js
    sha256: aa078c6418feabe4b27efaabc289925325a457869f437d446b540c1633a79ec5
    bytes: 4944
    eol: LF
  - path: 02-backend-node\src_restored\plugins\api\index.js
    sha256: 7aad66f12cca69ae0e63203448d03c9b5e96137494c9b6ac49ee9c7c56625bf5
    bytes: 3390
    eol: LF
allowed_paths:
  - 04-landing\runtime\landing-runtime.js
  - 02-backend-node\src_restored\plugins\api\routes\landing.js
  - 02-backend-node\src_restored\plugins\api\index.js      # 仅「注册新路由」这一处改动
  - E:\ios漏洞\_integration\_fix_work\verify_f1c5_landing_api.mjs
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本，只读）"
  - "08-infra\\nginx\\**（属 F1-C6）"
  - "01-backend-go/**（★ 按契约落地页走 Node:3000，不落 Go）"
  - "02-backend-node\\src\\**（扁平版，P-8）"
  - "02-backend-node\\src_restored\\core\\db\\models\\**（★ 若需新增集合 ⇒ 停下升级，见停靠点 2）"
  - "05-ios/**、06-android/**"
  - "_manifest.sha256"
verify:
  - node _fix_work\verify_f1c5_landing_api.mjs                  # ①动前：须【红】，退出码 != 0，留证
  - node _fix_work\verify_f1c5_landing_api.mjs                  # ②动后：须【绿】，退出码 0
  - node --check 02-backend-node/src_restored/plugins/api/routes/landing.js   # 退出码 0
packages: {}
---

# F1-C5 [R2] 落地页 5 个 API 在两个后端均无定义

## 目标

消除「落地页调用的 API 在服务端没有任何实现」。

## 缺陷事实（本轮实读）

`04-landing/runtime/landing-runtime.js` 调用：

| 行 | 端点 |
|---|---|
| `:4` | `DOWNLOAD_URL = "/api/apk/download"` |
| `:40,:49,:55` | `POST /api/track/heartbeat` |
| `:59` | `GET /api/pixel-config` |
| `:119` | `POST /api/track/click` |
| `:151` | `POST /api/track/start` |

**核验**：在 `02-backend-node/src_restored/` 全目录 grep 这 5 个路径 → **零命中**。
⇒ **前端写了调用，后端没有对应路由。**

**性质**：不是"统计丢了"的小问题 —— 落地页的**统计与 APK 下载**整体失效，
且需求文档原先**未把它列为验收项**（本轮已补为 §3.1 #1.9）。

## 规格

### (a) 归属已裁：**Node 侧新增路由**

| 选项 | 内容 | 状态 |
|---|---|---|
| **(a1) Node 侧新增路由** | 落地页按契约走 Node:3000（D 线），在 `plugins/api/routes/` 新增 landing 路由 | ✅ **本卡采用** |
| (a2) 静态响应 | `pixel-config` 返回静态配置 | 未采用 |
| (a3) 摘掉前端调用 | 承认功能不做 | 未采用 |

### (b) 幂等与鉴权

- `track/*` 为**公开埋点**（落地页面向匿名访客）⇒ **不得**套 `ServiceTokenAuth`
- 须有**基本防滥用**（按 `sid` 去重/限频）—— 阈值由执行者给出并说明理由
- `apk/download` 须返回**真实文件或 404**，**不得静默 200 空体**

### (c) ★ 与 `entries` 的关系（重要）

`apk/download` 的目标文件来自载荷分发链。**该链在一期不通**
（`chain-router.js` 已按 `V0` 裁决 **D-1** 降二期）⇒
本卡的 `apk/download` **可能只能返回「未就绪」或 404**。

★ **执行者必须如实实现并标注**，
**不得伪造一个可下载的假包**（那是 **P-1** 形态：把"看起来通了"当通）。

## ★ 判据先于实现（判据 9）

| # | 断言 | 红态（改前） |
|---|---|---|
| R1 | `landing-runtime.js` 中出现的**每个** `/api/*` 路径，在 Node 侧**均有路由注册** | 5 个**全无** ⇒ 红 |
| R2 | 路由注册与前端调用**路径逐字符相等** | 不成立 ⇒ 红 |
| R3 | `apk/download` 在文件缺失时返回 **404**（不得静默 200） | 未实现 ⇒ 红 |
| R4 | `track/*` **不要求**鉴权 header | 绿（防改过头） |

★ **R1 必须用「反向枚举」而非硬编码清单**：从 `landing-runtime.js` **提取** `/api/...` 字面量，
逐个去 Node 路由表里找 —— 这样**将来前端新增调用也会被这条判据抓到**（**防复发**）。

## 不在范围

- 不改 nginx（属 F1-C6）
- 不在 Go 侧实现（契约：落地页 → Node:3000）
- 不做 `track` 数据的统计报表（属后续）
- 不改 `_manifest.sha256`

## 证据要求

- `verify_f1c5_landing_api.mjs` 改前红 / 改后绿两次真实退出码
- 5 个端点**逐个**的实测响应（真实状态码与 body）
- 新增/修改文件的 sha256
- ★ **`apk/download` 的实际能力声明**（若载荷链未通，须写明返回什么）
- ★ **留出 `landing-runtime.js` 未改动的证据**（若实际无需改前端，须说明）

## 停靠点

1. 若执行者认为应改在 **Go 侧**或**摘掉前端调用** ⇒ **停下升级**（与已裁的 (a1) 冲突）
2. 若新增路由需要**新 Mongo 集合**（触 `core/db/models/**`）⇒ **停下升级**
3. 若发现 `landing-runtime.js` 还有**未被本次枚举到**的端点 ⇒ 登记上报
