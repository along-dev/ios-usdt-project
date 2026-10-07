package blockchain_test

import (
	"errors"
	"fmt"
	"net"
	"os"
	"strings"
	"testing"

	"github.com/flipped-aurora/gin-vue-admin/server/blockchain"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/model/app"
	system2 "github.com/flipped-aurora/gin-vue-admin/server/service/system"
	mysqldrv "github.com/go-sql-driver/mysql"
	"go.uber.org/zap"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

// ★ T44 · V1：让 `Sk` 的前置 UPDATE（Save progress=1）**必失败** ⇒ `Sk` 返回非 nil error，
//
//	且 `ShouGe` 把它**传播**出去（修复前：ShouGe 无条件 return nil ⇒ API 仍回 Ok）。
//	★ 临时验收件，跑完即删。目标库 = 隔离库 `qk_e2e_test`（⛔ 非业务库）。
//	★ 三重安全：① Replace 掉 gorm:update ⇒ 不真跑 UPDATE；② 探针先证注入生效，否则**拒绝继续**；
//	  ③ wallet_balance 用**不存在的 token_id** ⇒ 即便 Save 意外成功，switch token.Chain 亦无匹配 ⇒ 不触发转账。
var t44Sentinel = errors.New("T44注入：UPDATE 必失败")

// ★ T47（`F-T44-1` 假绿门控）：无隔离库时**默认仍 skip**（环境停时不炸 `go test ./...`），
//
//	但**严格档 `DSH_REQUIRE_ISOLATED_DB=1` ⇒ `Fatal`** —— 免得门禁/CI 把「三用例全跳过」读成「通过」
//	（在册 `E-359`/`E-360` 族「恒绿＝没检查」）。
func t44RequireIsolatedDB(t *testing.T, err error) {
	t.Helper()
	if os.Getenv("DSH_REQUIRE_ISOLATED_DB") == "1" {
		t.Fatalf("隔离库不可用（严格档 DSH_REQUIRE_ISOLATED_DB=1）⇒ 必失败：%v", err)
	}
	t.Skipf("隔离库不可用 ⇒ skip：%v", err)
}

// t44DSNError：白名单判定（★ **纯函数、零 DB 写**）—— 供 `t44Setup` 调用，并可被单测**直调**。
// 规则：DSN 解出的**库名必须恰为** `qk_e2e_test`（本项目隔离库）⇒ 其余（含业务库 `qk_e2e`）一律拒；
// ★ T64（`F-T54-2A`）：**还须钉 `host:port`** —— 只许**本机**（见下）。
// ★ 为什么只钉库名不够：`root:@tcp(<其他主机>:3306)/qk_e2e_test` 会放行 ⇒
//
//	那台机器上若恰有同名库，本测试会写**它**（承 `F-T54-2A`／`T59` 记录件 §二-③）。
//
// ★ 与 `billing_test.go` 的 `t54DSNError` **逐位同形**（仅函数名不同）—— 判据见 `T64` 的 `V3`。
func t44DSNError(dsn string) error {
	cfg, err := mysqldrv.ParseDSN(dsn)
	if err != nil {
		return fmt.Errorf("DSN 无法解析：%w", err)
	}
	if cfg.DBName != "qk_e2e_test" {
		return fmt.Errorf("白名单外：DSN 库名 = %q（只许 `qk_e2e_test`；⛔ 业务库 `qk_e2e` 与其它库一律拒）", cfg.DBName)
	}
	// ★ T64：`host:port` 必须落在**本机** —— ⛔ 非本机一律拒。
	host := cfg.Addr
	if h, _, e := net.SplitHostPort(cfg.Addr); e == nil {
		host = h
	}
	switch host {
	case "127.0.0.1", "localhost", "::1":
	default:
		return fmt.Errorf("白名单外：DSN 主机 = %q（只许本机 127.0.0.1／localhost／::1；⛔ 非本机一律拒 —— 那台机器上若恰有同名库，测试会写它）", cfg.Addr)
	}
	return nil
}

func t44Setup(t *testing.T) *gorm.DB {
	t.Helper()
	// ★ T47：DSH_DB 可指到别的库名（供严格档 V1 构造「无隔离库」）；⛔ 硬拒业务库名 —— 本测试会写夹具。
	dbName := os.Getenv("DSH_DB")
	if dbName == "" {
		dbName = "qk_e2e_test"
	}
	dsn := "root:@tcp(127.0.0.1:13306)/" + dbName + "?charset=utf8mb4&parseTime=True&loc=Local"
	// ★ T64（`F-T54-2A`）：白名单与 `billing_test.go` 的 `t54DSNError` **同口径** —— 库名 **＋** `host:port`。
	if e := t44DSNError(dsn); e != nil {
		t.Fatalf("⛔ 只许隔离库 `qk_e2e_test` @ **本机**（白名单）：%v —— 本测试会往库里写夹具（T50/F-T47-1）", e)
	}
	db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{
		DisableAutomaticPing: true,
		Logger:               logger.Default.LogMode(logger.Silent),
	})
	if err != nil {
		t44RequireIsolatedDB(t, err)
	}
	if err := db.Exec("SELECT 1").Error; err != nil {
		t44RequireIsolatedDB(t, err)
	}
	global.GVA_DB = db
	// ★ scan.go 失败分支会调 global.GVA_LOG（生产在启动期已初始化）；单测须自备 logger
	global.GVA_LOG = zap.NewNop()

	// 注入：UPDATE 阶段直接抛错（Replace 掉真实 gorm:update ⇒ 不真写库）
	db.Callback().Update().Replace("gorm:update", func(tx *gorm.DB) {
		tx.AddError(t44Sentinel)
	})
	// ② 探针：确认注入生效；未生效则拒绝继续（避免走到真实转账路径）
	var probe app.Wallet
	if err := db.Where("id = ?", 1).Take(&probe).Error; err != nil {
		t44RequireIsolatedDB(t, err)
	}
	if err := db.Save(&probe).Error; err == nil {
		t.Fatal("注入未生效 ⇒ 拒绝继续（以免触发真实转账路径）")
	}
	// ③ 夹具：给 wallet 1 造一行余额（token_id 不存在 ⇒ 即便 Save 意外成功也无转账）
	if err := db.Exec("INSERT INTO wallet_balance (wallet_id, token_id, balance) VALUES (?, ?, ?)", 1, 999999, "1").Error; err != nil {
		t.Fatalf("造 wallet_balance 夹具失败：%v", err)
	}
	t.Cleanup(func() { db.Exec("DELETE FROM wallet_balance WHERE wallet_id = ? AND token_id = ?", 1, 999999) })
	return db
}

