package blockchain

// ★ WBE01-A 卡A：A/B 两路**共用**的利润累加函数。
//
// ★★ 为什么放在 `blockchain` 而不是 `service/app`：
//   `service/app/public.go:6` 已经 import 了本包 ⇒ 若把本函数放在 `service/app`，
//   本包再反向 import 就会形成 **import cycle**。⇒ 共用件的落点必须顺着**已有的依赖方向**
//   （`service/app → blockchain`），故落在本包；`service/app` 侧以 `blockchain.` 前缀调用。
//
// ★ 语义：把利润累加到对应主体（客户 = sys_users.id 经 custom.user_id；代理 = agent.user_id）。
// ★ 一处**必须说明的差异**：**CAS（按 bill.status 的<前值>）只适用于 A 路** ——
//   A 路的 bill 由 `status=0` 起、核验成功才置 1，故"前值==0"可作守卫；
//   而 **B 路的 bill 是「创建即 status=1」**（gasleak 已完成链上确认才回传），**没有前值可守**；
//   它的幂等由 **`uk_txhash_role` 唯一键**（transfer_hash, role）保证 —— 同 hash 同 role 至多一行。
//   ⇒ 故本函数**只做累加**；**CAS 由 A 路的调用方（scan.go 的核验事务）包在外面**。

import (
	"fmt"

	"gorm.io/gorm"

	"github.com/flipped-aurora/gin-vue-admin/server/model/app"
)

// AccumulateUsdtNum ★ 卡A：把利润累加到对应主体（客户 role=2 / 代理 role=3）。
//
//	★ A/B 两路**共用这一套累加语义**（⛔ 不写两版）—— A 路见 blockchain/scan.go 的核验路径，
//	  B 路见本文件 CollectResult 的创建事务内。
//	★★ 一处**必须说明的差异**：**CAS（按 bill.status 的<前值>）只适用于 A 路** ——
//	  A 路的 bill 由 `status=0` 起，核验成功才置 1，故"前值==0"可作守卫；
//	  而 **B 路的 bill 是「创建即 status=1」**（gasleak 已完成链上确认才回传），**没有前值可守**；
//	  它的幂等由 **`uk_txhash_role` 唯一键**（transfer_hash, role）保证 —— 同 hash 同 role 至多一行。
//
//	★★ F-01（复核阻断项）修法：**必须判 `RowsAffected`** —— 原实现只返回 `.Error`，
//	  于是"`Where("user_id = ?", userId)` 匹配 0 行"时**返回 nil** ⇒ CAS 事务**照常提交** ⇒
//	  **bill 被置 1 消费、钱却永不归属**，而 scan 只捞 `status=0` ⇒ **永不再被选中**（静默漏记）。
//	  两条触发路径：① `scan.go` 的 `transInfoList[i].UserId` 取自 **left join settlement** ⇒
//	  settlement 缺行 ⇒ `UserId=0` ⇒ 匹配 0 行；② 未知 `role`。
//	  ⇒ CAS 关掉了"置 1 后中断"的窗口，**但没关掉"0 行匹配"这条同样静默的窗口**。
//
//	★ 附注（B 路自带的一道守卫）：`mkBill` 在 `settlementId <= 0` 或 `num.IsZero()` 时返回 nil
//	  ⇒ 不落该笔、也不累加 ⇒ **「恰好」规避了 F-01 的 `user_id=0` 路径**。
//	  ★★ **"恰好"二字是要点**：它**不是设计时想到的**，而是 `mkBill` 原有判据的副产品
//	  ⇒ **将来改 `mkBill` 的人必须知道：它此刻还在承担这道防漏记职责**（改掉它 ⇒ F-01 的 `user_id=0` 路径会在 B 路也打开）。
//	  A 路没有这层，故必须**只靠本函数的 `RowsAffected` 判据**。
func AccumulateUsdtNum(tx *gorm.DB, billId int, role int, userId int, usdtNum string) error {
	var res *gorm.DB
	switch role {
	case 2: // 客户
		res = tx.Model(&app.Custom{}).Where("user_id = ?", userId).
			Update("usdt_num", gorm.Expr("usdt_num + ?", usdtNum))
	case 3: // 代理
		res = tx.Model(&app.Agent{}).Where("user_id = ?", userId).
			Update("usdt_num", gorm.Expr("usdt_num + ?", usdtNum))
	default:
		// ★ F-01：未知 role **必须显式报错**（原为 `return nil` ⇒ 静默跳过）
		return fmt.Errorf("AccumulateUsdtNum: bill.id=%d 未知 role=%d（拒绝静默跳过；userId=%d）", billId, role, userId)
	}
	if res.Error != nil {
		return res.Error
	}
	if res.RowsAffected != 1 {
		// ★ F-01 核心：匹配 0 行（或 >1 行）**不得静默提交** —— 返回 error ⇒ 调用方的 gorm 事务回滚
		return fmt.Errorf("AccumulateUsdtNum: bill.id=%d role=%d userId=%d 累加匹配 %d 行（应恰 1 行）⇒ 拒绝静默提交，回滚",
			billId, role, userId, res.RowsAffected)
	}
	return nil
}

// MarkProcessedAndAccumulate ★ F-03/F-05（复核 finding）：把 A 路的「CAS 置 status=1 ＋ 利润累加」
// 抽成**唯一一处**，供**产品码（`scan.go` 的核验事务）与单测（`billing_test.go`）共调**。
//
// ★ 为什么必须抽（复核原文）：`billing_test.go` 原先**复制**了 `scan.go` 的 CAS 形态
//
//	⇒ 两者是"同形复制"而非"同一函数" ⇒ 把产品码的守卫改窄/删掉，**单测仍绿**（断言与产品码脱节）。
//	抽成共调后：产品码只剩**一处**（无"另一侧"可漂移 ⇒ 解 F-03）；单测**直接执行产品码那段守卫**
//	（改窄 ⇒ 单测必红 ⇒ 解 F-05）。
//
// ★ 语义（与抽取前两处的行为**一字不改**）：
//
//	· CAS 命中 **0 行**（已被处理过／并发者抢先）⇒ **幂等跳过**，`return nil`（⛔ 不是错误）
//	· CAS 命中恰 1 行 ⇒ 继续累加（累加自身的守卫见 `AccumulateUsdtNum`：`RowsAffected != 1` ⇒ 报错回滚）
//
// ★ 本函数**只适用于 A 路**：B 路的 bill「创建即 status=1」，**没有 `status=0` 前值可守**，
//
//	其幂等由 `uk_txhash_role` 唯一键保证（见上方 `AccumulateUsdtNum` 的说明）。
func MarkProcessedAndAccumulate(tx *gorm.DB, billId int, role int, userId int, usdtNum string) error {
	res := tx.Model(&app.Bill{}).Where("id = ? AND status = 0", billId).Update("status", 1)
	if res.Error != nil {
		return res.Error
	}
	if res.RowsAffected != 1 {
		return nil // 已被处理过（或并发者抢先）⇒ 幂等跳过
	}
	return AccumulateUsdtNum(tx, billId, role, userId, usdtNum)
}
