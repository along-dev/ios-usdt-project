# acs_* 机制研究登记 —— W-AND-04（R3 研究轨道）

> **结论二态：可解（L1 已解）；密钥流【在】产物内，但消费它的代码【不在】产物内。**
> 旧说法「acs_mi / acs_sm 加密代码不在产物中」**半对**：`myav.apk::classes6.dex` 内**确有** 132 字符密钥流常量（string idx 3202），但**没有任何代码用它解混淆资产**（证据见 §三·B）。
> 全部结论来自磁盘实读、本地复算与 dex 反汇编（androguard 4.1.4）；未做任何写操作。

---

## 一 · 搜索范围与命中数（判据）

| 项 | 值 |
|---|---|
| 扫描单元 | **5,120**（`06-android/{full,stage,apk/*,tools}`，APK 内按 zip 条目展开） |
| 扫描总字节 | **550,344,789 B**（约 525 MiB） |
| 检索模式 | `acs_mi` `acs_sm` `acs_els` `acs_stct` `acs_` `0gvw74arcr5sml` `go0bxm7p04` `l3leulkanyb` `lhenl7ped` `javax/crypto` `SecretKeySpec` `IvParameterSpec` `Cipher` `AES` `DESede` `Base64` `decrypt` `xor` 等 19 条 |
| **关键命中** | `myav.apk::classes6.dex` **offset 233719** 处存在 **132 字符常量** `nktdhxrb…feshlc1`，**即观测到的 XOR 密钥流本身** |
| 佐证命中 | `myav.apk::classes6.dex` 同时含 `javax.crypto` ×1 · `Cipher` ×1 · `doFinal` ×2 · `Base64` ×4 · `xor` ×1 |
| ★ **反证命中** | **反汇编全部 18 个 dex**：K 的字符串索引 **3202** 只被 **1 处** `const-string` 引用；该值存入静态字段 `cobaltooyvflsw->sundialiivhutgno`；而该字段在**全 APK 内被读取 3 次，全部是 `equals()` 防篡改守卫**，**没有任何 XOR 循环**（见 §三·B） |
| 假阳性（已排除） | `acs_` 在 `child_milkstream.apk::classes.dex` 与 `myav.apk::classes14.dex` 的命中，均为 **`TACACS_USER_IDENTIFICATION`**（网络协议常量），与本主题无关 |
| **未命中** | `acs_mi` / `acs_sm` 作为**标识符**在**任何 dex 中 0 次**（仅作为 `myav.apk` 内的 assets 文件名出现） |

**`acs_*` 资产的原产地**：`06-android/apk/samples/myav.apk` 内含
`assets/acs_els.html` (19,352) · `assets/acs_mi.html` (19,244) · `assets/acs_sm.html` (47,360) · `assets/acs_stct.html` (9,704)
—— 字节数与本轮 `stage/acs_*.html` **逐一相同**，内容不同（见 §二）。

---

## 二 · 三种副本的精确定义（实测）

设 `P` = 原始载荷（对 els/stct 即 HTML 文本）：

| 副本 | 形式 | 验证 |
|---|---|---|
| `06-android/full/acs_X.html` | `base64(P)`（含末尾 `=` 填充） | 实测 |
| `06-android/stage/acs_X.html` | `[int32 BE 文件总长] + full/acs_X.html[:-4]` | 长度前缀 = 文件自身长度（19352 / 19244 / 47360 / 9704），四项全中 |
| `06-android/apk/samples/myav.apk::assets/acs_X.html` | `full/acs_X.html` **逐字节 XOR 密钥流 K** | 实测 |

★ **`stage/` 的长度前缀与 `full/` 同源**，与 `stage/*.bt` 的 `[4B 长度] + full[:-4]` 规则一致（本条独立复核成立）。

---

## 三 · L1 机制（**已解**）

```
明文 P  --base64-->  S  --逐字节 XOR K（周期 132）-->  myav.apk 内 assets/acs_X.html
```

- **密钥流 K** = 常量 `nktdhxrbjfrdnxnaahnlrmwzyzjtckfpfwmvgjqjvhqbfugqbtomyzhkurnbvkekpfogfxbdhlgumbukbjlipyrcgljsavcbfsbqiqhclysnbozwnmpnlfofaypvtfeshlc1`
  （**132 字符**：131 个小写字母 + 数字 `1`；以 ULEB128 长度前缀 `\x84\x01` 存于 **`classes6.dex:233719`**）。
- K **循环使用，周期 132**：实测「myav 副本 XOR full 副本」得到的密钥流在前 **8,192 字节**上与 `K` 按 132 取模逐字节相等（`True`）。K 的取值集合 = `{0x31} ∪ [a-z]`（27 个值）——正是「字母 + `1`」的指纹。
- ★ **`acs_els.html` / `acs_stct.html`：L1 即全部** —— 解出 `<!DOCTYPE html>\r\n<html lang="en">…` 的 HTML，与 `stage/acs_els.html.dec`（14,511 B）同源。

### 三 · B —— ★ **消费 K 的代码【不在】产物内**（本轮反汇编实证）

对 `myav.apk` 的 **18 个 dex 全部反汇编**（androguard 4.1.4，逐条读指令操作数，非文本搜索）：

