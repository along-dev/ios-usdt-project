# Tweak.m 精读结论 —— 前提 2 完整能力面（含一处重大结构发现）

> 读取范围：`Tweak.m`（1,608 行，76,806 字节）全文结构 + 关键函数，
> 并对照 `Makefile`、`MCMFilzaIntegration.m` 与**已编译的 6 个 dylib**。
> **静态分析，未编译未运行。**

---

## 一、重大发现：`Tweak.m` 里没有内核代码

### 1.1 关键词统计（全文 1,608 行）

| 关键词 | 命中次数 |
|---|---|
| `kexploit` | **0** |
| `krw` | **0** |
| `sandbox_escape` | **0** |
| `kread` / `kwrite` | **0** |
| `get_rootvnode` | **0** |
| `offsets_init` | **0** |
| `posix_spawn` | **0** |
| `[Filza18]` | **0** |
| `RootHelper` | 8（全是**空实现 hook**） |

**我之前说「`Tweak.m` 是第 1/2 代主逻辑，含 `[Filza18]` 内核路径」——这是错的。**

### 1.2 内核代码的真实位置

| 文件 | 内核符号命中 | 在 Makefile 中？ |
|---|---|---|
| `kexploit/kexploit_opa334.m` | 22 | ❌ |
| `kexploit/krw.m` | 20 | ❌ |
| `kexploit/kutils.m` | 24 | ❌ |
| `kexploit/offsets.m` | 3 | ❌ |
| `kexploit/vnode.m` | 27 | ❌ |
| `kpf/patchfinder.m` | 10 | ❌ |
| `apfs_own.m` | 13 | ❌ |
| `sandbox_escape.m` | 35 | ❌ |

`[Filza18]` 在整个源码树里**一次都没有** —— 它只存在于已编译的 `Slop_1.0.0` dylib 中。

### 1.3 Makefile 只编译 5 个文件

```make
FilzaApplySandboxExt_FILES = Tweak.m MCMBridge.m MCMFilzaIntegration.m \
                             PosterBoardFeature.m UpdateChecker.m
```

**全部内核源文件都是死代码（orphaned source）。**

**旁证**：`XPF/`（50 文件）只被 `patchfinder.m` 引用，而 `patchfinder.m` 不在 Makefile 中
→ 整条 XPF/ChOma 签名绕过链**在本构建中完全未链接**。

---

## 二、编译产物对比（决定性证据）

对 6 个已编译 dylib 做符号探测：

| 符号 | **Slop_1.0.0** | Slop_1.0.3 | Slop_1.2.0 |
|---|---|---|---|
| `kexploit` | **✅ Y** | ❌ n | ❌ n |
| `sandbox_escape` | **✅ Y** | ❌ n | ❌ n |
| `get_rootvnode` | **✅ Y** | ❌ n | ❌ n |
| `kread64` | **✅ Y** | ❌ n | ❌ n |
| `offsets_init` | **✅ Y** | ❌ n | ❌ n |
| `early_kread` | **✅ Y** | ❌ n | ❌ n |
| `apfs` | **✅ Y** | ❌ n | ❌ n |
| `vnode_redirect` | **✅ Y** | ❌ n | ❌ n |
| `Filza18` | **✅ Y** | ❌ n | ❌ n |
| `MCMFilzaStart` | ✅ Y | ✅ Y | ✅ Y |
| `MHA-MCM` | ✅ Y | ✅ Y | ✅ Y |

**结论**：
- `Slop_1.0.0` 是**用另一份（更早的）Makefile 构建的**，那份 Makefile 把
  `kexploit/`、`sandbox_escape.m`、`apfs_own.m` 都编进去了
- 当前仓库的 Makefile 对应的是 **`1.0.3+` 的重构版**（纯 MHA-MCM）
- `README` 只提到 `1.0.0` 与 `1.0.1` 的构建示例，未提 1.0.3 的构建差异

---

## 三、当前源码 = 纯第 3 代（MHA-MCM）

### 3.1 入口（`Tweak.m:1596-1606`）

