---
id: R4-C4
mode: 实施
wave: R4
depends: [R-05 裁决]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R1
定档理由: |
  ★ 源卡 `R4-C4` **自己给出档位**：「**纯文档登记，配合裁决 A ⇒ R1**」。
  ★ 但 **Owner 裁决 (a) 扩展为「脱敏后保留」** ⇒
    本卡**同时**：① 脱敏 `privesc_results.json`；② 新建 README 登记"未证实"。
  ★ 脱敏是**数据修改** ⇒ 需**保形断言**（结构不变、仅密钥被替换）。
来源: ★ **`后续剩余工作策划_卡片化.md:845-886`**（`R4-C4` 规格）
      + ★★ **Owner 裁决 (a)**（对 R-05 的处置）
      + ★★ **R-05 登记**（`残余暴露面登记.md`）
      + ★★ **R3-C1-B 独立复核**（`#22` 明文 `AccessKey`+`SecretKey`）
base:
  - path: 11-payment\privesc_results.json
    sha256: b59b7c6c0f3861ca4ac7641a21c54243988a026f459ca7b9160727b7ca2bce76
    bytes: 14774
    eol: CRLF
    note: |
      ★★ **调度勘误（执行者纠正）**：
      - **真实 bytes = 14,774**（非 14,563）
      - **真实 eol = CRLF（211 对）**，裸 LF=0、裸 CR=0（**非 LF**）
      - 行数 = **212**（211 个 CRLF 分隔符，末行无尾随换行）
      - 结构：list，**30 条**，键集合 `['method','path','resp','status','tag']`
      - ★ **不在 `_manifest.sha256` 中**（0 命中）

      ★★ **我的错误根源**：
      我用 `io.open(encoding='utf-8', errors='replace')` **文本模式**读文件，
      **文本模式做通用换行转换** ⇒ `\r\n` 已被转成 `\n` ⇒ **CRLF 计数恒 0**；
      且 `len(s.encode('utf-8'))=14,563` 是**转换后**的字节数，**非文件真实字节数**。
      **⇒ 用文本模式测二进制属性（eol/bytes）必然错。**
      ★ 这是 **P-36**（**P-5 / P-32 的同族**）。

## ★★★ 停靠点全部消除（**执行者实测**）

**全 30 条的凭据扫描（正则修正后）**：

| 关键词 | 命中 |
|---|---|
| **`AccessKey`** | **1 处** —— `[22]`（**0-based**）/ **第 23 条**（**1-based**）|
| **`SecretKey`** | **1 处** —— 同一条 |
| `password` / `Password` / `token` / `Token` / `Bearer` / `JWT` | **全部 0 处** |

**★ 且两值在全文各仅出现 1 次、同一物理行（0-based line 160）**
⇒ **行内局部操作，不涉及跨行结构重排**。

**★ 替换对反斜杠完全透明**（两个值均为**纯 ASCII**，不含引号/反斜杠）
⇒ **转义层级不可能被破坏** ⇒ **停靠点 3 排除**。

**⇒ 无扩大泄漏** ⇒ **脱敏范围精确为「仅第 23 条的这两个值」** ✓

★★ **Owner 裁决：V5 = 「eol 与 base 一致（CRLF）」**（**不是「LF 保持」**）
—— 因 (B) 转 LF 会动 **211 处行尾** ⇒ **违反 V4** ⇒ **V4/V5 互斥，不可行**。
allowed_paths:
  - 11-payment\privesc_results.json（★ 仅脱敏密钥字段）
  - 11-payment\README.md（★ 新建：登记"未证实"）
forbidden_paths:
  - "★ 11-payment\\token.json（已不存在，不得生成）"
  - "09-docs\\spec\\contracts.md"
  - "全部其他产物代码"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_r4c4_privesc.py    # 动前红 / 动后绿
packages: {}
---

# R4-C4 [R1] `privesc_results.json` 脱敏 + 标注"未证实"

## ★★★ Owner 裁决（**已下达**）

**对 R-05 的裁决：方案 (a) —— 产物层脱敏，凭据替换为 `<REDACTED>`。**

## ★★★ 事实（**调度 + R3-C1-B 双路确认**）

### 文件

```
E:\USDT项目\11-payment\privesc_results.json
  sha256 = b59b7c6c0f3861ca4ac7641a21c54243988a026f459ca7b9160727b7ca2bce76
  bytes  = 14,774    eol = CRLF    顶层 = list，30 条
  ★ 不在 _manifest.sha256 中（0 命中）
```

