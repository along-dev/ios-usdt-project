# Filza 能不能读到密钥 —— 结论

> 基于 FilzaSlop 源码与 `pe_main.js` 实际代码核实。
> **静态分析，未真机验证。**

---

## 一、直接回答

| 密钥类型 | 第 1/2 代（内核链） | 第 3 代（MHA-MCM） |
|---|---|---|
| **钱包助记词/私钥**（MetaMask/imToken 等容器内） | ✅ **能** | ✅ **能**（class 2 容器） |
| **`keychain-2.db`** 文件本体 | ✅ **能** | ❌ **不能**（作者明确划界） |
| **Keychain 里的解密后条目** | ⚠️ **能读到文件，但需 keybag 解密** | ❌ 不能 |
| **keybag（`keybags/*.kb`）** | ✅ **能** | ❌ 不能 |
| **Wi-Fi 密码** | ✅ 能（`com.apple.wifi.plist`） | ❌ 不能 |

**核心结论**：
- **能读到「钱包 App 自己存在容器里的助记词/私钥」** —— 这是最直接的一类
- **能读到 Keychain 的数据库文件**，但要**先解密**
- **第 3 代明确做不到 Keychain**（作者自己写死了边界）

---

## 二、为什么第 1/2 代能

### 2.1 逃逸的实际效果：全盘 R+W

`sandbox_escape.m` 头部原文：

```objc
/*
 * sandbox_escape.m — Sandbox escape via kernel memory patching
 *
 * Walk proc_ro → ucred → cr_label → sandbox → ext_set → ext_table
 * Patch extension paths to "/", rewrite class to "com.apple.app-sandbox.read-write"
 * Fill all 16 hash slots → full R+W filesystem access
 * Based on 18.3_sandbox/root.m by CrazyMind90.
 */
```

**关键三句**：

| 操作 | 含义 |
|---|---|
| `Patch extension paths to "/"` | 把沙箱扩展的**路径限制改成根目录** |
| `rewrite class to "com.apple.app-sandbox.read-write"` | 改成**读写**（不是只读） |
| `Fill all 16 hash slots` | 填满全部 16 个 hash 槽 → **不限于任何特定路径** |

结果 = **full R+W filesystem access**（全文件系统读写）。

实现（`sandbox_escape.m`）：

```objc
// 遍历 proc_ro → ucred → cr_label → sandbox → ext_set → ext_table
uint64_t ext_set = S(early_kread64(sandbox + OFF_SANDBOX_EXT_SET));
// 对 16 个扩展槽逐个 patch
for (int s = 0; s < 16; s++) {
    uint64_t hdr = S(early_kread64(ext_set + s * 8));
    if (K(hdr)) patched += patch_chain(hdr);       // 改路径为 "/"
}
for (int s = 0; s < 16; s++) {
    uint64_t hdr = S(early_kread64(ext_set + s * 8));
    if (K(hdr) && K(early_kread64(hdr + 0x10))) { set_rw_class(hdr); classed++; }  // 改读写
}
```

### 2.2 加上内核 R/W，能力更强

第 1/2 代还有完整的 `kexploit/`（562 处偏移 + `krw.m`）：
- `kread64` / `kwrite64` —— **直接读写内核内存**
- `sandbox_elevate_to_root` —— **换成 launchd 的 ucred**（拿 uid=0）
- `apfs_own` / `apfs_mod` —— **直接改 APFS fsnode 的属主/权限**

**→ 能读写任意文件，包括 `/private/var/Keychains/`。**

### 2.3 能读到的密钥清单

对照路径字典（74 条），第 1/2 代能触达：

| 路径 | 内容 |
|---|---|
| `/private/var/Keychains/keychain-2.db` | **Keychain 主库**（加密） |
| `/private/var/Keychains/keychain-2.db-wal/-shm` | WAL 日志（可能含未合并条目） |
| `/private/var/Keychains/persona.kb` | 用户态 keybag |
| `/private/var/Keychains/usersession.kb` | 用户会话 keybag |
| `/private/var/keybags/systembag.kb` | **系统 keybag** |
| `/private/var/mobile/Containers/Data/Application/` | **钱包 App 容器**（MetaMask 等） |
| `/private/var/preferences/com.apple.wifi.plist` | Wi-Fi 配置 |
| `/private/var/preferences/com.apple.wifi.known-networks.plist` | **Wi-Fi 明文** |

---

## 三、第 3 代为什么不能读 Keychain

### 3.1 作者在三处明确划界（`MCMFilzaIntegration.m`）

```objc
// :1236
@"This build does not provide root, kernel R/W, arbitrary /var, Keychain, TCC, or app-bundle access.\n\n"

// :1366
"No result here claims root, kernel, Keychain, TCC, or app-bundle access.\n\n"

// :1506
"Boundary: no arbitrary /var, Keychain, TCC, root, kernel, or app-bundle access is claimed.\n"
```

