# T121 —— 落地页挂载 IPA 分支（IPA-3）执行报告

> **卡**：T121 ｜ **档**：R1 ｜ **执行**：ipa 线 ｜ **时刻**：⌛2026-10-07

## 一 · 交付件

| 件 | 字节 | sha256 |
|---|---|---|
| `04-landing/runtime/landing-runtime.js`（改：+resolveDownloadUrl） | 5903 | `63581062c4174c04ddb0a2118112d760e67eeb6211011b1d7240c20271727ad6` |

## 二 · 改动

`landing-runtime.js` 的下载目标由写死 `DOWNLOAD_URL = "/api/apk/download"` 改为运行时 `resolveDownloadUrl()` 解析：

| 页面声明 | 下载目标 |
|---|---|
| （无声明，默认） | `/api/apk/download`（APK 分支，原行为不变）|
| `<body data-ipa>` 或 `data-ipa="true"` | `/api/ipa-url` |
| `<body data-ipa="https://...">` | 该显式 URL |
| `<body data-mode="ipa">` 或 `?mode=ipa` | `/api/ipa-url` |

★ 与 APK 分支同构：APK 走 `window.location.assign("/api/apk/download")`，IPA 走 `window.location.assign("/api/ipa-url")`。
★ 注：R1 只做「取 IPA 下载地址」；`itms-services://` OTA 包装属 T123（需证书）。

## 三 · 验证（★ 真退出码；取样时刻 ⌛2026-10-07 16:50）

- mock DOM 加载**真实** `landing-runtime.js` 源码，触发 `window.landingDownload()`，断言 `location.assign` 目标：**7/7 PASS**（exit 0）。
  覆盖：默认→apk、data-ipa 空/true/显式 URL、data-mode=ipa/apk、?mode=ipa。

## 四 · 边界 / 停靠点

- 本卡无外部依赖，**无停靠点**。
- 未做真实浏览器渲染验证（无 iOS 真机）；`itms-services` 安装链路属 T123/T124。
