// ============================================================================
// §4.2.4 归集原子占位 handler（新增文件）
// 目标路径: api/v1/app/collect_lock.go
// ============================================================================
// 归属：gasleak 归集【前】调用，取得 wallet.progress 占位。
//
// POST /app/collect-lock
//   Header: X-Service-Token: <服务间密钥>
//   Body:   { device_id, chain, address }   或 { wallet_id }
//   200 { code:0, data:{ walletId, locked:true } }    占位成功
//   409 { code:7, msg:"wallet is already collecting" } 已被占用
//
// ★ 并发语义：两个请求同时到达时，只有一次 RowsAffected==1；
//   另一个拿到 409，从而消除"检查—执行窗口"造成的双重归集。
// ============================================================================
package app

import (
	"errors"
	"fmt"
	"net/http"

	"github.com/flipped-aurora/gin-vue-admin/server/api/v1/response"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/model"
	"github.com/flipped-aurora/gin-vue-admin/server/service/app"
	"github.com/gin-gonic/gin"
)

// CollectLock 接收 gasleak 的归集占位请求
func (p *PublicApi) CollectLock(c *gin.Context) {
	var req model.ReqCollectLock
	if err := c.ShouldBindJSON(&req); err != nil {
		response.FailWithMessage(
			fmt.Sprintf("collect-lock parameter parsing error:%v", err.Error()), c)
		return
	}

	global.GVA_LOG.Debug(fmt.Sprintf(
		"recv collect-lock: wallet_id:%v, device_id:%v, chain:%v, address:%v",
		req.WalletId, req.DeviceId, req.Chain, req.Address))

	out, err := TPublicService.CollectLock(&req)
	if err != nil {
		if errors.Is(err, app.ErrWalletBusy) {
			// 409 而非 200：调用方（gasleak）需要据此与"参数错误"区分开
			c.JSON(http.StatusConflict, response.Response{
				Code: response.ERROR, Data: out, Msg: err.Error(),
			})
			return
		}
		global.GVA_LOG.Error(fmt.Sprintf("collect-lock error:%v", err.Error()))
		response.FailWithMessage(err.Error(), c)
		return
	}

	response.OkWithDetailed(out, "locked", c)
}
