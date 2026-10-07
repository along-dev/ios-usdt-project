package app

type Agent struct {
	ID         uint   `gorm:"primarykey"`
	UserId     int    `json:"userId" gorm:"column:user_id;comment:用户id;"`
	Country    string `json:"country" gorm:"column:country;comment:国家;"`
	PacketId   int    `json:"packetId" gorm:"column:packet_id;comment:项目id;"`
	Ratio      int    `json:"ratio" gorm:"column:ratio;comment:佣金比例（百分比）;"`
	UsdtNum    string `json:"usdtNum" gorm:"column:usdt_num;comment:总利润(折算成usdt的数量);"`
	CreateTime string `json:"createTime" gorm:"column:create_time;comment:创建时间;"`
}

func (Agent) TableName() string {
	return "agent"
}
