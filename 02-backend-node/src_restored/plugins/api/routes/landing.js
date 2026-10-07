import mongoose from 'mongoose';
import { createHash } from 'node:crypto';
import { existsSync } from 'node:fs';
import { open } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { logger } from '../../../core/logger/index.js';
import { Channel } from '../../../core/db/models/index.js';

/**
 * 落地页公开 API（卡 F1-C5）。
 *
 * ★ 为什么需要本文件：
 *   04-landing/runtime/landing-runtime.js 调用了 5 个 /api/* 端点，
 *   本轮实测在 02-backend-node/src_restored 全量 90 条注册路由中【零命中】
 *   ⇒ 前端写了调用、后端没有对应路由 ⇒ 统计与 APK 下载功能整体失效。
 *
 * ★ 鉴权：本组端点面向【匿名访客】，四个 track/pixel 端点已在
 *   middleware/auth.js 的 SKIP_AUTH_PATHS 中放行（见该文件）。
 *   ★ 不得给它们套 adminOnly / ServiceTokenAuth。
 *
 * ★ 防滥用：公开埋点必须有基本限频（见 TOUCH_THROTTLE_MS）。
 *
 * ★ apk/download 的诚实性（重要）：
 *   【F1-C5 时的状态】全仓不存在任何 .apk 文件 ⇒ 端点如实返回 404，绝不伪造。
 *   ★★ 【T5 更正（二期，2026 本轮）】该状态【已变更】：
 *     · 载荷分发链【已接入】（`app.js:18/70` 的 `c2Plugin`；Node 启动日志
 *       `I1-C2: coruna/darksword payload sync done {"upserted":15/5}`）
 *       ⇒ 原「chain_router 接入已裁决降为二期」的理由【已过期】。
 *     · 产物内【已有真实 apk】（`06-android/apk/japapp/` 的投递物，
 *       经 T5 归集到 `templates/apk/`）⇒ 本端点现已返回 **200**。
 *   ⇒ 仍保留「产物内没有 apk 就 404、不伪造」的设计（见下），
 *     但**理由**改为「文件未就绪」，**不再是**「载荷链未通」。
 *     把"看起来通了"当"通了"正是本项目反复踩过的坑（P-1）。
 *   若将来产物内的 apk 被移除，本端点会在【不重启】的情况下自动回到 404。
 */

// ---------------------------------------------------------------------------
// 数据模型：落地页访客会话（按 sid 幂等）
// ---------------------------------------------------------------------------

const LandingVisitSchema = new mongoose.Schema(
  {
    sid: { type: String, required: true, unique: true, index: true },
    // 停留时长（毫秒，前端累加后上报）
    dwell: { type: Number, default: 0 },
    lang: { type: String, default: '' },
    url: { type: String, default: '' },
    started: { type: Boolean, default: false },
    clicked: { type: Boolean, default: false },
    heartbeatAt: { type: Date, default: null },
    // 便于按渠道/域名统计
    channelCode: { type: String, default: '' },
    domain: { type: String, default: '' },
  },
  { timestamps: true, collection: 'landing_visits' }
);

const LandingVisit =
  mongoose.models.LandingVisit || mongoose.model('LandingVisit', LandingVisitSchema);

// ---------------------------------------------------------------------------
// 防滥用：同一 sid 的最小写入间隔（毫秒）
// 前端心跳为 15s 一次；此处限到 3s，既挡刷量又不误伤正常心跳。
const TOUCH_THROTTLE_MS = 3000;

// 进程内最近写入时刻（仅用于限频，非业务真相）
const lastTouch = new Map();

function throttled(sid) {
  const now = Date.now();
  const prev = lastTouch.get(sid);
  if (prev && now - prev < TOUCH_THROTTLE_MS) return true;
  lastTouch.set(sid, now);
  // 防止 Map 无限增长
  if (lastTouch.size > 10000) {
    const cutoff = now - 10 * 60 * 1000;
    for (const [k, v] of lastTouch) if (v < cutoff) lastTouch.delete(k);
  }
  return false;
}

