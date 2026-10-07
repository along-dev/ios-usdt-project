# 06-android/reference —— 参照素材目录

> **本目录是「参照素材」，不是投递给设备的 APK。**
> **投递包见 `06-android/apk/`（D2-C4）。两者必须严格分开，不得混放。**

## 目录职责

| 路径 | 性质 | 说明 |
|---|---|---|
| `06-android/reference/apk/` | **参照素材** | 从证据树取回的业务 APK 原件，仅用于比对、脱壳链复现、哈希溯源。**不进入投递流程。** |
| `06-android/apk/` | **投递物** | 实际交付/投递到设备侧的 APK 包（D2-C4 负责）。 |

## `reference/apk/` 内容

业务 APK ×5（按 sha256 去重后的唯一集），逐个校验一致。完整哈希与字节数见同目录
[`_MANIFEST.txt`](apk/_MANIFEST.txt)。

| 文件名 | 字节 | 用途 |
|---|---:|---|
| `japapp.apk` | 16,603,645 | 载荷 APK |
| `child_milkstream.apk` | 15,789,421 | 载荷 APK（子） |
| `myav.apk` | 24,139,973 | 样本 |
| `strip.apk` | 16,043,281 | ★ 脱壳链 L1 入口样本 |
| `inner_b.apk` | 7,748,611 | ★ 脱壳链 L2 产物（b.apk） |

合计 80,324,931 字节（约 76.6 MiB）。

### 已排除内容

- **系统模拟器 Overlay APK（16 个文件 / 16 个唯一哈希）**：位于
  `E:\ios漏洞\recon\_sdk\sdkroot\emulator\resources\skins\android-36\...`，是 AOSP 模拟器皮肤资源，
  与业务无关。判别方式：文件名匹配 `Overlay`（`*Overlay.apk`），大小均在 8–21 KB 量级。
- **同哈希副本**：`jxrdxzps.apk`、`9812f565298c.apk` 与 `japapp.apk` 同哈希；
  `child.apk`（×2）与 `child_milkstream.apk` 同哈希。均不计为独立唯一文件，不重复搬运。

## 约束

- 本目录**只增不改**：不得改写已落盘的 APK 二进制。
- 不得在本目录放入投递物；不得把本目录的 APK 直接当作投递包使用。
- `06-android/tools/*.py` 属 D0-C1 范围；`_manifest.sha256` 不得改动。
