// ============================================================================
// §4.2.3 归集结果接收 service（新增文件）
// 目标路径: service/app/collect_result.go
// ============================================================================
// ⚠ 与 sys_qianke.Sk() 的关键差异：
//
//	Sk()  = 【创建 bill + 执行链上 Transfer*】   ← 手动兜底路径
//	本文件 = 【仅创建 bill，不转账】              ← gasleak 归集后的记账路径
//
// 分账口径【必须在两份代码间保持一致】：
//
//	  systemAmount = totalAmount * packet.TechnicalServiceFee / 100
//	  agentAmount  = totalAmount * agent.Ratio / 100
//	  customAmount = totalAmount - systemAmount - agentAmount   ← 金额残差
//	↑ 与 scan.go 的 Sk() 完全同源，改动任一处必须同步另一处。
//
// ============================================================================
package app

import (
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/flipped-aurora/gin-vue-admin/server/blockchain"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/model"
	"github.com/flipped-aurora/gin-vue-admin/server/model/app"
	"github.com/flipped-aurora/gin-vue-admin/server/utils"
	"github.com/go-sql-driver/mysql"
	"github.com/google/uuid"
	"github.com/shopspring/decimal"
	"gorm.io/gorm"
)

// CollectResultOut 归集回传结果
type CollectResultOut struct {
	BillId     int  `json:"billId"`     // 主 bill（平台侧 role=1）ID
	Duplicated bool `json:"duplicated"` // true = 该 tx_hash 已处理过
}

