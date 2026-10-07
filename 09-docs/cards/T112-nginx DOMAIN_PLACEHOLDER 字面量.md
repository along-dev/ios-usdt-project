# T112 —— nginx DOMAIN_PLACEHOLDER 字面量（`G-04`）

> **卡**：T112 ｜ **来源**：★ Owner「产品面缺口14项立项」· 架构线立项建议件（`产品面缺口14项-立项建议_20261007.md`）｜ 总调度第七任立卡
> **档**：**R1** ｜ **执行**：待派 ｜ **收口/提交**：总调度第七任
> **状态**：已立卡 · 排队待派 ｜ **日期**：2026-10-07

## 一 · 范围

- 改 `08-infra/nginx/default.conf.template:115` `server_name DOMAIN_PLACEHOLDER;` → `${LANDING_DOMAIN}`（与 `ADMIN_DOMAIN` 同法），`docker-compose.yml`/部署说明补默认值

## 二 · 验收（★ 真退出码；★ 取码不接管道）

- V1 静态 `grep -n "DOMAIN_PLACEHOLDER" 08-infra/nginx/default.conf.template` → 0；V2 路径等价验证（沿用 L049 9/9 手法）

## 三 · 边界

- ★ 无（验法走静态＋路径等价、⛔ 不依赖真 nginx）
- ★ 承本批正向格式：★ 报件 `sha` 前重算 · ★ 报计数同句写取样时刻 · ★⛔ 不得把凭据值写进件/报文
