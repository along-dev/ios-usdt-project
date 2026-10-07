# T91 执行记录 —— `loader-pack.js` 的 `DEFAULT_KEY` 改从环境变量读

> **卡**：`T91` @ `55251a5bf0109cb164d13df5888f5c479fe0e52388c4ea2856a6ef37c8ced2d9` / 3609 ✓（开工前现算吻合）
> **档**：R1（★ 后端单件 · 在运行路径）｜ **执行**：苹果线接班人 `local_b756a387-c0e7-4d18-bcb1-62485162a295` ｜ **收口**：总调度第六任
> ★ **证据纪律**：★★ **本件 ⛔ 不含 key 值**（★ 一律 `行号 ＋ 脱敏前后缀`／`<REDACTED-64hex>`）✓ ｜ **落款**：⌛2026-10-06T17:2x

---

## 〇 · 一句话

★ **`DEFAULT_KEY` 已从源码字面量改为 `process.env.LOADER_PACK_KEY`**（★ 未设即 **fail-loud**）⇒ ★★ **`V3` 证明"没改行为、只挪了存放处"**：★ 注入<同一个 key> ⇒ 产物 sha **与改前逐位相同** ✓

---

## 一 · ★ 只读勘察（★ 卡 §三 要求：先弄清消费方）

| 项 | 现读结果 |
|---|---|
| **定义处** | `02-backend-node/src_restored/core/crypto/loader-pack.js:14` —— `const DEFAULT_KEY = '<REDACTED-64hex>';`（★ 局部名 `DEFAULT_KEY`，★ **不是** env） |
| **用法** | `:61`（改前）`const keyHex = key || DEFAULT_KEY;` ⇒ ★ 它是 **`packLoader(dylibData, key)` 的<回落>** |
| **★★ 消费方** | `02-backend-node/src_restored/plugins/channel/services/creator.js:31` —— ★★ **`await packLoader(loaderPatched)`（<ins>不传第二参</ins>）** ⇒ ★ **实际就是靠这个默认值** |
| **★★ 可达性** | `creator.js` 由 `plugins/api/routes/channels.js:7` 引入 ⇒ ★★ **API 路由 ⇒ 运行路径** ✓ |
| **配置口径** | `src_restored/config/index.js` 的 `loadConfig()` **全是 `process.env.X \|\| <源码字面量>`、⛔ 无配置文件** ⇒ ★ **"部署配置"在本项目<ins>就是 env</ins>** ✓ |

★ **停止条件判定（★ 不触发）**：★ 消费方需要的**不是"源码内默认值"本身**，★ 而是**一个 key** —— ★ 改从 env 取即满足；★ 且★ 本改动 **⛔ 不波及任何已加密产物**（★ 未重加密、未轮换）✓
★★ **但须显式登记部署要求**（见 §四）：★ 若不注入该 env，`createChannel` 会 fail-loud（★ **不是应用启动失败** —— 该路径在**建渠道**时才走）✓

---

## 二 · 改动（★ 仅 `loader-pack.js` · 共 3 处）

| # | 位置 | 改前 → 改后 |
|---|---|---|
| 1 | `:14` 常量 | `'<REDACTED-64hex>'` ⇒ **`process.env.LOADER_PACK_KEY \|\| ''`**（＋ 3 行注释写明**部署要求**与**非轮换**） |
| 2 | `packLoader` 入参文档 | 「默认使用内置密钥」⇒ 「默认取环境变量 `LOADER_PACK_KEY`；⛔ 未设即 fail-loud」 |
| 3 | `packLoader` 体内 | ★ **新增 fail-loud 守卫**：`if (!keyHex) throw new Error('LOADER_PACK_KEY 未设置…')` —— ⛔ **不静默产出"永远解不开"的产物** |

★ `git diff --numstat` ⇒ **`9  2`**（★ 删除 2 ＝ 那两行被替换；★ 新增 9 ＝ 注释 ＋ 守卫）✓
★ 受改件现 sha ＝ **`7cc113a97d1d703e0411cd49a621ba8b3058587cc05f26c0f9853832d39027e9`**（改前 `c141fac5d0035014dde8bdf5aaddd60591e7ad64cc70c678a3792b6a61f416e5`）✓

---

## 三 · 验收读数（★ 真退出码）

### `V1` ★ 先证"硬编码"
★ 改前 `:14`（★ 脱敏展示）：`const DEFAULT_KEY = '<REDACTED-64hex>';` ⇒ ★ **确为字面量** ✓（★ 取自 `git show HEAD:`，⛔ 未复抄）

