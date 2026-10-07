---
id: D2-C1
mode: 实施
wave: D2
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  补 `package-lock.json` + 验证 `npm ci` / `npm run build` 可跑通。
  ★ 会**新增** `package-lock.json` 与 `node_modules/`（**两者均为构建依赖，非交付产物**）。
  ★ **不改任何产物业务代码**（`src/`、`static/` 不动）⇒ R2。
  门禁强度自知：判据须【真跑 `npm ci` 与 `build`】并取真实退出码，
  不得只检查"lock 文件存在"。
来源: `完整版本开发方案_终版.md:231`（D2-C1）
      + 调度实测：`package-lock.json` **不存在**、`node_modules` **不存在**
      + 调度实测：`registry.npmjs.org` **可访问**（HTTP 200）⇒ 可行
base:
  - path: 03-web-admin\package.json
    sha256: 5face9ec603725492ba8b96e14ac9b9111b35b22729ae032ae43602d18151e67
    bytes: 1770
    eol: LF
  - path: 03-web-admin\vite.config.js
    sha256: e084dc2dd8608bf82779756eb8cbec50924f9f5177a97e5b09979e14161a2ea1
    bytes: 2694
    eol: LF
  - path: 03-web-admin\static\admin_dashboard.html
    sha256: 9bad2f7f3a047a9fb988ca9f0c022df2db61b05ac2d548c74449eecdd6b85ce5
    bytes: 60126
    eol: LF
  - path: 03-web-admin\static\admin_login.html
    sha256: 2674aeab104190b8725a2d33fbdac010295a2891cd317726c2e40b6fece8a8c5
    bytes: 3187
    eol: LF
allowed_paths:
  - 03-web-admin\package-lock.json（★ 新建）
  - 03-web-admin\node_modules\**（★ 新建，构建依赖）
  - 03-web-admin\dist\**（★ 若 build 产出）
  - E:\ios漏洞\_integration\_fix_work\verify_d2c1_web_build.py
forbidden_paths:
  - "03-web-admin\\src\\**（★ 业务源码，只读）"
  - "03-web-admin\\static\\**（★ 已构建产物，运行时用；本卡【不得】改）"
  - "03-web-admin\\package.json（★ 不得改依赖声明）"
  - "03-web-admin\\vite.config.js、index.html、.env.*（不得改）"
  - "01-backend-go/**、02-backend-node/**、04-landing/**、05-ios/**、06-android/**"
  - "09-docs\\spec\\contracts.md"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_d2c1_web_build.py    # 动前红 / 动后绿
packages: {}
---

# D2-C1 [R2] `03-web-admin` 可构建（补 lock + 验证 `npm ci`/`build`）

## 目标

补 `package-lock.json`，并**真跑** `npm ci` 与 `npm run build`，证明该模块**可构建**。

## ★ 现状（调度实测）

| 项 | 状态 |
|---|---|
| `package.json` | ✅ 存在（v2.5.0，gin-vue-admin；`build` = `vite build --mode production`） |
| **`package-lock.json`** | ❌ **不存在** ⇒ `npm ci` **会直接失败** |
| **`node_modules`** | ❌ **不存在** ⇒ 无法构建 |
| **`static/`** | ✅ **已有产物**（`admin_dashboard.html` 60,126 B、`admin_login.html` 3,187 B） |
| **网络** | ✅ `registry.npmjs.org` **可访问**（HTTP 200） |

### ★★ 关键定位澄清

`static/` **已有构建产物** ⇒ **运行时（`plugins/android/admin.js` 提供登录页）不依赖本卡**。

**⇒ 本卡是"可构建性验证"，不是"必须产出新 dist"。**

**⇒ 若 `build` 失败，只要证明"失败原因与产物无关"（如依赖冲突），即可如实登记，
不必强求构建成功** —— 但**必须给出真实失败证据**，**不得伪造成功**。

## ★ 规格

### (a) 先 `npm install` 生成 lock（`03-web-admin/` 内）

```powershell
$env:PATH = "E:\CTF\runtime\node;" + $env:PATH    # ★ node/npm 不在 PATH（P-7）
cd E:\USDT项目\03-web-admin
npm.cmd install --package-lock-only     # 只生成 lock，不装 node_modules（更快）
# 或直接 npm.cmd install（装依赖并生成 lock）
```

★ **用 `npm.cmd`**（`npm.ps1` 会被执行策略拦，已在 L008 记录）。

### (b) `npm ci`（须能用 lock 装出依赖）

```powershell
npm.cmd ci
```

★ 若 `npm ci` 失败（如 lock 与 package.json 不一致）⇒ **如实报告**。

### (c) `npm run build`

```powershell
npm.cmd run build
```

★ 记录**真实退出码**与**输出产物路径**（`dist/`？`static/`？—— 须实读 `vite.config.js` 确认）。

★ **不得**把 `dist/` 的内容覆盖到 `static/`（**`static/` 不得改**）。

## ★ 判据要求

| # | 断言 |
|---|---|
| **W1** | ★ **`package-lock.json` 存在且可被 `npm ci` 使用**（真跑 `npm ci`，取退出码） |
| **W2** | ★ **`npm run build` 真跑**，取真实退出码 |
| **W3** | ★ `03-web-admin/src/**` **未改**（sha256 抽样核对） |
| **W4** | ★ `03-web-admin/static/**` **未改**（`admin_dashboard.html` = `9bad2f7f…`、`admin_login.html` = `2674aeab…`） |
| **W5** | `package.json` **未改**（依赖声明不动） |
| **W6** | 守护：`_manifest.sha256` 未改 |

★ **W1/W2 是本卡核心** —— 必须真跑，取真实退出码。
★ **W3/W4 是防改过头** —— 不得为了"能构建"去改源码或产物。

## ★ 不在范围

- **不改** `src/`、`static/`、`package.json`、`vite.config.js`
- **不把 `dist/` 覆盖到 `static/`**
- 不改 `_manifest.sha256`

## 证据要求

- ★ **`npm ci` 与 `npm run build` 的真实退出码 + 输出尾部**（各至少 10 行）
- `package-lock.json` 的 sha256 与字节数
- **构建产物路径**（实读 `vite.config.js` 确认 `outDir`）
- ★ 若 `build` 失败 ⇒ **给出真实错误原文**，并说明是否与产物本身有关

## 停靠点

1. **若 `npm install` 下载依赖超过 15 分钟或大量失败** ⇒ 停下报告（网络不可用）
2. **若 `build` 失败且原因涉及"需要改源码"** ⇒ **停下升级**（改源码属停靠点）
3. 若构建产物会**覆盖 `static/`** ⇒ **停下升级**（会破坏已验收产物）
4. 若发现 `package.json` 的依赖有**已知重大漏洞** ⇒ 登记（不在本卡范围）