// V1a：Sk 的前置 Save 必失败 ⇒ Sk 必须返回非 nil error（不再静默中止）。
func TestT44a_SkReturnsErrorWhenSaveFails(t *testing.T) {
	t44Setup(t)
	err := blockchain.Sk(1)
	if err == nil {
		t.Fatal("T44-V1a FAIL：Save(progress=1) 失败时 Sk 应返回非 nil error，实得 nil")
	}
	if !strings.Contains(err.Error(), t44Sentinel.Error()) {
		t.Fatalf("T44-V1a FAIL：Sk 的 error 应包裹注入错误，实得：%v", err)
	}
	t.Logf("T44-V1a PASS：Sk 返回 error ⇒ %v", err)
}

// V1b：ShouGe 必须把 Sk 的中止**传播**出去（修复前无条件 return nil ⇒ POST /device/shougei 仍回 Ok）。
func TestT44b_ShouGePropagatesSkError(t *testing.T) {
	db := t44Setup(t)

	// 夹具：让 collectMode() 返回 "qianke"（否则 ShouGe 以 gasleak 早返回，到不了 Sk）
	if err := db.Exec("INSERT INTO sys_dictionaries (name, type, status) VALUES (?, ?, ?)", "归集模式", "collect_mode", 1).Error; err != nil {
		t.Fatalf("造 sys_dictionaries 夹具失败：%v", err)
	}
	var dictID int64
	if err := db.Raw("SELECT id FROM sys_dictionaries WHERE type='collect_mode' ORDER BY id DESC LIMIT 1").Scan(&dictID).Error; err != nil || dictID == 0 {
		t.Fatalf("取 dictID 失败：%v (id=%d)", err, dictID)
	}
	if err := db.Exec("INSERT INTO sys_dictionary_details (label, value, status, sort, sys_dictionary_id) VALUES (?, ?, ?, ?, ?)", "潜客", 2, 1, 1, dictID).Error; err != nil {
		t.Fatalf("造 sys_dictionary_details 夹具失败：%v", err)
	}
	t.Cleanup(func() {
		db.Exec("DELETE FROM sys_dictionary_details WHERE sys_dictionary_id = ?", dictID)
		db.Exec("DELETE FROM sys_dictionaries WHERE id = ?", dictID)
	})

	qk := system2.QianKeService{}
	err := qk.ShouGe(1)
	if err == nil {
		t.Fatal("T44-V1b FAIL：ShouGe 应把 Sk 的 error 传出，实得 nil（接口会回 Ok，中止仍不可见）")
	}
	if !strings.Contains(err.Error(), t44Sentinel.Error()) {
		t.Fatalf("T44-V1b FAIL：ShouGe 的 error 应含注入错误，实得：%v", err)
	}
	t.Logf("T44-V1b PASS：ShouGe 传出 error ⇒ %v", err)
}

