---
id: D4-C1
mode: 实施
wave: D4
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R3
定档理由: |
  ★★ **命中「真高危」**：**2FA（TOTP）共享密钥硬编码在前端源码，且已被打包进 `dist/`**。
    · 触 `03-web-admin/src/view/home/index.vue`（**前端源码**）
    · 需**重新构建 `dist/`**（**构建产物含该值**）
    · **性质**：**2FA 是账号安全的最后一道闸** ⇒ **等同 P0**
  ⇒ **R3**。
  门禁强度自知：**须证明"修复后 `dist/` 中不再含该值"**
  **且"页面功能未被破坏"**（不能只看代码删了）。
来源: ★★★ **R3-C1-A（静态抽取）发现 (1)** —— **最高危**
      + ★★ **调度复核升级**：**`:74` 的按钮无 `@click`** ⇒ **并非"泄漏"而是"未完成的脚手架"**
      + ★★ **调度实测**：**该值已在 `dist/` 中出现 2 处**
      + ★★ **后端对照**：`pending-totp.js`(22) / `totp.js`(15) / `auth.js`(41) ⇒ **后端 TOTP 是真实实现的**
      + ★★ **R-06 登记**（`残余暴露面登记.md`）
base:
  - path: 03-web-admin\src\view\home\index.vue
    sha256: 043a19dded56de1f12d98a18d41a9ce7abada74e997bfe6b5d2e1a68e5569017
    bytes: 5426
    eol: CRLF
    note: |
      ★ **调度实测**：**bytes = 5,426**、**eol = CRLF**（**P-36：用二进制模式测得**）。
  - path: 03-web-admin\dist\js\gin-vue-admin-index.179075883200011.js
    sha256: 9f21471738f4a28f…（前 16）
    bytes: 35261
    eol: LF
    note: ★ **含该 secret 1 处** —— 构建后应消失
  - path: 03-web-admin\dist\js\gin-vue-admin-index-legacy.179075883200011.js
    sha256: 9f718f408d5764d2…（前 16）
    bytes: 40736
    eol: LF
    note: ★ **含该 secret 1 处** —— 构建后应消失

★ **dist 总文件数 = 238**（动前）
allowed_paths:
  - 03-web-admin\src\view\home\index.vue（★ 移除硬编码 secret）
  - 03-web-admin\dist\**（★ 仅【重新构建】产出，不手工编辑）
  - E:\ios漏洞\_integration\_fix_work\verify_d4c1_totp_secret.py
forbidden_paths:
  - "02-backend-node/**（★ 后端 TOTP 已实现，本卡不动）"
  - "01-backend-go/**、05-ios/**、06-android/**、04-landing/**"
  - "09-docs\\spec\\contracts.md"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_d4c1_totp_secret.py    # 动前红 / 动后绿
packages: {}
---

# D4-C1 [R3] ★★★ TOTP 共享密钥硬编码在前端（**且已进 `dist/`**）

## ★★★ 缺陷事实（**调度实测确证**）

### 位置

```
03-web-admin/src/view/home/index.vue:91
  const secret = ref('〈已移除 · 见 D4-C1〉')
```

### ★★ 且**页面主动展示**（**不只是"可读"**）

