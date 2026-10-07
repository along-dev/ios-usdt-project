---
id: R2-C4
mode: 实施
wave: R2
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R1
定档理由: |
  ★ 源卡 `R2-C4` **自己给出档位**：「**纯风格修正，无行为变更 ⇒ R1**」。
  ★ 但 `sys_captcha.go:6` 的 tag 语法错**可能有行为影响** ⇒
    判据须**验证 captcha 接口行为未变**（**不只是 vet 通过**）。
  门禁强度自知：**不能只看 vet 通过**。
来源: ★ **`后续剩余工作策划_卡片化.md:481-519`**（`R2-C4` 完整规格）
      + ★ **调度实测**：`go vet ./...` 当前 **5 条**告警（**4 条属本卡 + 1 条 card 外**）
base:
  - path: 01-backend-go\api\v1\response\sys_captcha.go
    sha256: ea09af84146e0f93af1c6ff82dfbed4d0c56e462dcce26b2a1697955377bb095
    bytes: 179
    eol: LF
  - path: 01-backend-go\service\system\sys_user.go
    sha256: e878fc1b6bcd15c7bac8903ba9300b2fff6011bb22bbfc46fa58a13b85d2b535
    bytes: 8882
    eol: LF
  - path: 01-backend-go\service\system\sys_initdb_mysql.go
    sha256: 16507f025760c96587794d84110bca29394ffed2d107d4df29221cceb6540755
    bytes: 2882
    eol: LF
  - path: 01-backend-go\service\system\sys_initdb_pgsql.go
    sha256: 6a2be098241f75fdd53d1bdc92c16a8899b35f2ab5c62f45c93818eda4bf8aba
    bytes: 2716
    eol: LF
allowed_paths:
  - 01-backend-go\api\v1\response\sys_captcha.go
  - 01-backend-go\service\system\sys_user.go
  - 01-backend-go\service\system\sys_initdb_mysql.go
  - 01-backend-go\service\system\sys_initdb_pgsql.go
  - 09-docs\reports\开发规则与调度说明.md（★ 更正"3 条"为"5 条"）
  - E:\ios漏洞\_integration\_fix_work\verify_r2c4_govet.py
forbidden_paths:
  - "01-backend-go\\blockchain\\**（归 D0-C2，已验收）"
  - "01-backend-go\\blockchain\\trc_test.go（★ 其 vet 告警【不属本卡】）"
  - "09-docs\\spec\\contracts.md"
  - "02-backend-node/**、05-ios/**、06-android/**、03-web-admin/**、04-landing/**"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_r2c4_govet.py    # 动前红 / 动后绿
packages: {}
---

# R2-C4 [R1] `go vet` 风格告警处置

## ★★★ 实测的 5 条告警（**调度已取原文**）

| # | 位置 | 内容 | 属本卡？ |
|---|---|---|---|
| **1** | `api\v1\response\sys_captcha.go:6:2` | `struct field tag \`json:"captchaLength""\` not compatible with reflect.StructTag.Get` | ✅ **是** |
| **2** | `blockchain\trc_test.go:392:8` | `using res before checking for errors` | ❌ **卡外**（既有，归 D0-C2 范畴）|
| **3** | `service\system\sys_user.go:179:40` | `SysUseAuthority struct literal uses unkeyed fields` | ✅ **是** |
| **4** | `service\system\sys_initdb_mysql.go:86:4` | `Printf format %+v reads arg #3, but call has 2 args` | ✅ **是** |
| **5** | `service\system\sys_initdb_pgsql.go:85:4` | 同上 | ✅ **是** |

★ **源卡 `:519` 明文**：
> ★ 文档记载「**3 条既有告警**」**实测是 5 条** ⇒ **同步更正 `开发规则与调度说明.md`**。

## ★★★ 四处源码原文（**调度已取**）

### #1 `sys_captcha.go:6`（**179 B 的小文件**）

