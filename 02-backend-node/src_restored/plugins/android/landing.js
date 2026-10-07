import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { logger } from '../../core/logger/index.js';
import { Channel } from '../../core/db/models/index.js';

/**
 * 落地页侧端点（卡 D1-C1）。
 *
 * ★ 前端硬契约（三级验证 · 真实源码）：
 *   `04-landing/runtime/index_root.html:12-16`:
 *     fetch('/api/template').then(r=>r.json()).then(d=>{
 *       var t = d.template || 'vodex';
 *       window.location.replace('/'+t+'.html');
 *     }).catch(function(){window.location.replace('/vodex.html');});
 *   ⇒ `GET /api/template` 必须返回 **JSON `{ template: "<name>" }`**，
 *     ★ 不是 302（卡里早前的 302 是错的，已更正）。
 *   ⇒ `GET /vodex.html` 是同一前端的 **catch fallback 目标**。
 *
 * ★ 鉴权：两个端点均面向【匿名访客】——
 *   必须在 `plugins/api/middleware/auth.js` 的 SKIP_AUTH_PATHS 中放行，
 *   否则全局 preHandler 会把它们全部拦成 401（"路由写了也等于没写"）。
 *   ★ `/vodex.html` **不是 `/api/` 前缀**，但中间件按 `request.url` 整路径比较
 *     ⇒ 同样会被 401（陷阱 2），故一并入白名单。
 *
 * ★ 模板名取值集合（index_root.html:14 列的 40 个）：
 *   前端用它拼路径 `/${t}.html`，取值不在集合内会跳到不存在的页面。
 *   本实现只在集合内取值，并对环境变量做白名单校验（非法值回退默认）。
 *
 * ★ 不在本卡范围：管理台侧的 `${ADMIN}/api/template`（D1-C5）、
 *   `/api/theme`、`/api/pixel`、`/api/stats`；也不得在此重复注册
 *   `/api/track/*`、`/api/pixel-config`、`/api/apk/download`（已由 landing.js 提供）。
 */

// ---------------------------------------------------------------------------
// 模板名集合 —— ★ W-AD-05：以 `04-landing/templates/` 的**磁盘实况为准**（53 个）
//   ⌛2026-10-03 实测：磁盘 53 个 `.html`，而旧白名单只有 40 个
//   ⇒ 多出的 13 个（含**默认模板 vodex 本身**）会走到"不在集合内"的分支。
//   旧实现靠 `DEFAULT_TEMPLATE` 的副作用兜住 vodex（能跑但脆弱）；其余 12 个则
//   既不在白名单、也没有对应路由 ⇒ 真 404。本卡把集合补齐到磁盘实况。
// ---------------------------------------------------------------------------
export const KNOWN_TEMPLATES = [
  'apumex', 'arabic', 'bokepx', 'bolt', 'chatee', 'cosern', 'cosply', 'dptvlx',
  'dramabox', 'dramahub', 'elef', 'fizzio', 'gplayx', 'hztvlx', 'igniti', 'japapp',
  'kiss', 'kuaibo', 'kyssap', 'livesp', 'lovely', 'lustyl', 'meetic', 'minidr',
  'myloveday', 'nightm', 'nightp', 'noxxxt', 'paradx', 'phubxx', 'playstore', 'premhd',
  'promox', 'prtvxx', 'qiyoux', 'reelen', 'reelsh', 'reelshort', 'secure', 'shortv',
  'smartr', 'soccer', 'stkval', 'teleparty', 'ultrap', 'velocx', 'vidion', 'vodex',
  'xhamst', 'xvidep', 'xvides', 'ykluo7', 'zonaviva',
];

export const DEFAULT_TEMPLATE = 'vodex';

/**
 * 解析当前生效的落地页模板名。
 *
 * 存储方式：环境变量 `LANDING_TEMPLATE`，默认 `'vodex'`
 *   —— 与同文件族（landing.js）用 `LANDING_PIXEL_IDS` / `LANDING_APK_PATH`
 *      的既有约定一致，无需引入 DB/配置文件（见停靠点 1 的判断）。
 * ★ 取值须落在 KNOWN_TEMPLATES 内，否则回退默认：
 *   前端会拿返回值直接拼 `/${t}.html`，非法值 ⇒ 跳到不存在的页面。
 */
export function resolveTemplateName() {
  const raw = String(process.env.LANDING_TEMPLATE || '').trim();
  if (!raw) return DEFAULT_TEMPLATE;
  if (KNOWN_TEMPLATES.includes(raw)) return raw;
  logger.warn(
    { value: raw, fallback: DEFAULT_TEMPLATE },
    'LANDING_TEMPLATE 不在 index_root.html 的已知模板集合内，已回退默认值'
  );
  return DEFAULT_TEMPLATE;
}

/**
 * ★ W-AD-05：按【请求的 Host】解析生效模板（渠道绑定 → 环境变量 → 默认）。
 *
 * 解析键为什么是 Host：`/api/template` 面向【匿名访客】，请求里没有任何身份信息，
 * 而渠道模型自带 `primaryDomain` / `domains`（创建渠道时由 DGA 生成）——
 * 这是本进程内**唯一**能把一个请求关联到渠道的键。
 *
 * ★ 已知边界（如实声明，勿当成已完成）：`packet.landing_page`（Go / MariaDB 侧）
 *   **不参与**本解析 —— Node 无 MariaDB 客户端，Go 也未向 Node 暴露 packet 只读端点。
 *   故「改 `packet.landing_page` ⇒ 落地页实际切换」当前**不成立**，
 *   须先补一条 Node→Go 的 packet 只读通道（跨线事项）。
 */