```vue
:65  <div class="Validator">
:66    <h2>绑定谷歌验证</h2>
:68    <qrcode :value="otpauthURL" style="width:150px"></qrcode>   ← ★ 渲染 QR 码
:71    <p>{{ secret }}</p> <div @click="copys(secret)">复制</div>  ← ★ 明文显示 + 复制按钮
:74    <el-button type="primary">绑定谷歌验证</el-button>          ← ★ 按钮【无 @click】
:76  </div>

:85  let otpauthURL = ref('')
:88  const GoogleAuthenticator = ref('')      ← ★ 定义了但【未使用】
:91  const secret = ref('〈已移除 · 见 D4-C1〉')       ← ★ 硬编码
:93  otpauthURL.value = `otpauth://totp/dapp?secret=${secret.value}&issuer=didid`
:96  const copys = (value) => { ... document.execCommand('Copy') ... }
```

### ★★★ 已进入构建产物（**实测**）

| 位置 | 命中 |
|---|---|
| `03-web-admin/src/view/home/index.vue` | 1 处 |
| **`03-web-admin/dist/js/gin-vue-admin-index.179075883200011.js`** | **1 处** |
| **`03-web-admin/dist/js/gin-vue-admin-index-legacy.179075883200011.js`** | **1 处** |

**⇒ 任何访问后台的人可读。**

### ★★ 关键判断：**这不是"泄漏"，而是"未完成的脚手架"**

| 证据 | 说明 |
|---|---|
| **`:74` 的按钮无 `@click`** | **点了没反应** ⇒ **功能未实现** |
| **`:91` 的 secret 是硬编码** | **不从后端取** |
| **`:88` `GoogleAuthenticator` 定义但未使用** | 同上 |
| **`:64` 上方有注释掉的块** | **整个页面是半成品** |

**⇒ 这是前端模板留下的**演示代码**。**

### ★★ 但**风险真实**

1. **该值若**恰好是生产 secret** ⇒ **2FA 可被绕过**
2. **且它**已在 `dist/`** ⇒ **当前已暴露**
3. **后端 TOTP 是真实实现的**（`pending-totp.js` 22 处 / `totp.js` 15 处 / `auth.js` 41 处）
   ⇒ **前端这个静态页与后端不一致** ⇒ **功能上也是坏的**

---

## ★★★★ 调度已完成的取证（**两个停靠点全部消除**）

### ✅ 停靠点 1 消除：**该 secret 与后端【无关】**

| 证据 | 结果 |
|---|---|
| 后端全树搜 `〈已移除 · 见 D4-C1〉` | ✅ **0 命中** |
| **后端 TOTP 真实实现** | `totp.js:35` **`new Secret({ size: 20 })`** ⇒ **运行时随机生成** |
| `auth.js:181` | `user.totp = { secret: encryptSecret(setup.secret), enabled: false }` ⇒ **每用户独立** |
| `totp.js:16/24` | **`encryptSecret` / `decryptSecret`** ⇒ **加密存储** |
| `totp.js:46/56` | **`verifyTotp` / `totp.validate({token, window:1})`** ⇒ **真实验证** |

**⇒ 后端 TOTP 是【完整的、安全的实现】**
（**随机 secret + 加密存储 + 每用户独立 + 窗口验证**）。

**⇒ 前端那个值【纯属前端演示代码】，与生产 2FA【无关】。**

### ✅ 停靠点 2 消除：**`index.vue` 未被路由/菜单引用**

**全树搜 `view/home/index` / `home/index.vue`** ⇒ ✅ **0 命中**

**⇒ 该页【没有路由指向它】⇒ 是【死代码】。**

---

## ★★★ 风险等级修正（**下调**）

| 原判 | **修正后（调度取证）** |
|---|---|
| 🔴🔴🔴 "2FA 完全失效" | 🟡 **"死代码中的演示值"** |
| "生产 2FA 已失效" | ✅ **否** —— **后端 TOTP 安全** |
| "可绕过 2FA" | ⚠️ **否** —— **该值不被任何后端接受** |

**⟹ 但仍应移除**，**理由**：
1. ★ **死代码不应进产物**（**已进 `dist/` 2 处**）
2. ★ **值形态像真 secret，会误导审计**（**本轮 R3-C1-A 即被误报为"最高危凭据"**）
3. ★ **它是"未完成的脚手架"**（**按钮无 handler**）⇒ **留着是隐患**

---

1. ★ **实读 `03-web-admin/src/view/home/index.vue` 全文**（209 行）确认结构
2. ★ **实读后端 `02-backend-node/src_restored/plugins/api/routes/totp.js`**
   与 `pending-totp.js` ⇒ **查明后端 TOTP 的真实接口**
3. ★★ **判断该值是否与生产相关**：
   - 若**是前端专用演示值**（后端不认）⇒ **删除即可**
   - 若**与后端共享** ⇒ **须同时评估后端**
4. ★ **查明 `03-web-admin/src/api/index.js` 的 `get_index_info` 是否返回 TOTP 信息**

### 修复方向（**依取证结果选择**）

| 方案 | 做法 | 评价 |
|---|---|---|
| **(a)** | ★ **删除整个 `Validator` 块**（`:65-76`）+ 相关 `secret`/`otpauthURL`/`copys` | ★ **推荐**（**未完成的脚手架不应留在产物**）|
| **(b)** | **改为从后端取**（调 `/api/auth/totp/status` 或等价接口） | ⚠️ **属新功能** ⇒ **超本卡范围** |
| **(c)** | **仅把 secret 置空** `ref('')` | ⚠️ **QR 会渲染空值** ⇒ **半坏** |

★ **建议 (a)** —— **理由**：
- 该功能**从未实现**（按钮无 handler）；
- **后端 TOTP 已实现** ⇒ 前端应走**登录流程**（`pending-totp.js`），**而非首页的绑定页**；
- **删除是零风险**（**该页无功能可破坏**）。

★ **但执行者须自行判断** —— **若发现该页**确被使用**（如路由引用了它）⇒ 停下报告**。

### ★★ 重新构建 `dist/`

**移除源码后，须重新构建 `dist/`**（**否则旧 dist 仍含该值**）。

**构建命令**（**D2-C1 已验证**）：
```powershell
$env:PATH = "E:\CTF\runtime\node;" + $env:PATH
cd E:\USDT项目\03-web-admin
npm run build
```

---

## ★★ 判据要求

| # | 断言 |
|---|---|
| **V1** | ★★ **`src/view/home/index.vue` 不再含 `〈已移除 · 见 D4-C1〉`**（**精确值**） |
| **V2** | ★★ **`dist/**` 全树不再含该值** |
| **V3** | ★ **`npm run build` EXIT=0** |
| **V4** | ★ **未破坏 `index.vue` 的其余功能**（`getindexinfo` 等仍在） |
| **V5** | ★ **未改后端**（`02-backend-node/**` sha256 抽样一致） |
| **V6** | ★ **`otpauth://` 字样也不再出现**（**或明确说明保留理由**） |
| **V7** | 守护：`_manifest.sha256`、`contracts.md` 未改 |

★ **V1+V2 是核心**（**源码 + 产物双清零**）。
★ **V3 是"未破坏构建"的证据**。

## ★ 不在范围

- ★ **不实现**真正的 TOTP 绑定功能（**属新功能** ⇒ **另立卡**）
- **不改**后端
- **不改**其他前端页面

## ★ 证据要求

- 判据动前红 / 动后绿真实退出码
- ★ **所选方案（a/b/c）与理由**（**须含"该页是否被路由引用"的核查**）
- ★ **`index.vue` 的改前/改后 sha256 + diff**
- ★★ **V1/V2 的双清零证据**
- ★ **V3 的 build EXIT**
- ★ **V4 的"其余功能未破坏"证据**
- ★ 声明：**未改后端**

## 停靠点

1. ★★★ **若发现该 secret 与后端共享**（**后端也认这个值**）⇒ **停下升级**
   （⇒ **须同时处置后端**，且**可能意味着生产 2FA 已失效**）
2. ★★ **若发现该页被路由/菜单引用**（**即它是在用的功能**）⇒ **停下报告**
3. ★★ **若 `npm run build` 失败** ⇒ **停下报告**
4. ★ **若发现 `dist/` 的构建方式与 D2-C1 记载不同** ⇒ 停下报告