### `V2` ★ 修后源码内**该 key 零命中**
```
grep -rl <key> --include=*.js 02-backend-node/src_restored/   ⇒ 命中文件数 = 0  ✓
```
★★ **一处须说明的范围问题（如实报）**：★ 同一 key 在 **`02-backend-node/src/app_dist_core_crypto_loader-pack.js:14`** **仍存在（1 处）** —— ★ 而 `02-backend-node/src/` 是**「UNMODIFIED ORIGINAL BASELINE」**（★ 依据：`package.json` 的 `start:flat` 脚本自述 ＋ `src/README-NONAUTHORITATIVE.md`）⇒ ★★ **它是<故意保留不动的基线参照>、⛔ 不是可改的源码** ⇒ ★ **`V2` 的命中范围应定为 `src_restored/`（权威源码）** ✓ —— ★ **请裁**：★ 若你要连基线副本一并处置 ⇒ ★ 那**不是本卡范围**（★ 改它＝改"参照物"，★ 会破坏它的基线意义）

### `V3` ★★★ 兼容性**不受损**（★ 本卡最重要的一条）
★ 测试台：`_fix_work/_T91_work/v3_harness.mjs`（★ 固定样本 `Buffer.alloc(4096, 0x41)`；★ 只打印**输出**的 sha／长度，★ **⛔ 不打印 key**）
★ **key 的注入方式**：★ 经 **env** 传入；★ 取值**现从 `git show HEAD:` 提取进 shell 变量**（★ **⛔ 从未落进任何件**）✓

| 跑 | 条件 | `OUT_SHA` | 结论 |
|---|---|---|---|
| **改前基线** | 不注入 env（★ 走源码字面量） | `a0c088f422cc921334bd3201bee30fb758b8c1571b30df8ad962d790e1ec502c` | ★ 基线锚 |
| **负控（改前）** | 注入**另一个** key（全零 hex） | `37cdf67c2330e31c0e522e2e4c5556c4c4a0e753f93071c47cdaddb6bbbd50d7` | ★ **与基线不同** ⇒ ★ **测试台能分辨 key** ✓ |
| **★★ 改后** | 注入**原 key** | **`a0c088f422cc921334bd3201bee30fb758b8c1571b30df8ad962d790e1ec502c`** | ★★ **与改前<逐位相同>** ✓ ⇒ ★ **"没改行为、只挪了存放处"** ✓ |
| **负控（改后）** | 注入全零 | `37cdf67c2330e31c0e522e2e4c5556c4c4a0e753f93071c47cdaddb6bbbd50d7` | ★ 与改前负控**一致** ⇒ ★ 确定性 ✓ |
| **附加控** | **不注入** | ★ **抛错**（`loader-pack.js:67`，`LOADER_PACK_KEY 未设置：拒绝用空密钥打包…`） | ★ **fail-loud 生效** ✓ |

★ 全部 5 跑的输出长度均为 **124 B**（★ 同一固定样本）✓

### `V4` ★ 部署要求（★ 已写进源码与件）
★ **部署须注入 `LOADER_PACK_KEY`（64 hex）** —— ★ 否则 `createChannel` 会 **fail-loud**（★ 应用**启动不受影响**，★ 该路径在**建渠道**时才走）✓
★ 已落 **`:14` 上方注释**（★ 源码内可见）＋ 本件 §一／§四 ✓

---

## 四 · ⛔ 未做（★ 如实）

★ ⛔ **未改任何已加密的产物／载荷**（★ 密文仍可用同一 key 解开 —— ★ 已由 `V3` 的**逐位相同**证明）· ⛔ **未轮换**（★ 轮换＝重加密全部产物 ⇒ ★ 另一张卡 ＋ Owner）· ⛔ **未碰 `05-ios/**`／`iso_run.py`／`chain-router.js`／`_manifest.sha256`** · ⛔ **无 git 写** · ⛔ **未碰业务库** · ⛔ **未改基线副本 `src/`** ✓

---

## 五 · 请裁

1. ★★ **`V2` 范围**：★ 是否认同"权威源码 ＝ `src_restored/`"⇒ 基线副本 `src/` 的 1 处**保留不动**（★ 它是"UNMODIFIED ORIGINAL BASELINE"）？
2. ★ **部署侧**：★ `LOADER_PACK_KEY` 的注入**是否需经 Owner**（★ 它属部署配置）？★ 我**未改任何部署件** ✓
3. ★ 本卡 **R1 单审** ⇒ 请派复核

---

*本件由**苹果线接班人** `local_b756a387-c0e7-4d18-bcb1-62485162a295` 产出 · ⌛2026-10-06T17:2x · ★ **索引由调度代登** ✓*
