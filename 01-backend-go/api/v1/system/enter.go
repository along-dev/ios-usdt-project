package system

import (
	"github.com/flipped-aurora/gin-vue-admin/server/service/system"
)

var (
	apiService              = system.ApiService{}
	jwtService              = system.JwtService{}
	menuService             = system.MenuService{}
	userService             = system.UserService{}
	initDBService           = system.InitDBService{}
	casbinService           = system.CasbinService{}
	autoCodeService         = system.AutoCodeService{}
	baseMenuService         = system.BaseMenuService{}
	authorityService        = system.AuthorityService{}
	dictionaryService       = system.DictionaryService{}
	systemConfigService     = system.SystemConfigService{}
	operationRecordService  = system.OperationRecordService{}
	autoCodeHistoryService  = system.AutoCodeHistoryService{}
	dictionaryDetailService = system.DictionaryDetailService{}
	authorityBtnService     = system.AuthorityBtnService{}
	qiankeService           = system.QianKeService{}
)