### ★ 泄漏内容（**第 22 条记录**）

```json
{
  "method": "GET",
  "path": "/api/ApiKey/List",
  "tag": "API密钥列表",
  "status": 200,
  "resp": "{\"Data\": {\"AccessKey\": \"<REDACTED_ACCESSKEY>\",
                    \"SecretKey\": \"670aaaa1039cfe6ef25d48678acfe4a65816396b\"},
            \"Code\": 0, \"Message\": \"\"}"
}
```

| 字段 | 值 |
|---|---|
| **`AccessKey`** | **`<REDACTED_ACCESSKEY>`** |
| **`SecretKey`** | **`670aaaa1039cfe6ef25d48678acfe4a65816396b`** |

### ★ 决策 9 的冲突

**决策 9 原文**：「**保留 `privesc_results.json`**（30 条提权结论，~~非凭据~~）」
⇒ **实测证明「非凭据」为假** ⇒ **Owner 据实裁决为「脱敏后保留」**。

## ★★ 规格

### (1) 脱敏 `privesc_results.json`

**★ 只替换密钥的值**，**其余结构逐字节保持**：

| 字段 | 原值 | 替换为 |
|---|---|---|
| `AccessKey` | `3elznokxabjq7ert7snruprh` | **`<REDACTED_ACCESSKEY>`** |
| `SecretKey` | `670aaaa1039cfe6ef25d48678acfe4a65816396b` | **`<REDACTED_SECRETKEY>`** |

★ **关键约束**：
- ★ **只改第 22 条的 `resp` 字段内的这两个值**（**因为 `resp` 是被转义的 JSON 字符串**）
- ★ **其余 29 条记录、其余字段、JSON 缩进格式【一律不变】**
- ★ **`\` 转义层级必须保持**（`resp` 是字符串，内含转义引号）
- ★ **CRLF 保持**

### (2) 新建 `11-payment/README.md`（**登记"未证实"**）

**须含**：
1. **`privesc_results.json` 的定性**：30 条**项目外目标**的提权结论
2. ★ **「未证实」标注**（**明文出现"未证实"三字**）
3. **决策 9 的依据**（**保留、非凭据** ~~已证伪~~ ⇒ **脱敏后保留**）
4. ★ **脱敏说明**（哪些字段被替换、为何）
5. **`token.json` 已排除**的说明

## ★★ 判据要求

| # | 断言 |
|---|---|
| **V1** | ★ **`privesc_results.json` 中【不再含】原 `AccessKey`/`SecretKey` 值** |
| **V2** | ★ **`<REDACTED_ACCESSKEY>` / `<REDACTED_SECRETKEY>` 出现** |
| **V3** | ★★ **保形断言**：**JSON 结构不变**（仍为 list、**30 条**、键集合不变）|
| **V4** | ★ **其余 29 条记录的 `resp` 逐字节不变**（对比 base） |
| **V5** | ★ **CRLF 保持** |
| **V6** | ★ **`11-payment/README.md` 存在且含"未证实"** |
| **V7** | ★ **`token.json` 仍不存在** |
| **V8** | 守护：`_manifest.sha256`、`contracts.md` 未改 |

★ **V4 是"不过度脱敏"的证据**（**只动该动的**）。
★ **V3 是"保形"的证据**。

## ★ 不在范围

- **不改** 其余 29 条记录的内容
- **不删** 任何记录
- **不改** `token.json`（不存在）
- **不做** `resp` 字段的整体脱敏（**Owner 未裁，本卡只脱密钥**）

## ★ 证据要求

- 判据**真实退出码**（动前红 / 动后绿）
- ★ **脱敏前后的 key 值对照**
- ★ **V3 的保形断言输出**（30 条、键集合）
- ★ **V4 的"其余 29 条逐字节不变"证据**
- ★ **README 全文**
- ★ 声明：**未改其余 29 条、未改 `token.json`**

## 停靠点

1. ★★ **若发现该文件的**其他记录**也含凭据** ⇒ **停下升级**（登记后另裁）
2. ★★ **若脱敏会破坏 JSON 结构** ⇒ **停下报告**
3. ★ **若 `resp` 的转义层级无法精确保留** ⇒ **停下报告**