/** 取 sid，做基本校验（长度/字符集），不合法返回 null */
function normalizeSid(raw) {
  if (typeof raw !== 'string') return null;
  const s = raw.trim();
  if (!s || s.length > 64) return null;
  if (!/^[A-Za-z0-9_-]+$/.test(s)) return null;
  return s;
}

function touchMeta(request) {
  const ua = String(request.headers['user-agent'] || '');
  const host = String(request.headers.host || '');
  return { ua, domain: host.split(':')[0] || '' };
}

// ---------------------------------------------------------------------------
// APK 库存（★ W-AD-04，来源：`06-android/apk/japapp/_MANIFEST.txt`，
//   经 `06-android/apk/_BINDING.md` §1 复核，2026-10-03 磁盘实测复算）
//
//   ★ 为什么把 sha256 写死在代码里而不读清单文件：
//     本表的作用是**防止目录被塞入非登记文件 / APK 被悄悄换掉**（§5-4）。
//     若改成「读清单再比对」，替换者只要连清单一起改就绕过了 —— 写死才有意义。
//     换 APK 时**必须**同步改本表，这是一次显式的、可审计的改动。
// ---------------------------------------------------------------------------
const DISTRIBUTABLE_APK = 'japapp.apk';
const APK_INVENTORY = {
  'japapp.apk': '30d6701dd6ed010ce842a7d521fed10e4284356270c0214f44aa4fd0792765a5',
  'child_milkstream.apk': 'cdbb17465b64d74fc3fefa80a69275d773cde526094b7581807ecd1b26fdf5f3',
};

// ---------------------------------------------------------------------------
// APK 校验：同时满足两条互相拉扯的约束 —— **不牺牲 CPU**、**也不牺牲校验**。
//
//   两轮实测的教训：
//   · 版本 A（每请求重算）：校验可靠，但匿名端点每请求 ≈57 ms 主线程 CPU
//     （16.6 MB；审核方 ⌛2026-10-03 实测：冷 110 ms、暖均值 57.5 ms ⇒ 约 17 rps 打满一核），
//     而 **3000 是全线条共用进程**（落地页/埋点/admin 一并受累）⇒ 必须有缓解。
//   · 版本 B（缓存键 `size:mtimeMs`）：CPU 缓过来了，但被「**等长 + 还原 mtime**」的
//     替换件绕过（原地改写后键不变 ⇒ 命中缓存 ⇒ 跳过校验）。
//   ⇒ 本版：键扩为 `ino:size:mtimeMs:ctimeMs`，并让【取键的 stat】与【算哈希】
//     走**同一个 fd**（后者同时闭合"校验的是 A、发出的是 B"的 TOCTOU）。
//     · 原地改写（等长、还原 mtime）⇒ **ctime 变** ⇒ 未命中 ⇒ 重算 ⇒ 拒绝
//     · rename / 换文件 ⇒ **ino 变** ⇒ 未命中
//     · 文件没动 ⇒ 键不变 ⇒ 命中 ⇒ 省掉那 57 ms
//
//   ★★ 平台边界（如实声明，勿当成全平台保证）：
//     上面依赖的是 **Linux** 的 ctime 语义 —— 由内核置位、**用户态改不了**。
//     **Windows 上 `ctime` 是创建时间**，且可被 `SetFileTime` 之类伪造
//     ⇒ **该键在 Windows 上不构成保证**。
//     本项目的**部署形态是 Docker / Linux**（`08-infra/compose/docker-compose.yml`），
//     Windows 仅是本机 dev ⇒ **本机复跑该替换攻击若仍能绕过，属平台语义差异，不是修复失效**；
//     报告时必须并列两个平台的口径。
// ---------------------------------------------------------------------------
// ★★ 平台闸（总调度 ⌛2026-10-03 裁定）：**只有 Linux 才启用缓存**。
//
//   上面那个键的保证**依赖 Linux 的 `ctime` 语义** —— `ctime` 由**内核置位、用户态改不了**
//   ⇒「原地改写（等长 + 还原 mtime）」必然改 `ctime` ⇒ 键变 ⇒ 未命中 ⇒ 重算 ⇒ 拒绝。
//   **非 Linux 平台上 `ctime` 是创建时间，原地覆写不更新它** ⇒ 键不变 ⇒ 缓存命中 ⇒
//   那个优化**不构成保证**（本机 Windows 实测：替换后仍 **200 分发替换件**）。
//   ⇒ 非 Linux 一律**每请求重算**：牺牲那 ~50 ms，换"不在保证不了的地方留优化"。
//
//   ★ 采纳本闸的代价（已登记，**不得当成"已验"**）：
//     **prod(Linux) 的缓存分支在本地完全不被覆盖** ⇒ 部署期必须复跑替换攻击并确认 503
//     （部署期验证项见 `09-docs/ledger/L050-广告线交付与测试夹具登记.md` §2）。
const APK_SHA_CACHE_ENABLED = process.platform === 'linux';
const apkShaCache = new Map();

