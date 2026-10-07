package app

type Token struct {
	ID          uint   `gorm:"primarykey"`
	Chain       string `json:"chain" gorm:"column:chain;comment:主链;"`
	CoinName    string `json:"coinName" gorm:"column:coin_name;comment:币种;"`
	CoinAddress string `json:"coinAddress" gorm:"column:coin_address;comment:币的地址;"`
	RadioUsdt   int    `json:"radioUsdt" gorm:"column:radio_usdt;comment:折算成usdt的比例;"`
	Rpc         string `json:"rpc" gorm:"column:rpc;comment:rpc地址;"`
}

func (Token) TableName() string {
	return "token"
}
