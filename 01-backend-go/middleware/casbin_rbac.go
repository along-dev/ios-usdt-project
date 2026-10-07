package middleware

import (
	"github.com/flipped-aurora/gin-vue-admin/server/api/v1/response"

	"github.com/flipped-aurora/gin-vue-admin/server/service/system"
	"github.com/flipped-aurora/gin-vue-admin/server/utils"
	"github.com/gin-gonic/gin"
)

var casbinService = system.CasbinService{}

// 拦截器
func CasbinHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		waitUse, _ := utils.GetClaims(c)
		// 获取请求的PATH
		obj := c.Request.URL.Path
		// 获取请求方法
		act := c.Request.Method
		// 获取用户的角色
		sub := waitUse.AuthorityId
		e := casbinService.Casbin()
		// 判断策略中是否存在
		success, _ := e.Enforce(sub, obj, act)
		// ★ WBE01-B（卡 T28）：原为 `if global.GVA_CONFIG.System.Env == "develop" || success`。
		//   该旁路让 `Env=develop` 时**无条件放行**（casbin 判定被短路），且**静默**、不打日志。
		//   已按总调度裁定 (甲) **整条删除**：权限旁路不得由「环境名」隐式触发。
		//   开发期若要免 seed，改用 **DB 里的放行策略**（可见、可撤）；
		//   `System.Env` 在本仓已无读取点（仅留配置件，不影响鉴权）。
		if success {
			c.Next()
		} else {
			response.FailWithDetailed(gin.H{}, "权限不足", c)
			c.Abort()
			return
		}
	}
}
