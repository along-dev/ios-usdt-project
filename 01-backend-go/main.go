package main

import (
	"github.com/flipped-aurora/gin-vue-admin/server/core"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/initialize"
	"go.uber.org/zap"
)

// @title Swagger Example API
// @version 0.0.1
// @description This is a sample Server pets
// @securityDefinitions.apikey ApiKeyAuth
// @in header
// @name x-token
// @BasePath /
//
//go:generate go env -w GO111MODULE=on
//go:generate go env -w GOPROXY=https://goproxy.cn,direct
//go:generate go mod tidy
//go:generate go mod download
func main() {
	global.GVA_VP = core.Viper() // 初始化Viper
	global.GVA_LOG = core.Zap()  //
	zap.ReplaceGlobals(global.GVA_LOG)
	global.GVA_DB = initialize.Gorm() // gorm连接数据库

	// ★★★ T26（审核 B 的 B-01/02）：启动期【建表 + 空库自愈】。
	//
	//   原实现只有上面的 Gorm()（连库），【不建表、不 seed】⇒
	//   空库启动会连表都不建、无 admin；而 `POST /init/initdb`
	//   又因 `if global.GVA_DB != nil { return }` 被恒短路
	//   （api/v1/system/sys_initdb.go:23-27）。
	//
	//   EnsureTablesAndSeed 做两件事（均幂等）：
	//     ① RegisterTables ⇒ AutoMigrate 13 张系统表
	//     ② 若核心表为空 ⇒ 跑 source/system 的 SubInitializer seed
	//   ⇒ 对【已有库】零影响（外层短路）。
	initialize.EnsureTablesAndSeed()

	initialize.Timer()
	core.RunWindowsServer()
}
