# B2 报告：补 02-backend-node/package.json 并定运行目录

> 编制日期：2026-09-27
> 目标产物：`E:\USDT项目\02-backend-node`
> 权限来源：镜像 `gasleak-server:v0.0.101`（`ios-xy-main\gasleak-system\images.tar`）

---

## 一、来源：从 Docker 镜像提取，而非推测

材料中**没有** `package.json` / `Dockerfile` / `ecosystem.config.cjs`
（部署包 `gasleak-system.tar.gz` 的 10 个条目里也没有）。
权威清单在 **`images.tar`** 内 —— 该 tar 是 Docker save 格式，
`manifest.json` 列出 4 个镜像标签：

```
gasleak-server:v0.0.101   ← 应用镜像
gasleak-nginx:v0.0.101
redis:7-alpine
mongo:4.4
```

提取到（原文件留档于 `_fix_work\_image_extract\`）：

| 提取物 | 大小 | 用途 |
|---|---|---|
| `app/package.json` | 1,535 B | 依赖清单与 npm 脚本 |
| `app/package-lock.json` | 174,424 B | **精确版本树（380 包）** |
| `app/ecosystem.config.cjs` | 546 B | pm2 启动配置 |

---

## 二、★ 关键认识：镜像是 TypeScript 项目，产物是它的 `dist`

镜像内 `app/` 的构成（实测）：

```
app/node_modules   13234 文件
app/dist            1344 文件   ← 只有编译产物，【没有 app/src】
app/templates        105 文件
app/ecosystem.config.cjs / package.json / package-lock.json / chain-config-route.js
```

`package.json` 原文：

```json
"type": "module",
"main": "dist/app.js",
"scripts": { "dev": "tsx watch src/app.ts", "build": "tsc", "start": "node dist/app.js" }
```

**→ 本工作区里的 `02-backend-node/src/` 与 `src_restored/` 装的是 `dist/` 的 JS**
（webpack 扁平命名 `app_dist_core_db_models_user.js` 即证据），
**不是 TS 源**。故依赖清单须以**编译产物的实际 import** 为准。

---

## 三、交付物

| 文件 | 说明 |
|---|---|
| `02-backend-node/package.json` | **依赖块与镜像逐字保真**；仅改 `main`/`scripts` 以匹配产物布局 |
| `02-backend-node/package-lock.json` | 镜像原件，保证 `npm ci` 精确复现 |
| `02-backend-node/ecosystem.config.cjs` | pm2 配置，`script` 由 `./dist/app.js` 改为 `./src_restored/app.js` |

**`scripts` 的改动及理由**：

```json
"start":      "node --env-file-if-exists=.env src_restored/app.js"
"start:flat": "node --env-file-if-exists=.env src/app_dist_app.js"
"decrypt":        "node src_restored/cli/decrypt.js"
"generate-dga":   "node src_restored/cli/generate-dga.js"
```

- 镜像原脚本 `dev`/`build`/`test`/`init-payloads`/… 全部指向 `src/*.ts`、`tools/*.ts`、
  `tsc`、`vitest` —— **产物中没有这些**，原样保留只会给出误导性的报错，故移除。
  新增的 `decrypt`/`generate-dga` 对应产物中**实际存在**的 `src_restored/cli/*.js`。
- ★ **`--env-file-if-exists=.env` 是必需的发现**：`app.js` 与 `config/index.js`
  **没有任何 dotenv 加载**，纯读 `process.env`（镜像里由 pm2 的 `env_file: '.env'` 注入）。
  裸跑 `node app.js` 会静默使用 `config/index.js` 的默认值（`localhost:27017` 等），
  拿不到 `.env`。用 `--env-file-if-exists` 可兼顾"有 .env"与"无 .env"两种情况
  （后者不报错，回退到默认值）。

**依赖保真的副作用（有意为之）**：`devDependencies` 7 项（`typescript`/`tsx`/`vitest`/
`@types/*`/`i18n-iso-countries`）在产物中**无用**，但保留可让 `package-lock.json`
与 `package.json` 严格一致，从而 `npm ci` 可用。取舍：**可复现性 > 整洁**。

**一项未声明的直接依赖**：`core/logger/transport.js` 直接 `import 'pino-abstract-transport'`，
而镜像的 `dependencies` 未列它。已验证它在 lock 树内已解析（`v3.0.0`，由 `pino` 传递带入），
故 `npm ci` 会装上、运行不受影响。**建议**：若将来 `pino` 移除该依赖，需把它提升为直接依赖。

---

## 四、★ 运行目录：`src_restored`（C4 由此闭合）

此前 C4 待判"以 `src_restored` 还是 `src` 为运行目录"。本轮以**实际启动**定论：

| 目录 | 形态 | 判定 |
|---|---|---|
| `src/` | 扁平名 `app_dist_core_db_models_user.js` | 镜像 `dist/` 的原始扁平产物 |
| **`src_restored/`** | 嵌套 `core/db/models/user.js` | ★ **运行目录**（目录树还原版，且承载本轮新增的回传桥代码） |

两者均为 175 个 `.js`，内容一一对应；`src_restored` 的 import 路径可解析。

---

## 五、验证证据（全部实跑）

### 5.1 `npm ci` 真装成功

在**产物之外**的临时目录执行（`node_modules` 达 **3.8 GB**，绝不能进产物）：

```
added 323 packages in 46s          exit=0
fastify 5.8.5 / mongoose 9.6.3 / tronweb 6.3.0 / ethers 6.16.0
bitcoinjs-lib 7.0.1 / ioredis 5.11.0 / pino 10.3.1
pino-abstract-transport 3.0.0 / 7zip-bin 5.2.0 / toad-scheduler 4.0.1
```

### 5.2 ★ `npm ci` 首次失败，根因是环境事实

```
npm error command failed
npm error command C:\WINDOWS\system32\cmd.exe /d /s /c node install.js
npm error 'node' 不是内部或外部命令
```

即 esbuild 等包的 **postinstall 需要 `node` 在 PATH**，
而本机 Node 位于 `E:\CTF\runtime\node\node.exe`（不在 PATH，见主方案 §6.6）。
**把该目录加入 PATH 后 `npm ci` 通过。**
→ 凡在本机跑 `npm install/ci`，必须先 `export PATH="/e/CTF/runtime/node:$PATH"`。

### 5.3 app 实际启动并监听 3000

```
MongoDB connected
Redis connected
Default admin account created
Server listening on port 3000
tasks: [log-cleanup, balance-init, subscription-sync, tatum-webhook-process, ...]
```

**全日志零 warn / 零 error**（level ≥ 40 命中数为 0）。

### 5.4 载荷注册写入 MongoDB

```
集合数: 32
payloads: 12          ← 与补回的 12 个 dylib 一一对应
users: 1
```

### 5.5 静态依赖覆盖校验

```
src_restored 引用的裸包: 27
引用但未声明: 仅 pino-abstract-transport（已确认在 lock 树内）
```

### 5.6 回归基线未破

| 项 | 结果 |
|---|---|
| `verify_field_mapping.py` | ✅ 修正后 13 条映射目标列全部存在 |
| `test_chain_router.mjs` | ✅ 59/59 |
| `acceptance_final.ps1` | ✅ 缺陷命中 0（载体 16） |
| `verify_redaction_reverse.py` | ✅ 命中 28 条 / 9 文件，**全部为已知载体** |
| `go build ./...` | ✅ exit=0 |

---

## 六、★ 顺带发现两个真实缺陷（均已修）

### 6.1 模板漏拷：13 个文件（含 12 个载荷 dylib）

对比镜像 `app/templates/` 与产物，产物**缺 13 个文件**：

```
darksword-payloads/extract.js
payloads/{a1lib,b2lib,c3lib,d4lib,f6lib,helion,l12lib,p16lib,r18lib,taskagent,tglib,wap}.dylib
```

**根因**：`build_unified.ps1` 的拷贝清单是
`@('landing','exploit','raw')` —— **漏了 `payloads` 与 `darksword-payloads`**。
素材里两者分别有 13 与 1 个文件，产物中却是空目录。
**不是素材缺失，是构建漏拷。**

**影响**：启动日志 `templates/payloads/ not found, skipping payload init`
→ **不注册任何载荷**，C2 投递链路整体失效。

**处置**：清单补全；13 个文件已补入；集合比对由 85/98 → **98/98（缺失归零）**。
另把 macOS 元数据 `.DS_Store` 加入 `$EXCLUDE_FILES`。

### 6.2 模板路径不符合运行时要求

`app.js:76` 实测：

```javascript
const templateDir = path.join(process.cwd(), 'templates/payloads');
```

即要求 `templates/` 位于**进程 cwd**（= `02-backend-node/`）下，
而产物按方案 §1.2 的分组把它放在 `04-landing/ios-templates/`。

**处置（Owner 裁决：两处都留，非破坏性）**：
- `04-landing/ios-templates/` 保留（方案分组）
- **新增 `02-backend-node/templates/`**（运行时要求），98 文件 / 39 MB，
  与源**逐文件 sha256 一致**
- `build_unified.ps1` 改为**同时产出两处**

**实测有效性**：templates 就位后，启动日志由
`templates/payloads/ not found` 变为**逐个注册**（c3lib/helion/a1lib/… /d4lib），
且 `MongoDB.gasleak.payloads = 12`。

> 附带确认：全仓**无任何代码引用** `ios-templates`（仅文档提及），
> 故新增第二处不影响既有引用。

---

## 七、遗留与建议

| # | 项 | 说明 |
|---|---|---|
| 1 | `node_modules` 不进产物 | 3.8 GB，且 §1.2 明确排除。首次部署需 `npm ci` |
| 2 | 两处 templates 有漂移风险 | 已在构建脚本中同源产出；若手工改动其中一处会不一致 |
| 3 | `chain-config-route.js` 未纳入产物 | 镜像 `app/` 根下有此文件（2,619 B），产物中不存在。**全仓无引用**，不阻塞启动，但属覆盖缺口 |
| 4 | `pino-abstract-transport` | 建议提升为直接依赖（见 §三） |
| 5 | `devDependencies` | 为保 lockfile 一致而保留；若接受丢失可复现性可精简 |

---

## 八、证据局限

1. **未在容器内验证**：本轮用本机 Node 22.19 + 本地 MongoDB 6.0.14 / Redis 5.0.14
   启动，**非**镜像原生的 Node 22.23.1 / Mongo 4.4 / Redis 7.4.11。
   版本差异可能掩盖镜像特有的问题。
2. **未验证对外接口**：仅确认"监听 3000 + 载荷入库"，未逐个调用
   `/api/*`、`/taskget`、C2 路由等业务端点。
3. **未验证 nginx 与落地页**：`docker-compose.yml` 的 nginx 路由未起。
4. **`npm ci` 的 3.8 GB 体积未逐包审计**，仅确认关键依赖版本正确。
5. **模板集合比对以镜像 `app/templates` 为真值**：若镜像本身相对实网有缺，
   本比对无法发现。
6. `darkswordpayloads` 集合在实测中为 **0**，而 `payloads` 为 12。
   未追查 `darksword-payloads/extract.js` 的注册路径（可能懒加载或走别的集合）。
