// ============================================================================
// T22 潜客侧 bill 分账明细查询 service（新增文件）
// 目标路径: service/app/bill.go
// ============================================================================
// 用途：供 Node 侧归集看板（/api/dashboard/collect-summary）跨库合并潜客侧数据。
//
// ★ 为什么由 Go 提供读取：
//   `bill` 表位于 MariaDB qk_e2e。Node 侧【无 MySQL 连接】（.env 无 MYSQL_*），
//   而 Go 侧 Global.GVA_DB 已连该库 ⇒ 由 Go 暴露只读端点，Node 经 HTTP 取用，
//   避免给 Node 引入第二套数据库连接（不改 Node 架构）。
//
// ★ 本文件【只读】：仅 SELECT / COUNT，不产生任何写库路径。
// ============================================================================
package app

import (
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/model/app"
)

// Bill 分页查询的边界常量。
//
// ★ 上限 200 是硬约束：bill 表随归集持续增长，无上限会让单次请求
//   把整表拉进内存并序列化返回。看板只需 total + 首页样本，故 200 足够。
const (
	BillLimitDefault = 50
	BillLimitMax     = 200
)

// BillListOut bill 分页结果
type BillListOut struct {
	Total int64      `json:"total"`
	List  []app.Bill `json:"list"`
}

// BillList 分页查询潜客侧 bill 分账明细（只读）。
//
//	limit   : 每页条数，<=0 用默认 50；>200 截断为 200
//	offset  : 偏移，<0 归零
//	walletId: >0 时按 wallet_id 过滤；否则全量
//
// ★ 返回的 Total 是【过滤条件下的总数】（COUNT），与 List 的当前页解耦，
//   调用方才能据 total 判断"潜客侧共有多少条"而不必翻页。
func (p *PublicService) BillList(limit, offset, walletId int) (out BillListOut, err error) {
	// ---- 边界归一化：handler 传入的值不可信 ----
	if limit <= 0 {
		limit = BillLimitDefault
	}
	if limit > BillLimitMax {
		limit = BillLimitMax
	}
	if offset < 0 {
		offset = 0
	}

	// list 初始化为空切片而非 nil：nil 会被 json 序列化成 null，
	// 前端对 null 做 .length / .map 会抛错。空结果应为 []。
	out.List = make([]app.Bill, 0)

	db := global.GVA_DB.Model(&app.Bill{})
	if walletId > 0 {
		db = db.Where("wallet_id = ?", walletId)
	}

	// ---- COUNT：先算总数（在分页条件下统计，复用同一套 where）----
	if err = db.Count(&out.Total).Error; err != nil {
		return out, err
	}

	// ---- SELECT：按 id 升序稳定分页 ----
	// ★ 必须显式排序：SQL 不保证无序查询的行序，无 ORDER BY 时分页
	//   可能重复或漏行。id 为主键，升序即入库顺序，便于对照。
	// ★ Offset/Limit 顺序不可颠倒，GORM 要求先 Offset 后 Limit。
	if err = db.
		Order("id ASC").
		Offset(offset).
		Limit(limit).
		Find(&out.List).Error; err != nil {
		return out, err
	}

	return out, nil
}
