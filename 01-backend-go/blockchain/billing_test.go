package blockchain

import (
	"errors"
	"fmt"
	"net"
	"os"
	"strings"
	"testing"

	mysqldrv "github.com/go-sql-driver/mysql"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"

	"github.com/flipped-aurora/gin-vue-admin/server/model/app"
)

// ★ WBE01-A 卡A · F-02 三条表驱动测试：CAS ＋ 累加 ＋ **F-01 的"0 行匹配不得静默提交"**。
//
// ★★ 安全约束（承 WBE01-C 的教训：判据不得写业务库）：
//   - 只在 `WBE01A_TEST_DSN` 显式设置时运行；未设 ⇒ **t.Skip**（前提缺失即 SKIP，不判 PASS；严格档见 `requireIsolatedDB`）
//   - ★ **白名单**（`T54`／`F-T50-2`，与 `t44_v1_test.go` **同口径**）：DSN 解出的**库名必须恰为 `qk_e2e_test`**（本项目**隔离库**）
//     ⇒ `qk_e2e`（业务库）与其它任何库**一律拒**；★ 判定在 `gorm.Open` **之前** ⇒ **零 DB 写**。
//     ★ 旧实现用 `strings.Contains(dsn,"qk_e2e")` **子串**判据 ⇒ **误拒**合法的 `qk_e2e_test`（也含任何带该子串的库）。
//   - 本测试**自建自删** 专用表（`custom/agent/bill`）—— ★ 故必须落在**专用测试库**（= `qk_e2e_test`），
//     ⛔ 绝不许指向业务库 `qk_e2e`。
//
// 用法（本机实测用；★ 不指向 qk_e2e）：
//
//	WBE01A_TEST_DSN='root:@tcp(127.0.0.1:13306)/qk_e2e_test?charset=utf8mb4&parseTime=True&loc=Local' \
//	  go test ./blockchain/ -run TestAccumulateUsdtNum -v
//
// ★ T50（`F-T47-1` 同族，口径与 `T47` 的 `t44RequireIsolatedDB` 一致）：
//
//	无前置时**默认仍 `Skip`**（环境停时不炸 `go test ./...`），
//	但**严格档 `DSH_REQUIRE_ISOLATED_DB=1` ⇒ `Fatal`** —— 免得门禁/CI 把「全跳过」读成「通过」。
func requireIsolatedDB(t *testing.T, err error) {
	t.Helper()
	if os.Getenv("DSH_REQUIRE_ISOLATED_DB") == "1" {
		t.Fatalf("独立测试库不可用（严格档 DSH_REQUIRE_ISOLATED_DB=1）⇒ 必失败：%v", err)
	}
	// ★ T54（`F-T50-5`）：把原 `:38` 的现场提示「P-53：拿不到真值不得判 PASS」**补回**（`T50` 统一文案时丢了）。
	t.Skipf("独立测试库不可用 ⇒ skip（P-53：拿不到真值不得判 PASS）：%v", err)
}

// t54DSNError：白名单判定（★ **纯函数、零 DB 写**）—— 供 `openTestDB` 调用，并可被单测**直调**。
// 规则：DSN 解出的**库名必须恰为** `qk_e2e_test`（本项目隔离库）⇒ 其余（含业务库 `qk_e2e`）一律拒；
// ★ T64（`F-T54-2A`）：**还须钉 `host:port`** —— 只许**本机**（见下）。
// ★ 为什么只钉库名不够：`root:@tcp(<其他主机>:3306)/qk_e2e_test` 会放行 ⇒
//
//	那台机器上若恰有同名库，本测试会写**它**（承 `F-T54-2A`／`T59` 记录件 §二-③）。
func t54DSNError(dsn string) error {
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

// ★ T54 · V1＋★ T64 · V1/V2：白名单表驱动 —— ★ 全部是**纯函数判定**，**在 gorm.Open 之前** ⇒ **零 DB 写**。
func TestT54_WhiteListGuard(t *testing.T) {
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
		err := t54DSNError(dsn)
		if c.wantErr && err == nil {
			t.Fatalf("白名单 FAIL[%s]：应拒但放行（host=%s db=%s）", c.name, c.host, c.dbName)
		}
		if !c.wantErr && err != nil {
			t.Fatalf("白名单 FAIL[%s]：应放行但被拒：%v", c.name, err)
		}
		t.Logf("白名单 OK[%s]：host=%s err=%v", c.name, c.host, err)
	}
	// DSN 不可解析 ⇒ 拒（不 panic）
	if err := t54DSNError("this is not a dsn"); err == nil {
		t.Fatal("白名单 FAIL：不可解析的 DSN 应被拒")
	}
}

