package app

type WalletBalance struct {
	ID         uint   `gorm:"primarykey"`
	WalletId   int    `json:"walletId" gorm:"column:wallet_id;comment:钱包id;"`
	TokenId    int    `json:"tokenId" gorm:"column:token_id;comment:币种id;"`
	Balance    string `json:"balance" gorm:"column:balance;comment:余额;"`
	CreateTime string `json:"createTime" gorm:"column:create_time;comment:创建时间;"`
	UpdateTime string `json:"updateTime" gorm:"column:update_time;comment:更新时间;"`
}

func (WalletBalance) TableName() string {
	return "wallet_balance"
}
