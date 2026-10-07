package app

type Custom struct {
	ID      uint   `gorm:"primarykey"`
	UserId  int    `json:"userId" gorm:"column:user_id;comment:用户id;"`
	UsdtNum string `json:"usdtNum" gorm:"column:usdt_num;comment:总利润(折算成usdt的数量);"`
}

func (Custom) TableName() string {
	return "custom"
}
