package app

import (
	"github.com/flipped-aurora/gin-vue-admin/server/api/v1/app"
	"github.com/gin-gonic/gin"
)

type PublicRouter struct {
}

// InitPublicRouter 裸奔端点：gasleak → 潜客 的【既有】写入通道。
// ★ 不加鉴权：/app/device 与 /app/wallet 是现网在用的链路，加鉴权须先解决
//   设备侧 token 分发，否则会打断写入。
func (p *PublicRouter) InitPublicRouter(Router *gin.RouterGroup) {
	publicRouter := Router.Group("app")
	var publicApi = app.PublicApi{}
	{
		publicRouter.POST("device", publicApi.Device) //添加 device
		publicRouter.POST("wallet", publicApi.Wallet) //添加 wallet
	}
}

// InitAuthRouter 需服务间鉴权的端点（gasleak 归集回传桥，§4.2.3 / §4.2.4）。
// 单独成组的理由：这些端点由 gasleak 服务端主动调用，属【新增】端点，
// 且是唯一能污染分账数据（bill）的写入口，故必须鉴权；
// 而 device/wallet 是既有通道，加鉴权需先解决设备 token 分发，风险不对称。
func (p *PublicRouter) InitAuthRouter(Router *gin.RouterGroup) {
	publicRouter := Router.Group("app")
	var publicApi = app.PublicApi{}
	{
		publicRouter.GET("wallet-status", publicApi.WalletStatus)      // §4.2.4 归集互斥查询
		publicRouter.GET("bill-list", publicApi.BillList)              // T22 潜客侧 bill 只读查询（供看板跨库合并）
		publicRouter.POST("collect-lock", publicApi.CollectLock)       // §4.2.4 原子占位
		publicRouter.POST("collect-release", publicApi.CollectRelease) // §4.2.4 失败路径释放
		publicRouter.POST("collect-result", publicApi.CollectResult)   // §4.2.3 归集回传
	}
}