// CollectResult 处理 gasleak 归集结果，幂等落 bill（不执行链上转账）
func (p *PublicService) CollectResult(req *model.ReqCollectResult) (out CollectResultOut, err error) {
	if req.TxHash == "" {
		return out, errors.New("txHash is required")
	}

	// ---- ⓪ chain 归一（★ 必须在【全部】settlement / token 查询之前）----
	// gasleak 回传的 chain 取的是它自己的枚举 {eth, tron, btc}，
	// 而潜客侧 settlement.chain ∈ {eth,bsc, trx}、token.chain ∈ {eth,trx,bsc}。
	// 不归一 ⇒ 下面三处 LIKE '%tron%' 匹配不到任何行、token 也查不到
	//        ⇒ 三处 settlement 全为 0 ⇒ mkBill 全部返回 nil
	//        ⇒ 一条 bill 不写、billId=0，但事务照常提交、占位照常释放、
	//          HTTP 200 + code:0 —— 链上钱已转出，潜客侧 0 记账（静默丢账）。
	// 词表与取舍见 09-docs/spec/contracts.md C-1（只读契约）。
	chain, err := normalizeChain(req.Chain)
	if err != nil {
		return out, err
	}

	err = global.GVA_DB.Transaction(func(tx *gorm.DB) error {
		// ---- ① 定位钱包（wallet_id 直取，或由 device_id+chain+address 反查）----
		// gasleak 侧 DerivedAddress/CollectLog 不持有 wallet id，
		// 故须支持用 device_id + chain + address 反查（见 wallet_resolver.go）。
		// ★ 传归一后的 chain：wallet_resolver 的词表同时接受 trx 与 tron。
		walletId, e := ResolveWalletId(tx, req.WalletId, req.DeviceId, chain, req.Address)
		if e != nil {
			return e
		}
		var wallet app.Wallet
		if e = tx.Where("id = ?", walletId).First(&wallet).Error; e != nil {
			return fmt.Errorf("wallet %d not found: %w", walletId, e)
		}

		// ---- ② 幂等：以 tx_hash 为唯一键 ----
		// 先查后插挡住绝大多数重复；并发下由复合唯一索引
		// uk_txhash_role (transfer_hash, role) 兜底。
		//
		// ★ 注意：分账会为同一 tx_hash 写【多行】（role 1/2/3），
		//   故唯一键**必须**是 (transfer_hash, role) 复合键；
		//   若建成全列唯一 (transfer_hash)，第 2 行必然报
		//   ERROR 1062 Duplicate entry —— 已实测踩坑（见迁移脚本说明）。
		//
		// ★★ T31（契约 C-6）：**本次删除的那行必须按「首次那笔」取** ——
		//   原为裸 `Limit(1)`（**无 ORDER BY**）⇒ 返回**任意一行**（可能是 role=2/3/4）
		//   ⇒ 与 C-6「返回**首次的 bill** id」不符，也与本函数 §⑤-b「平台那笔作为主 bill」的自述不符。
		//   加 `Order("id ASC")` ⇒ 同一 transfer_hash 下 **id 最小者**：
		//     public（Region != 2）：role=1 **先插** ⇒ id 最小者即 role=1（＝首次提交返回给调用方的那笔）；
		//     private（Region == 2）：只落 role=4 **一行** ⇒ 同一结论成立。
		//   ★⛔ **不得**改成 `AND role = 1` —— 私域根本不写 role=1（§⑤-a）⇒ 硬编码会让**私域幂等彻底失效**。
		var exist app.Bill
		if e = tx.Where("transfer_hash = ?", req.TxHash).Order("id ASC").Limit(1).Find(&exist).Error; e != nil {
			return e
		}
		if exist.ID > 0 {
			out.BillId = int(exist.ID)
			out.Duplicated = true
			// 重复回传说明上一次已完成归集，占位理论上已释放；
			// 此处仍兜底归零，避免异常路径把钱包永久锁死。
			return ReleaseCollectLock(tx, walletId)
		}

		// ---- ③ 取分账基数（与 Sk() 同源）----
		totalAmount, e := decimal.NewFromString(req.Amount)
		if e != nil {
			return fmt.Errorf("invalid amount %q: %w", req.Amount, e)
		}
		// ★ F1-C8：金额必须为【正】。
		//   实测缺陷（由 I2-C1 真 HTTP + 真 DB 发现）：
		//     负 amount 会被完整接受（code=0）并落负数账单 ——
		//     平台/代理/客户三笔 num 均为负，可【反向冲减】代理与客户的 usdt_num。
		//   归集回传是唯一能污染分账数据的写入口，故负值必须在入口拒绝。
		//   零值：mkBill 有 num.IsZero() 兜底不会落账，但回 code=0 会
		//     误导调用方"已记账"，故一并显式为错。
		if totalAmount.IsNegative() || totalAmount.IsZero() {
			return fmt.Errorf("invalid amount %q: must be positive", req.Amount)
		}

		var packet app.Packet
		if e = tx.Select("packet.*").Model(app.Machine{}).
			Joins("left join agent on machine.agent_id = agent.id").
			Joins("left join packet on agent.packet_id = packet.id").
			Where("machine.id = ?", wallet.MachineId).Find(&packet).Error; e != nil {
			return e
		}

		// 代理佣金比例
		var agentSettlement struct {
			ID      int
			Address string
			Ratio   int
			UserId  int
		}
		_ = tx.Model(app.Agent{}).
			Where("machine.id = ? AND settlement.chain LIKE ?", wallet.MachineId, "%"+chain+"%").
			Joins("left join settlement on settlement.user_id = agent.user_id").
			Joins("left join machine on machine.agent_id = agent.id").
			Select("settlement.id, settlement.address, agent.ratio, agent.user_id").
			Find(&agentSettlement).Error

		// 平台技术服务费收款地址
		var systemSettlement app.Settlement
		_ = tx.Select("settlement.*").
			Where("settlement.user_id = 0 AND settlement.chain LIKE ?", "%"+chain+"%").
			Find(&systemSettlement).Error

		// ---- ④ 比例计算（口径与 Sk() 一致）----
		techFee := decimal.NewFromFloat(float64(packet.TechnicalServiceFee) / 100)
		agentRatio := decimal.NewFromFloat(float64(agentSettlement.Ratio) / 100)
		systemAmount := techFee.Mul(totalAmount)
		agentAmount := agentRatio.Mul(totalAmount)
		// ★ 客户用【金额残差】而非"比例残差"：
		//   保证 system + agent + custom 恒等于 totalAmount，
		//   避免三方比例之和不为 100% 时出现分账缺口或溢出。
		customAmount := totalAmount.Sub(systemAmount).Sub(agentAmount)

		// 折算 USDT 系数（token.radio_usdt）
		// ★ 这里是【精确匹配】：故 eth 归一后必须仍是 eth，不得写成 "eth,bsc"（见 C-1）
		var token app.Token
		radio := decimal.NewFromFloat(100)
		if e = tx.Where("chain = ?", chain).Limit(1).Find(&token).Error; e == nil && token.RadioUsdt != 0 {
			radio = decimal.NewFromFloat(float64(token.RadioUsdt) / 100)
		}

		// BatchId 是 int64（bill.batch_id），由 gasleak 传入的 collectedAt 毫秒时间戳充当批次号；
		// 缺失时用当前毫秒。★ 不要塞时间字符串——类型不符。
		batchId := req.CollectedAt
		if batchId == 0 {
			batchId = time.Now().UnixMilli()
		}
		now := utils.GetGMTTimeLongFormat()

		// ---- ④-b ★ F1-C9：to_address 一致性校验 ----
		// 背景：req.ToAddress 在接口上声明为"实际落账地址"（model/common.go:145），
		//   但此前【服务层完全忽略它】（本文件 grep ToAddress 零命中）
		//   ⇒ gasleak 若把资金转到与账单不一致的地址，潜客侧仍按 settlement 正常记账，
		//     且 code=0 完全静默（"钱去了 A，账记在 B"）。
		//
		// 判定规则（依据 scan.go 实读）：
		//   · 私域（Region==2）: 记账只涉及 privateSettlement（user_id=-1），1 笔转账；
		//   · 公域（Region!=2）: 记账涉及平台/客户/代理三方 settlement，链上分三笔转账；
		//   · to_address 为空 ⇒ 不校验（向后兼容：gasleak 可能未传该字段）；
		//   · to_address 非空且不在本次涉及的地址集合内 ⇒ 显式拒绝。
		reqToAddr := strings.TrimSpace(req.ToAddress)
		checkToAddress := func(scope string, addrs ...string) error {
			if reqToAddr == "" {
				return nil
			}
			expect := make([]string, 0, len(addrs))
			for _, a := range addrs {
				a = strings.TrimSpace(a)
				if a == "" {
					continue
				}
				expect = append(expect, a)
				if a == reqToAddr {
					return nil
				}
			}
			return fmt.Errorf(
				"to_address %q does not match any %s settlement address; expected one of %v",
				reqToAddr, scope, expect)
		}

		// ---- ⑤ 落 bill ----
		//   ★ 数量列用 total_num / num / usdt_num —— bill【无 amount 列】
		mkBill := func(role int, settlementId int, num decimal.Decimal) *app.Bill {
			if settlementId <= 0 || num.IsZero() {
				return nil
			}
			return &app.Bill{
				WalletId:     walletId,
				TokenId:      int(token.ID),
				Role:         role,
				BatchId:      batchId,
				TotalNum:     totalAmount.String(),
				Num:          num.String(),
				UsdtNum:      num.Mul(radio).String(),
				SettlementId: settlementId,
				OrderId:      uuid.New().String(),
				TransferHash: req.TxHash, // ★ 幂等键落库
				CreateTime:   now,
				Status:       1, // 1 = 已确认（gasleak 已完成链上确认才回传）
			}
		}

		// ---- ⑤-a ★ F1-C2：私域钱包（Region == 2）单独一套口径 ----
		// 口径基准 = 潜客 Sk() 的 else 分支（01-backend-go/blockchain/scan.go:211-235），逐条抄录：
		//   · settlement 定位：user_id = **-1**
		//   · bill 笔数：**1 笔**（公域是 3 笔）
		//   · Role = **4**
		//   · 金额：**全额 totalAmount**（不扣平台技术服务费、不扣代理佣金）
		//   · UsdtNum 同样按 token.radio_usdt 折算
		// ★ 必须在公域三笔【之前】并 return，否则私域会同时落公域三笔（口径双写）。
		// ★ 本卡只做口径对齐，不抽公共函数（一期铁律「只整合、不新造」）。
		if wallet.Region == 2 {
			var privateSettlement app.Settlement
			_ = tx.Select("settlement.*").
				Where("settlement.user_id = -1 AND settlement.chain LIKE ?", "%"+chain+"%").
				Find(&privateSettlement).Error

			// ★ F1-C9：私域只涉及 privateSettlement 一个收款方 ⇒ 校验单一地址。
			//   必须在【落任何 bill 之前】，确保拒绝时一笔都不落。
			if e = checkToAddress("private", privateSettlement.Address); e != nil {
				return e
			}

			// 私域为【单笔全额】：settlementId 取自 user_id=-1，金额即 totalAmount。
			if b := mkBill(4, int(privateSettlement.ID), totalAmount); b != nil {
				if e = tx.Create(b).Error; e != nil {
					return e
				}
				out.BillId = int(b.ID)
			}

			// 私域不写 role 1/2/3 —— 直接释放占位并返回。
			if e = ReleaseCollectLock(tx, walletId); e != nil {
				return e
			}
			out.Duplicated = false
			return nil
		}

		// ---- ⑤-b 公域 / 临时域（Region != 2）：平台 + 客户 + 代理 三笔 ----
		// ★ F1-C9：公域链上分三笔转账（scan.go:149-179 实读），
		//   故 to_address 应为平台/客户/代理三方 settlement 地址之一。
		//   必须在【落任何 bill 之前】校验，确保拒绝时一笔都不落。
		if e = checkToAddress("public",
			systemSettlement.Address,
			agentSettlement.Address,
			customSettlementAddr(tx, chain, walletId),
		); e != nil {
			return e
		}

		// role=1 平台（本函数返回其 ID 作为主 bill）
		if b := mkBill(1, int(systemSettlement.ID), systemAmount); b != nil {
			if e = tx.Create(b).Error; e != nil {
				return e
			}
			out.BillId = int(b.ID)
		}
		// role=2 客户（★ 卡A：按域解客户；未绑定 ⇒ settlementId=0 ⇒ mkBill 返回 nil ⇒ 不落该笔）
		if b := mkBill(2, customSettlementId(tx, chain, walletId), customAmount); b != nil {
			if e = tx.Create(b).Error; e != nil {
				return e
			}
			// ★ 卡A 裁定②条件①：累加写在**创建同一事务内**（⛔ 不许事后再扫一遍 —— 那会重现 A 路的窗口问题）
			if e = blockchain.AccumulateUsdtNum(tx, int(b.ID), 2, customUserIdForWallet(tx, walletId), b.UsdtNum); e != nil {
				return e
			}
			if out.BillId == 0 {
				out.BillId = int(b.ID)
			}
		}
		// role=3 代理
		if b := mkBill(3, agentSettlement.ID, agentAmount); b != nil {
			if e = tx.Create(b).Error; e != nil {
				return e
			}
			// ★ 卡A 裁定②条件①（同 role=2）：创建事务内累加
			if e = blockchain.AccumulateUsdtNum(tx, int(b.ID), 3, agentSettlement.UserId, b.UsdtNum); e != nil {
				return e
			}
			if out.BillId == 0 {
				out.BillId = int(b.ID)
			}
		}

		// ---- ⑥ 释放占位（progress → 0）----
		// 必须与 collect-lock 成对：只占不放会把钱包永久锁死，
		// 使 gasleak 与潜客 Sk() 都无法再归集该钱包。
		if e = ReleaseCollectLock(tx, walletId); e != nil {
			return e
		}

		out.Duplicated = false
		return nil
	})

	// ★★ T31（契约 C-6）：**并发落败方收敛为幂等** ——
	//   两条并发 POST 双双越过上面的"先查后插"预检时，只有一条能把 `(transfer_hash, role)` 插进去，
	//   另一条被复合唯一键 `uk_txhash_role` 拒绝（MySQL **1062**）⇒ 事务回滚 ⇒ 错误冒到此处。
	//   原实现**直接把该错误抛给调用方** ⇒ 落败方拿 `code=7`，与**串行**路径（`code=0` ＋ `duplicated=true`）**不一致**。
	//   ⇒ 此处捕获 1062，**重读「首次那笔」并以幂等响应返回**，使串行/并发语义一致（C-6）。
	//   ★ 冲突**必然发生在第一次 INSERT**（public 是 role=1、private 是 role=4）⇒ 落败方在
	//     `ReleaseCollectLock` **之前**即已返回 ⇒ **其事务回滚不会把占位重新锁上**（占位由赢家那笔释放）。
	//   ★ 重读**仍拿不到**（异常路径）⇒ **保持原错误**，⛔ **不静默吞**。
	if err != nil && isDuplicateKey(err) {
		var exist app.Bill
		if e2 := global.GVA_DB.Where("transfer_hash = ?", req.TxHash).
			Order("id ASC").Limit(1).Find(&exist).Error; e2 == nil && exist.ID > 0 {
			out.BillId = int(exist.ID)
			out.Duplicated = true
			return out, nil
		}
	}

	return out, err
}

