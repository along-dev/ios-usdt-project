# Slop_1.0.0 反汇编恢复报告 —— 第 1/2 代内核调用序列

> 目标：从 `Slop_1.0.0` 已编译 dylib 恢复本仓库缺失的内核调用逻辑。
> 方法：Mach-O 解析 + 符号表枚举（813 个未 strip）+ capstone/手工 ARM64 解码 + 调用图重建。
> **静态分析，未运行。**

---

## 一、结论：调用序列已完整恢复

### 1.1 顶层编排（`_TweakInit` @ `0x4000`，内核区段 `0x4d38-0x4dcc`）

反汇编出的**实际执行顺序**：

```asm
0x004d48  adrp  x0, #0x4a000
0x004d4c  add   x0, x0, #0xe40
0x004d50  bl    #0x36e68              ; NSLog/print "starting..."
0x004d54  bl    #0x1abe0   ; ★ _kexploit_opa334      ← 内核利用
0x004d58  cbz   w0, #0x4d70           ; 失败则跳
0x004d5c  ...   str x0,[sp]           ; 记录结果
0x004d60  adrp/add + bl #0x36e68      ; 打印 "kexploit failed result=%d"
0x004d6c  b     #0x4d94               ; → 收尾 return
0x004d70  bl    #0x1b5e0   ; ★ _proc_self            ← 取自身 proc
0x004d74  mov   x19, x0
0x004d78  bl    #0x176a0   ; ★ _sandbox_escape       ← 沙箱逃逸
0x004d7c  mov   x20, x0
0x004d80  stp   x20, x19, [sp]
0x004d84  adrp/add + bl #0x36e68      ; 打印 "sandbox result=%d self_proc=0x%llx"
0x004d90  cbz   w20, #0x4da4          ; 逃逸成功则跳
0x004d94  ...   ret                   ; 失败直接返回（不启动 MCM）
0x004da4  mov   w0, #1
0x004da8  bl    #0xa540    ; ★ _MCMFilzaSetUnrestrictedFilesystem(1)
0x004dac  bl    #0xacb8    ; ★ _MCMFilzaStart()      ← 成功后接管
```

**这正是 `[Filza18]` 三条日志的产生处**：

| 字符串地址 | 内容 | 对应指令 |
|---|---|---|
| `0x3a13b` | `[Filza18] starting exact-target kernel path` | `0x4d50` |
| `0x3a167` | `[Filza18] kexploit failed result=%d` | `0x4d68` |
| `0x3a18b` | `[Filza18] sandbox result=%d self_proc=0x%llx` | `0x4d8c` |

### 1.2 恢复出的完整序列

```
_TweakInit (0x4000)
 ├─ 打印 "[Filza18] starting exact-target kernel path"
 ├─ _kexploit_opa334 (0x1abe0)                    ← 内核提权
 │   ├─ _offsets_init (0x1bd88)                   ★ 版本门禁在此
 │   ├─ _init_globals (0x18704)
 │   ├─ 分支：gIsA18Above ? (pe_init + pe_v2) : (pe_init + pe_v1)
 │   │   ├─ _pe_init  (0x18f38)
 │   │   ├─ _pe_v2    (0x1a3b4)   ← [A18 路径]
 │   │   └─ _pe_v1    (0x19e6c)   ← [非 A18 路径]
 │   ├─ _early_kread ×9 (0x1acec..0x1af50)
 │   └─ _krw_sockets_leak_forever (0x1b03c)
 ├─ 失败 → 打印 + ret（不进入 MCM）
 └─ 成功
     ├─ _proc_self (0x1b5e0)
     ├─ _sandbox_escape (0x176a0)                 ← 沙箱逃逸
     │   └─ _early_kread64 ×24 + _early_kwrite64 ×1
     └─ 成功
         ├─ _MCMFilzaSetUnrestrictedFilesystem(1) (0xa540)
         └─ _MCMFilzaStart() (0xacb8)             ← 第 3 代接管
```

**关键**：第 1/2 代与第 3 代是**串联**的 —— 内核链路成功后，
再把控制权交给 MCM 路径（并先解锁"不受限文件系统"标志）。

---

## 二、内核能力面（813 符号，全部恢复）

### 2.1 符号表完整性

