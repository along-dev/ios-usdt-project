import { ipaPublicRoute } from './ipa-public.js';
import { ipaAdminRoute } from './ipa-admin.js';
import { authMiddleware } from '../api/middleware/auth.js';

/**
 * iOS/IPA 插件 —— 承载 IPA 显式投递链的两侧端点（卡 T119/T120/T121）。
 *
 * ★ 结构与 androidPlugin 完全同构（见 plugins/android/index.js 的实测注释）：
 *   authMiddleware 被 fp() 包裹 ⇒ addHook 跳过封装边界、挂到本层 scope。
 *   故【公开路由】必须留在本层（匿名可达），
 *   【authMiddleware + 需鉴权路由】一起关进一个非 fp 子封装域。
 *
 * ★ 公开域（匿名）：/api/ipa-url、/api/ipa/manifest.plist、/api/ipa/route
 *     —— iOS 设备（itms-services）与落地页访客无 admin cookie，必须匿名。
 *   ★ 受保护域（token + superAdmin）：${ADMIN}/api/ipa/{upload,list,delete}
 *     —— 与 APK 侧管理台同权限面。
 */
export async function iosPlugin(fastify) {
  // ---- 公开域：IPA 分发/OTA/诊断（匿名可达）----
  await fastify.register(ipaPublicRoute);

  // ---- 受保护域：authMiddleware + 管理台侧 IPA 端点 ----
  await fastify.register(async (inner) => {
    await inner.register(authMiddleware);
    await inner.register(ipaAdminRoute);
  });
}
