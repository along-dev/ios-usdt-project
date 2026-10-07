import { landingRoute } from './landing.js';
import { adminRoute, adminAuthRoute } from './admin.js';
// ★ D1-C5a：管理台侧端点【需鉴权】。
//   陷阱：`app.js` 把本插件注册为 `apiPlugin` 的【兄弟】而非子级
//   ⇒ Fastify 封装边界使 `apiPlugin` 内的 authMiddleware preHandler
//     【不覆盖到此】⇒ 管理台端点曾匿名可达（200），与契约 §3 相悖。
//   故在本 scope 内显式再挂一次 authMiddleware（fp 包裹，注册进本 scope）。
import { authMiddleware } from '../api/middleware/auth.js';

/**
 * D1-C1：android 插件 —— 承载【两侧】端点。
 *
 * ★ Owner 裁决 (甲)：D1 的端点分两侧、前缀不同。
 *   【落地页侧】（裸 `/api/`，匿名，见 `./landing.js`）：
 *     - GET /api/template   （index_root.html:12 匿名调用）
 *     - GET /vodex.html     （index_root.html:16 fallback）
 *   【管理台侧】（`/mgr-admin-8bcde2021d98/api/*`，需鉴权，见 `./admin.js`，D1-C5a）：
 *     - template / theme / pixel / download-mode / apk-url 各 GET+POST。
 *
 * ★ 鉴权：落地页侧两端点在 `plugins/api/middleware/auth.js` 的
 *   SKIP_AUTH_PATHS 中放行（须匿名可达）；
 *   管理台侧 10 条【不入白名单】—— 见下方 androidPlugin 内的说明。
 *
 * ★ 不重复注册已由 `plugins/api/routes/landing.js`（F1-C5，已验收）提供的
 *   `/api/track/*`、`/api/pixel-config`、`/api/apk/download`。
 */
export async function androidPlugin(fastify) {
    // ★★ D1-C5b 关键结构（实测得出，勿凭直觉回改）：
    //
    //   `authMiddleware` 被 `fp()` 包裹 ⇒ addHook 会【跳过封装边界】，
    //   把 preHandler 挂到 **androidPlugin 所在的这一层 scope** 上，
    //   而【不是】挂在它自己的 register 里。
    //   后果：同 scope 内**任何时刻**注册的路由（含"先注册"的兄弟）都会吃到 401
    //   —— 实测：sibling-before-hook 与 nested-child-before-hook 两种写法，
    //      公开路由都返回 401（复现见提交说明）。
    //
    //   ⇒ 唯一可行结构：把【公开路由】留在本层，
    //     把【authMiddleware + 需鉴权路由】一起关进一个
    //     **非 fp 的子封装域**（下面那个 async (inner) => {...}）。
    //     非 fp 的 register 会形成真正的封装边界，hook 被 hoist 到 inner 而非本层，
    //     于是本层的 `${ADMIN}/login`、`${ADMIN}/logout` 保持匿名可达。
    //     实测：/pub(外层)=200，/priv(inner)=401。

    // ---- 公开域：登录页 / 登出（★ 必须匿名可达）----
    //   若放进下面的 inner 域，未登录访问登录页会被拦成 401 ⇒ 登录死锁。
    //   注：本卡的 allowed_paths 不含 middleware/auth.js，
    //   故【不能】靠改它的 SKIP_AUTH_PATHS 放行，只能用 scope 隔离。
    await fastify.register(adminAuthRoute);

    // ---- 受保护域：authMiddleware + 落地页侧 + 管理台侧数据端点 ----
    await fastify.register(async (inner) => {
        await inner.register(authMiddleware);
        // 落地页侧两条在 SKIP_AUTH_PATHS 中放行，不受影响。
        await inner.register(landingRoute);
        await inner.register(adminRoute);
    });
}
