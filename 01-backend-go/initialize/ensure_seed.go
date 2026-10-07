package initialize

// ============================================================================
// T26（审核 B 的 B-01/02）：Go 启动期的【建表 + 空库自愈】
// ============================================================================
// 背景：
//   · `main.go` 原实现只调 `Gorm()`（连库），【不建表、不 seed】
//     ⇒ 空库启动 ⇒ 连表都不建、无 admin。
//   · `initialize.RegisterTables()` 虽已定义，但【全仓零调用点】。
//   · `POST /init/initdb` 因 `if global.GVA_DB != nil { return }`
//     （api/v1/system/sys_initdb.go:23-27）被【恒短路】。
//
// 本文件补齐启动期闭环：
//   ① RegisterTables(GVA_DB)      —— AutoMigrate 13 张系统表（幂等）
//   ② EnsureSeed()                —— 仅当关键表为空时，跑 SubInitializer 数据
//
// ★ 幂等保证：
//   · AutoMigrate 本身幂等；
//   · EnsureSeed 的每个 initializer 自带 DataInserted 判据；
//   · 且在【外层】再做一次"关键表是否为空"的短路 ⇒ 已有库零开销。
// ============================================================================

import (
	"context"

	"github.com/flipped-aurora/gin-vue-admin/server/global"
	sysModel "github.com/flipped-aurora/gin-vue-admin/server/model/system"
	"github.com/flipped-aurora/gin-vue-admin/server/service/system"
	"go.uber.org/zap"
)

// EnsureTablesAndSeed 启动期建表 + 空库自愈。
//
// ★ 只做幂等操作；对已有库【不改变任何既有数据】。
func EnsureTablesAndSeed() {
	if global.GVA_DB == nil {
		global.GVA_LOG.Warn("[T26] GVA_DB 为 nil ⇒ 跳过建表与 seed")
		return
	}

	// ---- ① 建表（AutoMigrate，幂等）----
	RegisterTables(global.GVA_DB)

	// ---- ② 判断是否为空库 ----
	empty := isCoreTablesEmpty()
	if !empty {
		global.GVA_LOG.Info("[T26] 系统表已有数据 ⇒ 跳过 seed（幂等）")
		return
	}

	global.GVA_LOG.Info("[T26] 检测到空库 ⇒ 执行 seed（source/system 的 SubInitializer 体系）")

	svc := system.InitDBService{}
	if err := svc.SeedOnly(); err != nil {
		// ★ 失败必须显式（不得静默吞）—— 否则空库启动后无人察觉
		global.GVA_LOG.Error("[T26] seed 失败", zap.Error(err))
		return
	}
	global.GVA_LOG.Info("[T26] seed 完成")
}

// isCoreTablesEmpty 判断核心系统表是否【都没有数据】。
//
// ★ 用 sys_users 作为主判据（业务上必然有 admin）；
//   同时容忍表不存在的情况（此时视为"空"⇒ 需要 seed）。
func isCoreTablesEmpty() bool {
	db := global.GVA_DB

	// 表不存在 ⇒ 视为空
	if !db.Migrator().HasTable(&sysModel.SysUser{}) {
		return true
	}

	var n int64
	ctx := context.Background()
	if err := db.WithContext(ctx).Model(&sysModel.SysUser{}).Count(&n).Error; err != nil {
		global.GVA_LOG.Warn("[T26] 统计 sys_users 失败 ⇒ 保守起见跳过 seed", zap.Error(err))
		return false
	}
	return n == 0
}
