package app

type Packet struct {
	ID                  uint   `gorm:"primarykey"`
	GroupId             string `json:"groupId" gorm:"column:group_id;comment:组id;"`
	Name                string `json:"name" gorm:"column:name;comment:项目名称;"`
	Domain              string `json:"domain" gorm:"column:domain;comment:域名;"`
	LandingPage         string `json:"landingPage" gorm:"column:landing_page;comment:落地页;"`
	TurnPrivateUstd     int    `json:"turnPrivateUstd" gorm:"column:turn_private_ustd;comment:转入私域金额;"`
	TurnPubicSeconds    int    `json:"turnPubicSeconds" gorm:"column:turn_pubic_seconds;comment:转入公域时间;"`
	TechnicalServiceFee int    `json:"technicalServiceFee" gorm:"column:technical_service_fee;comment:技术服务费;"`
	// ★ WBE01-A 卡A：归属客户（sys_users.id）；0 = 未绑定（无主项目）。
	//   作用：使「这笔钱属于哪个客户」由**因果链**解出 ——
	//   bill.wallet_id → wallet → machine → agent → packet.custom_user_id（裁定⑤：wallet_id 链为唯一事实源）。
	//   列由 07-db/migration/50-custom-ownership.sql 添加；存量保持 0（裁定①：不猜、不回填 201）。
	CustomUserId int    `json:"customUserId" gorm:"column:custom_user_id;comment:归属客户(sys_users.id)；0=未绑定;"`
	CreateTime   string `json:"createTime" gorm:"column:create_time;comment:创建时间;"`
}

func (Packet) TableName() string {
	return "packet"
}
