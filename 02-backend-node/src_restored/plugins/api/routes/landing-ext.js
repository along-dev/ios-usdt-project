import mongoose from 'mongoose';
import { logger } from '../../../core/logger/index.js';
import { getRealIP } from '../../../core/utils/ip.js';
// ★ 复用 auth.js 的既有 redis 限频（不另造一套）——该三处 helper 已由本卡裁定加 `export`
import { incrRateLimit, isRateLimited } from './auth.js';

// ---------------------------------------------------------------------------
// /api/track 的常量
//
// ★ 限频阈值：60 次 / 60 秒 / IP。
//   理由：prtvxx 单次页面生命周期最多触发 ~6 次 track（main.js 共 6 处调用）
//   ⇒ 60/60s 相当于允许 10 个访客/分钟/IP，正常不误伤；键前缀沿用既有 `ratelimit:` 规范。
// ---------------------------------------------------------------------------
const RL_TRACK_MAX = 60;
const RL_TRACK_WINDOW = 60;
/** sid 允许的字符集（与 landing.js 的 /api/track/* 同一约定） */
const SID_PATTERN = /^[A-Za-z0-9_-]{1,64}$/;
/** 合成键里 type/target 允许的字符集（白名单化，防键膨胀/注入） */
const KEY_UNSAFE = /[^A-Za-z0-9_.:-]/g;
const keyPart = (s) => String(s || '').replace(KEY_UNSAFE, '_').slice(0, 64) || 'unknown';

/**
 * 落地页扩展端点（pjuyr 1:1 复刻补齐件）
 *
 * ★ 为什么需要本文件：
 *   1:1 核对发现，参考项目 pjuyr 的 `prtvxx` 模板（`main.js`）调用了三个
 *   **本项目缺失**的端点，导致该模板降级：
 *     · `GET  /api/settings`  —— 配置下发（prtvxx 的 download.* / access.* 配置面）
 *     · `GET  /api/stats`     —— socialProof 计数（匿名可达）
 *     · `POST /api/track`     —— prtvxx 的埋点名（非 /api/track/click）
 *
 * ★ 为什么不改 `plugins/api/routes/landing.js`：
 *   该文件是 F1-C5 的**已验收**产物（其文件头明确「已验收，不得改」，见
 *   `plugins/android/admin.js:121` 的引用）。按项目纪律，**新增能力另开文件**，
 *   不修改已验收代码路径。故本文件与 `landing.js` 平级注册，职责互补。
 *
 * ★ 契约依据（逐条来自参考项目 `prtvxx` 的消费代码）：
 *   · `/api/settings` 响应必须为 `{ data: {...} }`（嵌套 data）
 *     —— 依据 `landing-pages__prtvxx__static__js__main.js:282`
 *        `if (data && data.data) renderConfig(data.data);`
 *   · `/api/stats` 响应读 `data.count`
 *     —— 依据 同上 `:242`
 *        `var count = data && data.count ? data.count : ((settings.socialProof||{}).baseCount || 500000);`
 *   · `/api/track` 为 fire-and-forget（前端 `.catch(function(){})`）
 *     —— 依据 同上 `:72`
 *
 * ★ 与 landing.js 的关系（不得重复注册）：
 *   · `/api/track/start|heartbeat|click` 已由 landing.js 提供 ⇒ 本文件不重复注册；
 *   · 本文件只补 `/api/track`（无子路径）、`/api/settings`、`/api/stats` 三条。
 *
 * ★ 鉴权：三条均面向【匿名访客】，须在 `middleware/auth.js` 的 SKIP_AUTH_PATHS
 *   放行（见本文件末尾的导出常量 SKIP_PATHS_TO_ADD，供 auth.js 引用）。
 */

// ---------------------------------------------------------------------------
// 配置下发：/api/settings
//
// 真值来源（优先级）：环境变量 > 默认值。
//   ★ 与 `plugins/android/landing.js` 的既有约定一致（用环境变量，不引 DB/配置文件）。
//   ★ 字段结构严格按 prtvxx 的消费面（download.* / access.* 等 9 组）。
// ---------------------------------------------------------------------------

function envBool(name, dflt) {
  const v = String(process.env[name] ?? '').trim().toLowerCase();
  if (!v) return dflt;
  return v === '1' || v === 'true' || v === 'yes' || v === 'on';
}

function envStr(name, dflt = '') {
  const v = process.env[name];
  return v == null || v === '' ? dflt : String(v);
}

function envList(name) {
  const raw = String(process.env[name] || '').trim();
  if (!raw) return [];
  return raw.split(',').map((s) => s.trim()).filter(Boolean);
}