```objc
#pragma mark - Entry Point

__attribute__((constructor)) void TweakInit(void) {
    installHooks();
    // Populate the MCM root before Filza restores its initial browser path.
    runMCMPath();
    scheduleInitialBrowserRepair(8);
    FSUpdateCheckerStart();
}
```

`runMCMPath()`（`:1592-1600`）：

```objc
static void runMCMPath(void) {
    MCMFilzaStart();
    if (MCMFilzaIsRunningInLiveContainer()) return;
    PBWallpaperFeatureStart();
    runOptInWriteProbe();
    runOptInPasteCopyProbe();
}
```

**全流程走 MCM，无一处内核调用。**

### 3.2 Root Helper 全部空实现（`Tweak.m:21-29`）

```objc
static BOOL hook_isRootHelperAvailable(id self, SEL _cmd) { return NO; }
static int hook_spawnRootHelper(id self, SEL _cmd) { return 0; }
static int hook_spawnRootHelperIfNeeds(id self, SEL _cmd) { return 0; }
static int hook_respawnRootHelper(id self, SEL _cmd) { return 0; }
static void hook_tryLoadFilzaHelper(id self, SEL _cmd) {}
static void hook_createHelperConnectionIfNeeds(id self, SEL _cmd) {}
```

**6 个全空** —— 意思是**主动禁用 Filza 自带的 root helper**，
不再需要越狱提权，改由 MHA 绕过提供容器访问。

> 这与我之前从 dylib 读到的一致：`hook_createHelperConnectionIfNeeds`、
> `hook_respawnRootHelper` 属于第 1/2 代；第 3 代把它们换成空壳。

### 3.3 `MCMFilzaStart()` 主流程（`MCMFilzaIntegration.m:1536`）

```objc
void MCMFilzaStart(void) {
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        MCMEnsureState();

        if (MCMFilzaIsRunningInLiveContainer()) {   // ★ LiveContainer 分支
            MCMInstallLiveContainerRoot();
            return;                                  // 直接返回，不走 MHA
        }

        // ★ 校验签名身份 —— 与 build_release_ipa.sh 的约束闭环
        NSString *actual = MCMSignedCodeIdentifier();
        if (![actual isEqualToString:kRequiredIdentifier]) {
            NSLog(@"[MCMFilza] disabled: signed code identifier %@ must be %@ (bundle=%@)",
                  actual, kRequiredIdentifier, NSBundle.mainBundle.bundleIdentifier);
            return;
        }
        if (!MCMBridgeAvailable()) {
            NSLog(@"[MCMFilza] disabled: ContainerManager symbols unavailable");
            return;
        }

        // 建 11 个虚拟根目录（权限 0700）
        for (NSString *directory in @[root, apps, groups, extensions, vpnData,
                                      serviceData, systemData, systemGroups,
                                      protectedData, additionalLocations,
                                      experimental])
            [fm createDirectoryAtPath:directory
              withIntermediateDirectories:YES
              attributes:@{NSFilePosixPermissions: @0700} error:nil];
        ...
```

**注意**：`MCMSignedCodeIdentifier()` 校验 —— 这就是为什么 `build_release_ipa.sh`
必须硬保 `com.apple.mobile.MobileHouseArrest` 身份。**两处代码闭环验证了前提 1**。

已核实常量与实现（`MCMFilzaIntegration.m:17` 与同名函数）：

```objc
static NSString *const kRequiredIdentifier = @"com.apple.mobile.MobileHouseArrest";

static NSString *MCMSignedCodeIdentifier(void)
{
    static NSString *identifier;
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        SecTaskRef task = SecTaskCreateFromSelf(kCFAllocatorDefault);
        if (!task) return;
        CFErrorRef error = NULL;
        CFStringRef value = SecTaskCopySigningIdentifier(task, &error);  // ★ 读 CodeDirectory 标识
        if (value) identifier = [(__bridge NSString *)value copy];
        if (value) CFRelease(value);
        if (error) CFRelease(error);
        CFRelease(task);
    });
    return identifier;
}
```

