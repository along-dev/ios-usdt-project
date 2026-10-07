package system

import (
	"errors"
	"fmt"
	"github.com/flipped-aurora/gin-vue-admin/server/api/v1/request"
	"os"

	"sync"

	"github.com/casbin/casbin/v2"
	gormadapter "github.com/casbin/gorm-adapter/v3"
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	_ "github.com/go-sql-driver/mysql"
)

//@author: [piexlmax](https://github.com/piexlmax)
//@function: UpdateCasbin
//@description: 更新casbin权限
//@param: authorityId string, casbinInfos []request.CasbinInfo
//@return: error

type CasbinService struct{}

var CasbinServiceApp = new(CasbinService)

func (casbinService *CasbinService) UpdateCasbin(authorityId string, casbinInfos []request.CasbinInfo) error {
	casbinService.ClearCasbin(0, authorityId)
	rules := [][]string{}
	for _, v := range casbinInfos {
		rules = append(rules, []string{authorityId, v.Path, v.Method})
	}
	e := casbinService.Casbin()
	success, _ := e.AddPolicies(rules)
	if !success {
		return errors.New("存在相同api,添加失败,请联系管理员")
	}
	return nil
}

//@author: [piexlmax](https://github.com/piexlmax)
//@function: UpdateCasbinApi
//@description: API更新随动
//@param: oldPath string, newPath string, oldMethod string, newMethod string
//@return: error

func (casbinService *CasbinService) UpdateCasbinApi(oldPath string, newPath string, oldMethod string, newMethod string) error {
	err := global.GVA_DB.Model(&gormadapter.CasbinRule{}).Where("v1 = ? AND v2 = ?", oldPath, oldMethod).Updates(map[string]interface{}{
		"v1": newPath,
		"v2": newMethod,
	}).Error
	return err
}

//@author: [piexlmax](https://github.com/piexlmax)
//@function: GetPolicyPathByAuthorityId
//@description: 获取权限列表
//@param: authorityId string
//@return: pathMaps []request.CasbinInfo

func (casbinService *CasbinService) GetPolicyPathByAuthorityId(authorityId string) (pathMaps []request.CasbinInfo) {
	e := casbinService.Casbin()
	list := e.GetFilteredPolicy(0, authorityId)
	for _, v := range list {
		pathMaps = append(pathMaps, request.CasbinInfo{
			Path:   v[1],
			Method: v[2],
		})
	}
	return pathMaps
}

//@author: [piexlmax](https://github.com/piexlmax)
//@function: ClearCasbin
//@description: 清除匹配的权限
//@param: v int, p ...string
//@return: bool

func (casbinService *CasbinService) ClearCasbin(v int, p ...string) bool {
	e := casbinService.Casbin()
	success, _ := e.RemoveFilteredPolicy(v, p...)
	return success
}

//@author: [piexlmax](https://github.com/piexlmax)
//@function: Casbin
//@description: 持久化到数据库  引入自定义规则
//@return: *casbin.Enforcer

var (
	syncedEnforcer *casbin.SyncedEnforcer
	once           sync.Once
	// ★★★ T32：初始化失败必须被**记住** ——
	//   原实现两处都用 `_` 吞掉（`a, _ :=` / `syncedEnforcer, _ =`）⇒ 失败时
	//   `syncedEnforcer` 留 **nil** ⇒ 之后**每一个** casbin 保护请求都在 `LoadPolicy()` 上
	//   **panic**（客户端只看到连接被重置／500，**不是清晰的启动错误**），
	//   且 `sync.Once` 令该失败**不重试**。
	initErr error
)

func (casbinService *CasbinService) Casbin() *casbin.SyncedEnforcer {
	once.Do(func() {
		var a *gormadapter.Adapter
		a, initErr = gormadapter.NewAdapterByDB(global.GVA_DB)
		if initErr != nil {
			return
		}
		syncedEnforcer, initErr = casbin.NewSyncedEnforcer(global.GVA_CONFIG.Casbin.ModelPath, a)
	})
	if syncedEnforcer == nil {
		// ★ T32：**取不到就不得解引用** —— 原实现在此必然 panic（nil.LoadPolicy()）。
		return nil
	}
	_ = syncedEnforcer.LoadPolicy()
	return syncedEnforcer
}

// Init ★★★ T32：供**启动期**调用一次；失败必须**响亮**（由调用方 `global.GVA_LOG.Fatal`）。
//
//	★ 报错**必须带 `model-path` 现值与 `os.Getwd()`** —— 因为 `model-path` 是 **cwd 相对路径**
//	  （`./resource/rbac_model.conf`）⇒ 运行目录里没有 `resource/` 时它必然失败；
//	  不带这两个值，这个 pitfall 重现时**还是看不出**"是 cwd 的问题"。
//	★ **不改变 `Casbin()` 的签名** —— 那 4 个调用方（`UpdateCasbin`/`GetPolicyPathByAuthorityId`/
//	  `ClearCasbin` 等）一律不动。
func (casbinService *CasbinService) Init() error {
	_ = casbinService.Casbin()
	if initErr == nil {
		return nil
	}
	wd, _ := os.Getwd()
	return fmt.Errorf("casbin 初始化失败：model-path=%q（★ 相对 **cwd**；实际 cwd=%q）⇒ %w",
		global.GVA_CONFIG.Casbin.ModelPath, wd, initErr)
}
