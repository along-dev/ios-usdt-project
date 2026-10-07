package middleware

import (
	"crypto/subtle"
	"net/http"

	"github.com/flipped-aurora/gin-vue-admin/server/api/v1/response"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/gin-gonic/gin"
)

// ServiceTokenAuth 服务间共享密钥鉴权（gasleak → 潜客 的回传桥）。
//
// 为什么不用 AppJWTAuth：
//  1. 本仓【没有任何签发 app token 的路由】—— api/v1/app/public.go 的 tokenNext
//     整段被注释，故调用方拿不到合法 token；
//  2. AppJWTAuth 还要求 token 同时存在于 Redis（app_jwt.go 的 GVA_REDIS.Get），
//     引入会话依赖，Redis 不可用即桥全断；
//  3. 调用方 gasleak 是【服务端】而非 App 用户，AppJWTAuth 是给设备侧设计的。
//
// 密钥取自 app-jwt.service-token（可用环境变量注入）。
func ServiceTokenAuth() gin.HandlerFunc {
	return func(c *gin.Context) {
		want := global.GVA_CONFIG.AppJwt.ServiceToken
		got := c.GetHeader("X-Service-Token")
		// ★ 未配置密钥时必须拒绝（fail closed）。否则 want=="" 会让"不带该头"
		//   的请求也判等通过，鉴权形同虚设。
		if want == "" || subtle.ConstantTimeCompare([]byte(got), []byte(want)) != 1 {
			// 401 而非业务码 7：调用方需要能与"参数错误"区分，
			// 且这是标准的"凭据缺失/无效"语义。
			c.JSON(http.StatusUnauthorized, response.Response{
				Code: response.ERROR, Data: map[string]interface{}{},
				Msg: "invalid or missing X-Service-Token",
			})
			c.Abort()
			return
		}
		c.Next()
	}
}