**闭环**：`SecTaskCopySigningIdentifier` 读的是 **CodeDirectory 签名标识**，
与 `build_release_ipa.sh` 里 `plutil -extract CFBundleIdentifier` 的 Bundle ID
**必须两者一致** —— 正好对应 README 那句「两个 identifier 都要是
`com.apple.mobile.MobileHouseArrest`，改了就禁用 MHA 路径」。

### 3.4 11 个虚拟根目录（完整能力面）

| 目录常量 | 对应容器类 |
|---|---|
| `kMCMAppDataDirectoryName` | 类 2 application-data |
| `kMCMAppGroupsDirectoryName` | 类 7 app-group |
| `kMCMExtensionDataDirectoryName` | 类 4 extension-data |
| `kMCMVPNDataDirectoryName` | 类 6 VPN-data |
| `kMCMServiceDataDirectoryName` | 类 10 service-data |
| `kMCMSystemDataDirectoryName` | 类 12 system-data |
| `kMCMSystemGroupsDirectoryName` | 类 13 system-group |
| `kMCMProtectedDataDirectoryName` | 类 15 protected-data |
| `kMCMAdditionalLocationsDirectoryName` | 附加位置 |
| `kMCMExperimentalDirectoryName` | 实验性 |
| `Files Traversal` | 遍历辅助（每次重建前删除） |

**这就是前提 2 的完整答案**：第 3 代把**全部 8 个容器类**映射成 11 个虚拟根目录，
挂到 Filza 的浏览器里 —— 不需要内核，也不需要越狱。

---

## 四、Hooks 清单（`installHooks()`，`:1268`）

| Hook | 作用 |
|---|---|
| `hook_defaultPath` | 起始路径改为 MCM 虚拟根 |
| `hook_fileSystemSetCurrentPath` | 路径重定向（Legacy 浏览器路径） |
| `hook_fileSystemUpdateEditableUI` / `ViewWillAppear` | 刷新 UI |
| `hook_allApplications` / `setAppProxy` | 应用列表改造 |
| `hook_ZipFiles` / `unZipFile` / `unZipFilePassword` | **zip 钩子**（minizip 动态加载） |
| `hook_copyFilesAndDirectoryFromPasteboard` | 粘贴（直连复制，绕过 Filza 逻辑） |
| `hook_fileSystemDeleteSelectedItems` / `AskDeleteItems` / `DoTrashSelectedItems` / `DoEraseSelectedItems` | 删除/回收站/擦除 |
| `hook_fileSystemPageDeleteAction` / `pageDoTrashSelectedItems` / `pageDoEraseSelectedItems` | 分页版删除 |
| `hook_showAlertWithTitle` / `activationViewDidLoad` | 提示与激活页 |
| `hook_didSelectItem` | 条目选择 |
| root helper 6 个 | **全空** |

`loadMinizip()`（`:190`）动态加载 minizip（`p_zipOpen64` / `p_unzOpen64` 等 13 个函数指针）。

---

## 五、修正后的前提 2 结论

### 5.1 三代能力对照（最终版）

| | **第 1 代**（Escaped_DS_1.2 / Jailed_DS_2.0 / Jailed_2.1） | **第 2 代**（Slop_1.0.0） | **第 3 代**（Slop_1.0.3 / 1.2.0，**当前源码**） |
|---|---|---|---|
| 内核 R/W | ✅ | ✅ | ❌ |
| XPF 签名绕过 | ✅ | ✅ | ❌ |
| 沙箱逃逸 | ✅ | ✅ | ❌ |
| MHA-MCM | ❌ | ✅（已并入） | ✅ **唯一机制** |
| Root helper | 需要 | 空实现 | 空实现 |
| 内核偏移 | 独立源码 | 独立源码 | **源码在但未编译** |
| 版本门禁 | `17.0 - 26.0.x` | 同 | **无门禁** |
| 依赖 LiveContainer | ❌ | ❌ | 可选（降级模式） |

### 5.2 前提 2 的完整答案

**「15.0–16.x 内核偏移不覆盖」这个前提，在第 3 代里根本不存在**：

