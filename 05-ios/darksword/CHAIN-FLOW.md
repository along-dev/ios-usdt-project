# DarkSword 实际执行流程（代码核实版）

> 本文档以**代码为准**，不是 README 的宣传性描述。
> 每条流程都带文件 + 行号，可自行跳转核对。
> 目标：纠正流传较广的流程图误传（如 "ANGLE 越界"、"mach_port UAF 提权 root"）。

适用版本：**iOS 18.4 – 18.4.1（完整）；18.5 – 18.6.2 仅前段可跑**。

---

## 0. 一句话总结

链路是**一条单向流水线**，五个 JS 模块按固定顺序接力，前一个 `eval` 后一个：

```
rce_loader.js
  └─ rce_worker.js          # Web Worker 内跑 stage1
       └─ sbx0_main_18.4.js # WebContent 沙箱逃逸（Mach 消息伪造）
            └─ sbx1_main.js # IOSurface -> 内核原语
                 └─ pe_main.js  # ICMPv6 内核读写 -> 沙箱扩展篡改 -> 跨进程注入 -> 窃取
```

模块顺序**不可调换**：sbx0 依赖 worker 建立的 fcall 原语；sbx1 依赖 sbx0 建好的跨进程桥梁；
pe_main 依赖 sbx1 提供的内核读写。

---

## 1. 逐阶段流程（含代码证据）

### ① 设备指纹 / 偏移表选择

| 项 | 内容 |
|---|---|
| 文件 | `rce_loader.js` → `rce_module.js` |
| 关键行 | `rce_module.js:3237` |

```javascript
// rce_module.js:3237
device_model = linkedit_to_device[ios_version][libsystem_pthread_linkedit];
chipset = device_chipset[device_model];
offsets = rce_offsets[device_model];
slide   = globalFuncParseFloat - offsets.JavaScriptCore__globalFuncParseFloat;
```

**实际做法**：不是"读芯片型号"，而是**用 `libsystem_pthread` 的 linkedit 地址反查机型**。
`ios_version` 来自 UA（`iPhone OS 18_5` → `'18,5'`），`linkedit` 地址运行时读出，
两者一起查 `linkedit_to_device` 表得到 `device_model`，再查 `rce_offsets` 拿偏移。

**必然失败点**：若 `ios_version` 或 linkedit 地址不在表里 → `device_model = undefined`
→ 下一行取 `offsets.JavaScriptCore__*` **立即 TypeError**。

> **证据等级**：18.5 走到 ⑤ 才挂是**实测**（真机日志）；
> 18.3.1 在此处崩溃是**代码推断**（`linkedit_to_device` 无 `18,3` 键），
> 未在 18.3.1 真机上验证过。

---

### ② JSC 内存破坏 → addrof / fakeobj

| 项 | 内容 |
|---|---|
| 文件 | `rce_module.js` |
| 关键行 | `2754` (stage1)、`2760` (addrof)、`2764` (fakeobj)、`3447` (check_victim) |

```javascript
// rce_module.js:2760
function addrof(object) { boxed_arr[0] = o; return BigInt.fromDouble(unboxed_arr[0]); }
// rce_module.js:2764
function fakeobj(addr)  { unboxed_arr[0] = addr.asDouble(); return boxed_arr[0]; }
```

```javascript
// rce_module.js:3447  — 建立 OOB 重叠
const check_victim = () => {
    for (let j = 0; j < victim_cursor; j++){
        if (victim_list[j].length > (victim_array_allocation_size*10)){ oob_array_idx = j; break; }
    }
    ...
    if(oob_array[i+1] === egg1 && oob_array[i+2] === egg2){ overlap_array_idx = oob_array[i+3]; ... }
};
```

**纠错**：这里是**JSC 类型混淆**（破坏数组长度字段造出 OOB 数组），
**不是 "WebKit UAF"**。`the_oob_object.splice(30,0,...)` + egg 标记扫描是典型类型混淆手法。

**实测特征**：该阶段**不稳定**，失败时打 `Failed RCE`，成功打 `RCE success`。
失败诊断（已注入）：`DIAG no-oob-array cursor=N want_len>N max_len=N heap_relative=normal`。

---

### ③ WebContent RCE（stage2 定位 + 劫持）

