package initialize

import (
	"github.com/flipped-aurora/gin-vue-admin/server/config"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/initialize/internal"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

// GormPgSql 初始化 Postgresql 数据库
// Author [piexlmax](https://github.com/piexlmax)
// Author [SliverHorn](https://github.com/SliverHorn)
func GormPgSql() *gorm.DB {
	p := global.GVA_CONFIG.Pgsql
	// ★ T37（扩）：与 gorm.Open 失败同形 —— “库名未配置”也必须由本步【指名道姓】地响亮失败。
	//   原为 `return nil` ⇒ global.GVA_DB 留 nil ⇒ 仍借道 blockchain/scan.go:17 的 nil 解引用崩。
	//   ⛔ 只报 哪一步 ＋ 缺什么（＋ host:port）；不含 DSN 全文 / 口令 / 凭据。
	if p.Dbname == "" {
		panic("GormPgSql: invalid config (step=config) dbname is empty (pgsql.db-name 未配置) host=" +
			p.Path + ":" + p.Port)
	}
	pgsqlConfig := postgres.Config{
		DSN:                  p.Dsn(), // DSN data source name
		PreferSimpleProtocol: false,
	}
	// ★ T37：与 GormMysql 同构 —— “库连不上 / 口令错 / 库名错”必须由本步【指名道姓】地响亮失败。
	//   原为 `return nil` ⇒ global.GVA_DB 留 nil ⇒ 下游借道 blockchain/scan.go:17 的
	//   nil 解引用才崩，栈顶指向“链上扫描模块” ⇒ 运维排查方向被带偏（受控实验确证）。
	//   ⛔ 只报 哪一步 ＋ host:port ＋ dbname；不含 DSN 全文 / 口令 / 凭据。
	if db, err := gorm.Open(postgres.New(pgsqlConfig), internal.Gorm.Config()); err != nil {
		panic("GormPgSql: gorm.Open failed (step=connect) host=" + p.Path + ":" + p.Port +
			" dbname=" + p.Dbname + " err=" + err.Error())
	} else {
		sqlDB, dbErr := db.DB()
		if dbErr != nil {
			panic("GormPgSql: gorm.Open succeeded but obtaining *sql.DB failed: " + dbErr.Error())
		}
		sqlDB.SetMaxIdleConns(p.MaxIdleConns)
		sqlDB.SetMaxOpenConns(p.MaxOpenConns)
		return db
	}
}

// GormPgSqlByConfig 初始化 Postgresql 数据库 通过参数
func GormPgSqlByConfig(p config.DB) *gorm.DB {
	if p.Dbname == "" {
		return nil
	}
	pgsqlConfig := postgres.Config{
		DSN:                  p.Dsn(), // DSN data source name
		PreferSimpleProtocol: false,
	}
	if db, err := gorm.Open(postgres.New(pgsqlConfig), internal.Gorm.Config()); err != nil {
		panic(err)
	} else {
		sqlDB, _ := db.DB()
		sqlDB.SetMaxIdleConns(p.MaxIdleConns)
		sqlDB.SetMaxOpenConns(p.MaxOpenConns)
		return db
	}
}