// isDuplicateKey ★ T31：判定 err 是否为「唯一键冲突（MySQL 1062）」。
//
//	★ 本仓 gorm 为 **v1.22.5** ⇒ **`gorm.ErrDuplicatedKey` 不可用**（该符号 v1.25+ 才有）
//	  ⇒ 必须 `errors.As` 到 `*mysql.MySQLError` 判 `Number == 1062`。
//	★ 它**只是信号**：命中后**重读「首次那笔」**并以幂等响应返回（见契约 C-6），⛔ **不是"把错误吞掉"**。
func isDuplicateKey(err error) bool {
	var me *mysql.MySQLError
	if errors.As(err, &me) {
		return me.Number == 1062
	}
	return false
}

// normalizeChain 把 gasleak 的入参 chain 词表归一为潜客内部 chain 词表。
//
// 契约（09-docs/spec/contracts.md C-1）：
//   - gasleak → 潜客（入参）: {eth, tron, btc}  ← 不变，是 gasleak 自己的 model 枚举
//   - 潜客内部 settlement   : {eth,bsc, trx}    ← 不变，是后台既有生产数据
//   - tron → trx
//   - eth  → eth（★ 不得写成 "eth,bsc"：token 查询是精确匹配，生产 token.chain 实测为 eth）
//   - btc  → 显式失败（潜客后台无法登记 BTC 收款地址、生产 settlement 表亦无 btc 行；
//     静默丢账比报错更坏）
//   - 词表外的值 → 同样显式失败，不得回落默认值
//
// 大小写/空白处理与 wallet_resolver.go 的既有做法一致（ToLower + TrimSpace）。
func normalizeChain(chain string) (string, error) {
	switch strings.ToLower(strings.TrimSpace(chain)) {
	case "eth":
		return "eth", nil
	case "tron":
		return "trx", nil
	case "btc":
		return "", errors.New("不支持的 chain: btc（潜客侧无 BTC 收款地址登记，拒绝静默丢账）")
	default:
		return "", fmt.Errorf("不支持的 chain: %q（gasleak 词表为 eth/tron/btc）", chain)
	}
}

