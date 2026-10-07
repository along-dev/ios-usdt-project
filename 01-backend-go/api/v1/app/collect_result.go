// ============================================================================
// §4.2.3 归集结果接收 handler（新增文件）
// 目标路径: api/v1/app/collect_result.go
// ============================================================================
// 归属：gasleak 执行链上归集 → POST /app/collect-result → 潜客【仅记账】
//
// ⚠ 本 handler 【不执行任何链上转账】——转账由 gasleak 负责。
//   潜客侧只复用 Sk() 的分账口径（技术服务费/代理佣金/客户分成）落 bill。
//
// 幂等：以 tx_hash 为唯一键，先查后插 + DB 唯一索引兜底（uk_transfer_hash）。
// ============================================================================
package app

import (
	"fmt"

	"github.com/flipped-aurora/gin-vue-admin/server/api/v1/response"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/model"
	"github.com/gin-gonic/gin"
)

// CollectResult 接收 gasleak 归集结果
// POST /app/collect-result
//   Header: X-Service-Token: <服务间密钥>（见 middleware/service_token.go）
//   Body:   { wallet_id | device_id+chain+address, chain, tx_hash, amount, to_address, collected_at }
//   Resp:   { code, data: { billId, duplicated } }
// 副作用：成功后释放 collect-lock 占位（wallet.progress → 0）。
func (p *PublicApi) CollectResult(c *gin.Context) {
	var req model.ReqCollectResult
	if err := c.ShouldBindJSON(&req); err != nil {
		response.FailWithMessage(
			fmt.Sprintf("collect-result parameter parsing error:%v", err.Error()), c)
		return
	}

	global.GVA_LOG.Debug(fmt.Sprintf(
		"recv collect-result: wallet_id:%v, chain:%v, tx_hash:%v, amount:%v, to:%v",
		req.WalletId, req.Chain, req.TxHash, req.Amount, req.ToAddress))

	out, err := TPublicService.CollectResult(&req)
	if err != nil {
		global.GVA_LOG.Error(fmt.Sprintf("collect-result error:%v", err.Error()))
		response.FailWithMessage(err.Error(), c)
		return
	}

	response.OkWithDetailed(out, "ok", c)
}