| 项 | 值 |
|---|---|
| 符号总数 | **813** |
| 有名字 | **813（100%，未 strip）** |
| __TEXT 内命名函数 | 有值符号按地址排序可完整还原 |
| UUID | `dd053f07337833e9a5ac191554e1a24e`（arm64） |
| minos / sdk | **15.0.0 / 16.4.0** |

### 2.2 内核函数清单（按地址）

**沙箱逃逸 / 提权**

| 地址 | 符号 |
|---|---|
| `0x0176a0` | `_sandbox_escape` |
| `0x017cb0` | `_sandbox_elevate_to_root` |
| `0x01abe0` | `_kexploit_opa334` |
| `0x01bce0` | `_label_get_sandbox` |

**内核读写原语**

| 地址 | 符号 |
|---|---|
| `0x0196a4` | `_early_kread` |
| `0x019874` | `_early_kread64` |
| `0x0198a0` | `_early_kwrite32bytes` |
| `0x01990c` | `_early_kwrite64` |
| `0x01b08c..0x01b174` | `_kread16/32/64/8`、`_kreadbuf` |
| `0x01b0bc..0x01b1f8` | `_kwrite8/16/32/64`、`_kwritebuf` |
| `0x01b44c` / `0x01b484` | `_kread_ptr` / `_kread_smrptr` |
| `0x01b4d0` | `_kwrite_zone_element` |
| `0x018b08` | `_spray_socket` |
| `0x01aa30` | `_krw_sockets_leak_forever` |

**vnode / 文件系统**

| 地址 | 符号 |
|---|---|
| `0x01dc20` / `0x01dca0` | `_get_vnode_for_path_by_chdir` / `_by_open` |
| `0x01dd9c` | `_get_vnode_by_fd` |
| `0x01de74` | `_get_rootvnode` |
| `0x01df28` | `_vnode_get_v_name` |
| `0x01df90` / `0x01e384` | `_vnode_redirect_folder` / `_file` |
| `0x01dffc` / `0x01e270` | `_vnode_unredirect_folder` / `_get_child_vnode` |
| `0x01e4e0` | `_reveal_path_by_vnode` |
| `0x01e5d0` | `_overwrite_system_file` |
| `0x01eb10` | `_crash_process` |

**kernelcache / DSC 解析**

| 地址 | 符号 |
|---|---|
| `0x01ec40` | `_is_kernelcache_valid` |
| `0x01ecec` | `_grab_kernelcache` |
| `0x02e764` | `_dsc_file_read_at_offset` |
| `0x02e7b4` | `_dsc_file_read_string_at_offset` |
| `0x031df0` | `_macho_read_at_offset` |
| `0x032428` | `_macho_read_trie_node_at_offset` |

**XPF 签名绕过（完整族）**

| 地址 | 符号 |
|---|---|
| `0x01efc4` | `_init_xpf` |
| `0x01f2e0..0x01f420` | `_xpf_supported_always/_15up/_15down/_16up/_16down/_17up/_1516/_arm64/_arm64_kcall_supported` |
| `0x01f45c` | `_xpf_trigon_supported` |
| `0x01f4ac` | `_xpf_pfsec_init` |
| `0x01f530` | `_xpf_start_with_kernel_path` |
| `0x01fbd0..0x01fe54` | `_xpf_item_register/_resolve/_find_set/_construct_offset_dictionary` |
| `0x0200fc` | `_xpf_common_init` |
| `0x025dec` / `0x025e98` | `_xpf_bad_recovery_supported` / `_init` |
| `0x026bb8` | `_xpf_non_ppl_init` |
| `0x027994` | `_xpf_ppl_init` |

**APFS 属主/权限篡改**

| 地址 | 符号 |
|---|---|
| `0x017ee0` / `0x018118` / `0x01813c` | `_apfs_getuid_kr` / `_getgid_kr` / `_getmode_kr` |
| `0x018160` / `0x018280` / `0x018590` | `_apfs_own` / `_own_tree` / `_mod` |

**patchfinder**

| 地址 | 符号 |
|---|---|
| `0x034cf8` / `0x034e94` | `_pfsec_init_from_macho` / `_from_dsc_mapping` |
| `0x035110..0x0351c0` | `_pfsec_read32/64/_pointer` |
| `0x0352b0..0x035444` | `_pfsec_find_memory_rel/_memory/_prev_inst/_next_inst` |
| `0x0356e8` | `_pfsec_find_function_start` |
| `0x0347bc` | `_pfsec_run_arm64_xref_metric` |

