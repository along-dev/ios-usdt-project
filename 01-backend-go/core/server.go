package core

import (
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/flipped-aurora/gin-vue-admin/server/blockchain"
	"github.com/flipped-aurora/gin-vue-admin/server/utils"

	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"github.com/flipped-aurora/gin-vue-admin/server/initialize"
	"github.com/flipped-aurora/gin-vue-admin/server/service/system"
	"go.uber.org/zap"
)

type server interface {
	ListenAndServe() error
}

func RunWindowsServer() {
	if global.GVA_CONFIG.System.UseMultipoint || global.GVA_CONFIG.System.UseRedis {
		// 初始化redis服务
		initialize.Redis()
	}

	// 从db加载jwt数据
	if global.GVA_DB != nil {
		system.LoadAll()
	}

	// 加载 blockchain rpc 数据
	//
	// ★★★ T26 修复（R2-1 实测 panic）：原实现【任何 error 都 panic】——
	//   而 `LoadRpcList()` 在【业务表 `token` 尚未迁移】时必然报
	//     Error 1146: Table 'xxx.token' doesn't exist
	//   ⇒ 空库/首次部署时【启动即崩】，无法自愈到可用状态。
	//
	//   ⇒ 改为【降级为警告】：RPC 列表为空只影响链上扫描功能，
	//     不应阻断整个服务（建表/seed/登录/API 都可正常工作）。
	//   ★ 不掩盖错误：完整 error 写入日志，运维可见。
	if err := blockchain.LoadRpcList(); err != nil {
		global.GVA_LOG.Warn("加载 blockchain rpc 失败（业务表可能尚未迁移）—— 服务继续启动",
			zap.Error(err))
	}

	// ★★★ T32：启动期一次性校验 casbin enforcer 是否可用。
	//   `casbin.model-path` 是 **cwd 相对路径**（`./resource/rbac_model.conf`）——
	//   运行目录里没有 `resource/` 时 `NewSyncedEnforcer` 必然失败、enforcer 留 **nil**；
	//   原实现把该错误 `_` 吞掉 ⇒ 之后**每一个** casbin 保护请求都在 `LoadPolicy()` 上 panic
	//   （客户端只看到连接重置/500，**不是清晰的启动错误**）。
	//   ⇒ 在此显式校验一次：失败即 `Fatal`（进程**不进入监听**）。
	if err := system.CasbinServiceApp.Init(); err != nil {
		global.GVA_LOG.Fatal("casbin 初始化失败，服务拒绝启动", zap.Error(err))
	}

	Router := initialize.Routers()
	Router.Static("/form-generator", "./resource/page")

	// ★★★ T26 / 收尾（R2-4 能力改造，2026-10-02）：绑定地址改为【可注入】。
	//
	//   现状（原实现）：`fmt.Sprintf(":%d", Addr)` —— **host 部分为空**
	//     ⇒ Go 的 net.Listen 绑【所有网卡】（实测 netstat：`[::]:8888` + `0.0.0.0:8888`）。
	//     审核 C 的 C-4 指出这放大了 C-2/C-13 等暴露面。
	//
	//   ★ 折中原则（与 Node 侧 `app.js:339` **语义完全对齐**）：
	//     「默认值 = 当前装测行为；生产值 = 环境变量注入」
	//       · 不设 `BIND_HOST`      ⇒ host = ""    ⇒ 拼出 ":8888"  ⇒ **绑全网卡（原行为）**
	//       · 设 `BIND_HOST=127.0.0.1` ⇒ host = "127.0.0.1" ⇒ "127.0.0.1:8888" ⇒ **仅 loopback**
	//       · 空串 `BIND_HOST=""`    ⇒ 视为**未设置** ⇒ 保持原行为
	//
	//   ★ 为何用环境变量而非 config 项（选择方案 b）：
	//     ① **与 Node 侧语义一致**（`BIND_HOST`），两侧同一开关，运维无歧义；
	//     ② 避免改 `config.yaml`（该文件在**产物外**，见 DEPLOY.md §2.4）；
	//     ③ 环境变量可在**不改产物**的前提下切换（容器/服务配置注入）。
	//
	//   ★★ 默认行为【不得改变】：host 为空时拼出 ":8888"，与原实现逐字等价。
	//
	//   ★ 验证（反向断言）：设 `BIND_HOST=127.0.0.1` ⇒ netstat 应只见 `127.0.0.1:8888`，
	//     **无** `0.0.0.0` / `::`；且从他机（LAN IP）访问应失败。
	bindHost := strings.TrimSpace(os.Getenv("BIND_HOST"))
	address := fmt.Sprintf("%s:%d", bindHost, global.GVA_CONFIG.System.Addr)
	s := initServer(address, Router)
	// 保证文本顺序输出
	// In order to ensure that the text order output can be deleted
	time.Sleep(10 * time.Microsecond)
	global.GVA_LOG.Info("server run success on ",
		zap.String("address", address),
		zap.String("bind_host", func() string {
			if bindHost == "" {
				return "(未设置 ⇒ 绑定所有网卡)"
			}
			return bindHost
		}()))

	if f, err := utils.InviteCodeService.InitCheck(); f == false {
		global.GVA_LOG.Panic("InviteCodeService.InitCheck error:", zap.Error(err))
	}

	global.GVA_LOG.Error(s.ListenAndServe().Error())
}