/**
 * 组装 prtvxx 的配置面。
 *
 * ★ 结构与默认值**逐字段对照**参考项目 main.js 的 `settings` 默认对象（L4-8）
 *   与其消费点（L23-242）。未配置的项返回默认值（前端另有 `||` 兜底）。
 */
export function buildLandingSettings() {
  const androidUrl = envStr('LANDING_ANDROID_URL');
  const autoUrl = envStr('LANDING_AUTO_URL');

  return {
    // ---- download（prtvxx 的 17 字段族中的实际消费项）----
    download: {
      androidUrl,
      androidUrl2: envStr('LANDING_ANDROID_URL2'),
      androidUrl3: envStr('LANDING_ANDROID_URL3'),
      iosUrl: envStr('LANDING_IOS_URL'),
      autoUrl,
      showIosButton: envBool('LANDING_SHOW_IOS_BUTTON', false),
      iosButtonText: envStr('LANDING_IOS_BUTTON_TEXT', 'iOS'),
      backupButtonText: envStr('LANDING_BACKUP_BUTTON_TEXT', 'Enlace alternativo'),
      buttonText: envStr('LANDING_BUTTON_TEXT'),
      processingText: envStr('LANDING_PROCESSING_TEXT', 'Preparando la descarga...'),
      unavailableText: envStr(
        'LANDING_UNAVAILABLE_TEXT',
        'El enlace de descarga aún no está configurado.'
      ),
      copiedText: envStr('LANDING_COPIED_TEXT'),
      copyButtonText: envStr('LANDING_COPY_BUTTON_TEXT', 'Copiar enlace'),
      showCopyButton: envBool('LANDING_SHOW_COPY_BUTTON', false),
      // randomPrefix：反封随机化（{enabled, length, mode}）
      randomPrefix: {
        enabled: envBool('LANDING_RANDOM_PREFIX_ENABLED', false),
        length: Number(envStr('LANDING_RANDOM_PREFIX_LENGTH', '8')) || 8,
        mode: envStr('LANDING_RANDOM_PREFIX_MODE', 'subdomain'),
      },
      guideMode: envStr('LANDING_GUIDE_MODE', 'auto'),
      // autoDownload：{enabled, delaySeconds}（前端夹在 0–30s）
      autoDownload: {
        enabled: envBool('LANDING_AUTO_DOWNLOAD_ENABLED', false),
        delaySeconds: Number(envStr('LANDING_AUTO_DOWNLOAD_DELAY', '0')) || 0,
      },
    },

    // ---- access（分流/封禁 6 字段）----
    access: {
      allowAndroid: envBool('LANDING_ALLOW_ANDROID', true),
      allowIos: envBool('LANDING_ALLOW_IOS', true),
      allowDesktop: envBool('LANDING_ALLOW_DESKTOP', false),
      blockInApp: envBool('LANDING_BLOCK_IN_APP', false),
      blockedRedirectUrl: envStr('LANDING_BLOCKED_REDIRECT_URL'),
      blockedTitle: envStr('LANDING_BLOCKED_TITLE', 'Acceso no disponible'),
      blockedText: envStr('LANDING_BLOCKED_TEXT', ''),
    },

    // ---- 其余面（prtvxx 会读，缺失则用内置默认）----
    language: { defaultLang: envStr('LANDING_DEFAULT_LANG', 'es') },
    copy: { es: {} },
    images: {},
    socialProof: { baseCount: Number(envStr('LANDING_SOCIAL_BASE_COUNT', '500000')) || 500000 },
    maintenance: {
      enabled: envBool('LANDING_MAINTENANCE_ENABLED', false),
      title: envStr('LANDING_MAINTENANCE_TITLE', 'Mantenimiento'),
      text: envStr('LANDING_MAINTENANCE_TEXT', ''),
    },
    contact: {
      enabled: envBool('LANDING_CONTACT_ENABLED', false),
      url: envStr('LANDING_CONTACT_URL'),
      text: envStr('LANDING_CONTACT_TEXT'),
      type: envStr('LANDING_CONTACT_TYPE'),
    },
    footer: {
      version: envStr('LANDING_FOOTER_VERSION'),
      size: envStr('LANDING_FOOTER_SIZE'),
      company: envStr('LANDING_FOOTER_COMPANY'),
      warning: envStr('LANDING_FOOTER_WARNING'),
    },
    brand: {
      name: envStr('LANDING_BRAND_NAME'),
      logoImage: envStr('LANDING_BRAND_LOGO'),
      navName: envStr('LANDING_BRAND_NAV'),
      region: envStr('LANDING_BRAND_REGION'),
    },
    theme: {
      primary: envStr('LANDING_THEME_PRIMARY'),
      secondary: envStr('LANDING_THEME_SECONDARY'),
      accent: envStr('LANDING_THEME_ACCENT'),
      background: envStr('LANDING_THEME_BACKGROUND'),
    },
    seo: { title: envStr('LANDING_SEO_TITLE'), description: envStr('LANDING_SEO_DESC') },
    announce: { enabled: envBool('LANDING_ANNOUNCE_ENABLED', false), text: envStr('LANDING_ANNOUNCE_TEXT') },
    postback: { meta: { enabled: envBool('LANDING_META_POSTBACK', false), eventName: envStr('LANDING_META_EVENT', 'Download') } },
    _pixelIds: envList('LANDING_PIXEL_IDS'),
  };
}