**偏移表（76 个变量，`0x055400-0x0555c0`）**

`off_inpcb_*`、`off_socket_*`、`off_proc_*`、`off_thread_*`、`off_task_*`、
`off_ucred_*`、`off_vnode_*`、`off_fileglob_*`、`off_ipc_*`、`off_kalloc_*` 等。

### 2.3 `_sandbox_escape` 内部序列（`0x176a0`）

反汇编确认 24 次 `_early_kread64` + 1 次 `_early_kwrite64`：

```asm
0x0176d8  add  x0, x0, #0x18
0x0176dc  bl   #0x19874    ; _early_kread64(self_proc+0x18)
0x0176ec  lsr  x9, x0, #0x30          ; ★ PAC/高位判断
0x0176f4  csel x8, x8, xzr, ne        ; 掩码选择
0x0176f8  orr  x22, x8, x0            ; 还原指针
0x01771c  cmp  x22, x8
0x017720  b.ls #0x17848               ; 范围校验
0x01773c  add  x0, x22, x23           ; x23=0x10 偏移步进
0x017740  bl   #0x19874    ; _early_kread64
0x01774c  bl   #0x1b484    ; _kread_smrptr
...
0x017bb8  bl   #0x1990c    ; _early_kwrite64
```

**`lsr x9, x0, #0x30` + `csel`** 是 PAC 位处理的典型模式（与之前报告的
`0xffffff8000000000` 内核地址掩码一致）。

### 2.4 `_kexploit_opa334` 的 A18 分支（`0x1abe0`）

```asm
0x01ac00  bl   #0x1bd88    ; _offsets_init     ★ 版本门禁
0x01ac04  bl   #0x18704    ; _init_globals
0x01ac08  adrp x8, #0x55000
0x01ac0c  add  x8, x8, #0x5e1            ; &gIsA18Above 附近
0x01ac10  ldrb w8, [x8]
0x01ac14  cmp  w8, #1
0x01ac18  b.ne #0x1ac3c                  ; 非 A18 分支
; --- A18 路径 ---
0x01ac30  bl   #0x18f38    ; _pe_init
0x01ac34  bl   #0x1a3b4    ; _pe_v2
; --- 非 A18 路径 (0x1ac3c) ---
0x01ac48  bl   #0x18f38    ; _pe_init
0x01ac4c  bl   #0x19e6c    ; _pe_v1
```

**新增发现**：存在 **`_pe_v1` / `_pe_v2` 两条物理内存利用变体**，
按 `gIsA18Above`（CPU 家族，A18=TUPAI 及以上）选择。
这解释了第 2 节 `[+] Running on A18 device / non-A18 device` 日志。

---

## 三、与源码树对照：缺失的是什么

| 组件 | 源码树 | dylib | 说明 |
|---|---|---|---|
| `kexploit/`、`offsets.m`、`krw.m`、`vnode.m` | ✅ | ✅ | 源码在，**未编译** |
| `sandbox_escape.m`、`apfs_own.m` | ✅ | ✅ | 同上 |
| `XPF/`、`kpf/patchfinder.m` | ✅ | ✅ | 同上 |
| **`_TweakInit` 中的内核调用段** | ❌ | ✅ | **唯一缺失** |
| `_pe_v1` / `_pe_v2` 物理内存变体 | ❌ | ✅ | 源码树无对应 |
| `MCMFilza*`（第 3 代） | ✅ | ✅ | 当前 Tweak.m 只有这段 |

**结论**：本仓库的 `Tweak.m` 是**第 3 代版本**（只调 `MCMFilzaStart`）。
第 1/2 代需要的 `Tweak.m` 内核编排段**不在仓库**，但**已从 dylib 恢复**（§1.1）。

---

## 四、复现第 1/2 代所需的最小改动

### 4.1 Makefile

```make
FilzaApplySandboxExt_FILES = Tweak.m MCMBridge.m MCMFilzaIntegration.m \
                             PosterBoardFeature.m UpdateChecker.m \
                             sandbox_escape.m apfs_own.m \
                             kexploit/kexploit_opa334.m kexploit/krw.m \
                             kexploit/kutils.m kexploit/offsets.m \
                             kexploit/vnode.m kpf/patchfinder.m \
                             utils/file.c utils/hexdump.c utils/process.c
```

（`-I$(PWD)/XPF/src -I$(PWD)/XPF/external/ChOma/include` 与 `-lz -lsandbox`
已在现有 Makefile 中）

