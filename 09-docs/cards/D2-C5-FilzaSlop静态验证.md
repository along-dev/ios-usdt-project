---
id: D2-C5
mode: 验证
wave: D2
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  方案 `:199` 要求「验证 FilzaSlop Theos 可编译出 dylib」（R2）。
  ★ **本机不可执行真编译**（Theos 官方不支持 Windows；无 THEOS / clang / iOS SDK）——
    已由调度实测确证（Owner 已裁 **(B1) 降级为静态验证**）。
  ⇒ 本卡为**静态验证卡**，且**必须如实登记"未在真 SDK 编译"**（V0 D-4 同族，不得假装）。
来源: `完整版本开发方案_终版.md:199`（D2-C5）
      + Owner 裁决 (B1)：降级为静态验证
      + ★ 调度实测：本机无 Theos / clang / iOS SDK（Theos 不支持 Windows）
base:
  - path: 05-ios\tools\FilzaSlop\Makefile
    sha256: 由调度现场重取
    bytes: 由调度现场重取
    eol: LF
  - path: 05-ios\tools\FilzaSlop\Tweak.m
    sha256: 由调度现场重取
    bytes: 由调度现场重取
    eol: LF
allowed_paths:
  - E:\ios漏洞\_integration\_fix_work\verify_d2c5_filzaslop_static.py
forbidden_paths:
  - "★ 全部产物（本卡为纯验证卡，不修改任何文件）"
  - "05-ios\\tools\\FilzaSlop\\**（只读）"
  - "09-docs\\spec\\contracts.md"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_d2c5_filzaslop_static.py    # 须【绿】，退出码 0
packages: {}
---

# D2-C5 [R2] FilzaSlop 静态验证（Theos 编译**在本机不可执行**）

## ★★ 结论先行

### 1. **真编译不可执行**（环境限制，非产物缺陷）

| 项 | 实测 |
|---|---|
| **Theos** | ❌ **未安装**（`E:\theos` 等均无；`THEOS` env 未设置） |
| **clang / iOS SDK** | ❌ **无**（`Get-Command clang` 失败） |
| **Theos 平台支持** | Theos **官方只支持 macOS / Linux**，**不支持 Windows** |

**⇒ 本卡**降级为静态验证**（Owner 已裁 (B1)）。**

★ **必须如实登记"未在真 SDK 编译"** ——
**不得**把"静态检查通过"表述为"可编译"（**P-22/P-24 同族**）。

### 2. ★★ **静态验证已发现一处真实缺口**

**Makefile 的 `-I` 路径与源码的 `#include` 不匹配**：

```makefile
# Makefile
FilzaApplySandboxExt_CFLAGS = -I$(PWD)/compat -I$(PWD) \
    -I$(PWD)/XPF/src \
    -I$(PWD)/XPF/external/ChOma/include \     ← ★ 该目录【不存在】
    -Wno-unused-function ...
```

**实测**：

| `-I` 路径 | 实际 |
|---|---|
| `$(PWD)/compat` | ✅ 存在 |
| `$(PWD)` | ✅ 存在 |
| `$(PWD)/XPF/src` | ✅ 存在 |
| **`$(PWD)/XPF/external/ChOma/include`** | ❌ **不存在** |

**而 ChOma 的实际结构是 `XPF/external/ChOma/src/`**（38 个文件，**无 `include/` 子目录**）。

**源码 `#include` 的头**（如 `CSBlob.h`、`DyldSharedCache.h`、`CachePatching.h`、
`MachO.h`、`PatchFinder.h`、`arm64.h`、`fixup-chains.h`）
**全部位于 `ChOma/src/`** —— 而 **Makefile 的 `-I` 列表里【没有】`ChOma/src`**。

**⇒ 若真编译，这些头将无法解析** ⇒ **编译必然失败**。

★ **但**：本机**无法真编译验证** ⇒ 该结论是**静态推断**，**须如实标注**。

## 本卡的验证目标（静态）

| # | 断言 | 说明 |
|---|---|---|
| **V1** | FilzaSlop 源码**完整性**：Makefile 声明的 5 个 `.m` 全部存在 | `Tweak.m` / `MCMBridge.m` / `MCMFilzaIntegration.m` / `PosterBoardFeature.m` / `UpdateChecker.m` |
| **V2** | 依赖子目录存在：`XPF/` `compat/` `kexploit/` `kpf/` `utils/` `Resources/` | — |
| **V3** | ★ **Makefile 的每个 `-I` 路径都存在** | **本项即能抓出上述缺口** |
| **V4** | ★ **源码 `#include` 的裸头名在其 `-I` 路径中可解析** | 逐头核对 |
| **V5** | `Makefile` 语法自洽（`TARGET` / `ARCHS` / `include $(THEOS)`） | — |
| **V6** | ★ **如实声明"未真编译"**（判据输出中明确打印） | 防"假绿" |

★ **V3/V4 是本卡的核心** —— 它们把"可编译性"的**静态部分**变成机械判据。

## 不在范围

- **不改任何文件**（纯验证）
- **不安装 Theos**（需 macOS/Linux）
- **不尝试交叉编译**（无 iOS SDK）

## 证据要求

- 判据的真实退出码
- ★ **V3 的逐路径核对结果**（哪条存在/不存在）
- ★ **V4 的逐头核对结果**（哪些头能解析、哪些不能）
- ★ **明确声明**：本卡**未**在真 Theos / 真 iOS SDK 上编译
- ★ **若 V3/V4 发现缺口** ⇒ **如实报告，并给出修复建议**（不改文件）

## 停靠点

1. 若发现**需改 Makefile** 才能编译 ⇒ **登记并升级**（改 Makefile 属产物改动，本卡不做）
2. 若发现**源码本身不完整**（缺关键 `.m`/`.h`）⇒ **停下升级**
3. 若 WSL 可用且能装 Theos ⇒ **登记该可能性**（本卡不执行）