| 项 | 内容 |
|---|---|
| 文件 | `rce_module.js` |
| 关键行 | `3252` (stage2) |

```javascript
// rce_module.js:3252
stage2() {
    const contexts = this.read64(offsets.WebCore__ZZN7WebCoreL29allScriptExecutionContextsMapEvE8contexts);
    ...
    if (vtable.noPAC() != offsets.WebCore__DedicatedWorkerGlobalScope_vtable) continue;
    const id = this.read64(scriptExecutionContext + 0x138n);   // 取 id 最大的 worker
    ...
    this.write64(unboxed_arr + 8n, butterfly);                  // 劫持 JS 堆
}
```

定位**自己的 Worker 上下文**并劫持其 JS 堆，从而在 WebContent 进程内获得任意 JS 执行。
之后 `rce_worker.js` 接手。

---

### ④ dyld interpose + PAC 绕过 → fcall

| 项 | 内容 |
|---|---|
| 文件 | `rce_worker.js` |
| 关键行 | `513-515` (InterposeTupleAll)、`641` (interpose signPointer)、`668/672` (paciza_dlopen/signPointer) |

```javascript
// rce_worker.js:513
const p_InterposeTupleAll_buffer = runtimeState + 0xb8n;
const p_InterposeTupleAll_size   = runtimeState + 0xc0n;
```

```javascript
// rce_worker.js:641
interpose(offsets.CMPhoto__CMPhotoCompressionSessionAddExif, offsets.dyld__signPointer);
// rce_worker.js:668
const paciza_dlopen      = p.read64(offsets.ImageIO__gFunc_CMPhotoCompressionSessionAddAuxiliaryImageFromDictionaryRepresentation);
const paciza_signPointer = p.read64(offsets.ImageIO__gFunc_CMPhotoCompressionSessionAddExif);
```

**纠错（重要）**：**此阶段没有 "ANGLE 越界"**。全库搜索 `ANGLE` 零命中。

实际手法：
1. 破坏 `CFBundle` → `dlopen` 加载 `AVSpeechSynthesisVoice`
2. 劫持 dyld 的 `InterposeTupleAll`（`runtimeState + 0xb8/0xc0`）
3. **把 dyld 的 `signPointer` 当 PAC 签名 oracle 用** → 拿到 `paciza_*` / `pacib_*` 签名结果
4. 起 JOP 线程 → 得 `fcall`（任意函数调用）

> PAC 绕过发生在**这里**，不是流程末段。后续 sbx0 / sbx1 / pe_main 都只是**复用**已建好的 fcall。

---

### ⑤ sbx0：WebContent 沙盒逃逸（Mach 消息伪造）

| 项 | 内容 |
|---|---|
| 文件 | `sbx0_main_18.4.js` |
| 关键行 | `18-19` (dlsym)、`6700` (mach_port_insert_right)、`8440` (Calling _exit) |

```javascript
// sbx0_main_18.4.js:18
offsets.mach_port_insert_right = dlsym(libsystem_kernel, 'mach_port_insert_right').noPAC();
offsets.mach_msg_fn            = dlsym(libsystem_kernel, 'mach_msg').noPAC();
// :6700
kr = fcall(offsets.mach_port_insert_right, __mach_task_self, receivePort, receivePort, 0x14n);
```

**纠错**：**不是 ICMPv6 socket，也不是 ANGLE**。
这里用 **Mach 消息**（`mach_msg` + 端口权限插入）伪造消息，骗过 **GPU 进程的
RemoteRenderingBackend 连接**，从而获得跨进程调用能力。

**结束时主动自杀**（设计如此，清理痕迹）：

```javascript
// sbx0_main_18.4.js:8440
LOG("Calling _exit()");
fcall(offsets.exit, 0n);
```

> 这也解释了为什么日志会断在 sbx0 之后 —— WebContent 进程被自己杀掉了。

---

### ⑥ sbx1：IOSurface → 内核原语

| 项 | 内容 |
|---|---|
| 文件 | `sbx1_main.js` |
| 关键行 | `4746` (IOConnectCallStructMethod)、`4758` (IOSurfaceCreate)、`6755/6852` (spawn_pe) |

