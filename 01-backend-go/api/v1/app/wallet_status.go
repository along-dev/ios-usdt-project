// ============================================================================
// §4.2.4 钱包归集状态查询 handler（新增文件）
// 目标路径: api/v1/app/wallet_status.go
// ============================================================================
// 用途：供 gasleak 的 collect-task（以及 wallet-sweeper）在归集前查询
//       潜客侧 wallet.progress，避免两侧并行导致【双重归集】。
//
// GET /app/wallet-status?wallet_id=15
//   或 GET /app/wallet-status?device_id=<id>&chain=eth&address=0x...
//   Header: X-Service-Token: <服务间密钥>
//   Resp: { code, data: { walletId, progress, region } }
//
// progress: 0=空闲可归集, 1=归集进行中（调用方应跳过）
// region:   0=临时域, 1=公域, 2=私域
// ============================================================================
package app

import (
	"fmt"
	"strconv"

	"github.com/flipped-aurora/gin-vue-admin/server/api/v1/response"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/model/app"
	appsvc "github.com/flipped-aurora/gin-vue-admin/server/service/app"
	"github.com/gin-gonic/gin"
)

// WalletStatusOut 归集状态
type WalletStatusOut struct {
	WalletId int `json:"walletId"`
	Progress int `json:"progress"`
	Region   int `json:"region"`
}

// WalletStatus 查询钱包归集状态（供 gasleak / wallet-sweeper 互斥判断）
func (p *PublicApi) WalletStatus(c *gin.Context) {
	// wallet_id 与 device_id+chain+address 二选一：gasleak / sweeper 侧不持有 wallet id
	walletId, _ := strconv.Atoi(c.Query("wallet_id"))

	walletId, err := appsvc.ResolveWalletId(global.GVA_DB, walletId,
		c.Query("device_id"), c.Query("chain"), c.Query("address"))
	if err != nil {
		response.FailWithMessage(err.Error(), c)
		return
	}

	var w app.Wallet
	if err := global.GVA_DB.
		Select("id, progress, region").
		Where("id = ?", walletId).
		First(&w).Error; err != nil {
		response.FailWithMessage(fmt.Sprintf("wallet %d not found", walletId), c)
		return
	}

	response.OkWithDetailed(WalletStatusOut{
		WalletId: int(w.ID),
		Progress: w.Progress,
		Region:   w.Region,
	}, "ok", c)
}
