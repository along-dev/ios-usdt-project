# T119 —— IPA 投放端点（`IPA-1`）

> **卡**：T119 ｜ **来源**：★ Owner「准备 IPA 方案执行」· 架构线方案说明（`IPA方案说明.md`）｜ 总调度第七任立卡
> **档**：**R1** ｜ **执行**：待派 ｜ **收口/提交**：总调度第七任
> **状态**：已立卡 · 排队待派 ｜ **日期**：2026-10-07

## 一 · 范围

- `/mgr-admin-8bcde2021d98/api/ipa/{upload,list,delete,ipa-url,manifest.plist,route}`（★ 同构 APK 侧投放端点）

## 二 · 验收（★ 真退出码；★ 取码不接管道）

- V1 各端点真 HTTP 通（upload/list/delete/ipa-url/manifest.plist/route）；V2 与 APK 侧行为同构（★ 对照既有 APK 端点）

## 三 · 边界

- ★ 无外部依赖；⛔ 不触证书/真机
- ★ 停靠点：无
- ★ 承本批正向格式：★ 报件 `sha` 前重算 · ★ 报计数同句写取样时刻 · ★⛔ 不得把凭据值写进件/报文
