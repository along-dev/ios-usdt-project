---
id: D1-C3
mode: 实施
wave: D1
depends: [D1-C5a, D1-C5b]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  在 `plugins/android/` 内新增 **APK 上传**端点（multipart）。
  属 `02-backend-node/**` ⇒ 至少 R2。
  ★ 涉及**文件写入**（落盘）⇒ 须有**路径安全**与**大小限制**的门禁。
  ★ 不触碰资金路径、不改契约、不改已验收文件 ⇒ 不上 R3。
来源: `09-docs/reports/D1-管理台侧端点契约.md` + `admin_dashboard.html:829-861`
      + `完整版本开发方案_终版.md:221`（D1-C3）
base:
  - path: 02-backend-node\src_restored\plugins\android\index.js
    sha256: b2a8c68ce5284d5a2bef24edb72e23326feb33a498918de7ca48ca70305658cf
    bytes: 3325
    eol: LF
  - path: 02-backend-node\src_restored\plugins\android\admin.js
    sha256: 28b9faede6151fd923a19ce84e49bb09e20d2cbf8a59c11aac6b0c6d21763abb
    bytes: 34154
    eol: LF
  - path: 03-web-admin\static\admin_dashboard.html
    sha256: 9bad2f7f3a047a9fb988ca9f0c022df2db61b05ac2d548c74449eecdd6b85ce5
    bytes: 60126
    eol: LF
# ★ 追加授权（调度 2026-09-30 补）：
#   `02-backend-node\templates\apk\**` —— 运行时数据目录（非产物；
#   已核实 _manifest.sha256 不含它）。上传须 mkdirSync 后落盘于此。
追加授权路径:
  - 02-backend-node\templates\apk\**
allowed_paths:
  - 02-backend-node\src_restored\plugins\android\**
  - E:\ios漏洞\_integration\_fix_work\verify_d1c3_apk_upload.py
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本，只读）"
  - "02-backend-node\\src_restored\\plugins\\api\\routes\\landing.js（已验收）"
  - "02-backend-node\\src_restored\\plugins\\api\\routes\\visitors.js（只读）"
  - "03-web-admin\\static\\**（前端契约来源，只读）"
  - "02-backend-node\\src_restored\\app.js（D1-C1b 刚更正过）"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_d1c3_apk_upload.py    # 动前红 / 动后绿
packages: {}
---

# D1-C3 [R2] APK 上传端点（multipart）

## ★★ 范围已大幅缩小（方案原列 5 端点，实只剩 1 个）

| 方案原列端点 | 实际归属 |
|---|---|
| `apk/list` | ✅ **D1-C5b** |
| **`apk/upload`** | ★ **本卡（唯一剩下的）** |
| `apk/delete` | ✅ **D1-C5b** |
| `apk-url` | ✅ **D1-C5a** |
| `download-mode` | ✅ **D1-C5a** |

## 契约（前端硬证据，`admin_dashboard.html:829-861`）

```js
const fd = new FormData();
fd.append("apk", file);                                  // ★ 字段名 = "apk"
const xhr = new XMLHttpRequest();
xhr.open("POST", ADMIN + "/api/apk/upload");             // ★ multipart
xhr.upload.onprogress = ...;                             // ★ 前端有进度条 ⇒ 需支持流式
xhr.onload = function() {
    const d = JSON.parse(xhr.responseText);
    if (d.ok) {
        // ★ 读 filename、size、tg_ok
        let msg = '上传成功：' + d.filename + '（' + fmtSize(d.size) + '）';
        if (d.tg_ok) msg += ' · Telegram 已同步';
        else if (target === 'tg') msg += ' · ⚠️ Telegram 同步失败，请检查文件大小（限 30MB）';
    } else {
        // ★ 读 error
    }
};
```

### 契约表

| 项 | 值 |
|---|---|
| **方法** | `POST ${ADMIN}/api/apk/upload` |
| **Content-Type** | **`multipart/form-data`** |
| **字段名** | **`apk`** |
| **成功响应** | `{ ok: true, filename, size, tg_ok? }` |
| **失败响应** | `{ ok: false, error }` |
| **前端预校验** | 文件名须 `.apk` 结尾 |
| **Telegram 上限** | **30 MB**（`:851`） |