func openTestDB(t *testing.T) *gorm.DB {
	t.Helper()
	dsn := strings.TrimSpace(os.Getenv("WBE01A_TEST_DSN"))
	if dsn == "" {
		requireIsolatedDB(t, errors.New("WBE01A_TEST_DSN 未设置（需一个【独立测试库】；⛔ 不得指向业务库 qk_e2e）"))
	}
	if e := t54DSNError(dsn); e != nil {
		t.Fatalf("★ 拒绝对白名单外的库运行：%v（承 WBE01-C：判据不得写业务库）", e)
	}
	db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{Logger: logger.Default.LogMode(logger.Silent)})
	if err != nil {
		requireIsolatedDB(t, err)
	}
	// 自建表（与 model 同名；只建本测试用到的最小列）
	if err := db.Exec("DROP TABLE IF EXISTS custom, agent, bill").Error; err != nil {
		t.Fatalf("drop: %v", err)
	}
	if err := db.AutoMigrate(&app.Custom{}, &app.Agent{}, &app.Bill{}); err != nil {
		t.Fatalf("automigrate: %v", err)
	}
	t.Cleanup(func() {
		_ = db.Exec("DROP TABLE IF EXISTS custom, agent, bill").Error
	})
	return db
}

// seedBill 造一条 bill；status 由调用方给；另外造好对应主体。
func seedBill(t *testing.T, db *gorm.DB, id int, role int, status int, userId int) {
	t.Helper()
	b := app.Bill{ID: uint(id), Role: role, Status: status, UsdtNum: "10",
		TransferHash: fmt.Sprintf("t-hash-%d", id), TotalNum: "10", Num: "10"}
	if err := db.Create(&b).Error; err != nil {
		t.Fatalf("create bill: %v", err)
	}
	switch role {
	case 2:
		_ = db.Create(&app.Custom{UserId: userId, UsdtNum: "0"}).Error
	case 3:
		_ = db.Create(&app.Agent{UserId: userId, UsdtNum: "0"}).Error
	}
}

func sumOf(t *testing.T, db *gorm.DB, role int, userId int) string {
	t.Helper()
	var s string
	if role == 2 {
		_ = db.Model(&app.Custom{}).Where("user_id = ?", userId).Pluck("COALESCE(usdt_num,'0')", &s).Error
	} else {
		_ = db.Model(&app.Agent{}).Where("user_id = ?", userId).Pluck("COALESCE(usdt_num,'0')", &s).Error
	}
	return s
}

func statusOf(t *testing.T, db *gorm.DB, id int) int {
	t.Helper()
	var b app.Bill
	_ = db.Where("id = ?", id).First(&b).Error
	return b.Status
}

// TestAccumulateUsdtNum 三条表驱动用例（F-02 要求）
func TestAccumulateUsdtNum(t *testing.T) {
	cases := []struct {
		name      string
		role      int
		userId    int
		wantErr   bool
		wantAccum bool
		desc      string
	}{
		{"status=0 ⇒ 置1且累加", 2, 101, false, true, "正向：CAS 命中、累加 1 行"},
		{"未知 role ⇒ 显式错误（不静默）", 9, 101, true, false, "F-01②：未知 role 必须报错"},
		{"userId 无对应主体 ⇒ 报错且不提交", 2, 999, true, false, "F-01①：匹配 0 行 ⇒ 拒绝静默提交"},
	}

	for i, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			db := openTestDB(t)
			_ = db.Exec("DELETE FROM bill")
			_ = db.Exec("DELETE FROM custom")
			_ = db.Exec("DELETE FROM agent")
			bid := 1000 + i
			seedBill(t, db, bid, c.role, 0, 101) // ★ 一律以 status=0 起（A 路形状）

			var err error
			txErr := db.Transaction(func(tx *gorm.DB) error {
				// ★ F-05：调**产品码同一个函数**（原为"同形复制"的内联 CAS ⇒ 把产品码改窄时单测不红）
				err = MarkProcessedAndAccumulate(tx, bid, c.role, c.userId, "10")
				return err
			})
			gotErr := (txErr != nil) || (err != nil)
			if gotErr != c.wantErr {
				t.Fatalf("%s: wantErr=%v got=%v（err=%v txErr=%v）", c.desc, c.wantErr, gotErr, err, txErr)
			}
			// ★ F-01 的验收核心：出错时事务必须回滚 ⇒ status 保持 0（不得静默置 1）
			if c.wantErr {
				if st := statusOf(t, db, bid); st != 0 {
					t.Fatalf("%s: ★ 应回滚（status 保持 0），实测 status=%d ⇒ 静默置 1 未被拦住", c.desc, st)
				}
				return
			}
			if st := statusOf(t, db, bid); st != 1 {
				t.Fatalf("%s: 成功路径应置 1，实测 %d", c.desc, st)
			}
			if s := sumOf(t, db, c.role, c.userId); c.wantAccum && s != "10" {
				t.Fatalf("%s: 应累加为 10，实测 %q", c.desc, s)
			}
		})
	}
}