export async function resolveLandingTemplate(request) {
  const host = String(request?.headers?.host || '').split(':')[0].trim().toLowerCase();
  if (host) {
    try {
      const channel = await Channel.findOne({ $or: [{ primaryDomain: host }, { domains: host }] });
      if (channel) {
        const bound = typeof channel.landingTemplate === 'string' ? channel.landingTemplate.trim() : '';
        if (bound && KNOWN_TEMPLATES.includes(bound))
          return bound;
        if (bound) {
          logger.warn(
            { host, channelCode: channel.code, value: bound, fallback: DEFAULT_TEMPLATE },
            '渠道绑定的落地页模板不在已知集合内，已回退默认值'
          );
        }
      }
    }
    catch (err) {
      logger.error({ err, host }, '按 Host 解析落地页模板失败，回退环境变量/默认值');
    }
  }
  return resolveTemplateName();
}

/**
 * 定位落地页模板目录（`<tpl>.html` 所在目录）。
 *
 * ★ 运行时 cwd = `02-backend-node`（见 app.js:265 及产物目录布局），
 *   而模板真实位于 `04-landing/templates/`。构建脚本
 *   `_integration/build_unified.ps1:686` 亦把 `pj/templates` → `<Target>/04-landing/templates`，
 *   即 `04-landing/templates/` 是【权威运行时路径】。
 *
 * 候选顺序（自本文件位置向上查找，不依赖 cwd，因此 cwd 变化也稳）：
 *   ① 环境变量 `LANDING_TEMPLATE_DIR`（显式覆盖）
 *   ② `<repo>/04-landing/templates`   ← 权威
 *   ③ `<cwd>/04-landing/templates`    ← 兼容从仓库根启动
 *   ④ `<cwd>/templates/landing`       ← 兼容模板被就地复制进产物的部署
 *
 * 返回 { dir, source }；全部不存在时 dir = null。
 */
export function resolveTemplateDir() {
  const here = path.dirname(fileURLToPath(import.meta.url));
  // here = <repo>/02-backend-node/src_restored/plugins/android
  const repoRoot = path.resolve(here, '..', '..', '..', '..');

  const candidates = [
    [String(process.env.LANDING_TEMPLATE_DIR || '').trim(), 'env:LANDING_TEMPLATE_DIR'],
    [path.join(repoRoot, '04-landing', 'templates'), `repo:${path.join(repoRoot, '04-landing', 'templates')}`],
    [path.join(process.cwd(), '04-landing', 'templates'), `cwd:${path.join(process.cwd(), '04-landing', 'templates')}`],
    [path.join(process.cwd(), 'templates', 'landing'), `cwd:${path.join(process.cwd(), 'templates', 'landing')}`],
  ];

  for (const [dir, source] of candidates) {
    if (dir && existsSync(dir)) return { dir, source };
  }
  return { dir: null, source: 'none' };
}

/**
 * 读取模板页内容。返回 { ok, dir, source, file, html } 或 { ok:false, reason, candidates }。
 * ★ 找不到就【如实】报错，绝不返回伪造的空页面（P-1：不许把"看起来通了"当"通了"）。
 */
export function loadTemplateHtml(name) {
  const { dir, source } = resolveTemplateDir();
  if (!dir) {
    return { ok: false, reason: 'template_dir_not_found', candidates: source };
  }
  const file = path.join(dir, `${name}.html`);
  if (!existsSync(file)) {
    return { ok: false, reason: 'template_file_not_found', dir, source, file };
  }
  try {
    const html = readFileSync(file, 'utf8');
    return { ok: true, dir, source, file, html };
  } catch (e) {
    return { ok: false, reason: 'template_read_failed', dir, source, file, err: String(e) };
  }
}

// ---------------------------------------------------------------------------
// 路由
// ---------------------------------------------------------------------------

export async function landingRoute(fastify) {
  // ---- GET /api/template ----
  // 前端 index_root.html:12 匿名调用；返回 JSON `{ template: "<name>" }`（★ 非 302）。
  // ★ W-AD-05：改为【Host 感知】—— 同一部署下不同渠道域名可给不同模板。
  fastify.get('/api/template', async (request) => {
    return { template: await resolveLandingTemplate(request) };
  });

  // ---- GET /:name.html ----
  // ★ W-AD-05：由字面量 `/vodex.html` 改为【参数 + 静态后缀】路由。
  //   ⌛2026-10-03 探针实测（Fastify 5 / find-my-way）：`/:name.html` 受支持；
  //   `/api/template` 仍由静态路由优先命中（不被遮蔽），`/login` 等单段路径不受影响，
  //   `/a/b.html`（多段）不匹配。旧写法只注册了 `/vodex.html` 一条字面路由
  //   ⇒ 其余模板名（如 `/japapp.html`）实测 **404**，与"白名单里有 40 个名字"自相矛盾。
  //   `/vodex.html` 仍是 index_root.html:16 的 catch fallback 目标，现由本路由承接。
  // ★ 名字必须落在白名单内，否则回退默认 —— 参数经 URL 解码后仍走白名单，
  //   故 `%2e%2e%2f` 之类的路径穿越会被挡下。
  fastify.get('/:name.html', async (request, reply) => {
    const raw = request.params?.name ?? '';
    const name = KNOWN_TEMPLATES.includes(raw) ? raw : DEFAULT_TEMPLATE;

    const res = loadTemplateHtml(name);
    if (!res.ok) {
      // 如实 500/404，并说明原因（不静默 200 空体）
      logger.error({ name, ...res }, 'D1-C1 落地页模板读取失败');
      if (res.reason === 'template_file_not_found') {
        return reply.code(404).send({ error: '未找到', detail: `模板 ${name}.html 不存在` });
      }
      return reply.code(500).send({ error: '服务器内部错误', detail: '落地页模板目录不可用' });
    }
    reply.type('text/html; charset=utf-8');
    return res.html;
  });
}