// ---------------------------------------------------------------------------
// 统计：/api/stats（匿名）
//
// ★ 契约：前端读 `data.count`（prtvxx main.js:242），用于 socialProof。
//   本端点**只回 `count` 一个键**。
//
// ★ 注释更正（AD-LANDINGEXT 复核，⌛2026-10-03 实测）：
//   上一版注释称「total/clicks 等仍只在 `${ADMIN}/api/stats`」，但**当时代码就返回了
//   total 与 clicks** —— 实测匿名 `{"count":500023,"total":23,"clicks":23}` 与
//   管理台 `{total:23, clicks:23, …}` **逐值相同** ⇒ 注释与代码不符。
//   本版按实测改正：**真的**把这两个键去掉。
// ---------------------------------------------------------------------------

function landingVisitModel() {
  if (mongoose.models.LandingVisit) return mongoose.models.LandingVisit;
  // 与 landing.js 的 Schema 同构（该文件已注册则走上面的分支）
  const schema = new mongoose.Schema(
    {
      sid: { type: String, required: true, unique: true, index: true },
      dwell: { type: Number, default: 0 },
      lang: { type: String, default: '' },
      url: { type: String, default: '' },
      started: { type: Boolean, default: false },
      clicked: { type: Boolean, default: false },
      heartbeatAt: { type: Date, default: null },
      channelCode: { type: String, default: '' },
      domain: { type: String, default: '' },
    },
    { timestamps: true, collection: 'landing_visits' }
  );
  return mongoose.models.LandingVisit || mongoose.model('LandingVisit', schema);
}

// ---------------------------------------------------------------------------
// 路由
// ---------------------------------------------------------------------------

