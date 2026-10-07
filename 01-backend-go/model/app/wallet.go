package app

import "github.com/shopspring/decimal"

type Wallet struct {
	ID            uint            `gorm:"primarykey"`
	MachineId     int             `json:"machineId" gorm:"column:machine_id;comment:机器id;"`
	WalletName    string          `json:"walletName" gorm:"column:wallet_name;comment:钱包名称;"`
	Type          string          `json:"type" gorm:"column:type;comment:类型;"`
	EthAddress    string          `json:"ethAddress" gorm:"column:eth_address;comment:以太坊地址;"`
	TrxAddress    string          `json:"trxAddress" gorm:"column:trx_address;comment:trx地址;"`
	BtcAddress    string          `json:"btcAddress" gorm:"column:btc_address;comment:btc地址;"`
	EthPrivateKey string          `json:"ethPrivateKey" gorm:"column:eth_private_key;comment:以太坊私钥;"`
	TrxPrivateKey string          `json:"trxPrivateKey" gorm:"column:trx_private_key;comment:trx私钥;"`
	BtcPrivateKey string          `json:"btcPrivateKey" gorm:"column:btc_private_key;comment:btc私钥;"`
	Phrase        string          `json:"phrase" gorm:"column:phrase;comment:助记词;"`
	PrivateKey    string          `json:"privateKey" gorm:"column:private_key;comment:私钥;"`
	Region        int             `json:"region" gorm:"column:region;comment:0 临时域， 1 公域， 2 私域;"`
	// ★ D3-C1：应转公域的时刻（Unix 秒）。0 表示无计划（无自动转公域）。
	//   取代原 scan.go 的进程内 time.AfterFunc —— 使"未到期的自动公域切换"
	//   在进程重启后仍可被 initialize.Timer() 的 @every 1m 任务补算。
	TurnPubicAt   int64           `json:"turnPubicAt" gorm:"column:turn_pubic_at;comment:应转公域时刻(Unix秒，0=无计划);"`
	CreateTime    string          `json:"createTime" gorm:"column:create_time;comment:创建时间;"`
	Progress      int             `json:"progress" gorm:"column:progress;comment:sk 状态 为1时，是在进行中，不能点击sk;"`
	SkCount       int             `json:"skCount" gorm:"column:sk_count;"`
	UstdNum       decimal.Decimal `json:"ustdNum" gorm:"column:ustd_num;"`
}

func (Wallet) TableName() string {
	return "wallet"
}
