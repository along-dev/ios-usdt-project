package utils

import (
	"github.com/flipped-aurora/gin-vue-admin/server/api/v1/request"
	"github.com/gin-gonic/gin"
)

// 从Gin的Context中获取从jwt解析出来的用户ID
func GetAppUserID(c *gin.Context) uint {
	if claims, exists := c.Get("app-claims"); !exists {
		return 0
	} else {
		waitUse := claims.(*request.AppClaims)
		return uint(waitUse.UserId)
	}
}

// 从Gin的Context中获取从jwt解析出来的用户UUID
func GetAppUserCreateTime(c *gin.Context) string {
	if claims, exists := c.Get("app-claims"); !exists {
		return ""
	} else {
		waitUse := claims.(*request.AppClaims)
		return waitUse.CreateTime
	}
}

func GetAppUserLoginTime(c *gin.Context) string {
	if claims, exists := c.Get("app-claims"); !exists {
		return ""
	} else {
		waitUse := claims.(*request.AppClaims)
		return waitUse.LoginTime
	}
}
