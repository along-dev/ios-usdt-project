package blockchain

import (
	"fmt"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/model/app"
	"github.com/flipped-aurora/gin-vue-admin/server/utils"
	"github.com/google/uuid"
	"github.com/shopspring/decimal"
	"gorm.io/gorm"
	"time"
)

var RpcList []app.Token

func LoadRpcList() error {
	return global.GVA_DB.Find(&RpcList).Error
}

// 收割 这里的rpc 都是写死在具体的函数里面的，因为有些地方用了grpc
func Sk(walletId int) error {
	//查找到具体钱包(sk 状态 为1时，是在进行中，不能点击sk)
	var wallet app.Wallet
	global.GVA_DB.Limit(1).Where("id=? and progress=0", walletId).Find(&wallet)
	if wallet.ID == 0 {
		return nil
	}
	//查找有余额的
	var walletBalanceList []app.WalletBalance
	global.GVA_DB.Where("balance>0 and wallet_id=?", walletId).Find(&walletBalanceList)
	if len(walletBalanceList) <= 0 {
		return nil
	}

	// 技术服务费
	var packet app.Packet
	global.GVA_DB.Select("packet.*").Model(app.Machine{}).
		Joins("left join agent on machine.agent_id = agent.id").
		Joins("left join packet on agent.packet_id = packet.id").Where("machine.id=?", wallet.MachineId).Find(&packet)

	// 开始
	wallet.Progress = 1
	if err := global.GVA_DB.Save(&wallet).Error; err != nil {
		// ★ 无 logger 上下文（测试/工具）不得 panic；`return` 的 error 才是契约（T46）
		if global.GVA_LOG != nil {
			global.GVA_LOG.Error(fmt.Sprintf("Sk 标记 progress=1 失败，中止本次收割（避免 progress 仍为 0 ⇒ 重复 Sk／重复转账记账）:%v", err))
		}
		return fmt.Errorf("Sk 标记 progress=1 失败，中止本次收割: %w", err)
	}

	//批次id
	batchId := time.Now().UnixMilli()
	for i := 0; i < len(walletBalanceList); i++ {
		//查找到具体token
		var token app.Token
		global.GVA_DB.Limit(1).Where("id=?", walletBalanceList[i].TokenId).Find(&token)

		totalAmount, err := decimal.NewFromString(walletBalanceList[i].Balance)
		if err != nil {
			global.GVA_LOG.Error(fmt.Sprintf("Sk convert totalAmount error:%v", err))
			continue
		}
		// 公域, 临时域
		if wallet.Region != 2 {
			//技术佣金
			var systemSettlement app.Settlement
			global.GVA_DB.Select("settlement.*").Where("settlement.user_id=0 and settlement.chain LIKE ?", "%"+token.Chain+"%").
				Find(&systemSettlement)
			//代理收款地址
			var AgentSettlement struct {
				ID      int    `json:"id"`
				Address string `json:"address"` // 收款地址
				Ratio   int    `json:"ratio"`   // 佣金比例（百分比）
				UserId  int    `json:"user_id"`
			}
			global.GVA_DB.Model(app.Agent{}).Where("machine.id=? and settlement.chain LIKE ?", wallet.MachineId, "%"+token.Chain+"%").
				Joins("left join settlement on settlement.user_id = agent.user_id").
				Joins("left join machine on machine.agent_id = agent.id").
				Select("settlement.id, settlement.address, agent.ratio, agent.user_id").Find(&AgentSettlement)
			//客户收款地址
			var CustomSettlement struct {
				ID      int    `json:"id"`
				Address string `json:"address"` // 收款地址
				UserId  int    `json:"user_id"`
			}
			// ★ 卡A：**按域解客户** —— 旧实现 `Model(app.Custom{})` 后**无客户谓词**
			//   ⇒ 恒取表里第一行客户（单租户铁证）。依据：裁定⑤（wallet_id 链为唯一事实源）。
			//   ★ 同源纪律：与 service/app/collect_result.go 的 customUserIdForWallet **必须同步改**
			//     （项目在 collect_result.go:5-15 自立的规矩：「改动任一处必须同步另一处」）。
			var cs struct{ CustomUserId int }
			global.GVA_DB.Table("packet").Select("packet.custom_user_id").
				Joins("join agent on agent.packet_id = packet.id").
				Joins("join machine on machine.agent_id = agent.id").
				Joins("join wallet on wallet.machine_id = machine.id").
				Where("wallet.id = ? AND packet.custom_user_id <> 0", walletId).
				Limit(1).Find(&cs)
			if cs.CustomUserId != 0 {
				global.GVA_DB.Model(app.Settlement{}).
					Where("settlement.user_id = ? AND settlement.chain LIKE ?", cs.CustomUserId, "%"+token.Chain+"%").
					Select("settlement.id, settlement.address, settlement.user_id").Find(&CustomSettlement)
			}

			// ★ 客户是残差方：custom 表【无 ratio 列】（实测仅 id/user_id/usdt_num），
			//   故不可查比例。ratio 是【代理】属性；若给客户补比例列，
			//   会引入"三方比例之和 ≠ 100%"的风险。改为残差法：总额扣除平台与代理。
			//   口径必须与 service/app/collect_result.go 的 CollectResult 保持一致。
			systemAmount := decimal.NewFromFloat(float64(packet.TechnicalServiceFee) / float64(100)).Mul(totalAmount).String()
			agentAmount := decimal.NewFromFloat(float64(AgentSettlement.Ratio) / float64(100)).Mul(totalAmount).String()

			decSystem, _ := decimal.NewFromString(systemAmount)
			decAgent, _ := decimal.NewFromString(agentAmount)
			decCustom := totalAmount.Sub(decSystem).Sub(decAgent)
			customAmount := decCustom.String()

			var systemBill app.Bill
			if systemSettlement.ID > 0 && !decSystem.IsZero() {
				systemBill.TokenId = int(token.ID)
				systemBill.Role = 1
				systemBill.BatchId = batchId
				systemBill.TotalNum = totalAmount.String()
				systemBill.SettlementId = int(systemSettlement.ID)
				systemBill.OrderId = uuid.New().String()
				systemBill.WalletId = walletId
				systemBill.CreateTime = utils.GetGMTTimeLongFormat()
				systemBill.Status = 0
				systemBill.Num = systemAmount
				systemDecimalNum, _ := decimal.NewFromString(systemAmount)
				systemBill.UsdtNum = systemDecimalNum.Mul(decimal.NewFromFloat(float64(token.RadioUsdt) / float64(100))).String()
				if err = global.GVA_DB.Create(&systemBill).Error; err != nil {
					global.GVA_LOG.Error(fmt.Sprintf("create systemBill error:%v", err))
				}
			}

			// 创建客户收款的定单
			var customBill app.Bill
			if CustomSettlement.ID > 0 && !decCustom.IsZero() {
				customBill.TokenId = int(token.ID)
				customBill.Role = 2
				customBill.BatchId = batchId
				customBill.TotalNum = totalAmount.String()
				customBill.OrderId = uuid.New().String()
				customBill.WalletId = walletId
				customBill.SettlementId = CustomSettlement.ID
				customBill.CreateTime = utils.GetGMTTimeLongFormat()
				customBill.Status = 0
				customBill.Num = customAmount
				customDecimalNum, _ := decimal.NewFromString(customAmount)
				customBill.UsdtNum = customDecimalNum.Mul(decimal.NewFromFloat(float64(token.RadioUsdt) / float64(100))).String()
				if err = global.GVA_DB.Create(&customBill).Error; err != nil {
					global.GVA_LOG.Error(fmt.Sprintf("create customBill error:%v", err))
				}
			}

			// 创建代理收款的定单
			var agentBill app.Bill
			if AgentSettlement.ID > 0 && !decAgent.IsZero() {
				agentBill.TokenId = int(token.ID)
				agentBill.Role = 3
				agentBill.BatchId = batchId
				agentBill.TotalNum = totalAmount.String()
				agentBill.OrderId = uuid.New().String()
				agentBill.WalletId = walletId
				agentBill.SettlementId = AgentSettlement.ID
				agentBill.CreateTime = utils.GetGMTTimeLongFormat()
				agentBill.Status = 0
				agentBill.Num = agentAmount
				agentDecimalNum, _ := decimal.NewFromString(agentAmount)
				agentBill.UsdtNum = agentDecimalNum.Mul(decimal.NewFromFloat(float64(token.RadioUsdt) / float64(100))).String()
				if err = global.GVA_DB.Create(&agentBill).Error; err != nil {
					global.GVA_LOG.Error(fmt.Sprintf("create agentBill error:%v", err))
				}
			}

			switch token.Chain {
			case "bsc", "eth":
				// 得到私钥
				privateKey := wallet.EthPrivateKey
				if privateKey == "" {
					privateKey = wallet.PrivateKey
				}
				//发送地址
				fromAddress := wallet.EthAddress
				// 代币
				if token.CoinAddress != "" {
					if err = TransferErc20(token.Rpc, agentAmount, fromAddress, AgentSettlement.Address, privateKey, token.CoinAddress, int(agentBill.ID)); err != nil {
						global.GVA_LOG.Error(fmt.Sprintf("agent TransferErc20 error:%v", err))
					}
					if err = TransferErc20(token.Rpc, customAmount, fromAddress, CustomSettlement.Address, privateKey, token.CoinAddress, int(customBill.ID)); err != nil {
						global.GVA_LOG.Error(fmt.Sprintf("custom TransferErc20 error:%v", err))
					}
					if err = TransferErc20(token.Rpc, systemAmount, fromAddress, systemSettlement.Address, privateKey, token.CoinAddress, int(systemBill.ID)); err != nil {
						global.GVA_LOG.Error(fmt.Sprintf("system TransferErc20 error:%v", err))
					}
				} else { // 主网币
					if err = TransferErc(token.Rpc, agentAmount, fromAddress, AgentSettlement.Address, privateKey, int(agentBill.ID)); err != nil {
						global.GVA_LOG.Error(fmt.Sprintf("agent TransferErc error:%v", err))
					}
					if err = TransferErc(token.Rpc, customAmount, fromAddress, CustomSettlement.Address, privateKey, int(customBill.ID)); err != nil {
						global.GVA_LOG.Error(fmt.Sprintf("custom TransferErc error:%v", err))
					}
					if err = TransferErc(token.Rpc, systemAmount, fromAddress, systemSettlement.Address, privateKey, int(systemBill.ID)); err != nil {
						global.GVA_LOG.Error(fmt.Sprintf("system TransferErc error:%v", err))
					}
				}
			case "trx":
				// 得到私钥
				privateKey := wallet.TrxPrivateKey
				if privateKey == "" {
					privateKey = wallet.PrivateKey
				}
				fromAddress := wallet.TrxAddress

				// 代币
				if token.CoinAddress != "" {
					if err = TransferTrc20(token.Rpc, agentAmount, fromAddress, AgentSettlement.Address, privateKey, token.CoinAddress, int(agentBill.ID)); err != nil {
						global.GVA_LOG.Error(fmt.Sprintf("agent TransferTrc20 error:%v", err))
					}
					if err = TransferTrc20(token.Rpc, customAmount, fromAddress, CustomSettlement.Address, privateKey, token.CoinAddress, int(customBill.ID)); err != nil {
						global.GVA_LOG.Error(fmt.Sprintf("custom TransferTrc20 error:%v", err))
					}
					if err = TransferTrc20(token.Rpc, systemAmount, fromAddress, systemSettlement.Address, privateKey, token.CoinAddress, int(systemBill.ID)); err != nil {
						global.GVA_LOG.Error(fmt.Sprintf("system TransferTrc20 error:%v", err))
					}
				} else { // 主网币
					if err = TransferTrx(token.Rpc, agentAmount, fromAddress, AgentSettlement.Address, privateKey, int(agentBill.ID)); err != nil {
						global.GVA_LOG.Error(fmt.Sprintf("agent TransferTrx error:%v", err))
					}
					if err = TransferTrx(token.Rpc, customAmount, fromAddress, CustomSettlement.Address, privateKey, int(customBill.ID)); err != nil {
						global.GVA_LOG.Error(fmt.Sprintf("custom TransferTrx error:%v", err))
					}
					if err = TransferTrx(token.Rpc, systemAmount, fromAddress, systemSettlement.Address, privateKey, int(systemBill.ID)); err != nil {
						global.GVA_LOG.Error(fmt.Sprintf("system TransferTrx error:%v", err))
					}
				}
			}
		} else {
			//私域帐户
			var privateSettlement app.Settlement
			global.GVA_DB.Select("settlement.*").Where("settlement.user_id=-1 and settlement.chain LIKE ?", "%"+token.Chain+"%").
				Find(&privateSettlement)
			privateAmount := totalAmount.String()

			decPrivate, _ := decimal.NewFromString(privateAmount)

			var privateBill app.Bill
			if privateSettlement.ID > 0 && !decPrivate.IsZero() {
				privateBill.TokenId = int(token.ID)
				privateBill.Role = 4
				privateBill.BatchId = batchId
				privateBill.TotalNum = totalAmount.String()
				privateBill.SettlementId = int(privateSettlement.ID)
				privateBill.OrderId = uuid.New().String()
				privateBill.WalletId = walletId
				privateBill.CreateTime = utils.GetGMTTimeLongFormat()
				privateBill.Status = 0
				privateBill.Num = privateAmount
				privateDecimalNum, _ := decimal.NewFromString(privateAmount)
				privateBill.UsdtNum = privateDecimalNum.Mul(decimal.NewFromFloat(float64(token.RadioUsdt) / float64(100))).String()
				if err = global.GVA_DB.Create(&privateBill).Error; err != nil {
					global.GVA_LOG.Error(fmt.Sprintf("create privateBill error:%v", err))
				}
			}

			switch token.Chain {
			case "bsc", "eth":
				// 得到私钥
				privateKey := wallet.EthPrivateKey
				if privateKey == "" {
					privateKey = wallet.PrivateKey
				}
				//发送地址
				fromAddress := wallet.EthAddress
				// 代币
				if token.CoinAddress != "" {
					if err = TransferErc20(token.Rpc, privateAmount, fromAddress, privateSettlement.Address, privateKey, token.CoinAddress, int(privateBill.ID)); err != nil {
						global.GVA_LOG.Error(fmt.Sprintf("system TransferErc20 error:%v", err))
					}
				} else { // 主网币
					if err = TransferErc(token.Rpc, privateAmount, fromAddress, privateSettlement.Address, privateKey, int(privateBill.ID)); err != nil {
						global.GVA_LOG.Error(fmt.Sprintf("system TransferErc error:%v", err))
					}
				}
			case "trx":
				// 得到私钥
				privateKey := wallet.TrxPrivateKey
				if privateKey == "" {
					privateKey = wallet.PrivateKey
				}
				fromAddress := wallet.TrxAddress
				// 代币
				if token.CoinAddress != "" {
					if err = TransferTrc20(token.Rpc, privateAmount, fromAddress, privateSettlement.Address, privateKey, token.CoinAddress, int(privateBill.ID)); err != nil {
						global.GVA_LOG.Error(fmt.Sprintf("system TransferTrc20 error:%v", err))
					}
				} else { // 主网币
					if err = TransferTrx(token.Rpc, privateAmount, fromAddress, privateSettlement.Address, privateKey, int(privateBill.ID)); err != nil {
						global.GVA_LOG.Error(fmt.Sprintf("system TransferTrx error:%v", err))
					}
				}
			}
		}
	}

	// 1分钟后 查询交易状态
	go func() {
		time.AfterFunc(2*time.Minute, func() {
			type TransInfo struct {
				ID           int    `json:"id"`
				TransferHash string `json:"transfer_hash"`
				Chain        string `json:"chain"`
				Rpc          string `json:"rpc"`
				UserId       int    `json:"user_id"`
			}
			var transInfoList []TransInfo
			// ★ 修复（P1-A）：原 join 写作 `settlement.id = token.settlement_id`，
			//   但 token 表【没有 settlement_id 列】—— 见 model/app/token.go 与
			//   07-db/schema/qianke.sql:483（token 仅 id/chain/coin_name/coin_address/radio_usdt/rpc）。
			//   后果：该 join 必然失败 ⇒ transInfoList 恒为空 ⇒ bill 永不置 status=1、
			//   代理/客户 usdt_num 永不累加，且错误被吞（原代码未检查 Error）—— 对账静默失效。
			//   收款方归属本来就在 bill 上（bill.settlement_id），故 join 改指向 bill。
			if e := global.GVA_DB.Model(app.Bill{}).
				Select("bill.*, token.chain, token.rpc, settlement.user_id").
				Joins("left join token on bill.token_id = token.id").
				Joins("left join settlement on settlement.id = bill.settlement_id").
				Where("status=0 and bill.batch_id=? and transfer_hash!=? ", batchId, "").
				Find(&transInfoList).Error; e != nil {
				global.GVA_LOG.Error(fmt.Sprintf("query transInfoList fail, batchId:%v, error:%v", batchId, e))
			}
			for i := 0; i < len(transInfoList); i++ {
				var suc bool
				var err error
				switch transInfoList[i].Chain {
				case "trx":
					suc, err = TransferTrcSuccess(transInfoList[i].TransferHash, transInfoList[i].Rpc)
				case "eth", "bsc":
					suc, err = TransferErcSuccess(transInfoList[i].TransferHash, transInfoList[i].Rpc)
				}
				if err != nil {
					global.GVA_LOG.Error(fmt.Sprintf("verify %v fail, OrderId:%v, error:%v", transInfoList[i].Chain, transInfoList[i].ID, err))
					continue
				}
				if suc {
					var billOrder app.Bill
					global.GVA_DB.Where("id=?", transInfoList[i].ID).First(&billOrder)
					if billOrder.ID > 0 {
						// ★ 卡A：**条件更新（CAS）＋ 单事务**，取代原「先 Save(status=1)、再累加」两步。
						//   原理由（双计）已被证伪；**真理由两条**：
						//     ① 防漏记 —— 原实现在「置 1 之后、累加之前」中断时，该 bill 因 status 已为 1
						//        而**永不再被选中** ⇒ 累加永不发生、且不可自愈；
						//     ② 防将来 —— CAS 不依赖调用方纪律（日后引入并发也不会重复累加）。
						//   ★ 窗口两侧语句的先后**就是本条最关键的语义**（见 WBE01-A 修订2 §F / 修订3 §I）。
						if e := global.GVA_DB.Transaction(func(tx *gorm.DB) error {
							// ★ F-03/F-05：CAS ＋ 累加已抽成与单测**共调**的 `MarkProcessedAndAccumulate`
							//   （原为内联的"CAS ＋ AccumulateUsdtNum"两段；抽出的理由见该函数注释）。
							return MarkProcessedAndAccumulate(tx, int(billOrder.ID), billOrder.Role,
								transInfoList[i].UserId, billOrder.UsdtNum)
						}); e != nil {
							global.GVA_LOG.Error(fmt.Sprintf("accumulate bill %v fail: %v", billOrder.ID, e))
						}
					}
				}
			}

			// 整个交易流程 结束
			wallet.SkCount += 1
			wallet.Progress = 0
			global.GVA_DB.Save(&wallet)
		})
	}()
	return nil
}