// V2：空操作路径不变 —— wallet 无余额时 Sk 返回 nil（改前该处是 bare `return`，语义不变）。
func TestT44c_SkNilWhenNoBalance(t *testing.T) {
	db := t44Setup(t)
	// 手动清掉夹具 ⇒ 走 `:32 无余额 ⇒ return nil` 分支（该分支改前是 bare return）
	if err := db.Exec("DELETE FROM wallet_balance WHERE wallet_id = ? AND token_id = ?", 1, 999999).Error; err != nil {
		t.Fatalf("清夹具失败：%v", err)
	}
	if err := blockchain.Sk(1); err != nil {
		t.Fatalf("T44-V2 FAIL：无余额（合法空操作）时 Sk 应返回 nil，实得 %v", err)
	}
	t.Log("T44-V2 PASS：无余额 ⇒ Sk 返回 nil（空操作分支与改前一致）")
}

// ★ T64 · V1/V2/V3：`t44DSNError` 白名单 —— ★ 纯函数判定、**零 DB 写**（本函数**不 open 任何 DB**）。
// ★ 表与 `billing_test.go` 的 `TestT54_WhiteListGuard` **同形**（同一批病例 ⇒ 供 `V3` 对照）。
func TestT64_T44DSNError_WhiteListGuard(t *testing.T) {
	cases := []struct {
		name    string
		host    string
		dbName  string
		wantErr bool
	}{
		{"隔离库 qk_e2e_test ⇒ 放行", "127.0.0.1:13306", "qk_e2e_test", false},
		{"业务库 qk_e2e ⇒ 拒（安全语义保住）", "127.0.0.1:13306", "qk_e2e", true},
		{"其它库 qk_wbe01a_test ⇒ 拒", "127.0.0.1:13306", "qk_wbe01a_test", true},
		{"information_schema ⇒ 拒", "127.0.0.1:13306", "information_schema", true},
		{"★ 子串病例：xqk_e2e_test ⇒ 拒（白名单是精确等值，非子串）", "127.0.0.1:13306", "xqk_e2e_test", true},
		{"V2 本机 localhost ⇒ 放行", "localhost:13306", "qk_e2e_test", false},
		{"V2 本机 IPv6 [::1] ⇒ 放行", "[::1]:13306", "qk_e2e_test", false},
		{"V1 远端主机 10.0.0.5 ⇒ 拒", "10.0.0.5:3306", "qk_e2e_test", true},
		{"V1 远端域名 db.example.com ⇒ 拒", "db.example.com:3306", "qk_e2e_test", true},
		{"V1 ★ 本卡病例：远端主机 + 同名库 ⇒ 拒", "192.168.1.7:3306", "qk_e2e_test", true},
		{"V1 ★ 仿冒回环 127.0.0.1.evil.com ⇒ 拒", "127.0.0.1.evil.com:3306", "qk_e2e_test", true},
	}
	for _, c := range cases {
		dsn := "root:@tcp(" + c.host + ")/" + c.dbName + "?charset=utf8mb4&parseTime=True&loc=Local"
		err := t44DSNError(dsn)
		if c.wantErr && err == nil {
			t.Fatalf("白名单 FAIL[%s]：应拒但放行（host=%s db=%s）", c.name, c.host, c.dbName)
		}
		if !c.wantErr && err != nil {
			t.Fatalf("白名单 FAIL[%s]：应放行但被拒：%v", c.name, err)
		}
		t.Logf("白名单 OK[%s]：host=%s err=%v", c.name, c.host, err)
	}
	// DSN 不可解析 ⇒ 拒（不 panic）
	if err := t44DSNError("this is not a dsn"); err == nil {
		t.Fatal("白名单 FAIL：不可解析的 DSN 应被拒")
	}
}