```go
4:  CaptchaId     string `json:"captchaId"`
5:  PicPath       string `json:"picPath"`
6:  CaptchaLength int    `json:"captchaLength""`     ← ★ 多了一个引号
7:  }
```

**修法**：改为 `json:"captchaLength"`。

★★ **关键注意（源卡 `:516-517` 明文）**：
> `sys_captcha.go:6` 的 tag 语法错**可能导致该字段 JSON 序列化行为异常** ⇒
> **修完须验证 captcha 接口行为未变**（**不能只看 vet 通过**）。

**⇒ 本卡判据**须含**行为断言**：
- **修复前**：`json.Unmarshal` 该 tag 时字段名可能异常
- **修复后**：`captchaLength` 字段**正确序列化/反序列化**

### #3 `sys_user.go:179-181`

```go
179:  useAuthority = append(useAuthority, system.SysUseAuthority{
180:      id, v,          ← ★ 未命名字段
181:  })
```

**修法**：改为**具名字段**（**须先实读 `SysUseAuthority` 的字段定义**）。

★ **若字段顺序不确定** ⇒ **停下报告**（改错会**改变语义**）。

### #4/#5 `sys_initdb_{mysql,pgsql}.go`

```go
86:  color.Info.Printf(InitDataFailed, Mysql, err)     // mysql
85:  color.Info.Printf(InitDataFailed, Pgsql, err)     // pgsql
```

**`InitDataFailed` 的格式串有 3 个 `%`**（`%+v` 读 arg #3），**但只传了 2 个实参**。

**修法**：**须实读 `InitDataFailed` 的定义**，二者取一：
- **补一个实参**（若格式串本意是三段）
- **改格式串**（若本意是两段）

★ **须在报告中说明选择了哪种及理由**。

## ★★ 判据要求

| # | 断言 |
|---|---|
| **V1** | ★ **`go vet ./...` 中，4 条本卡告警【全部消失】** |
| **V2** | ★ **`trc_test.go:392` 的告警【仍在】**（**不得误改卡外文件**）|
| **V3** | ★ **`go build ./...` EXIT=0** |
| **V4** | ★ **captcha tag 的行为断言**：`captchaLength` 字段**正确序列化/反序列化** |
| **V5** | ★ **`sys_user.go` 的行为未变**（`SysUseAuthority` 的赋值语义相同）|
| **V6** | ★ **未改卡外文件**（`blockchain/**` 等 sha256 未变）|
| **V7** | ★ **规则手册已更正**「3 条 ⇒ 5 条」 |
| **V8** | 守护：`_manifest.sha256`、`contracts.md` 未改 |

★ **V1 + V2 是一对** —— **既证明修好了，又证明没改过头**。
★ **V4 是本卡的特殊要求**（源卡明文）。

## 不在范围

- **不改** `blockchain/**`（含 `trc_test.go`）
- **不改** Node 侧
- **不追求 `go vet ./...` 完全归零**（`trc_test.go` 的告警**有意保留**）

## 证据要求

- 判据动前红 / 动后绿两次真实退出码
- ★ **`go vet ./...` 的改前/改后完整输出**
- ★ **4 个文件的 sha256 改前/改后**
- ★ **`SysUseAuthority` 的字段定义**（证明具名赋值语义相同）
- ★ **`InitDataFailed` 的定义与所选修法**
- ★ **V4 的行为断言输出**
- ★ **V7 的规则手册更正**
- ★ 声明：**未改卡外文件**

## 停靠点

1. ★★ **若 `SysUseAuthority` 的字段顺序不确定** ⇒ **停下报告**（**改错会改语义**）
2. ★★ **若 `InitDataFailed` 的本意不明**（该补参还是改格式串）⇒ **停下报告**
3. ★ **若发现 `sys_captcha.go` 的 tag 修复会改变现有 API 响应** ⇒ **停下升级**
4. ★ **若 `go vet` 出现【新的】告警**（本卡引入）⇒ **停下报告**
