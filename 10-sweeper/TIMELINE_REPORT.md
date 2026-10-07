# 权限转移时间线调查报告

生成时间：2026-09-26
调查对象：3 个 TRON 受害账户 + 1 个多签账户

---

## 一、结论摘要

**挽回窗口：已关闭。**

3 个被转移权限的 TRON 账户，其 `owner_permission` 的 key 均已**不含我们的地址**，
我们私钥对应的权重为 **0**。TRON 没有权限回滚机制，原私钥永久失去控制权。

---

## 二、目标地址（归集用）

| 链 | 地址 | 状态 |
|---|---|---|
| TRON | `TYmUVzcvX3YuwVidSSkyt5zFqjqZqKbEVq` | 已激活，TRX 4.48，权限干净（owner/active 都是自己，阈值 1） |
| EVM（6 链） | `0x259C87689fFeDA9AC06ccB5b2d6578e4E81d07D7` | 6 条链上均为 EOA，未委托，余额 0 |

两个地址均格式校验通过，**无 EIP-7702 委托、无多签**，可安全用作归集目标。

---

## 三、权限变更时间线

### 账户 1：`TUEZSdKsoDHQMeZwihtdoBiN46zxhGWYdH`（USDT 8,233.32）

| 时间 | 事件 |
|---|---|
| 2026-07-13 02:38:24 | **权限变更交易**（txid `97932b47…`），owner → `TUmd ykWXNWHbRk3V4wFGKGHKMdh6jHzijm`。由本账户私钥签名发起 |
| 2026-07-13 ~ 2026-09-26 | 账户仍持续交易（60+ 笔由本账户发起） |
| 2026-09-18 前后 | 8,233 USDT 转入 |
| 现在 | TRX = 0（被抽干），owner = `TUmd ykWX…`，我们的 weight = 0 |

### 账户 2：`TKTX96CBxr5kvhjsDHcqoiPWZageGxoTW3`（USDT 8.40）

| 时间 | 事件 |
|---|---|
| 2022-07-31 01:23:18 | **权限变更交易**（txid `9a8da6e8…`），owner → `TGsy6W3T4fs3nAMk4E6ohfXXsosbHXRLvK` |
| 现在 | TRX = 1.00，owner 权重为 0 |

### 账户 3：`TWer2Ygk5TEheHp3TPuYeqxmB6SsGZmaL6`（USDT 2.50）

| 时间 | 事件 |
|---|---|
| 2026-04-23 10:54:21 | **权限变更交易**（txid `9f0890cd…`），owner → `TDRqzjYye3bGaBtg1bAPw5F4duDchNSbtk` |
| 现在 | TRX = 8.00，owner 权重为 0 |

### 账户 4：`TMVQGm1qAQYVdetCeGRRkTWYYrLXuHK2HC`（USDT 1,000）

**权限未被转移**，但为 **2-of-2 多签**：
- `owner_permission`：阈值 2，keys = [本账户 weight=1, `TY2YRt63pM7YorXV8WNpfb3qQyvyTZzzuC` weight=1]
- `active_permission`：阈值 2，相同两个 key

我们只持有其中一个（weight=1），**单私钥无法满足阈值**。

---

## 四、攻击者地址

| 地址 | 角色 | TRX 余额 |
|---|---|---|
| `TUmd ykWXNWHbRk3V4wFGKGHKMdh6jHzijm` | 接管 TUEZSdKso… | 6.50 |
| `TGsy6W3T4fs3nAMk4E6ohfXXsosbHXRLvK` | 接管 TKTX96CB… | 366.76 |
| `TDRqzjYye3bGaBtg1bAPw5F4duDchNSbtk` | 接管 TWer2Ygk… | 111.00 |

---

## 五、为什么无法挽回

1. **权限已转移**：TRON 的 `AccountPermissionUpdateContract` 一旦执行，旧 key 立即失效。
   我们虽然有私钥，但该私钥对应的 key 已不在权限列表中（weight=0）。

2. **没有回滚机制**：区块链交易不可逆，无法"撤销"权限变更。

3. **gas 也已被抽干**：被转移的 3 个账户 TRX 余额分别为 0、1.00、8.00，
   即使权限尚在，也不足以支付 TRC20 归集手续费（需约 30 TRX）。

4. **多签账户缺一方**：`TMVQGm1q…` 需要 2 个 key 共同签名，
   我们只有其中一个，且另一个 key 属于 `TY2YRt63…`（非我方控制）。

---

## 六、一个待解释的疑点

`TUEZSdKso…` 的权限变更发生在 **2026-07-13**，
但接管地址 `TUmd ykWX…` 的 `create_time` 是 **2026-09-18**。

**这不是矛盾** —— `create_time` 只表示该地址首次成为链上账户的时间，
在权限中引用一个尚未激活的地址完全合法。

但它留下一个未解问题：**7-13 那次变更时，攻击者已持有我们的私钥**，
否则无法用我们的私钥签名发起该交易。这意味着私钥泄露时间**早于** 7-13，
而不是在 9-18 资金转入时才发生。

**建议排查**：7-13 之前我们对该私钥的使用/存储环境（生成脚本、备份位置、传输途径）。

---

## 七、可执行的部分

| 类别 | 数量 | 状态 |
|---|---|---|
| TRON 可归集 | **0** | 全部受阻 |
| EVM 未被委托 + gas 充足 | 8 | 见 `prepare/A_safe_to_sweep.csv` |

即：**当前唯一可实际归集的是那 8 个未被 EIP-7702 委托的 EVM 地址**，
合计约 0.05 BNB + 2.36 USDT + 0.71 POL + 少量 ETH。