// customUserIdForWallet ★ 卡A 新增：按**域**解出"这笔钱属于哪个客户"——
//
//	packet.custom_user_id ← agent.packet_id ← machine.agent_id ← wallet.machine_id ← wallet.id
//	依据：裁定⑤（`wallet_id` 链为**唯一事实源**；`settlement` 链降为交叉校验）。
//	★ 未绑定（custom_user_id = 0）或链上解不出 ⇒ 返回 0（**不得**回落成"表里第一行客户"）。
func customUserIdForWallet(tx *gorm.DB, walletId int) int {
	var row struct {
		CustomUserId int
	}
	_ = tx.Table("packet").
		Select("packet.custom_user_id").
		Joins("join agent on agent.packet_id = packet.id").
		Joins("join machine on machine.agent_id = agent.id").
		Joins("join wallet on wallet.machine_id = machine.id").
		Where("wallet.id = ? AND packet.custom_user_id <> 0", walletId).
		Limit(1).
		Find(&row).Error
	return row.CustomUserId
}

// customSettlementId 取客户侧收款地址 ID。
// ★ 卡A 改造：**按域解客户**（旧实现 `Model(app.Custom{})` 后**无客户谓词 + Limit(1)**
//
//	⇒ 恒取表里第一行客户，是单租户铁证，见 WBE01-A 设计件 §1.2）。
//	未绑定 ⇒ 返回 0 ⇒ 上层 `mkBill` 因 `settlementId <= 0` **不落该笔**（客户侧无从归属）。
func customSettlementId(tx *gorm.DB, chain string, walletId int) int {
	uid := customUserIdForWallet(tx, walletId)
	if uid == 0 {
		return 0
	}
	var row struct {
		ID int
	}
	_ = tx.Model(app.Settlement{}).
		Where("settlement.user_id = ? AND settlement.chain LIKE ?", uid, "%"+chain+"%").
		Select("settlement.id").
		Limit(1).
		Find(&row).Error
	return row.ID
}

// customSettlementAddr 取客户侧收款地址（★ F1-C9：to_address 校验用）。
// 查询与 customSettlementId 完全同源，只是取 address 而非 id —— 保证二者指向同一行。
// ★ 卡A：同 customSettlementId，**按域解客户**；未绑定 ⇒ 返回 ""（不出现在可接受地址集合里）。
func customSettlementAddr(tx *gorm.DB, chain string, walletId int) string {
	uid := customUserIdForWallet(tx, walletId)
	if uid == 0 {
		return ""
	}
	var row struct {
		Address string
	}
	_ = tx.Model(app.Settlement{}).
		Where("settlement.user_id = ? AND settlement.chain LIKE ?", uid, "%"+chain+"%").
		Select("settlement.address").
		Limit(1).
		Find(&row).Error
	return row.Address
}
