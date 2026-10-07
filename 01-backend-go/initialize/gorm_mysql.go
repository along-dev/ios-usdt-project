package initialize

import (
	"github.com/flipped-aurora/gin-vue-admin/server/config"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/initialize/internal"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"time"
)

// GormMysql 初始化Mysql数据库
// Author [piexlmax](https://github.com/piexlmax)
// Author [SliverHorn](https://github.com/SliverHorn)
func GormMysql() *gorm.DB {
	m := global.GVA_CONFIG.Mysql
	// ★ T37（扩）：与 gorm.Open 失败同形 —— “库名未配置”也必须由本步【指名道姓】地响亮失败。
	//   原为 `return nil` ⇒ global.GVA_DB 留 nil ⇒ 仍借道 blockchain/scan.go:17 的 nil 解引用崩。
	//   ⛔ 只报 哪一步 ＋ 缺什么（＋ host:port）；不含 DSN 全文 / 口令 / 凭据。
	if m.Dbname == "" {
		panic("GormMysql: invalid config (step=config) dbname is empty (mysql.db-name 未配置) host=" +
			m.Path + ":" + m.Port)
	}
	mysqlConfig := mysql.Config{
		DSN:                       m.Dsn(), // DSN data source name
		DefaultStringSize:         191,     // string 类型字段的默认长度
		SkipInitializeWithVersion: false,   // 根据版本自动配置
	}
	// ★ T37：“库连不上 / 口令错 / 库名错”必须由本步【指名道姓】地响亮失败。
	//   原为 `return nil` ⇒ global.GVA_DB 留 nil ⇒ 下游借道 blockchain/scan.go:17 的
	//   nil 解引用才崩，栈顶指向“链上扫描模块” ⇒ 运维排查方向被带偏（受控实验确证）。
	//   ⛔ 只报 哪一步 ＋ host:port ＋ dbname；不含 DSN 全文 / 口令 / 凭据。
	if db, err := gorm.Open(mysql.New(mysqlConfig), internal.Gorm.Config()); err != nil {
		panic("GormMysql: gorm.Open failed (step=connect) host=" + m.Path + ":" + m.Port +
			" dbname=" + m.Dbname + " err=" + err.Error())
	} else {
		sqlDB, dbErr := db.DB()
		if dbErr != nil {
			panic("GormMysql: gorm.Open succeeded but obtaining *sql.DB failed: " + dbErr.Error())
		}
		sqlDB.SetMaxIdleConns(m.MaxIdleConns)
		sqlDB.SetMaxOpenConns(m.MaxOpenConns)
		sqlDB.SetConnMaxLifetime(5 * time.Minute)
		return db
	}
}

// GormMysqlByConfig 初始化Mysql数据库用过传入配置
func GormMysqlByConfig(m config.DB) *gorm.DB {
	if m.Dbname == "" {
		return nil
	}
	mysqlConfig := mysql.Config{
		DSN:                       m.Dsn(), // DSN data source name
		DefaultStringSize:         191,     // string 类型字段的默认长度
		SkipInitializeWithVersion: false,   // 根据版本自动配置
	}
	if db, err := gorm.Open(mysql.New(mysqlConfig), internal.Gorm.Config()); err != nil {
		panic(err)
	} else {
		sqlDB, _ := db.DB()
		sqlDB.SetMaxIdleConns(m.MaxIdleConns)
		sqlDB.SetMaxOpenConns(m.MaxOpenConns)
		sqlDB.SetConnMaxLifetime(5 * time.Minute)
		return db
	}
}
