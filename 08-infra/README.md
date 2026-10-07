# 08-infra（部署编排）

> **卡 I3-C3**｜基线：本轮实测｜**不得写入凭据明文**

## 职责

**部署编排**：nginx 反向代理 + docker-compose 服务编排。
本目录属**高风险路径**（命中即至少 R2）。

## 关键文件

| 路径 | 内容 |
|---|---|
| `nginx/default.conf.template` | nginx 反代配置 |
| `compose/docker-compose.yml` | 服务编排 |

## ★ 已知问题：`/api/` 前缀被两套后端同时使用（**未裁决**）

**这是本目录当前最重要的未决事项。**

### 事实（本轮实测）

| 侧 | 请求 | 需要落到 |
|---|---|---|
| **落地页**（`04-landing`） | `/api/track/*`、`/api/pixel-config`、`/api/apk/download` | **Node:3000** |
| **管理台**（`03-web-admin`） | `/api/base/login`、`/api/device/list` 等（axios `baseURL=/api`） | **Go:8888** |
| **Go 自注册** | `01-backend-go/router/system/sys_api.go` 有 `Router.Group("api")` | — |

⇒ **`/api/` 被两套后端同时使用，nginx 不能按前缀二分。**

### 现状

`default.conf.template` 中 `location /api/ { proxy_pass http://app_server; }`，
而 `app_server = server:3000`（Node）⇒
**管理台的 `/base/login`、`/user/*` 经 nginx 全被转给 3000（未注册）⇒ 404**。

且 `docker-compose.yml` 当前**没有 Go 后端服务**。

### 选项（**须 Owner 裁决后方可动**）

| 选项 | 做法 | 代价 |
|---|---|---|
| **(a1) 按 Host 分流** | 管理台域名 → Go；落地页域名 → Node | 最低；`ADMIN_DOMAIN` 已存在，落地页已有域名；**不需改前端、不需重新构建** |
| (a2) 改管理台 `VITE_BASE_API` 为 `/mgr-api` | 改前缀 | 需改前端 + 重新构建；★ `03-web-admin/src/api/api.js` 有 **8 处 url 自带 `/api`**，风险高 |
| (a3) 改落地页端点前缀 | — | 需改前端；`apk/download` 等已写死 |
| (a4) 精确 location 白名单 | 逐端点列举 | **脆弱** —— 新增端点数漏一个就静默错，不推荐 |

### 不决策时的行为

**管理台整体不可用**（现状）。属停靠点，未裁决前**不得开工**。

## 资源隔离（端口固定不得改）

| 用途 | 端口 |
|---|---|
| 潜客 Go | 8888 |
| gasleak Node | 3000 |
| MariaDB | 13306 |
| Redis | 16379 |
| MongoDB | 27018 |
| 管理台 vite dev | 8888（★ **与 Go 撞车，起前必查**） |

## 部署边界

★ **push / 部署 / 生产数据操作一律未授权**。
本目录的改动**只在本地文件层面验证**，不得据此认为"已在真实 docker 环境起服务验证"。