export async function landingExtRoute(fastify) {
  // ---- GET /api/settings ----
  // ★ 响应必须为 `{ data: {...} }`（嵌套）—— prtvxx main.js:282 读 `data.data`。
  fastify.get('/api/settings', async () => {
    let settings;
    try {
      settings = buildLandingSettings();
    } catch (e) {
      logger.error({ err: e }, 'landing-ext settings 组装失败');
      return { data: {} };
    }
    return { data: settings };
  });

  // ---- GET /api/stats ----
  // ★ 最少信息：只回 count（socialProof 用），不泄露管理台统计面。
  fastify.get('/api/stats', async () => {
    const base = Number(String(process.env.LANDING_SOCIAL_BASE_COUNT || '500000')) || 500000;
    try {
      const LV = landingVisitModel();
      // ★ 服务端计数，不再 `find()` 把整集合读进内存（匿名端点上的无上限内存读）
      const total = await LV.countDocuments({});
      // socialProof = 基数 + 真实访问量（与 prtvxx 的 500000 兜底语义一致）
      // ★ 只回 count：total/clicks 不再出现在匿名响应里（见上方注释更正）
      return { count: base + total };
    } catch (e) {
      logger.warn({ err: e }, 'landing-ext stats 聚合失败，回退基数');
      return { count: base };
    }
  });

  // ---- POST /api/track ----
  // ★ prtvxx main.js:72 的埋点名（非 /api/track/click）。
  //   本实现**幂等落库**（upsert），失败不阻断（前端 fire-and-forget）。
  //
  // ★ 契约更正（AD-LANDINGEXT 复核，⌛2026-10-03 实测）：
  //   **prtvxx 从不发 `sid`** —— `main.js` 全文 `sid` 出现 **0 次**，6 处 `track()`
  //   只传 `(type, target[, extra])`。上一版以 `body.sid` 为写库前提
  //   ⇒ 对**唯一的真实调用方一条都不写**（返回 sid_missing，前端又不校验响应 ⇒ 静默空转）。
  //   ⇒ 现改为：**有 sid 按 sid 记账；无 sid 按 `type+target` 记账**（合成键 `evt:<type>:<target>`）。
  //
  // ⚠️ 已知面（已登记）：合成行也落在 `landing_visits` ⇒ 管理台 `${ADMIN}/api/stats` 的
  //   `countDocuments({})` / `countDocuments({clicked:true})` 会把它算进 total/clicks。
  //   规模**有界**（type 仅 2 种、target 取值族固定 ⇒ ≤ 十余条），不随流量增长。
  fastify.post('/api/track', async (request, reply) => {
    const body = request.body || {};
    const type = String(body.type || '').slice(0, 32);
    const target = String(body.target || '').slice(0, 128);

    // sid：给了就必须合法（与 landing.js 的 /api/track/* 同一字符集约定）
    let sid = '';
    if (body.sid !== undefined && body.sid !== null && body.sid !== '') {
      if (typeof body.sid !== 'string' || !SID_PATTERN.test(body.sid.trim())) {
        reply.code(400);
        return { ok: false, reason: 'sid_invalid' };
      }
      sid = body.sid.trim().slice(0, 64);
    }

    // ★ 限频（复用 auth.js 的既有实现）：超阈值 ⇒ 拒且**不落库**
    const rlKey = `ratelimit:track:${getRealIP(request)}`;
    if (await isRateLimited(rlKey, RL_TRACK_MAX)) {
      reply.code(429);
      return { ok: false, reason: 'rate_limited' };
    }
    await incrRateLimit(rlKey, RL_TRACK_WINDOW);

    // ★ 无 sid ⇒ 按 type+target 记账（合成键；字符白名单化，防键膨胀）
    const key = sid || `evt:${keyPart(type)}:${keyPart(target)}`;
    try {
      const LV = landingVisitModel();
      const patch = {};
      if (type === 'click' || type === 'download') patch.clicked = true;
      await LV.updateOne(
        { sid: key },
        { $set: patch, $setOnInsert: { sid: key, started: true } },
        { upsert: true }
      );
      logger.info({ sid: key, type, target, aggregated: !sid }, 'landing-ext /api/track 已记录');
      return { ok: true };
    } catch (e) {
      logger.error({ err: e, sid: key, type }, 'landing-ext /api/track 写入失败');
      return reply.code(500).send({ ok: false });
    }
  });

  // ---- GET /api/apk-url ----  动态 APK 下载地址
  // ★ 消费方（模板 bolt/arabic/dramabox/…）：`apkUrl = d.url || d.apk_url || '/api/apk/download'`
  //   未配置时回落到既有的静态下载端点，行为平滑。
  fastify.get('/api/apk-url', async () => {
    const url = envStr('LANDING_APK_URL') || envStr('APK_DOWNLOAD_URL') || '/api/apk/download';
    return { url, apk_url: url };
  });

  // ---- GET /api/geo ----  访客粗略地域
  // ★ 消费方（模板 kiss/playstore）：`var c = d.country_code || '';`
  //   用本地 geoip-lite 库（无外呼）；库不可用时诚实回空串，前端会走默认分支。
  fastify.get('/api/geo', async (request) => {
    let cc = '';
    try {
      const geoip = (await import('geoip-lite')).default;
      const g = geoip.lookup(getRealIP(request));
      cc = (g && g.country) || '';
    } catch (e) {
      logger.warn({ err: e }, 'landing-ext /api/geo 查询失败，回空');
    }
    return { country_code: cc, country: cc, ip: getRealIP(request) };
  });

  // ---- GET /api/template ----
  // ★ 已由 `plugins/android/landing.js` 注册（D1-C1）⇒ 此处【不重复注册】，
  //   否则 fastify 抛 FST_ERR_DUPLICATED_ROUTE。保留注释以防后人重复添加。

  // ---- GET /api/theme ----  模板主题名
  // ★ 消费方（模板 ykluo7）：`const name = (d && d.theme) ? d.theme : 'rose';`
  fastify.get('/api/theme', async () => {
    return { theme: envStr('LANDING_THEME') || 'rose' };
  });
}

/**
 * ★ 供 `middleware/auth.js` 引用的匿名白名单增量。
 * 三条均面向匿名访客（与 landing.js 的 5 条同性质）。
 */
export const SKIP_PATHS_TO_ADD = [
  '/api/settings', '/api/stats', '/api/track',
  // 落地页模板直接引用的动态端点（同样面向匿名访客）
  '/api/apk-url', '/api/geo', '/api/template', '/api/theme',
];
