---
id: D2-C1b
mode: 实施
wave: D2
depends: [D2-C1]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  ★ **解冻 `package.json` 的一个依赖声明**（把 `"latest"` 钉为确定版本）。
  为何需授权：`package.json` 在 D2-C1 的 `forbidden_paths` 内（原卡不许改依赖声明）。
  **⇒ Owner 已裁 (A)：授权解冻**。
  ★ 改动**仅一行**（`@vitejs/plugin-vue`），**不动其他依赖** ⇒ R2。
  门禁强度自知：须**真跑** `npm ci` + `npm run build` 并取真实退出码。
来源: D2-C1 执行实测（判据 5/7 RED，停靠点 2 触发）
      + Owner 裁决 (A)
      + ★ 调度**预先验证**：`@vitejs/plugin-vue@2.3.4` 的 peer = `vite ^2.5.10`
        ⇒ 与实装的 `vite 2.9.18` **匹配** ⇒ 修复方向可行
base:
  - path: 03-web-admin\package.json
    sha256: 5face9ec603725492ba8b96e14ac9b9111b35b22729ae032ae43602d18151e67
    bytes: 1770
    eol: LF
  - path: 03-web-admin\vite.config.js
    sha256: e084dc2dd8608bf82779756eb8cbec50924f9f5177a97e5b09979e14161a2ea1
    bytes: 2694
    eol: LF
allowed_paths:
  - 03-web-admin\package.json（★ 仅允许修改 `@vitejs/plugin-vue` 这一行）
  - 03-web-admin\package-lock.json（npm 会重算）
  - E:\ios漏洞\_integration\_fix_work\verify_d2c1b_vite_pin.py
forbidden_paths:
  - "03-web-admin\\src\\**（业务源码，只读）"
  - "03-web-admin\\static\\**（已验收产物，只读）"
  - "03-web-admin\\vite.config.js、index.html、.env.*（不得改）"
  - "★ package.json 的【其他】依赖行（本卡只改 plugin-vue 一行）"
  - "01-backend-go/**、02-backend-node/**、04-landing/**、05-ios/**"
  - "09-docs\\spec\\contracts.md"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_d2c1b_vite_pin.py    # 动前红 / 动后绿
packages: {}
---

# D2-C1b [R2] 钉住 `@vitejs/plugin-vue` 的版本（修复构建互斥）

## 缺陷事实（D2-C1 实测 + 调度复核）

### `package.json` 自身互斥

```json
L34  "@vitejs/plugin-vue": "latest",    ← ★ 时间性炸弹：今日解析为 6.0.9
L48  "vite": "^2.8.0",                  ← 实装 2.9.18
```

### 报错链（实测原文）

```
npm error code ERESOLVE
npm error Found: vite@2.9.18
npm error Could not resolve dependency:
npm error peer vite@"^5.0.0 || ^6.0.0 || ^7.0.0 || ^8.0.0" from @vitejs/plugin-vue@6.0.9
```

```
> vite build --mode production
failed to load config from ...\vite.config.js
SyntaxError: The requested module 'vite' does not provide an export named 'createFilter'
```

### ★ 崩溃点（证明与业务源码无关）

`node_modules/@vitejs/plugin-vue/dist/index.mjs:3`：
```js
import { createFilter } from 'vite'    // ★ vite 2.9.18 无此导出
```

**实测**：`'createFilter' in require('vite')` = **false** ✓

**⇒ 崩溃发生在 vite.config.js 的**配置加载阶段** ⇒ **`src/` 代码从未被执行** ⇒
**与业务源码无关，纯属依赖版本漂移。**

## ★ 修复方案（**调度已预先验证**）

把 `package.json:34` 的 `"latest"` 改为 **`"^2.0.0"`**。

**验证依据**（`npm view` 实测）：

| plugin-vue 版本 | peer 要求 | 与 `vite 2.9.18` 匹配？ |
|---|---|---|
| **2.3.4**（`^2.0.0` 会解析到此） | **`vite: ^2.5.10`** | ✅ **匹配** |
| 4.0.0 | `vite: ^4.0.0` | ❌ |
| 5.0.0 | `vite: ^5.0.0` | ❌ |
| 6.0.9（现装） | `vite: ^5\|^6\|^7\|^8` | ❌ |

**⇒ `"^2.0.0"` 与 `"vite": "^2.8.0"` 兼容** ✓

## ★ 规格

### (a) 只改一行

```diff
-    "@vitejs/plugin-vue": "latest",
+    "@vitejs/plugin-vue": "^2.0.0",
```

★ **不得改其他依赖行**（`vite`、`axios`、`vue` 等一律不动）。

### (b) 重装依赖

```powershell
$env:PATH = "E:\CTF\runtime\node;" + $env:PATH
cd E:\USDT项目\03-web-admin
npm.cmd install          # 会重算 package-lock.json
```

★ **不要**用 `--legacy-peer-deps`（那只是绕过校验，**不修复 `createFilter` 缺失**）。

### (c) `npm ci` + `npm run build`

```powershell
npm.cmd ci
npm.cmd run build
```

★ 构建产物在 **`dist/`**（`vite.config.js:74` `outDir: 'dist'`）
⇒ **不得**覆盖 `static/`。

## ★ 判据要求

| # | 断言 |
|---|---|
| **X1** | ★ **`package.json` 的 `plugin-vue` 不再是 `"latest"`**（已钉住） |
| **X2** | ★ **`package.json` 的其他依赖行未变**（逐行核对） |
| **X3** | ★ **`npm ci` EXIT=0** |
| **X4** | ★ **`npm run build` EXIT=0** |
| **X5** | ★ **产出 `dist/`**（文件数 > 0） |
| **X6** | ★ `static/` **未改**（`admin_dashboard.html` = `9bad2f7f…`、`admin_login.html` = `2674aeab…`） |
| **X7** | `src/` **未改** |
| **X8** | `vite.config.js` 未改、`_manifest.sha256` 未改 |

★ **X4/X5 是本卡的核心目标**。
★ **X2/X6 是防改过头**。

## ★ 不在范围

- **不改**其他依赖、`src/`、`static/`、`vite.config.js`
- **不用** `--legacy-peer-deps` 作为通过手段
- 不把 `dist/` 覆盖到 `static/`

## 证据要求

- ★ **`npm ci` / `npm run build` 的真实退出码 + 输出尾部**
- `package.json` 改前/改后 **sha256 + diff**（应只有 1 行）
- `package-lock.json` 的 sha256 与字节数
- `dist/` 的**文件数与体积**
- ★ 声明：**未改 `src/`、`static/`、`vite.config.js`、其他依赖**

## 停靠点

1. 若改后 **`npm run build` 仍失败** ⇒ 停下升级（可能有其他依赖问题）
2. 若改后 **`package-lock.json` 出现大量非预期变更** ⇒ 停下升级
3. 若 `npm install` 试图**降级 `vite`** ⇒ 停下升级（会改变基础栈）
4. 若 `axios@0.19.2` 的漏洞告警需要处置 ⇒ 登记（不在本卡范围）
