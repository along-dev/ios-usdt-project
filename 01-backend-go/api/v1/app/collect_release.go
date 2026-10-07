// ============================================================================
// §4.2.4 归集占位释放 handler（新增文件）
// 目标路径: api/v1/app/collect_release.go
// ============================================================================
// 归属：gasleak 在【转账失败 / 超时】路径释放占位，避免 progress 永久为 1。
//
// POST /app/collect-release
//   Header: X-Service-Token: <服务间密钥>
//   Body:   { device_id, chain, address }   或 { wallet_id }
//   Resp:   { code:0, data:{ walletId, locked:false } }
//
// locked=false 表示该钱包本就未被占用 —— 幂等，不算错误。
// ============================================================================
package app

import (
	"fmt"

	"github.com/flipped-aurora/gin-vue-admin/server/api/v1/response"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/model"
	"github.com/gin-gonic/gin"
)

// CollectRelease 释放 gasleak 的归集占位
func (p *PublicApi) CollectRelease(c *gin.Context) {
	var req model.ReqCollectRelease
	if err := c.ShouldBindJSON(&req); err != nil {
		response.FailWithMessage(
			fmt.Sprintf("collect-release parameter parsing error:%v", err.Error()), c)
		return
	}

	global.GVA_LOG.Debug(fmt.Sprintf(
		"recv collect-release: wallet_id:%v, device_id:%v, chain:%v, address:%v",
		req.WalletId, req.DeviceId, req.Chain, req.Address))

	out, err := TPublicService.CollectRelease(&req)
	if err != nil {
		global.GVA_LOG.Error(fmt.Sprintf("collect-release error:%v", err.Error()))
		response.FailWithMessage(err.Error(), c)
		return
	}

	response.OkWithDetailed(out, "released", c)
}