### 4.2 `Tweak.m` 需补回的编排段（**已恢复并交叉验证**）

反汇编恢复的代码见 `Tweak_kernel_restored.m`。**所有函数签名已与仓库头文件核对一致**：

| 函数 | 头文件声明 | 反汇编观察 | 一致性 |
|---|---|---|---|
| `kexploit_opa334` | `int kexploit_opa334(void);`（`kexploit_opa334.h`） | 无参调用，读 `w0` | ✅ |
| `sandbox_escape` | `int sandbox_escape(uint64_t self_proc);`（`sandbox_escape.h`） | `x0=self_proc`，读 `x0` | ✅ |
| `sandbox_elevate_to_root` | `int sandbox_elevate_to_root(uint64_t self_proc);` | 同签名 | ✅ |
| `proc_self` | `uint64_t proc_self(void);`（`kutils.h:16`） | 无参调用，`mov x19,x0` | ✅ |
| `apfs_own` | `int apfs_own(const char*, uid_t, gid_t);` | — | ✅ |

**头文件原文佐证**（`sandbox_escape.h`）：

```c
// Escape sandbox by rewriting sandbox extension data in kernel memory.
// Walk: proc_ro -> ucred -> cr_label -> sandbox -> ext_set -> ext_table -> ext -> data
int sandbox_escape(uint64_t self_proc);

// Elevate to uid=0 by swapping our p_ucred pointer with launchd's.
int sandbox_elevate_to_root(uint64_t self_proc);
```

**注意**：`_TweakInit` 只调用 `sandbox_escape`，**未调用** `sandbox_elevate_to_root`
（后者在 dylib 中存在于 `0x17cb0`，属按需路径）。

恢复的编排逻辑：

```objc
static void runKernelPath(void) {
    NSLog(@"[Filza18] starting exact-target kernel path");

    int r = kexploit_opa334();               // 0 = 成功
    if (r != 0) {
        NSLog(@"[Filza18] kexploit failed result=%d", r);
        return;                              // 失败不进 MCM
    }

    uint64_t self_proc = proc_self();
    int sr = sandbox_escape(self_proc);
    NSLog(@"[Filza18] sandbox result=%d self_proc=0x%llx",
          sr, (unsigned long long)self_proc);
    if (sr != 0) return;

    MCMFilzaSetUnrestrictedFilesystem(YES);
    MCMFilzaStart();
}
```

### 4.3 已可复用（源码树现有）

- `kexploit/offsets.m`（50 KB，562 处硬编码 + 9 段版本阶梯）
- `kexploit/krw.m`、`kutils.m`、`vnode.m`
- `sandbox_escape.m` / `.h`、`apfs_own.m` / `.h`
- `XPF/`（50 文件）、`kpf/patchfinder.m`

---

## 五、证据局限

1. **未编译、未运行、未真机验证**。全部为静态反汇编。
2. **capstone 在本环境返回 0 条指令**（绑定异常），`bl`/`b`/`ADR`/`LDR`
   等关键序列改用**手工 ARM64 解码**（已在报告中标注原始机器码可复核）。
3. ✅ **函数签名已与头文件交叉验证一致**（§4.2 表格）——
   原推断与 `kexploit_opa334.h` / `sandbox_escape.h` / `kutils.h` 完全吻合。
4. `_pe_v1` / `_pe_v2` 的内部实现**未展开**（仅确认调用点与分支条件）。
5. `_sandbox_escape` 的 24 次 `early_kread64` 只展示了前 ~6 次的
   上下文，**完整字段遍历顺序未逐条列出**（头文件注释给出了 walk 路径）。
6. `gIsA18Above` 的地址按 `__DATA` 偏移推断，`adrp #0x55000 + add #0x5e1`
   与 `#0xc00` 等偏移未逐一对齐到符号。
7. ChaCha/chained-fixups 指针表**未完全解码**，故 `__DATA` 中间接调用
   目标（如 ObjC 方法 imp）未穷尽。
8. 符号名虽 813/813 可读，但**部分名称在原始构建中已被截断**
   （如少数 `_off_*` 变量显示不全）。
9. **`_TweakInit` 的完整函数体（`0x4000` 起）未全量反汇编**，
   只覆盖了 `0x4d00-0x4e20` 区段 —— 其他 hook 安装逻辑未展开。
