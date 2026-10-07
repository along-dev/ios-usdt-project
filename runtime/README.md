# runtime/ —— 判据套件 + 运行器（复制自树外）

> ★ 本目录是 ⌛2026-10-07 架构线从 **`E:\ios漏洞\_integration\_fix_work\`** 复制的**纯脚本**（判据 + 运行器 + 启动脚本），补进 git 使仓库自足。
> ★ **629 文件 / 3.0 MB**（只含脚本，⛔ 不含工具链二进制/素材/数据目录）。

## 关键运行器

| 脚本 | 作用 |
|---|---|
| `iso_run.py` | ★ 隔离运行器（8900 + `qk_e2e_test`），跑判据**必须经它注入** `DSH_DB`/`DSH_API` |
| `run_regression_v2.py` | 回归执行器（六端口 + 判据套件） |
| `run_regression_go_strict.py` | Go 严格档回归 |
| `restore_services.ps1` | ★ 一键恢复六服务 |
| `seed_test_db.py` | 判据播种 |
| `fleet_status.py` | 线况盘点（只读） |
| `verify_*.py`（96 个） | 判据套件 |

## ★★ 依赖警告（clone 下来「能跑」的前提）

这些脚本**内部硬编码了 `E:\ios漏洞\...` 路径**（素材 + 工具链），⛔ 复制进 git **并未改写**这些路径。
⇒ clone 到新机器后，要真正跑起来，需满足**三棵树齐备**：

| 树 | 内容 | 在本仓库？ |
|---|---|---|
| `E:\USDT项目`（本仓库） | 源码 + 文档 + 判据脚本（runtime/） | ✅ |
| `E:\ios漏洞\`（**素材**） | iOS 载荷源（`ios15-17版本漏洞\coruna\platform_module.js` 等） | ⛔ **须自备** |
| `E:\ios漏洞\_integration\_fix_work\_toolchain\`（**工具链**） | go / mariadb / mongodb / redis | ⛔ **须自备**（或用标准工具链，版本见 `DEPLOY.md`） |

★ **要消除这层依赖**（让仓库真正自足），须做「路径改写」：把脚本内的 `E:\ios漏洞\...` 改成相对路径或环境变量——这是 82+ 脚本的工程，**尚未做**（属远期设想）。

## 完整运行所需（一句话）

**源码（git clone）+ 工具链（自备 go/node/mysql/mongo/redis）+ 素材（自备 iOS 载荷源）** —— 三者齐，按 `09-docs/DEPLOY.md` 起服务、按 `runtime/` 跑判据。