/**
 * 打开 target 并算出其 sha256。
 * 返回 `{ fh, size, actualSha, cached }` —— **fh 的生命周期归调用方**（命中缓存时不读内容，
 * 但仍返回同一个已打开的 fh，供调用方从**同一 fd** 送流）。
 * ★ 是否走缓存由 `APK_SHA_CACHE_ENABLED` 决定（仅 Linux）。
 * ★ `cached` 三态：true 命中 / false 启用但未命中 / **null 缓存未启用**（详见下方返回处）。
 */
async function openAndHashApk(target) {
  const fh = await open(target, 'r');
  try {
    const st = await fh.stat();
    const key = `${st.ino}:${st.size}:${st.mtimeMs}:${st.ctimeMs}`;
    const cached = APK_SHA_CACHE_ENABLED ? apkShaCache.get(target) : undefined;
    if (cached && cached.key === key)
      return { fh, size: st.size, actualSha: cached.sha, cached: true };
    const hash = createHash('sha256');
    for await (const chunk of fh.createReadStream({ start: 0, autoClose: false }))
      hash.update(chunk);
    const actualSha = hash.digest('hex');
    if (APK_SHA_CACHE_ENABLED)
      apkShaCache.set(target, { key, sha: actualSha });
    // ★ `cached` 的三态（勿把后两者混为一谈 —— F-01 那族"读数与事实不符"）：
    //   true  = 缓存启用且命中 · false = 缓存启用但未命中 · **null = 缓存未启用（无从谈命中）**
    //   闸关闭时若写 `false`，单读该字段会被读成"缓存未命中"，与事实相反。
    return { fh, size: st.size, actualSha, cached: APK_SHA_CACHE_ENABLED ? false : null };
  }
  catch (err) {
    await fh.close().catch(() => {});
    throw err;
  }
}

// ---------------------------------------------------------------------------
// 路由
// ---------------------------------------------------------------------------