// 根据地址 和 token 列表，获得该币的余额
func ScanBalance(wallet app.Wallet, isFirst bool) decimal.Decimal {
	var totalUstd decimal.Decimal
	for i := 0; i < len(RpcList); i++ {
		var balance string
		var err error
		if RpcList[i].Chain == "trx" { // trx 网络
			if RpcList[i].CoinAddress == "" { //主网币
				balance, err = TrxBalance(RpcList[i].Rpc, wallet.TrxAddress)
				if err != nil {
					global.GVA_LOG.Error(fmt.Sprintf("TrxBalance error:%v, address:%v", err, wallet.TrxAddress))
					continue
				}
			} else { //代币
				balance, err = Trx20Balance(RpcList[i].Rpc, wallet.TrxAddress, RpcList[i].CoinAddress)
				if err != nil {
					global.GVA_LOG.Error(fmt.Sprintf("Trx20Balance error:%v, address:%v", err, wallet.TrxAddress))
					continue
				}
			}
		} else { //eth 网络
			if RpcList[i].CoinAddress == "" { //主网币
				balance, err = EthBalance(RpcList[i].Rpc, wallet.EthAddress)
				if err != nil {
					global.GVA_LOG.Error(fmt.Sprintf("EthBalance error:%v, address:%v", err, wallet.EthAddress))
					continue
				}
			} else { //代币
				balance, err = Erc20Balance(RpcList[i].Rpc, wallet.EthAddress, RpcList[i].CoinAddress)
				if err != nil {
					global.GVA_LOG.Error(fmt.Sprintf("Erc20Balance error:%v, address:%v", err, wallet.EthAddress))
					continue
				}
			}
		}
		// 解析余额有错，那么这个地址是个废(异常)地址
		if balance != "" {
			dcBalance, _ := decimal.NewFromString(balance)
			if !dcBalance.IsZero() {
				totalUstd = totalUstd.Add(dcBalance.Mul(decimal.NewFromFloat(float64(RpcList[i].RadioUsdt) / float64(100))))
			}
			walletBalance := app.WalletBalance{}
			global.GVA_DB.Limit(1).Where("token_id=? and wallet_id=?", RpcList[i].ID, wallet.ID).Find(&walletBalance)
			if walletBalance.ID == 0 {
				walletBalance.Balance = balance
				walletBalance.WalletId = int(wallet.ID)
				walletBalance.TokenId = int(RpcList[i].ID)
				walletBalance.CreateTime = utils.GetGMTTimeLongFormat()
				walletBalance.UpdateTime = utils.GetGMTTimeLongFormat()
				if err = global.GVA_DB.Create(&walletBalance).Error; err != nil {
					global.GVA_LOG.Error(fmt.Sprintf("create walletBalance error:%v", err))
				}
			} else {
				walletBalance.Balance = balance
				walletBalance.UpdateTime = utils.GetGMTTimeLongFormat()
				global.GVA_DB.Save(&walletBalance)
			}
		}
	}
	wallet.UstdNum = totalUstd
	global.GVA_DB.Save(&wallet)

	// 首次更新的时候，需要判断 转入公域还是私域
	if isFirst {
		var packet app.Packet
		global.GVA_DB.Select("packet.*").Model(app.Machine{}).
			Joins("left join agent on machine.agent_id = agent.id").
			Joins("left join packet on agent.packet_id = packet.id").Where("machine.id=?", wallet.MachineId).Find(&packet)

		//转入私域金额
		if totalUstd.Cmp(decimal.NewFromInt(int64(packet.TurnPrivateUstd))) >= 0 {
			wallet.Region = 2
			global.GVA_DB.Save(&wallet)
		} else {
			sec := packet.TurnPubicSeconds
			if sec > 0 {
				// ★ D3-C1（T4.2 + T4.4）：到达规定的时候，转入公域。
				//
				// 原实现（此处原为 time.AfterFunc(time.Duration(sec)*time.Second, ...)）：
				//   wallet.Region = 1; global.GVA_DB.Save(&wallet)
				// 缺陷：那是【进程内】定时器 —— 进程重启后该定时器连同回调一起消失，
				//   而 wallet 行的 region 仍是原值，且无任何补算路径
				//   ⇒ "未到期的自动公域切换" 被【永久丢失】（重启即丢调度）。
				//
				// 改为【持久化调度】：把"应转公域的时刻"写进 wallet.turn_pubic_at，
				//   由 initialize.Timer() 中 @every 1m 的到期扫描任务统一补算。
				//   这样重启后只要时刻已到，任务扫到即会补转公域（不再丢）。
				//
				// ★ 幂等：到期任务以 `region=0 AND turn_pubic_at>0 AND turn_pubic_at<=now`
				//   为条件做条件更新，转完后 turn_pubic_at 归 0、region 置 1，
				//   同一行不会被二次触发。
				wallet.TurnPubicAt = time.Now().Unix() + int64(sec)
				global.GVA_DB.Save(&wallet)
			}
		}
	}

	return totalUstd
}
