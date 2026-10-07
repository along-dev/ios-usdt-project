package initialize

import (
	"fmt"
	"time"

	"github.com/flipped-aurora/gin-vue-admin/server/config"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/model/app"
	"github.com/flipped-aurora/gin-vue-admin/server/utils"
)

// TurnPubicScanSpec ★ D3-C1（T4.3）：到期扫描周期。
const TurnPubicScanSpec = "@every 1m"

// TurnPubicTaskName 到期扫描任务的 cron 名（同名任务会被 AddTaskByFunc 复用同一 cron 实例）。
const TurnPubicTaskName = "TurnPubic"

// TurnWalletToPublicOnDue ★ D3-C1（T4.3/T4.4）：把【已到期】的临时域 wallet 补转为公域。
//
// 背景：原 scan.go 用进程内 time.AfterFunc 驱动 region 自动转公域，
// 进程重启即丢失该调度（且无补算路径）⇒ 重启后"未到期的自动公域切换"永久丢失。
// 现改为持久化调度：scan.go 把"应转公域时刻"写入 wallet.turn_pubic_at，
// 本函数周期扫描并补算。
//
// ★ 幂等（P6）：用【条件更新】而非先查后写 —— 更新条件含
//
//	region = 0 AND turn_pubic_at > 0 AND turn_pubic_at <= now AND (deleted 无关)
//
// 转成功后同一行 turn_pubic_at 归 0、region 置 1，
// 故重复执行（多副本 / 周期性重跑）不会重复触发。
//
// ★ 为什么 region 条件取 0 而不是 <=1：turn_pubic_at 只由"临时域(region=0)"
// 的首次余额扫描写入；region=2 的私域钱包不走该路径。
// 若钱包在到期前被人工置为公域(1)/私域(2)，则不应再被本任务改写。
//
// 返回本次实际转公域的行数（供日志与判据使用）。
func TurnWalletToPublicOnDue() int64 {
	now := time.Now().Unix()

	// ★ 单条条件 UPDATE ⇒ 天然幂等，且多副本并发下由 DB 行锁保证只有一次生效
	//   （后到的副本更新条件不再满足，RowsAffected=0）。
	res := global.GVA_DB.Model(&app.Wallet{}).
		Where("region = ? AND turn_pubic_at > 0 AND turn_pubic_at <= ?", 0, now).
		Updates(map[string]interface{}{
			"region":        1,
			"turn_pubic_at": 0,
		})

	if res.Error != nil {
		fmt.Println("TurnWalletToPublicOnDue error:", res.Error)
		return 0
	}
	if res.RowsAffected > 0 {
		fmt.Printf("TurnWalletToPublicOnDue: %d wallet(s) turned to public region\n", res.RowsAffected)
	}
	return res.RowsAffected
}

func Timer() {
	if global.GVA_CONFIG.Timer.Start {
		for i := range global.GVA_CONFIG.Timer.Detail {
			go func(detail config.Detail) {
				global.GVA_Timer.AddTaskByFunc("ClearDB", global.GVA_CONFIG.Timer.Spec, func() {
					err := utils.ClearTable(global.GVA_DB, detail.TableName, detail.CompareField, detail.Interval)
					if err != nil {
						fmt.Println("timer error:", err)
					}
				})
			}(global.GVA_CONFIG.Timer.Detail[i])
		}
	}

	// ★ D3-C1（T4.3）：域切换到期扫描任务。
	//   与上面的 ClearDB 不同：本任务【无条件注册】，不依赖 GVA_CONFIG.Timer.Start。
	//   理由：域切换是资金路径的一环，配置缺失不得导致该持久化调度静默失效
	//   （若依赖配置，本卡"重启不丢"的修复会在配置未启时归零）。
	go func() {
		if _, err := global.GVA_Timer.AddTaskByFunc(TurnPubicTaskName, TurnPubicScanSpec, func() {
			TurnWalletToPublicOnDue()
		}); err != nil {
			fmt.Println("timer error (turn pubic):", err)
		}
	}()
}