// TestAccumulateUsdtNum_Idempotent ★ 幂等：status 已是 1 ⇒ 再进不得再累加
func TestAccumulateUsdtNum_Idempotent(t *testing.T) {
	db := openTestDB(t)
	_ = db.Exec("DELETE FROM bill")
	_ = db.Exec("DELETE FROM custom")
	seedBill(t, db, 2001, 2, 1, 101) // ★ 已 status=1

	for n := 1; n <= 2; n++ { // 进两次
		_ = db.Transaction(func(tx *gorm.DB) error {
			// ★ F-05：同一处产品码函数 —— "把守卫改窄 ⇒ 必红"的落点就是它
			return MarkProcessedAndAccumulate(tx, 2001, 2, 101, "10")
		})
	}
	if s := sumOf(t, db, 2, 101); s != "0" {
		t.Fatalf("幂等失败：status=1 再进仍累加，实测 %q（应 0）", s)
	}
}

// TestMarkProcessedAndAccumulate_RejectsAnomalousStatus ★ F-05 收口：让 CAS 的「`AND status = 0`」
// **独立可检**（否则该条件在 status∈{0,1} 下被 `RowsAffected` 完全吸收 ⇒ 去掉它不可检出）。
//
// ★ 为什么需要这条（本线实测，非推断）：只保留 status∈{0,1} 的用例时，把产品码里
//
//	`Where("id = ? AND status = 0", ...)` 改成 `Where("id = ?", ...)`（＝删掉 CAS 条件），
//	**单测仍全 GREEN**。原因：MySQL 的 `RowsAffected` 计的是 **changed rows** ——
//	把一条 `status=1` 的行再置 1 ⇒ **0 行 changed** ⇒ `RowsAffected != 1` 那道守卫照样跳过。
//	⇒ 两条守卫里，**真正兜住幂等的是 `RowsAffected`**；`AND status = 0` 是**冗余防御**。
//
// ★ 本条让它不再冗余：`bill.status` 列**可空**（`int(32) NULL`，业务库与本测试库均如此）⇒
//
//	`status IS NULL` 是**可达的数据状态**（历史行／外部写入）。此时：
//	· 有 `AND status = 0` ⇒ `NULL = 0` 不成立 ⇒ **不匹配 ⇒ 幂等跳过（正确）**
//	· 去掉它 ⇒ `NULL → 1` **算 changed** ⇒ 被处理并累加（**错误**）
func TestMarkProcessedAndAccumulate_RejectsAnomalousStatus(t *testing.T) {
	db := openTestDB(t)
	_ = db.Exec("DELETE FROM bill")
	_ = db.Exec("DELETE FROM custom")
	if err := db.Exec("INSERT INTO bill (id, role, status, usdt_num, num, total_num, transfer_hash) " +
		"VALUES (3001, 2, NULL, '10', '10', '10', 't-hash-null')").Error; err != nil {
		t.Fatalf("造 status=NULL 的异常行失败: %v", err)
	}
	_ = db.Create(&app.Custom{UserId: 101, UsdtNum: "0"}).Error

	if err := db.Transaction(func(tx *gorm.DB) error {
		return MarkProcessedAndAccumulate(tx, 3001, 2, 101, "10")
	}); err != nil {
		t.Fatalf("应走「幂等跳过」路径、不该报错，实测 err=%v", err)
	}
	if s := sumOf(t, db, 2, 101); s != "0" {
		t.Fatalf("★ status 非 0（异常态）的行不得被处理；实测累加为 %q（应 0）", s)
	}
	var st *int
	if err := db.Raw("SELECT status FROM bill WHERE id = 3001").Scan(&st).Error; err != nil {
		t.Fatalf("回读 status 失败: %v", err)
	}
	if st != nil {
		t.Fatalf("★ status 应保持 NULL（未被置 1），实测 %d", *st)
	}
}
