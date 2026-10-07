package system

import (
	"context"
	sysModel "github.com/flipped-aurora/gin-vue-admin/server/model/system"
	"github.com/flipped-aurora/gin-vue-admin/server/service/system"
	"github.com/pkg/errors"
	"gorm.io/gorm"
)

const initOrderMenuAuthority = initOrderMenu + initOrderAuthority

type initMenuAuthority struct{}

// auto run
func init() {
	system.RegisterInit(initOrderMenuAuthority, &initMenuAuthority{})
}

func (i *initMenuAuthority) MigrateTable(ctx context.Context) (context.Context, error) {
	return ctx, nil // do nothing
}

func (i *initMenuAuthority) TableCreated(ctx context.Context) bool {
	return false // always replace
}

func (i initMenuAuthority) InitializerName() string {
	return "sys_menu_authorities"
}

func (i *initMenuAuthority) InitializeData(ctx context.Context) (next context.Context, err error) {
	db, ok := ctx.Value("db").(*gorm.DB)
	if !ok {
		return ctx, system.ErrMissingDBContext
	}
	authorities, ok := ctx.Value(initAuthority{}.InitializerName()).([]sysModel.SysAuthority)
	if !ok {
		return ctx, errors.Wrap(system.ErrMissingDependentContext, "创建 [菜单-权限] 关联失败, 未找到权限表初始化数据")
	}
	menus, ok := ctx.Value(initMenu{}.InitializerName()).([]sysModel.SysBaseMenu)
	if !ok {
		return next, errors.Wrap(errors.New(""), "创建 [菜单-权限] 关联失败, 未找到菜单表初始化数据")
	}
	next = ctx

	// ★★★ T26 修复（R2-1 实测 panic）：上游实现【硬编码切片下标】——
	//   `menus[:20]` / `menus[21:]` / `menus[:12]` / `menus[13:17]`
	//   以及 `authorities[0..2]`，隐含"菜单恰有 ≥22 个、角色恰有 3 个"。
	//   实测（空库自愈路径）：
	//     panic: slice bounds out of range [:20] with capacity 13
	//   ⇒ 当 seed 的菜单数或角色数不足时【整个进程 panic】。
	//
	//   ⇒ 本修复：把下标访问改为【边界安全】的辅助函数；
	//     不足时按实际长度降级（语义不变：仍尽量授权，只是不越界）。
	//   ★ 不改变"888 拿全部菜单"的意图；仅在数据少于预期时避免崩溃。
	//   ★ 且角色数量不足时跳过对应分支（而非 panic）。

	// 辅助：安全切片 [from, to)，越界则截断
	safeSlice := func(s []sysModel.SysBaseMenu, from, to int) []sysModel.SysBaseMenu {
		n := len(s)
		if from > n {
			from = n
		}
		if to > n {
			to = n
		}
		if from > to {
			from = to
		}
		return s[from:to]
	}
	// 辅助：取第 i 个元素（越界返回零值 + false）
	at := func(i int) (sysModel.SysAuthority, bool) {
		if i < 0 || i >= len(authorities) {
			return sysModel.SysAuthority{}, false
		}
		return authorities[i], true
	}

	// 888 —— 超级管理员：拿全部菜单
	if a, ok := at(0); ok {
		if err = db.Model(&a).Association("SysBaseMenus").Replace(safeSlice(menus, 0, 20)); err != nil {
			return next, err
		}
		if err = db.Model(&a).Association("SysBaseMenus").Append(safeSlice(menus, 21, len(menus))); err != nil {
			return next, err
		}
	}

	// 8881 —— 上游的第二个角色（本库可能不存在）
	if a, ok := at(1); ok && len(menus) >= 8 {
		menu8881 := safeSlice(menus, 0, 2)
		menu8881 = append(menu8881, menus[7])
		if err = db.Model(&a).Association("SysBaseMenus").Replace(menu8881); err != nil {
			return next, err
		}
	}

	// 9528 —— 普通用户：只读子集
	if a, ok := at(2); ok {
		if err = db.Model(&a).Association("SysBaseMenus").Replace(safeSlice(menus, 0, 12)); err != nil {
			return next, err
		}
		if err = db.Model(&a).Association("SysBaseMenus").Append(safeSlice(menus, 13, 17)); err != nil {
			return next, err
		}
	}

	return next, nil
}

func (i *initMenuAuthority) DataInserted(ctx context.Context) bool {
	db, ok := ctx.Value("db").(*gorm.DB)
	if !ok {
		return false
	}
	var count int64
	if err := db.Model(&sysModel.SysAuthority{}).
		Where("authority_id = ?", "9528").Preload("SysBaseMenus").Count(&count); err != nil {
		return count == 16
	}
	return false
}