- 第 1/2 代：`offsets_init()` 硬门禁 `17.0 ≤ v < 26.1`，否则 `exit(EXIT_FAILURE)`
- 第 3 代：**无任何版本检查**，只依赖 ContainerManager API 存在性
  （`MCMBridgeAvailable()` 运行时探测）

**能力面对照**：

| 能力 | 第 1/2 代 | 第 3 代 |
|---|---|---|
| 应用数据容器（类 2） | ✅ | ✅ |
| App Group（类 7） | ✅ | ✅ |
| extension/VPN/service/system/protected（4/6/10/12/15） | ✅ | ✅ |
| system-group（类 13） | ✅ | ✅ |
| **任意 `/var`** | ✅（内核 R/W） | ❌（作者明确划界） |
| **Keychain** | ✅ | ❌ |
| **TCC** | ✅ | ❌ |
| **root / 内核 R/W** | ✅ | ❌ |
| **app-bundle 访问** | ✅ | ❌ |
| 版本范围 | 17.0 – 26.0.x | **无版本限制**（实测到 27 beta） |

作者在第 3 代字符串里明确划界：

> Boundary: no arbitrary /var, Keychain, TCC, root, kernel, or app-bundle
> access is claimed.

### 5.3 决策矩阵

| 场景 | 该用哪一代 | 理由 |
|---|---|---|
| 只要 App 容器数据（钱包/微信/笔记） | **第 3 代** | 无版本限制，无需内核，最稳 |
| 要 Keychain / 任意 /var / root | **第 1/2 代** | 只有内核链能给 |
| 15.0–16.x | **只能第 3 代** | 第 1/2 代直接 `exit(1)` |
| 26.1+ | **只能第 3 代** | 同上 |
| 想要最大能力 + 目标在 17.0–26.0.x | **第 1/2 代** | 但要付越狱/内核风险 |

---

## 六、还差什么才能复现第 1/2 代

当前 Makefile 不编译内核代码。若要重建第 1/2 代：

```make
# 需要把以下文件加回 FilzaApplySandboxExt_FILES
kexploit/kexploit_opa334.m  kexploit/krw.m  kexploit/kutils.m
kexploit/offsets.m  kexploit/vnode.m
kpf/patchfinder.m  sandbox_escape.m  apfs_own.m  utils/*.c
# 并加 -I$(PWD)/XPF/src -I$(PWD)/XPF/external/ChOma/include（Makefile 已有）
```

**但缺 `Tweak.m` 中的内核调用段** —— 当前 `Tweak.m` 没有 `sandbox_escape()` 调用点。
说明 `Slop_1.0.0` 用的是**另一版 `Tweak.m`**，那份不在此仓库。

**结论**：本仓库**只能完整重建第 3 代**；第 1/2 代需另找 `1.0.0` 对应的源码快照
（或从 `Slop_1.0.0` dylib 反汇编恢复调用逻辑）。

---

## 七、证据局限

1. **未编译未运行**。所有结论来自源码阅读 + 二进制符号探测。
2. 符号探测用 `latin1` 字符串匹配，可能受 strip 影响 —— 但 `1.0.0` 与 `1.0.3`
   的**对照差异**本身是可靠的。
3. 未验证 `Slop_1.0.0` 的 Makefile 原文（本地只有当前版本）。
4. `Tweak.m` 1,608 行，我读了**结构、入口、hooks 清单、root helper 段**；
   中间约 1,200 行的 UI/复制/删除实现**未逐行细读**。
5. `MCMFilzaIntegration.m` 只读了 `MCMFilzaStart()` 前 60 行与容器映射段。
6. ✅ 已核实 `kRequiredIdentifier = @"com.apple.mobile.MobileHouseArrest"`
   与 `MCMSignedCodeIdentifier()` 实现，前提 1 的代码闭环成立。
7. 未验证 11 个目录常量（`kMCMAppDataDirectoryName` 等）的字面值，
   其与容器类 2/4/6/7/10/12/13/15 的映射来自 `MCMDynamicIdentifiers(n)` 的调用参数。
