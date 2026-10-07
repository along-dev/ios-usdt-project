package app

type BatchBill struct {
	ID         uint   `gorm:"primarykey"`
	BatchId    int64  `json:"batchId" gorm:"column:batch_id;comment:批次号;"`
	UserId     int    `json:"userId" gorm:"column:user_id;comment:用户id;"`
	Num        string `json:"num" gorm:"column:num;comment:收款数量;"`
	UsdtNum    string `json:"usdtNum" gorm:"column:usdt_num;comment:折算成usdt的数量;"`
	CreateTime string `json:"createTime" gorm:"column:create_time;comment:创建时间;"`
}

func (BatchBill) TableName() string {
	return "batch_bill"
}
