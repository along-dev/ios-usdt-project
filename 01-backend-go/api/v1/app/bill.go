// ============================================================================
// T22 潜客侧 bill 分账明细查询 handler（新增文件）
// 目标路径: api/v1/app/bill.go
// ============================================================================
// 用途：向 Node 侧归集看板暴露【只读】的 bill 分页查询，使看板能合并潜客侧数据。
//
// GET /app/bill-list?limit=50&offset=0&wallet_id=15
//   Header: X-Service-Token: <服务间密钥>
//   Resp: {"code":0,"data":{"total":33,"list":[{...bill...}]},"msg":"ok"}
//
// ★ 只读端点：只有 SELECT，不写库。
// ★ 鉴权：注册在 InitAuthRouter（middleware.ServiceTokenAuth），
//   无 token / token 错 ⇒ 401（与 wallet-status 同级同语义）。
// ============================================================================
package app

import (
	"strconv"

	"github.com/flipped-aurora/gin-vue-admin/server/api/v1/response"
	"github.com/gin-gonic/gin"
)

// BillList 分页查询潜客侧 bill 分账明细（只读，供归集看板跨库合并）。
func (p *PublicApi) BillList(c *gin.Context) {
	// ★ 参数解析刻意【不报错】：limit/offset/wallet_id 都是可选查询参数，
	//   非法值（如 limit=abc）退化为 0，再由 service 归一化为默认值。
	//   看板调用方不应因一个可选参数写错而整个端点失败。
	limit, _ := strconv.Atoi(c.Query("limit"))
	offset, _ := strconv.Atoi(c.Query("offset"))
	walletId, _ := strconv.Atoi(c.Query("wallet_id"))

	// 归一化（含 limit 上限截断）在 service 内完成，handler 不重复实现边界。
	// ★ TPublicService 与 collect-lock / collect-result 复用同一实例（见 public.go）。
	out, err := TPublicService.BillList(limit, offset, walletId)
	if err != nil {
		response.FailWithMessage(err.Error(), c)
		return
	}

	response.OkWithDetailed(out, "ok", c)
}
