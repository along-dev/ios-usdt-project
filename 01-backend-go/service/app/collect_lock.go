// ============================================================================
// §4.2.4 归集原子占位 service（新增文件）
// 目标路径: service/app/collect_lock.go
// ============================================================================
// 用途：gasleak 在链上归集前先占位（wallet.progress 0 → 1），
//
//	归集完成回传 collect-result 时由该 service 释放（1 → 0）。
//	潜客 Sk() 侧已有"progress==1 则拒绝"的既有保护，两端共用同一列。
//
// ============================================================================
package app

import (
	"errors"

	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/model"
	"github.com/flipped-aurora/gin-vue-admin/server/model/app"
	"gorm.io/gorm"
)

// ErrWalletBusy 该钱包已被占用（progress 已为 1）→ handler 应返回 409。
var ErrWalletBusy = errors.New("wallet is already collecting")

// CollectLockOut 占位结果
type CollectLockOut struct {
	WalletId int  `json:"walletId"`
	Locked   bool `json:"locked"`
}

// CollectLock 原子占位：UPDATE wallet SET progress=1 WHERE id=? AND progress=0
//
// ★ 必须用条件更新，不能"先查后置"：
//
//	gasleak 与潜客 Sk() 是两条独立归集路径，若各自先读 progress 再写，
//	会存在"检查—执行窗口"（TOCTOU），两端可同时判定为空闲 → 双重归集。
//	条件更新由 InnoDB 行锁保证互斥：RowsAffected==0 即已被对方占用。
func (p *PublicService) CollectLock(req *model.ReqCollectLock) (out CollectLockOut, err error) {
	// ---- ★ W1-C12 占位端前移校验（必须在 ResolveWalletId / 任何写库之前）----
	// 复用 CollectResult 的【同一份】词表实现 normalizeChain（同属 package app，无需导出），
	// 使 btc 与词表外的 chain 在【占位阶段】就响亮失败 —— 不占位、不写库
	// ⇒ BTC 归集根本不启动、钱不转出，从源头消除 W1-C2 的 F1：
	//   占位端词表含 btc ⇒ 能占到锁，而回传端在事务之前就失败 ⇒ 永不释放
	//   ⇒ progress 0→1→1，钱包被 gasleak 与潜客 Sk() 双侧永久锁死。
	//
	// ★ chain 为空 = C-2 允许的「wallet_id 直取」入参形态（不带链）⇒ 无需归一，
	//   原样交由 ResolveWalletId 走 wallet_id 分支（保持既有 409 语义不变）。
	//   chain 非空则必须过词表：btc / 词表外一律拒绝（单一事实来源，见契约 C-1）。
	chain := req.Chain
	if chain != "" {
		chain, err = normalizeChain(chain)
		if err != nil {
			return out, err
		}
	}

	walletId, err := ResolveWalletId(global.GVA_DB, req.WalletId, req.DeviceId, chain, req.Address)
	if err != nil {
		return out, err
	}
	out.WalletId = walletId

	res := global.GVA_DB.Model(&app.Wallet{}).
		Where("id = ? AND progress = 0", walletId).
		Update("progress", 1)
	if res.Error != nil {
		return out, res.Error
	}
	out.Locked = res.RowsAffected == 1
	if !out.Locked {
		return out, ErrWalletBusy
	}
	return out, nil
}

// ReleaseCollectLock 释放占位（progress → 0）。
// 由 CollectResult 在回传成功后调用；容忍"本就为 0"的情况（重复回传）。
func ReleaseCollectLock(tx *gorm.DB, walletId int) error {
	return tx.Model(&app.Wallet{}).
		Where("id = ?", walletId).
		Update("progress", 0).Error
}

// CollectRelease 显式释放归集占位（供 gasleak 在转账失败 / 超时路径调用）。
//
// 与 CollectResult 内置释放的区别：那条路径只在【回传成功】时走到，
// 失败路径不会回传，占位会永久泄漏。本方法补齐失败路径。
// 语义为条件更新（progress=1 → 0），重复调用安全。
func (p *PublicService) CollectRelease(req *model.ReqCollectRelease) (out CollectLockOut, err error) {
	walletId, err := ResolveWalletId(global.GVA_DB, req.WalletId, req.DeviceId, req.Chain, req.Address)
	if err != nil {
		return out, err
	}
	out.WalletId = walletId

	res := global.GVA_DB.Model(&app.Wallet{}).
		Where("id = ? AND progress = 1", walletId).
		Update("progress", 0)
	if res.Error != nil {
		return out, res.Error
	}
	// Released=false 表示本就未被占用——不算错误（幂等）
	out.Locked = res.RowsAffected == 1
	return out, nil
}