```javascript
// sbx1_main.js:4746
let IOCONNECTCALLSTRUCTMETHOD = func_resolve("IOConnectCallStructMethod");
// :4758
let IOSURFACECREATE          = func_resolve("IOSurfaceCreate");
```

**纠错**：**IOSurface 在这一步，不在 ⑤**。
经 GPU 进程用 IOSurface 建立稳定的内核读写载体，并泄露 `dyld_shared_cache_slide`。

跑通后拉起下一阶段：

```javascript
// sbx1_main.js:6755 / 6852
function spawn_pe() { ... }
...
if (sbx1sbx1_succeeded) { spawn_pe(); }
```

---

### ⑦ pe_main：ICMPv6 内核读写 + 沙箱扩展篡改

| 项 | 内容 |
|---|---|
| 文件 | `pe_main.js`（webpack 打包，源码模块名见注释） |
| 关键行 | `344` (ICMP6_FILTER)、`776` (EARLY_KRW_LENGTH)、`6656` (applySandboxEscape)、`6708` (ext_setAddr) |

```javascript
// pe_main.js:344
let ICMP6_FILTER = 18n;
// :776
let EARLY_KRW_LENGTH = 0x20n;      // 32 字节粒度
// :781
setsockopt(control_socket, IPPROTO_ICMPV6, ICMP6_FILTER, control_data, EARLY_KRW_LENGTH);
```

**这里才是真正的内核读写**（模块 `DriverNewThread.js`）。做法：

- **control socket**：`setsockopt` 把目标内核地址写进 socket 的 filter 结构
- **RW socket**：`getsockopt` / `setsockopt` 读写该地址
- **粒度 32 字节**；小于 32 字节的写走 read-modify-write

拿到内核读写后：

```javascript
// pe_main.js:6656
static applySandboxEscape() {
    let ourProcAddr = Task.getTaskProc(ourTaskAddr);
    let credRefAddr = Chain.read64(ourProcAddr + 0x18n);   // proc_ro + 0x18 = ucred ref
    ...
    let ext_setAddr = Chain.read64(sandboxAddr + 0x10n);   // :6708
```

**关于 `ucred` 的关键澄清**：
`ucred` **只作遍历沙箱结构的中转节点**，路径是
`proc → proc_ro → ucred → cr_label → sandbox → ext_set → ext_table`，
目的是**清零沙箱 extension data**，把"路径受限的扩展"变成"不受限扩展"。

**这条链不做 root 提权**。全文件搜索：`cr_uid` / `setuid` / `becomeRoot` 在
`pe_main.js` / `sbx1_main.js` / `sbx0_main_18.4.js` **均为 0 命中**；
`kernel_task_port` 同样 0 命中。

> 它获得能力的方式是**沙箱逃逸 + 注入到已有特权的进程**（launchd / SpringBoard 等），
> 而不是把自己变成 root。

---

### ⑧ 跨进程注入 + 窃取上报

| 项 | 内容 |
|---|---|
| 文件 | `pe_main.js` |
| 关键行 | `179` (NSInvocation)、`180` (JSContext)、`1502` (RemoteCall) |

```javascript
// pe_main.js:179
let invoke_class = objc_getClass("NSInvocation");
// pe_main.js:180
let jsc_class    = objc_getClass("JSContext");
```

机制：
1. **EXC_GUARD 线程劫持** → 控制目标进程线程
2. **RemoteCall**（`libs/TaskRop/RemoteCall`）在目标进程内发起调用
3. **`NSInvocation` + `JSContext` 注入** → 在目标进程内执行 JS
4. 各 payload 落地执行：

| Payload | 目标 |
|---|---|
| Forensics File Downloader | 取证相关文件 |
| WiFi Password Dump | WiFi 凭据（wifid 上下文有 keychain 权限） |
| Keybag Copier | 钥匙串 |
| Drive Dumper | iCloud Drive |
| Hidden photos / Screenshots | 相册 |

5. 上报 C2：`POST /stats`（文件窃取，HTTPS 443）、`POST /upload`（WiFi）

---

## 2. 与流传版本的差异对照

