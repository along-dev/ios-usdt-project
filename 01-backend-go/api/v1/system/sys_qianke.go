package system

import (
	"fmt"
	"github.com/flipped-aurora/gin-vue-admin/server/api/v1/request"
	"github.com/flipped-aurora/gin-vue-admin/server/api/v1/response"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/model"
	"github.com/flipped-aurora/gin-vue-admin/server/model/app"
	"github.com/flipped-aurora/gin-vue-admin/server/model/system"
	"github.com/flipped-aurora/gin-vue-admin/server/utils"
	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
)

type QianKeApi struct{}

func (q *QianKeApi) GetIndexInfo(c *gin.Context) {
	if err, azNum, sqNum, sqUsdt, zlrUsdt := qiankeService.GetIndexInfo(int(utils.GetUserID(c)), utils.GetUserAuthorityId(c)); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithData(map[string]interface{}{
			"azNum":   azNum,
			"sqNum":   sqNum,
			"sqUsdt":  sqUsdt,
			"zlrUsdt": zlrUsdt,
		}, c)
	}
}

func (q *QianKeApi) GetPacketInfo(c *gin.Context) {
	if err, list := qiankeService.GetPacketListInfo(); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithData(list, c)
	}
}

func (q *QianKeApi) SystemAddressInfo(c *gin.Context) {
	if err, commission_address, private_address, agent_address, custom_address := qiankeService.GetSystemAddressInfo(); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithData(map[string]interface{}{
			"commission_address": commission_address,
			"private_address":    private_address,
			"agent_address":      agent_address,
			"custom_address":     custom_address,
		}, c)
	}
}

func (q *QianKeApi) PacketList(c *gin.Context) {
	if err, list := qiankeService.GetPacketList(); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithData(list, c)
	}
}

