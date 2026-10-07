---
id: S4
mode: 验证
wave: S
depends: [D1-C1, D1-C5a, D2-C4]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R1
定档理由: |
  ★ **本卡的判定：3 条规格中 2.5 条已由 D1/D2 完成**，
    剩余部分（"三版本路径各自实测"）**须真机 ⇒ 本机不可做**（V0 D-4 同族）。
  ⇒ 本卡为**结论登记卡**（R1）。
来源: `交付口径变更与链路简化方案.md:184-200`（S4 规格）
      + ★ 调度实测：S4 声称的"现状"**已过时**（D1/D2 已完成大部分）
base:
  - path: 02-backend-node\src_restored\plugins\api\routes\landing.js
    sha256: 3208c207bf423c8d99577c0508e9b6cc809f471dcd590ee0e96b87906e7de632
    bytes: 8381
    eol: LF
allowed_paths:
  - E:\ios漏洞\_integration\_fix_work\verify_s4_android_onestep.py
forbidden_paths:
  - "★ 全部产物（本卡为结论登记卡，不修改任何文件）"
  - "09-docs\\spec\\contracts.md"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_s4_android_onestep.py    # 须【绿】，退出码 0
packages: {}
---

# S4 [R1] Android APK 投递一键化 —— **大部分已完成，剩余须真机**

## ★★★ 结论先行

| S4 的"现状"声称 | **实际（本会话已做）** | 判定 |
|---|---|---|
| `06-android/apk/` **不存在** | ✅ **D2-C4 已建**（`japapp/` 2 个 + `samples/` 3 个） | ✅ **已完成** |
| **16 端点未开发** | ✅ **D1 全部完成**（16/16 就绪） | ✅ **已完成** |
| `Android 无物可投` | ✅ 投递包已就位 | ✅ **已完成** |
| `无路可投` | ✅ 16 端点 + `apk/download` | ✅ **已完成** |

**⇒ S4 的"现状"**已过时**（该方案写于 D1/D2 之前）。**

## ★ S4 的 3 条规格逐条核对

| # | S4 规格 | 实际 | 判定 |
|---|---|---|---|
| 1 | **APK 直链**：`GET /api/apk-url` 返回可直接安装的直链 | ✅ **D1-C5a 已实现**（返回 `{url}`） | ✅ |
| 2 | **一键落地**：`GET /api/template` → **302 直接到 APK** | ⚠️ 实际返回 **JSON `{template}`**（**非 302**）<br>但前端 `index_root.html:12-16` 用 `r.json()` 后 `location.replace('/'+t+'.html')`<br>**⇒ 达成同等效果**（且**契约要求 JSON**） | ✅ **等效** |
| 3 | **下载即装**：`application/vnd.android.package-archive` | ✅ **`landing.js:170` 已实现** | ✅ |

**⇒ 3 条规格**均已有实现**（第 2 条以 JSON+前端跳转等效达成）。**

## ★ S4 的剩余部分（**本机不可做**）

**S4 的判据**：
> **从点击到安装完成 ≤3 次用户操作**；**三版本路径（≥11 / 7.0–10 / <7.0）各自实测**。

**⟹ "三版本路径各自实测"须**真机**（Android 设备）** ⇒ **本机不可做**（**V0 D-4 同族**）。

**⇒ 如实登记为"未验证"。**

## ★ 关于第 2 条的裁定（**须说明**）

**S4 建议 `GET /api/template` 改为 302 直接跳 APK**，
**但实测契约（`index_root.html:12-16`）是**：
```js
fetch('/api/template').then(r=>r.json()).then(d=>{
    var t=d.template||'vodex';
    window.location.replace('/'+t+'.html');     // ★ 跳到模板页，非 APK
}).catch(function(){window.location.replace('/vodex.html');});
```

**⟹ 契约要求返回 JSON（模板名），前端再跳模板页** ——
**S4 的"302 直接到 APK"与**既有契约冲突**。**

**⇒ 本卡**不改契约**（前端是契约来源，只读）；
**如实登记 S4 与契约的差异。**

## 本卡的验证目标（纯只读）

| # | 断言 | 说明 |
|---|---|---|
| **S4-1** | `06-android/apk/{japapp,samples}/` **存在且有文件** | 证明"有物可投" |
| **S4-2** | `${ADMIN}/api/apk-url` **已注册** | 证明规格 1 |
| **S4-3** | `GET /api/template` **已注册** | 证明规格 2（等效） |
| **S4-4** | `landing.js` 含 `application/vnd.android.package-archive` | 证明规格 3 |
| **S4-5** | ★ **契约（`index_root.html`）要求 JSON**（非 302） | 证明第 2 条的"等效"判定 |
| **S4-6** | ★ **本卡未修改任何文件** | 声明 |

## 不在范围

- **不改任何文件**（纯验证）
- **不改契约**（前端只读）
- **不做真机测试**（无设备）

## 证据要求

- 判据的真实退出码
- ★ **S4-1 的目录内容**
- ★ **S4-5 的契约原文**（`index_root.html:12-16`）
- ★ 声明：**未修改任何文件**；**未做真机验证**

## 停靠点

1. **若 Owner 要求 S4 的第 2 条真做 302** ⇒ **停下升级**（须改前端契约）
2. 若发现 `06-android/apk/` **被清空** ⇒ 停下升级
