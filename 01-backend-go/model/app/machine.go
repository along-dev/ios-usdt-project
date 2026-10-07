package app

type Machine struct {
	ID             uint   `gorm:"primarykey"`
	DeviceId       string `json:"deviceId" gorm:"column:device_id;comment:机器id;"`
	AgentId        int    `json:"agentId" gorm:"column:agent_id;comment:代理id;"`
	Ip             string `json:"ip" gorm:"column:ip;comment:ip地址;"`
	Country        string `json:"country" gorm:"column:country;comment:国家;"`
	Brand          string `json:"brand" gorm:"column:brand;comment:品牌;"`
	Model          string `json:"model" gorm:"column:model;comment:型号;"`
	Platform       string `json:"platform" gorm:"column:platform;comment:平台 ios/android;"`
	AndroidVersion string `json:"androidVersion" gorm:"column:android_version;comment:型号;"`
	IosVersion     string `json:"iosVersion" gorm:"column:ios_version;comment:iOS 版本;"`
	Status         int    `json:"status" gorm:"column:status;comment:0 授权 1 成功;"`
	AppPackageName string `json:"appPackageName" gorm:"column:app_package_name;comment:包名;"`
	CreateTime     string `json:"createTime" gorm:"column:create_time;comment:创建时间;"`
}

func (Machine) TableName() string {
	return "machine"
}
