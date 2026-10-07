package app

type Bill struct {
	ID           uint   `gorm:"primarykey"`
	BatchId      int64  `json:"batchId" gorm:"column:batch_id;comment:批次号;"`
	OrderId      string `json:"orderId" gorm:"column:order_id;comment:定单号;"`
	WalletId     int    `json:"walletId" gorm:"column:wallet_id;comment:钱包id;"`
	TokenId      int    `json:"tokenId" gorm:"column:token_id;comment:代币id;"`
	SettlementId int    `json:"settlementId" gorm:"column:settlement_id;comment:收款id;"`
	TotalNum     string `json:"totalNum" gorm:"column:total_num;comment:总数量;"`
	Num          string `json:"num" gorm:"column:num;comment:收款数量;"`
	UsdtNum      string `json:"usdtNum" gorm:"column:usdt_num;comment:折算成usdt的数量;"`
	TransferHash string `json:"transferHash" gorm:"column:transfer_hash;comment:交易hash;"`
	Status       int    `json:"status" gorm:"column:status;comment:成功状态;"`
	Role         int    `json:"role" gorm:"column:role;comment:角色 1平台， 2客户， 3代理, 4私域;"`
	CreateTime   string `json:"createTime" gorm:"column:create_time;comment:创建时间;"`
}

func (Bill) TableName() string {
	return "bill"
}
