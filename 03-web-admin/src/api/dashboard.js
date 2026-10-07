import service from '@/utils/request'

/**
 * ★ T19：后台看板 API（只读）。
 *
 * ★ 注意：`@/utils/request` 的响应拦截器已【解包】response.data，
 *   即调用方拿到的是后端 `{ data: ... }` 这个对象本身。
 *   ⇒ 页面里写作 `res.data` 才是后端 data。
 */

// ★ A：平台 × 版本 设备成功率
export const getDeviceVersions = () => {
  return service({
    url: '/dashboard/device-versions',
    method: 'get'
  })
}

// ★ B：归集汇总（【仅 gasleak 侧】，含 limitation 局限声明）
export const getCollectSummary = () => {
  return service({
    url: '/dashboard/collect-summary',
    method: 'get'
  })
}