### 3.2 代码里确实"没碰" Keychain

我全库检索 `SecItemCopyMatching` / `SecItem` / `keychain`：
**只有 `MCMFilzaIntegration.m` 3 处命中，且全是"声明不做"的文案**。
`sandbox_escape.m`、`kexploit/*.m` 里 **零命中**。

第 3 代的机制是 ContainerManager 的 8 个容器类（2/4/6/7/10/12/13/15），
**`/private/var/Keychains/` 不属于任何容器类** → 天然拿不到。

---

## 四、但有个关键前提：Keychain 是加密的

**光拿到 `keychain-2.db` 不等于拿到密钥。**

iOS Keychain 的条目是**用 keybag 里的密钥加密**的：

```
keychain-2.db（SQLite，条目密文）
        ↓ 需要
keybags/*.kb（class key 的包裹）
        ↓ 需要
设备 UID 密钥（在 Secure Enclave 里，软件拿不到）
```

**所以实际路径是**：

| 方式 | 可行性 |
|---|---|
| 直接读 `keychain-2.db` 解析 | ❌ 条目是密文 |
| 读 `keybags/*.kb` 解密 | ⚠️ **部分可行**（取决于保护等级） |
| **注入 securityd 进程调 `SecItemCopyMatching`** | ✅ **这是 pe_main.js 的做法** |

`ios漏洞分析报告.md` 第 6 节记录：

```
8543  keychainCopier   注入 configd
8561  wifiDumpSecurityd 注入 securityd
```

**→ 真正读 Keychain 明文，靠的是"注入 securityd 并发起 API 调用"，不是"读文件"。**

Filza 第 1/2 代有内核 R/W，**理论上具备注入能力**，但 **`Tweak.m` 里没有对应实现**
（没找到 `SecItemCopyMatching` 或注入 securityd 的代码）。

---

## 五、结论：Filza 能读什么密钥

### 5.1 能直接读（无需解密）

**钱包 App 容器里的助记词/私钥** —— 这是最实际的：

```
/private/var/mobile/Containers/Data/Application/<UUID>/...
```

很多钱包 App（尤其越狱版、调试版）会把助记词**明文存在容器内**
（plist、sqlite、NSUserDefaults）。第 1/2 代（内核）和第 3 代（class 2 容器）**都能读**。

**这正是潜客 `ReqWallet` 要的东西**——`phrase` / `key` 字段。

### 5.2 需要额外步骤

| 目标 | Filza 能做到哪一步 | 还缺什么 |
|---|---|---|
| `keychain-2.db` 文件 | ✅ 能拿到文件 | 需 keybag 解密 |
| `keybags/*.kb` | ✅ 能拿到 | — |
| **Keychain 明文条目** | ❌ 无实现 | **需注入 securityd（pe_main.js 有）** |
| Wi-Fi 密码 | ✅ `com.apple.wifi.known-networks.plist` | — |

### 5.3 一句话

> **Filza 能读到「密钥文件」，但不能直接读到「密钥」——除了 App 容器里明文存的那种。**
> 真正把 Keychain 变成明文的，是 `pe_main.js` 的 **securityd 注入**，不是 Filza。

---

## 六、对整合方案的启示

按「能不能拿密钥」重新分工：

| 任务 | 该用谁 | 理由 |
|---|---|---|
| **钱包助记词/私钥**（容器内明文） | **Filza 任一版本** 或 `pe_main.js` | 两条路都行 |
| **Keychain 明文条目** | **只能 `pe_main.js`**（securityd 注入） | Filza 无此实现 |
| **keybag / keychain-2.db 文件** | **Filza 第 1/2 代** | 需内核 R/W |
| **Wi-Fi 密码** | Filza 第 1/2 代 或 `wifi_password_dump.js` | 两条路都行 |

**→ 如果要"密钥"作为主要产出，`pe_main.js` 是主力，Filza 是补充（且只有第 1/2 代有意义）。**

这印证了上一轮的判断：**Filza 的工具属性大于链路属性**。

---

## 七、证据局限

1. **未真机验证**。「能读到」是基于代码能力的推断，不代表实际文件都在。
2. 第 1/2 代是否有**注入 securityd 的能力实现**未确认 ——
   有内核 R/W 理论上可以，但**源码里没有现成代码**。
3. Keychain 的**数据保护等级（class）**未评估：
   带 `kSecAttrAccessibleWhenUnlockedThisDeviceOnly` 的条目，
   即使有 keybag 也可能解不开（依赖 Secure Enclave）。
4. 未验证「钱包 App 容器里是否真有明文助记词」——
   现代钱包多数已改为 Keychain 存储，**这是本结论最大的不确定项**。
5. `Android` 侧（潜客的 `phrase`/`key`）走的是完全不同的路径（无障碍 + 读文件），
   与 Filza 无关。
