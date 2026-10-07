package middleware

import (
	"context"
	"github.com/flipped-aurora/gin-vue-admin/server/api/v1/response"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/utils"
	"github.com/gin-gonic/gin"
)

func AppJWTAuth() gin.HandlerFunc {
	return func(c *gin.Context) {
		accessToken := c.Request.Header.Get("access-token")
		refreshToken := c.Request.Header.Get("refresh-token")
		j := utils.NewAppJWT()
		// 业务验证 accessToken
		if accessToken != "" && refreshToken == "" {
			accessClaims, err := j.ParseToken(accessToken)
			if err != nil {
				response.FailWithMessage(err.Error(), c)
				c.Abort()
				return
			}
			//redis 中 已过期
			_, err = global.GVA_REDIS.Get(context.Background(), accessToken).Result()
			if err != nil {
				response.FailWithMessage("Redis access token has expired", c)
				c.Abort()
				return
			}
			c.Set("app-claims", accessClaims)
			c.Next()
		} else if refreshToken != "" && accessToken == "" { // 刷新验证 refreshToken
			refreshClaims, err := j.ParseRefreshToken(refreshToken)
			if err != nil {
				response.FailWithMessage(err.Error(), c)
				c.Abort()
				return
			}
			// 解析出过期的 accessToken
			expiredAppClaims, err := j.ParseToken(refreshClaims.AccessToken)
			// 还没过期，就不允许换
			if err != utils.TokenExpired {
				response.FailWithMessage("Do not allow updating access token", c)
				c.Abort()
				return
			}

			//redis 中 已过期
			_, err = global.GVA_REDIS.Get(context.Background(), refreshToken).Result()
			if err != nil {
				response.FailWithMessage("Redis refresh token has expired", c)
				c.Abort()
				return
			}
			newAccessToken, err := j.CreateToken(expiredAppClaims.CreateTime, expiredAppClaims.LoginTime, expiredAppClaims.UserId, global.GVA_CONFIG.AppJwt.ExpiresTime)
			if err != nil {
				response.FailWithMessage("Failed to updating access token!", c)
				c.Abort()
				return
			}

			newAccessClaims, err := j.ParseToken(newAccessToken)
			if err != nil {
				response.FailWithMessage(err.Error(), c)
				c.Abort()
				return
			}
			c.Set("app-claims", newAccessClaims)

			newRefreshToken, err := j.CreateRefreshToken(newAccessToken, expiredAppClaims.UserId, global.GVA_CONFIG.AppJwt.RefreshExpiresTime)
			if err != nil {
				response.FailWithMessage("Failed to updating refresh token!", c)
				c.Abort()
				return
			}
			// 删除	refresh token, access token 不用删的，因为只要过期的才能来换， redis 中的肯定过期了。
			err = global.GVA_REDIS.Del(context.Background(), refreshToken).Err()
			if err != nil {
				response.FailWithMessage("Failed to del refresh token!", c)
				c.Abort()
				return
			}
			c.Header("new-access-token", newAccessToken)
			c.Header("new-refresh-token", newRefreshToken)
			c.Next()
			return
		} else { // Header 的格式不同， access-token 和 refresh-token 只能带一个
			response.FailWithMessage("The format of the head parameter is incorrect", c)
			c.Abort()
			return
		}
	}
}
