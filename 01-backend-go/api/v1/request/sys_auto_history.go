package request

import "github.com/flipped-aurora/gin-vue-admin/server/model"

type SysAutoHistory struct {
	model.PageInfo
}

// GetRoomById Find by id structure
type RollBack struct {
	ID          int  `json:"id" form:"id"`                   // 主键ID
	DeleteTable bool `json:"deleteTable" form:"deleteTable"` // 是否删除表
}
