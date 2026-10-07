# ios-usdt-project

把 `../IOSUSDT/USDT项目` 的**核心业务闭环**在本地跑起来的运行版工作区。

- **运行说明 / 端口表 / 验证结果 / 已知问题** → 见 [`local/README-local.md`](local/README-local.md)
- **一键启动** → `cd local && bash start-all.sh`
- **一键停止** → `cd local && bash stop-all.sh`
- **登录** → 管理台 http://127.0.0.1:8898 ，`admin` / `123456`

模块职责（与原项目一致，详见 `README.md` 与各模块 README）：

| 模块 | 本地是否运行 |
|---|---|
| `01-backend-go` | ✅ Go 后端 (8888) |
| `02-backend-node` | ✅ Node 后端 (3313) |
| `03-web-admin` | ✅ 管理台 (8898) |
| `04-landing` | ✅ 落地页 (8080) |
| `07-db` | ✅ 数据库 schema/迁移（容器 13306/27018/16379） |
| `05-ios` / `06-android` | ⛔ 只读载荷，不运行（设计如此） |
| `10-sweeper` / `11-payment` | ⛔ 未运行（见运行说明 §八） |

> ⚠️ 本目录为**本地沙箱运行配置**，未改动源素材 `../IOSUSDT/`；凭据均为本地固定值。