## ★★ 数据源 = 文件系统（与 D1-C5b 的 `apk/list` 保持同一候选目录）

`landing.js:154-159` 的既有约定：
```js
const candidates = [
  process.env.LANDING_APK_PATH,
  path.join(process.cwd(), 'templates', 'apk'),
  path.join(process.cwd(), 'public', 'apk'),
].filter(Boolean);
```

**⇒ 上传须落到同一候选目录之一**（否则 `apk/list` 与 `/api/apk/download` 找不到）。

★ **执行者须与 D1-C5b 的 `apk/list` 保持一致**（若 C5b 已实现扫描逻辑，**复用同一函数**）。

## ★★ 必须实现的安全约束（本卡最大的风险面）

| # | 约束 | 理由 |
|---|---|---|
| **S1** | **文件名净化** | 拒 `../`、`/`、`\`、空字节等（**防目录穿越**） |
| **S2** | **落盘路径必须在候选目录内** | 落盘后 `realpath` 二次校验（**防符号链接逃逸**） |
| **S3** | **只接受 `.apk` 后缀** | 与前端一致；**不得**接受任意扩展名 |
| **S4** | **大小上限** | 建议 **50 MB**（Telegram 上限 30 MB，本地可略大） |
| **S5** | **需鉴权** | 管理台端点 ⇒ **无 token 必须 401**（沿用 C5a 的 scope 内 `authMiddleware`） |
| **S6** | **不得覆盖已有文件** | 同名时加后缀或拒绝（**须说明所选策略**） |

★ **S1–S2 是本卡的核心安全点** —— 上传端点是最典型的路径穿越入口。

## ★ 判据要求

| # | 断言 |
|---|---|
| U1 | 路由已注册（`${ADMIN}/api/apk/upload`，POST） |
| U2 | ★ **无 token ⇒ 401** |
| U3 | ★ **上传合法 .apk ⇒ 200 + `{ok:true, filename, size}`**，且**文件真落盘**（列目录可验证） |
| U4 | ★ **文件名含 `../` ⇒ 被拒或净化**（**不得**写到候选目录之外） |
| U5 | ★ **非 .apk 后缀 ⇒ 拒绝** |
| U6 | ★ **超大文件 ⇒ 拒绝**（须能验证；若难以构造 ⇒ 至少确认有上限配置） |
| U7 | ★ `apk/list` **能看到刚上传的文件**（与 C5b 一致） |
| U8 | 守护：`landing.js`、前端、`app.js`、`_manifest.sha256` 未改 |

★ **U3/U4 是核心** —— 必须证明"真落盘"与"穿越被阻"。

★★ **U4 的构造**：用文件名 `../../evil.apk` 或 `..%2F..%2Fevil.apk` 上传，
验证**候选目录之外没有生成文件**。

## 不在范围

- 不含 `apk/list` / `apk/delete`（**D1-C5b**）
- 不含 Telegram 真实同步（**若无凭据 ⇒ 返 `tg_ok:false` 即可**，并在报告说明）
- 不改前端、`landing.js`、`app.js`

## 证据要求

- 判据动前红 / 动后绿两次真实退出码
- 改动文件的 sha256 与 bytes
- ★ **U3/U4/U5 的真 HTTP 响应 + 落盘目录实测**
- ★ 明确说明：**Telegram 同步是否实现**（若未实现，须说明 `tg_ok` 的取值策略）

## 停靠点

1. 若 **Telegram 同步需要凭据** ⇒ **停下升级**（凭据属停靠点）
2. 若**落盘目录无法确定**（与 C5b 不一致）⇒ 停下升级
3. 若发现 **C5b 的 `apk/list` 尚未实现** ⇒ 停下升级（U7 依赖它）
4. 若**上传会影响 `_manifest.sha256`**（新增 .apk 文件）⇒ 登记（★ 已知：manifest 不含 .apk）