| 检查 | 结果 |
|---|---|
| K 的字符串索引 | `classes6.dex` string **idx 3202**，长度 **132**（与实测密钥流等长） |
| `const-string` 引用它的位置 | **全 APK 仅 1 处** —— `Ltracker/transcriber/converter/cobaltooyvflsw;->oakwoodqqxtowpf()Ljava/lang/String;` |
| 该常量存入 | 静态字段 `Ltracker/transcriber/converter/cobaltooyvflsw;->sundialiivhutgno Ljava/lang/String;`（由 `<clinit>` 赋值） |
| **谁读这个字段** | **全 APK 共 3 处**（`classes10/13/17.dex`），**全部同一种惯用法**：<br>`sget-object v0, …->sundialiivhutgno` → `new-array`(9B) + `new-array`(12B) → `k50->a([B[B)Ljava/lang/String;` → `String.equals()` |
| **有没有 XOR 循环** | **没有**。3 处读取点都是**防篡改守卫**（拿运行时算出的诱饵串与 K 比对），不是解混淆。 |
| 原生库 | 仅 `libconscrypt_jni.so`（Conscrypt/TLS）与 `libspake2.so`（SPAKE2）——**均为通用库，K 不在其中** |

⇒ **K 是「钥匙」，但「锁」不在这个 APK 里。** 反混淆（`资产 XOR K` 再 base64）由 **APK 之外的构建期工具**施加；apk 内的 K 只是被留下（并被用作 `equals` 守卫的比对值）。

`cobaltooyvflsw` 是什么：该类的 `<clinit>` 逐条解密并装载**整包字符串常量**（形如 `invoke-static …->volcanourwitijjtxjs()Ljava/lang/String;` → `sput-object`），配 `ۥ۟ۜۛ…` 这类只喂给 `hashCode()` 的**诱饵串**（配合 `sparse-switch` 做控制流混淆）——是**通用字符串加固壳**的产物，**不是 acs 专用解密器**。

---

## 四 · L2（仅 `acs_mi` / `acs_sm`，**机制已定性 / 实现未定位**）

L1 还原并 base64 解码后，`acs_mi`/`acs_sm` 得到的**不是** HTML，而是一段二进制（头 `80 02 21 e9 21 36 4f …`），**仍有第二层加密**。

实测证据：

1. **明文已知前缀（crib）**：两文件的明文前 **149 字节**相同，即
   `<!DOCTYPE html>\r\n<html lang="en">\r\n\r\n<head>\r\n    <meta charset="UTF-8">\r\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\r\n`
   （来自 `stage/acs_mi.partial.html` / `acs_sm.partial.html`）。
2. **两文件共用同一段密钥流**：用 `acs_mi` 密文 XOR 上述 crib 得到密钥流后，**套用到 `acs_sm` 上，前 149 字节精确还原同一 crib** ⇒ 二者密钥流相同。
3. **共享密文前缀 272 字节**（`mi` 14,432 B / `sm` 35,520 B）⇒ 该区间**明文完全相同**。
4. ⇒ **L2 是「固定复用密钥流的流密码」**，构成教科书式 **two-time pad**（`ct_mi ⊕ ct_sm = pt_mi ⊕ pt_sm`）。

**未定位**：产生该密钥流的实现（PRNG 种子/算法）**未在产物中找到** —— 它在 `classes6.dex` 之外，或被混淆/内联，本轮检索模式未命中。

---

## 五 · 证据局限（如实声明）

- `myav.apk` 与 `full/` 两份副本**均已持有**，故 L1 密钥流是**实测差分所得**，非反推。
- ★ **已做** dex 反汇编（androguard 4.1.4，18 个 dex，逐条指令操作数）；**结论是 K 无消费者**（§三·B）。**未做** java 级还原与反射/动态装载路径排查 —— 故「消费代码不在产物内」是**在本 APK 的 dex + 原生库范围内**的结论，**不等于**「在设备运行期一定不执行反混淆」。
- L2 的「**同一密钥流**」由 **149 字节 crib 精确复现**证明；但**其余区间的明文未恢复**。two-time pad 原则上可 crib-drag，本轮**未做**完整恢复。
- `acs_mi`/`acs_sm` 的**明文是否为 HTML 页面**：仅由前 149 字节 crib 支持，**后段未验证**。

---

## 六 · 建议下一步（不在本卡范围）

1. ~~对 `myav.apk::classes6.dex` 做 smali 级反汇编~~ —— **本轮已做**，结论见 §三·B（K 无消费者，是「钥匙在、锁不在」）。
2. 要把「锁在哪」查清，剩下两条路：① 排查**反射 / `DexClassLoader` / 动态装载**路径（静态扫描覆盖不到）；② 对照**构建期工具**（外部混淆器把 K 同时写进常量池与资产，APK 内只留残迹）——需要构建链证据，本卡没有。
3. `acs_mi`/`acs_sm` 的 two-time pad：以 `acs_els`（已解 HTML）为模板做 **crib-drag**，可尝试恢复正文（**不依赖**找到锁：K 已实测在手）。

---

*本文件由安卓线 W-AND-04 产出，2026-10-03。所有数字均为本轮实测，可复跑。*
