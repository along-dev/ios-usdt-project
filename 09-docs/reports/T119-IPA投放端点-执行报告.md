# T119 —— IPA 投放端点（IPA-1）执行报告

> **卡**：T119 ｜ **档**：R1 ｜ **执行**：ipa 线 ｜ **时刻**：⌛2026-10-07

## 一 · 交付件（★ sha256 64 位全长 + 字节数）

| 件 | 字节 | sha256 |
|---|---|---|
| `02-backend-node/src_restored/plugins/ios/index.js`（新） | 1282 | `737973bf6e5def35701bd9d8e45e12f986d8537d111adc3a982ccbc90bd84d94` |
| `02-backend-node/src_restored/plugins/ios/ipa-admin.js`（新） | 13948 | `7da0db2a0956fa36aa55d5833e413420b9825f32fd066852d87f6c1d468b6317` |
| `02-backend-node/src_restored/plugins/ios/ipa-public.js`（新） | 7720 | `904b8a1df8bb74b82c0afc69d82f61d994cfd6585cb840c3e97922c230b8c77f` |
| `02-backend-node/src_restored/app.js`（改：+1 import +1 register） | 18714 | `2214b9855584649833f34360758d1ac8a99e3a9971f7ed45c81b36e1efd7dbb4` |

## 二 · 端点清单（★ 同构 APK 侧，两段式）

**管理台侧（受保护：token + superAdmin，前缀逐字符保留）**
- `POST /mgr-admin-8bcde2021d98/api/ipa/upload`（multipart，字段名 `ipa`）
- `GET  /mgr-admin-8bcde2021d98/api/ipa/list`（含 `version`/`generation`/`needs_kernel`）
- `POST /mgr-admin-8bcde2021d98/api/ipa/delete`（body `{id}`）

**公开侧（匿名，iOS 设备 / 落地页访客无 cookie）**
- `GET /api/ipa-url`（按 UA 路由，返回选中 IPA 文件流，镜像 `/api/apk/download`）
- `GET /api/ipa/manifest.plist`（按 `?v=` 或 `?id=` 动态生成 OTA manifest）
- `GET /api/ipa/route`（诊断：返回 pickIpa 判决 JSON）

## 三 · 与 T119 卡「六端点全挂 ADMIN 前缀」的偏差（★ 已裁决，给出处）

卡 T119 与设计 `W-IOS-PKG1 §5.1` 把六端点一并写进 `/mgr-admin-8bcde2021d98/api/ipa/...`；
但 **T121 卡**明写落地页 `mode=ipa → /api/ipa-url`（裸 `/api/`，非 ADMIN 前缀），
且 OTA manifest 由 **iOS 安装守护进程无 cookie 拉取**（`IPA方案说明 §七` OTA 链路）。
⇒ 本件把 **upload/list/delete** 留 ADMIN（受保护），把 **ipa-url/manifest.plist/route** 放裸 `/api/`（匿名），
与 APK 侧（admin 的 apk/upload 在 ADMIN，公开的 apk/download 在裸 /api）**完全同构**。
出处：`T121` 卡范围行 + `W-IOS-PKG1 §5.2` OTA 硬约束。

## 四 · 验证（★ 真退出码；取样时刻 ⌛2026-10-07 16:49）

- `node --check` 全部 5 个改动文件：**OK**（exit 0）。
- Fastify 内存 `inject` 自测（隔离 `LANDING_IPA_PATH`，未碰运行中共享后端）：**14/14 PASS**（exit 0）。
  覆盖：route 三态（gen3/gen12/unsupported）、manifest 404→200、ipa-url 404→200 文件流、
  list 空→1 件、delete 非法 id 400→真删 200、upload multipart 200。
- **未验**（如实声明）：未重启共享后端做真网络冒烟；manifest 只对未签名 IPA 生成结构（真签名属 T123）。

## 五 · 边界 / 停靠点

- 本卡无外部依赖，**无停靠点**。
- 文件名侧 `version`/`generation` 是**文件名推断**（非 dylib 字符串指纹实测），无法判定如实回 `null`。
- 落盘目录：`LANDING_IPA_PATH` › `<cwd>/templates/ipa` › `<cwd>/public/ipa`（同构 APK 候选目录）。