export async function landingRoute(fastify) {
  // ---- POST /api/track/start ----  落地页加载即上报一次
  fastify.post('/api/track/start', async (request, reply) => {
    const body = request.body || {};
    const sid = normalizeSid(body.sid);
    if (!sid) return reply.code(400).send({ code: 400, msg: 'sid 非法' });
    if (throttled(sid)) return { code: 0, data: { throttled: true } };

    const meta = touchMeta(request);
    try {
      await LandingVisit.updateOne(
        { sid },
        {
          $set: {
            started: true,
            lang: String(body.lang || '').slice(0, 32),
            url: String(body.url || '').slice(0, 512),
            domain: meta.domain,
          },
          $setOnInsert: { sid },
        },
        { upsert: true }
      );
    } catch (e) {
      logger.error({ err: e, sid }, 'landing track/start 写入失败');
      return reply.code(500).send({ code: 500, msg: '记录失败' });
    }
    return { code: 0, data: { sid } };
  });

  // ---- POST /api/track/heartbeat ----  每 15s 一次 + 页面卸载时 beacon
  fastify.post('/api/track/heartbeat', async (request, reply) => {
    const body = request.body || {};
    const sid = normalizeSid(body.sid);
    if (!sid) return reply.code(400).send({ code: 400, msg: 'sid 非法' });
    if (throttled(sid)) return { code: 0, data: { throttled: true } };

    const dwell = Number(body.dwell);
    const patch = { heartbeatAt: new Date() };
    // 只在收到合法数值时更新，避免 NaN 覆盖已有值
    if (Number.isFinite(dwell) && dwell >= 0) patch.dwell = Math.floor(dwell);

    try {
      await LandingVisit.updateOne({ sid }, { $set: patch, $setOnInsert: { sid } }, { upsert: true });
    } catch (e) {
      logger.error({ err: e, sid }, 'landing track/heartbeat 写入失败');
      return reply.code(500).send({ code: 500, msg: '记录失败' });
    }
    return { code: 0, data: { sid } };
  });

  // ---- POST /api/track/click ----  下载按钮被点击（每会话首个点击才上报）
  fastify.post('/api/track/click', async (request, reply) => {
    const body = request.body || {};
    const sid = normalizeSid(body.sid);
    if (!sid) return reply.code(400).send({ code: 400, msg: 'sid 非法' });

    const dwell = Number(body.dwell);
    const patch = { clicked: true };
    if (Number.isFinite(dwell) && dwell >= 0) patch.dwell = Math.floor(dwell);

    try {
      await LandingVisit.updateOne({ sid }, { $set: patch, $setOnInsert: { sid } }, { upsert: true });
    } catch (e) {
      logger.error({ err: e, sid }, 'landing track/click 写入失败');
      return reply.code(500).send({ code: 500, msg: '记录失败' });
    }
    return { code: 0, data: { sid } };
  });

  // ---- GET /api/pixel-config ----  返回 FB Pixel ID 列表
  // 前端契约：{ pixel_ids: [...] }；无配置时返回空数组，前端会跳过加载。
  fastify.get('/api/pixel-config', async () => {
    const raw = String(process.env.LANDING_PIXEL_IDS || '').trim();
    const ids = raw
      ? raw.split(',').map((s) => s.trim()).filter((s) => /^\d{5,20}$/.test(s))
      : [];
    return { pixel_ids: ids };
  });

  // ---- GET /api/apk/download ----  下载跳转目标
  // ★★ W-AD-04（Owner 裁决「一链一包」，依据 06-android/apk/_BINDING.md）：
  //   · 对渠道分发的**唯一**载荷 = `japapp.apk`（外壳，运行时自取子包）；
  //   · `child_milkstream.apk` 是**链内载荷**，永不分发（请求即 404）；
  //   · ★ 与旧实现的差别：**不再回退取 `files[0]`** —— 解析不到已绑定渠道就如实 404。
  //     旧行为（恒取第一个）正是本卡要根除的形态：看起来通了，实际与渠道无关。
  //   · 解析渠道的两条路：`?channel=<商渠道码>` 显式指定；否则用 Host 匹配
  //     渠道的 `primaryDomain` / `domains`（域名由渠道创建时的 DGA 生成）。
  fastify.get('/api/apk/download', async (request, reply) => {
    const requestedFile = String(request.query?.file || '').trim() || DISTRIBUTABLE_APK;
    // §5-3：文件名不在库存内 ⇒ 拒绝，不得从目录里另挑一个顶替
    if (!(requestedFile in APK_INVENTORY)) {
      logger.warn({ requestedFile }, 'landing apk/download 拒绝：文件名不在库存内');
      return reply.code(404).send({
        code: 404,
        msg: 'APK 不存在',
        detail: `请求的文件名不在登记库存内：${requestedFile}`,
      });
    }
    // §5-2：链内载荷（distribute:false）⇒ 404
    if (requestedFile !== DISTRIBUTABLE_APK) {
      logger.warn({ requestedFile }, 'landing apk/download 拒绝：该文件为链内载荷，不对渠道分发');
      return reply.code(404).send({
        code: 404,
        msg: '不对渠道分发',
        detail: `${requestedFile} 是投递链内部载荷（distribute:false），仅 ${DISTRIBUTABLE_APK} 对渠道分发`,
      });
    }

    // ---- 解析请求的渠道 ----
    let channel = null;
    let resolvedVia = '';
    const explicitCode = String(request.query?.channel || '').trim();
    try {
      if (explicitCode) {
        channel = await Channel.findOne({ code: explicitCode });
        resolvedVia = 'query.channel';
      }
      else {
        const host = String(request.headers.host || '').split(':')[0].trim().toLowerCase();
        if (host) {
          channel = await Channel.findOne({ $or: [{ primaryDomain: host }, { domains: host }] });
          resolvedVia = 'host';
        }
      }
    }
    catch (e) {
      logger.error({ err: e, explicitCode }, 'landing apk/download 渠道解析失败');
      return reply.code(500).send({ code: 500, msg: '渠道解析失败' });
    }

    // §5-1：渠道不存在 / 无绑定 ⇒ 诚实 404（**不得**回退取第一个）
    const bound = channel && (channel.groupId || channel.packetId != null || channel.agentId != null);
    if (!bound) {
      logger.warn({ explicitCode, resolvedVia }, 'landing apk/download 拒绝：未解析到已绑定渠道');
      return reply.code(404).send({
        code: 404,
        msg: 'APK 尚未就绪',
        detail: channel
          ? `渠道 ${channel.code} 未绑定任何 packet/代理商（groupId/packetId/agentId 全为空）`
          : (explicitCode
            ? `渠道 ${explicitCode} 不存在`
            : '未能从请求中解析出渠道（既无 ?channel=，Host 也不匹配任何渠道域名）'),
      });
    }

    // ---- 定位并校验库存文件（§5-4：sha256 必须与登记一致）----
    const configured = String(process.env.LANDING_APK_PATH || '').trim();
    // ★ 兜底：从 import.meta.url 向上定位 repoRoot（不依赖 cwd），
    //   指向 06-android/apk/japapp —— 投递物 APK 的权威来源（卡 T5）。
    const here = path.dirname(fileURLToPath(import.meta.url));
    const repoRoot = path.resolve(here, '..', '..', '..', '..', '..');
    const candidates = [
      configured,
      path.join(process.cwd(), 'templates', 'apk'),
      path.join(process.cwd(), 'public', 'apk'),
      path.join(repoRoot, '06-android', 'apk', 'japapp'),
    ].filter(Boolean);

    let target = null;
    for (const dir of candidates) {
      const file = path.join(dir, DISTRIBUTABLE_APK);
      if (existsSync(file)) {
        target = file;
        break;
      }
    }
    if (!target) {
      logger.warn({ candidates }, 'landing apk/download 未就绪：候选目录内均无该文件');
      return reply.code(404).send({
        code: 404,
        msg: 'APK 尚未就绪',
        detail: '产物内未找到登记的 APK 文件（文件未就绪，非载荷链未通）',
      });
    }

    let opened;
    try {
      opened = await openAndHashApk(target);
    }
    catch (err) {
      logger.error({ err, target }, 'landing apk/download 读取失败');
      return reply.code(500).send({ code: 500, msg: 'APK 读取失败' });
    }

    const expectedSha = APK_INVENTORY[DISTRIBUTABLE_APK];
    if (opened.actualSha !== expectedSha) {
      // 目录被塞入非登记文件 / APK 被换过 ⇒ 拒绝分发并告警（**不回退到别的目录、不另挑文件**）
      await opened.fh.close().catch(() => {});
      logger.error(
        { target, expectedSha, actualSha: opened.actualSha },
        'landing apk/download 拒绝：文件 sha256 与登记不一致（疑似被替换）'
      );
      return reply.code(503).send({
        code: 503,
        msg: 'APK 校验失败',
        detail: '产物内 APK 的 sha256 与登记值不一致，已拒绝分发',
      });
    }

    logger.info(
      { target, channel: channel.code, resolvedVia, shaCacheEnabled: APK_SHA_CACHE_ENABLED, shaCacheHit: opened.cached },
      'landing apk/download 分发登记内的 APK'
    );
    // ★ 从**同一个 fd**送流：与刚才算哈希的是同一份内容 ⇒ 无"校验 A 发出 B"的窗口
    const stream = opened.fh.createReadStream({ start: 0 });
    stream.on('close', () => { opened.fh.close().catch(() => {}); });
    return reply.type('application/vnd.android.package-archive')
      .header('Content-Length', opened.size)
      .send(stream);
  });
}