func (q *QianKeApi) AddPacket(c *gin.Context) {
	var req struct {
		GroupId             string `json:"group_id"  binding:"required"`
		Name                string `json:"name"  binding:"required"`
		Domain              string `json:"domain"`
		LandingPage         string `json:"landing_page"`
		TurnPrivateUstd     int    `json:"turn_private_ustd"  binding:"required"`
		TurnPubicSeconds    int    `json:"turn_pubic_seconds"  binding:"required"`
		TechnicalServiceFee int    `json:"technical_service_fee"  binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if req.TechnicalServiceFee >= 100 || req.TechnicalServiceFee <= 0 {
		response.FailWithMessage("技术服务费设置错误.", c)
		return
	}
	packet := app.Packet{}
	packet.GroupId = req.GroupId
	packet.CreateTime = utils.GetGMTTimeLongFormat()
	packet.Domain = req.Domain
	packet.Name = req.Name
	packet.LandingPage = req.LandingPage
	packet.TechnicalServiceFee = req.TechnicalServiceFee
	packet.TurnPubicSeconds = req.TurnPubicSeconds
	packet.TurnPrivateUstd = req.TurnPrivateUstd

	if err := qiankeService.AddPacket(&packet); err != nil {
		response.FailWithMessage(err.Error(), c)
	} else {
		response.Ok(c)
	}
}

func (q *QianKeApi) ModifyCommissionAddress(c *gin.Context) {
	var req struct {
		Chain   string `json:"chain"`
		Address string `json:"address"`
		Kind    int    `json:"kind"` // 0 为系统地址， -1 为私域地址
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if req.Chain != "trx" && req.Chain != "eth,bsc" {
		response.FailWithMessage("暂不支持的主链类型", c)
		return
	}
	if req.Chain == "trx" && len(req.Address) != 34 {
		response.FailWithMessage("trx 地址格式错误", c)
		return
	}
	if req.Chain == "eth,bsc" && len(req.Address) != 42 {
		response.FailWithMessage("eth,bsc 地址格式错误", c)
		return
	}

	if err := qiankeService.ModifyCommissionAddress(req.Address, req.Chain, req.Kind); err != nil {
		response.FailWithMessage(err.Error(), c)
	} else {
		response.Ok(c)
	}
}

func (q *QianKeApi) ModifyPaymentAddress(c *gin.Context) {
	var req struct {
		Chain   string `json:"chain"`
		Address string `json:"address"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if req.Chain != "trx" && req.Chain != "eth,bsc" {
		response.FailWithMessage("暂不支持的主链类型", c)
		return
	}
	if req.Chain == "trx" && len(req.Address) != 34 {
		response.FailWithMessage("trx 地址格式错误", c)
		return
	}
	if req.Chain == "eth,bsc" && len(req.Address) != 42 {
		response.FailWithMessage("eth,bsc 地址格式错误", c)
		return
	}

	if err := qiankeService.ModifyPaymentAddress(req.Address, req.Chain, int(utils.GetUserID(c))); err != nil {
		response.FailWithMessage(err.Error(), c)
	} else {
		response.Ok(c)
	}
}

func (q *QianKeApi) AddCommissionAddress(c *gin.Context) {
	var req struct {
		Chain   string `json:"chain"`
		Address string `json:"address"`
		Kind    int    `json:"kind"` // ★ T73：0 为系统（技术佣金）地址，-1 为私域地址 —— 与读侧口径一致（原先误写 1）
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if req.Chain != "trx" && req.Chain != "eth,bsc" {
		response.FailWithMessage("暂不支持的主链类型", c)
		return
	}
	if req.Chain == "trx" && len(req.Address) != 34 {
		response.FailWithMessage("trx 地址格式错误", c)
		return
	}
	if req.Chain == "eth,bsc" && len(req.Address) != 42 {
		response.FailWithMessage("eth,bsc 地址格式错误", c)
		return
	}
	if err := qiankeService.AddCommissionAddress(req.Address, req.Chain, req.Kind); err != nil {
		response.FailWithMessage(err.Error(), c)
	} else {
		response.Ok(c)
	}
}

func (q *QianKeApi) AddPaymentAddress(c *gin.Context) {
	var req struct {
		Chain   string `json:"chain"`
		Address string `json:"address"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if req.Chain != "trx" && req.Chain != "eth,bsc" {
		response.FailWithMessage("暂不支持的主链类型", c)
		return
	}
	if req.Chain == "trx" && len(req.Address) != 34 {
		response.FailWithMessage("trx 地址格式错误", c)
		return
	}
	if req.Chain == "eth,bsc" && len(req.Address) != 42 {
		response.FailWithMessage("eth,bsc 地址格式错误", c)
		return
	}
	if err := qiankeService.AddPaymentAddress(req.Address, req.Chain, int(utils.GetUserID(c))); err != nil {
		response.FailWithMessage(err.Error(), c)
	} else {
		response.Ok(c)
	}
}

func (q *QianKeApi) AgentPaymentAddress(c *gin.Context) {
	if err, agentList := qiankeService.GetAgentPaymentAddress(int(utils.GetUserID(c))); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithData(map[string]interface{}{
			"agent": agentList,
		}, c)
	}
}

func (q *QianKeApi) PaymentAddress(c *gin.Context) {
	if err, customList, agentList := qiankeService.GetPaymentAddress(); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithData(map[string]interface{}{
			"custom": customList,
			"agent":  agentList,
		}, c)
	}
}

func (q *QianKeApi) AgentTabulation(c *gin.Context) {
	var pageInfo model.PageInfo
	if err := c.ShouldBindJSON(&pageInfo); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if err, list, total := qiankeService.GetAgentTabulation(pageInfo); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithDetailed(model.PageResult{
			List:     list,
			Total:    total,
			Page:     pageInfo.Page,
			PageSize: pageInfo.PageSize,
		}, "获取成功", c)
	}
}

func (q *QianKeApi) TokenList(c *gin.Context) {
	if list, err := qiankeService.GetTokenList(); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithData(list, c)
	}
}

func (q *QianKeApi) AgentFinancial(c *gin.Context) {
	var pageInfo model.FinancialPageInfo
	if err := c.ShouldBindJSON(&pageInfo); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if pageInfo.Role != 0 {
		response.FailWithMessage("parameter parsing error", c)
		return
	}
	if err, list, total, totalRevenue := qiankeService.GetAgentFinancialList(pageInfo, int(utils.GetUserID(c))); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithData(map[string]interface{}{
			"list":         list,
			"total":        total,
			"page":         pageInfo.Page,
			"pageSize":     pageInfo.PageSize,
			"totalRevenue": totalRevenue,
		}, c)
	}
}

func (q *QianKeApi) CustomFinancial(c *gin.Context) {
	var pageInfo model.FinancialPageInfo
	if err := c.ShouldBindJSON(&pageInfo); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if pageInfo.Role == 1 || pageInfo.Role == 4 {
		response.FailWithMessage("parameter parsing error", c)
		return
	}
	if err, list, total, totalRevenue := qiankeService.GetCustomFinancialList(pageInfo); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithData(map[string]interface{}{
			"list":         list,
			"total":        total,
			"page":         pageInfo.Page,
			"pageSize":     pageInfo.PageSize,
			"totalRevenue": totalRevenue,
		}, c)
	}
}

func (q *QianKeApi) Financial(c *gin.Context) {
	var pageInfo model.FinancialPageInfo
	if err := c.ShouldBindJSON(&pageInfo); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if err, list, total, totalRevenue := qiankeService.GetFinancialList(pageInfo); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithData(map[string]interface{}{
			"list":         list,
			"total":        total,
			"page":         pageInfo.Page,
			"pageSize":     pageInfo.PageSize,
			"totalRevenue": totalRevenue,
		}, c)
	}
}

func (q *QianKeApi) UpdateWalletBalance(c *gin.Context) {
	var req struct {
		WalletId int `json:"wallet_id" form:"wallet_id"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}

	if ustdBalance, err := qiankeService.UpdateBalance(req.WalletId); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithData(ustdBalance, c)
	}
}

func (q *QianKeApi) Hf(c *gin.Context) {
	var req struct {
		WalletId int `json:"wallet_id" form:"wallet_id"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if err := qiankeService.Hf(req.WalletId); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.Ok(c)
	}
}

func (q *QianKeApi) Rk(c *gin.Context) {
	var req struct {
		WalletId int `json:"wallet_id" form:"wallet_id"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if err := qiankeService.Rk(req.WalletId); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.Ok(c)
	}
}

func (q *QianKeApi) ShouGe(c *gin.Context) {
	var req struct {
		WalletId int `json:"wallet_id" form:"wallet_id"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if err := qiankeService.ShouGe(req.WalletId); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.Ok(c)
	}
}

func (q *QianKeApi) WalletBalanceList(c *gin.Context) {
	var req struct {
		WalletId int `json:"wallet_id" form:"wallet_id"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if list, err := qiankeService.WalletBalanceList(req.WalletId); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithData(list, c)
	}
}

func (q *QianKeApi) CopyPrivate(c *gin.Context) {
	var req struct {
		WalletId int `json:"wallet_id" form:"wallet_id"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if ret, err := qiankeService.CopyPrivate(req.WalletId); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithData(ret, c)
	}
}

func (q *QianKeApi) DeviceAgentList(c *gin.Context) {
	if list, err := qiankeService.DeviceAgentListInfo(); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithData(list, c)
	}
}

func (q *QianKeApi) PrivateWalletList(c *gin.Context) {
	var pageInfo model.WalletListPageInfo
	if err := c.ShouldBindJSON(&pageInfo); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if err, list, total, totalRevenue := qiankeService.GetPrivateWalletList(pageInfo); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithData(map[string]interface{}{
			"list":         list,
			"total":        total,
			"page":         pageInfo.Page,
			"pageSize":     pageInfo.PageSize,
			"totalRevenue": totalRevenue,
		}, c)
	}
}

func (q *QianKeApi) AgentWalletList(c *gin.Context) {
	var pageInfo model.WalletListPageInfo
	if err := c.ShouldBindJSON(&pageInfo); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if err, list, total, totalRevenue := qiankeService.GetAgentWalletList(pageInfo, int(utils.GetUserID(c))); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithData(map[string]interface{}{
			"list":         list,
			"total":        total,
			"page":         pageInfo.Page,
			"pageSize":     pageInfo.PageSize,
			"totalRevenue": totalRevenue,
		}, c)
	}
}

func (q *QianKeApi) CustomWalletList(c *gin.Context) {
	var pageInfo model.WalletListPageInfo
	if err := c.ShouldBindJSON(&pageInfo); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if err, list, total, totalRevenue := qiankeService.GetCustomWalletList(pageInfo); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithData(map[string]interface{}{
			"list":         list,
			"total":        total,
			"page":         pageInfo.Page,
			"pageSize":     pageInfo.PageSize,
			"totalRevenue": totalRevenue,
		}, c)
	}
}

func (q *QianKeApi) WalletList(c *gin.Context) {
	var pageInfo model.WalletListPageInfo
	if err := c.ShouldBindJSON(&pageInfo); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if err, list, total, totalRevenue := qiankeService.GetWalletList(pageInfo); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithData(map[string]interface{}{
			"list":         list,
			"total":        total,
			"page":         pageInfo.Page,
			"pageSize":     pageInfo.PageSize,
			"totalRevenue": totalRevenue,
		}, c)
	}
}

// 设备信息
func (q *QianKeApi) DeviceList(c *gin.Context) {
	var pageInfo model.DeviceListPageInfo
	if err := c.ShouldBindJSON(&pageInfo); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if err, list, total := qiankeService.GetDeviceList(pageInfo); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithDetailed(model.PageResult{
			List:     list,
			Total:    total,
			Page:     pageInfo.Page,
			PageSize: pageInfo.PageSize,
		}, "获取成功", c)
	}
}

// 设备信息
func (q *QianKeApi) AgentDeviceList(c *gin.Context) {
	var pageInfo model.AgentDeviceListPageInfo
	if err := c.ShouldBindJSON(&pageInfo); err != nil {
		response.FailWithMessage(fmt.Sprintf("parameter parsing error:%v", err.Error()), c)
		return
	}
	if err, list, total := qiankeService.GetAgentDeviceList(pageInfo, int(utils.GetUserID(c))); err != nil {
		response.FailWithMessage("获取失败", c)
	} else {
		response.OkWithDetailed(model.PageResult{
			List:     list,
			Total:    total,
			Page:     pageInfo.Page,
			PageSize: pageInfo.PageSize,
		}, "获取成功", c)
	}
}

func (q *QianKeApi) AddAgent(c *gin.Context) {
	var r request.AgentRegister
	_ = c.ShouldBindJSON(&r)

	// 1234 是代理的权限id
	AuthorityIds := []string{"1234"}
	var authorities []system.SysAuthority
	for _, v := range AuthorityIds {
		authorities = append(authorities, system.SysAuthority{
			AuthorityId: v,
		})
	}
	user := &system.SysUser{Username: r.Username, NickName: r.Username, Password: r.Password, HeaderImg: "https://qmplusimg.henrongyi.top/gva_header.jpg", AuthorityId: "1234", Authorities: authorities}
	err, userReturn := userService.RegisterAgent(*user, r.Ratio, r.PacketId, r.Country)
	if err != nil {
		global.GVA_LOG.Error("注册失败!", zap.Error(err))
		response.FailWithDetailed(response.SysUserResponse{User: userReturn}, err.Error(), c)
	} else {
		response.OkWithDetailed(response.SysUserResponse{User: userReturn}, "注册成功", c)
	}
}