| 流传描述 | 实际情况 | 代码依据 |
|---|---|---|
| ③ WebKit **UAF** | JSC **类型混淆**（OOB 数组重叠） | `rce_module.js:3447` `check_victim` |
| ④ **ANGLE 越界** | **不存在**；是 dyld interpose + PAC oracle | `ANGLE` 全库 0 命中 |
| ⑤ **IOSurface** 内核读写 | IOSurface 在 **⑥ sbx1**，不在 ⑤ | `sbx1_main.js:4758` |
| ⑤/⑦ 内核读写用 **ICMPv6** | 对，但在 **⑦ pe_main**，不在 ⑤ | `pe_main.js:344/776` |
| ⑥ **mach_port UAF → kernel_task_port** | mach_port 在 ⑤ sbx0，**用途是伪造 Mach 消息逃沙箱**，不是 UAF 提权 | `sbx0:6700` |
| ⑥ **改 ucred → root** | **不提权到 root**；ucred 只作沙箱结构遍历中转 | `cr_uid`/`setuid` 0 命中 |
| ⑦ **PAC 绕过** | PAC 绕过在 **④**（更早），⑦ 是内核读写 + fcall | `rce_worker.js:641/668` |
| ⑧ "文件系统读写" | 实际是 **EXC_GUARD 劫持 + NSInvocation/JSContext 注入** | `pe_main.js:179/180/1502` |

---

## 3. 运行前提（实测）

| 阶段 | 覆盖范围 | 说明 |
|---|---|---|
| ①–④（JSC → PAC → fcall） | iOS **18.4 – 18.6.2**，全 **iPhone** | `linkedit_to_device` 版本键：`18,4` `18,4,1` `18,5` `18,6` `18,6,1` `18,6,2` |
| ⑤（sbx0 沙箱逃逸） | **仅 18.4 / 18.4.1** | `sbx0_offsets` 只有 build `22E240` / `22E252`，各 23 机型 |
| ⑥–⑧ | 依赖 ⑤ | ⑤ 不过则永不执行 |

- **iPad 不支持**：`rce_offsets` / `sbx0_offsets` 均无 iPad 条目。
- **iOS 18.3.x 及以下不支持**：偏移表从 18.4 起。
- **iOS 18.5 的现实**：①–④ 可跑通（需重试），⑤ 必挂 → 全链不可用。

---

## 4. 故障定位速查

`rce_loader.js` **每次加载页面只尝试 2 次**（嵌套两层 `attempt.start()`），
第二次失败即静默放弃。想提高成功率**只能反复重新加载页面**。

| 现象 | 位置 | 原因 |
|---|---|---|
| `Failed RCE` | ② | JSC 类型混淆未成功（堆布局不稳，正常现象，重载即可） |
| `TypeError: undefined is not an object`（取 `MessageName.*`） | ⑤ | `sbx0_offsets[device_model]` 查不到 → 该 build 无偏移表 |
| `TypeError`（取 `offsets.JavaScriptCore__*`） | ① | `linkedit_to_device[ios_version]` 查不到 → 该 iOS 版本无偏移 |
| `DBG sbx0 FETCH FAILED (len=0)` | ⑤ | sbx0 脚本下载失败 |
| 日志停在 `all done` | ④ 之后 | 当前阶段正常收尾（页面跳 404 规避），非卡住 |
| 日志停在 `bundle[N]` 后无下文 | ① | 上一轮的 device_model 解析失败（已被 print 捕获） |

调试入口：`https://sqwas.ebwlyais.xyz/assets/index.html?debug=1`（手机端，同页触发+观测）

---

## 5. 证据文件清单

| 文件 | 行数 | 阶段 |
|---|---|---|
| `rce_loader.js` | 251 | 入口、重试（2 次） |
| `rce_module.js` | 3505 | ①②③ 设备指纹 / JSC / stage2 |
| `rce_worker.js` | 966 | ④ dyld interpose / PAC / fcall |
| `sbx0_main_18.4.js` | 8450 | ⑤ Mach 消息沙箱逃逸 |
| `sbx1_main.js` | 6862 | ⑥ IOSurface 内核原语 |
| `pe_main.js` | 8440 | ⑦⑧ ICMPv6 内核读写 / 注入 / payload |

---

*文档基于 `H:\ios-dark-sword\darksword-Exploit-main` 当前代码核实。若代码变动，行号可能偏移。*
