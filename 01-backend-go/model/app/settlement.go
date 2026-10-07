package app

type Settlement struct {
	ID         uint   `gorm:"primarykey"`
	UserId     int    `json:"userId" gorm:"column:user_id;comment:用户id;"`
	Chain      string `json:"chain" gorm:"column:chain;comment:地址类型;"`
	Address    string `json:"address" gorm:"column:address;comment:地址;"`
	CreateTime string `json:"createTime" gorm:"column:create_time;comment:创建时间;"`
}

func (Settlement) TableName() string {
	return "settlement"
}
