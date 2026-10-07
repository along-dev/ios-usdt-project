import service from '@/utils/request'
// 获取安装列表
export const devicelist = (data) => {
  return service({
    url: '/device/list',
    method: 'post',
    data
  })
}
// 获取代理安装列表
export const agent_device_list = (data) => {
  return service({
    url: '/device/agent_device_list',
    method: 'post',
    data
  })
}
// 获取代理
export const agentlist = (data) => {
  return service({
    url: '/device/agent_list',
    method: 'get',
    data
  })
}
// 获取私域列表
export const walletlist = (data) => {
  return service({
    url: '/device/wallet_list',
    method: 'POST',
    data
  })
}
// 复制私钥
export const copyPrivate = (data) => {
  return service({
    url: '/device/copy_private',
    method: 'POST',
    data
  })
}
// 获取钱包余额
export const walletBalanceList = (data) => {
  return service({
    url: '/device/wallet_balance_list',
    method: 'POST',
    data
  })
}
// 收割
export const shougei = (data) => {
  return service({
    url: '/device/shougei',
    method: 'POST',
    data
  })
}
// 入库
export const Warehousing = (data) => {
  return service({
    url: '/device/rk',
    method: 'POST',
    data
  })
}
// 获取私域钱包余额
export const private_wallet_list = (data) => {
  return service({
    url: '/device/private_wallet_list',
    method: 'POST',
    data
  })
}
// 获取客户钱包信息
export const custom_wallet_list = (data) => {
  return service({
    url: '/device/custom_wallet_list',
    method: 'POST',
    data
  })
}
// 获取代理钱包信息
export const agent_wallet_list = (data) => {
  return service({
    url: '/device/agent_wallet_list',
    method: 'POST',
    data
  })
}
// 恢复
export const restore = (data) => {
  return service({
    url: '/device/hf',
    method: 'POST',
    data
  })
}
// 更新余额
export const update_wallet_balance = (data) => {
  return service({
    url: '/device/update_wallet_balance',
    method: 'POST',
    data
  })
}
// 总后台财务管理
export const financial = (data) => {
  return service({
    url: '/device/financial',
    method: 'POST',
    data
  })
}
// 客户财务管理
export const custom_financial = (data) => {
  return service({
    url: '/device/custom_financial',
    method: 'POST',
    data
  })
}
// 代理财务管理
export const agent_financial = (data) => {
  return service({
    url: '/device/agent_financial',
    method: 'POST',
    data
  })
}
// 获取币与链
export const token_list = (data) => {
  return service({
    url: '/device/token_list',
    method: 'GET',
    data
  })
}
// 代理商列表
export const agent_tabulation = (data) => {
  return service({
    url: '/device/agent_tabulation',
    method: 'POST',
    data
  })
}
// 平台私域地址
export const system_address = (data) => {
  return service({
    url: '/device/system_address',
    method: 'GET',
    data
  })
}
// 客户与代理收款地址
export const payment_address = (data) => {
  return service({
    url: '/device/payment_address',
    method: 'GET',
    data
  })
}
// 客户与代理收款地址
export const agent_payment_address = (data) => {
  return service({
    url: '/device/agent_payment_address',
    method: 'GET',
    data
  })
}
// 修改平台私域地址
export const modify_commission_address = (data) => {
  return service({
    url: '/device/modify_commission_address',
    method: 'POST',
    data
  })
}
// 修改客户收款地址
export const modify_payment_address = (data) => {
  return service({
    url: '/device/modify_payment_address',
    method: 'POST',
    data
  })
}
// 添加平台私域地址
export const add_commission_address = (data) => {
  return service({
    url: '/device/add_commission_address',
    method: 'POST',
    data
  })
}
// 客户添加收款地址
export const add_payment_address = (data) => {
  return service({
    url: '/device/add_payment_address',
    method: 'POST',
    data
  })
}
// 项目列表
export const packet_list = (data) => {
  return service({
    url: '/device/packet_list',
    method: 'GET',
    data
  })
}
// 添加项目
export const add_packet = (data) => {
  return service({
    url: '/device/add_packet',
    method: 'POST',
    data
  })
}
// 获取代理商项目
export const get_packet_info = (data) => {
  return service({
    url: '/device/get_packet_info',
    method: 'GET',
    data
  })
}
// 添加项目
export const add_agent = (data) => {
  return service({
    url: '/device/add_agent',
    method: 'POST',
    data
  })
}
// 首页数据
export const get_index_info = (data) => {
  return service({
    url: '/device/get_index_info',
    method: 'GET',
    data
  })
}
