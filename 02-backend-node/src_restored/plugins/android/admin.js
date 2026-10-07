import {
  existsSync, statSync, readdirSync, unlinkSync, readFileSync,
  mkdirSync, createWriteStream, createReadStream, renameSync, realpathSync,
} from 'node:fs';
import { pipeline } from 'node:stream/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import mongoose from 'mongoose';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { AndroidConfig, User } from '../../core/db/models/index.js';
import { logger } from '../../core/logger/index.js';
import { loadConfig } from '../../config/index.js';
import { getAuthCookieOptions, issueLoginSession, setLoginCookies } from '../../core/auth/session.js';
import { getRealIP } from '../../core/utils/ip.js';
import { getRedis } from '../../core/db/connection.js';

/**
 * 管理台侧基础端点（卡 D1-C5a）。
 *
 * ★ 前缀（Owner 裁决 甲：两侧分前缀）——
 *   `const ADMIN = '/mgr-admin-8bcde2021d98'`，**逐字符保留**（硬约束）。
 *   落地页侧（裸 `/api/`）由 `./landing.js` 承载，两侧【同名不同路径】，
 *   不得互相覆盖。
 *
 * ★ 契约来源（前端硬证据，非纸面设计）：
 *   `03-web-admin/static/admin_dashboard.html:660` 的 `const ADMIN = "/mgr-admin-8bcde2021d98";`
 *   ⇒ 逐处 fetch 的 method + body + 响应字段处理
 *   ⇒ 已提取为 `09-docs/reports/D1-管理台侧端点契约.md`
 *
 * ★ 存储：**新建** `AndroidConfig` 单文档模型（`_id: 'global'`）。
 *   ★ 刻意【不复用】`PayloadParams` —— 后者服务 c2 载荷分发
 *     （`core/config/config-builder.js` / `plugins/c2/task.js` 读它），
 *     复用会污染载荷分发的配置面。
 *   读写模式参照 `core/config/payload-params-cache.js:8` 的 `findById('global').lean()`。
 *
 * ★ 鉴权：本文件 10 条端点【需鉴权】（前端 401 时跳 `${ADMIN}/login`）
 *   ⇒ **不得**加入 `plugins/api/middleware/auth.js` 的 SKIP_AUTH_PATHS。
 *   全局 preHandler 会为其校验 `accessToken` cookie。
 *
 * ★ 不在本卡范围（属 D1-C5b）：`stats` / `visits` / `visits/clear` /
 *   `apk/list` / `apk/delete` / `/login` / `/logout`；
 *   `/api/apk/upload` 属 D1-C3。
 */

export const ADMIN = '/mgr-admin-8bcde2021d98';
// ★ 路由注册用【字面量路径】（不用模板串）：
//   ① 判据 B3 按字面量匹配 `fastify.<m>('<ADMIN>/api/...'`；
//   ② B6 要求 `ADMIN` 前缀在源码中逐字符可核。
//   下面用一个字面量常量保持两者一致（改前缀只改一行，两处同步）。
export const ADMIN_API = '/mgr-admin-8bcde2021d98/api';

// ---------------------------------------------------------------------------
// 默认值 —— 与前端硬契约一致
// ---------------------------------------------------------------------------
export const DEFAULT_TEMPLATE = 'vodex';   // 契约：`template` 默认 vodex
export const DEFAULT_THEME = 'rose';       // 契约 `:910`  `d.theme || "rose"`
export const DEFAULT_DOWNLOAD_MODE = 'link'; // 契约 `:716` `d.mode || "link"`

// ★ 取值集合（前端硬证据）
// theme : admin_dashboard.html:498-521 的 data-theme 属性
// mode  : 双平台整合复刻方案.md:1180 的 link / upload / telegram
export const THEMES = ['blue', 'gold', 'neon', 'rose'];
export const DOWNLOAD_MODES = ['link', 'upload', 'telegram'];

/**
 * 读取全局配置。
 * ★ 不存在【不报错】—— 返回默认值（卡实现要点 2）。
 * 用 `findById('global').lean()`，与 payload-params-cache.js:8 同模式。
 */
export async function readAndroidConfig() {
  let doc = null;
  try {
    doc = await AndroidConfig.findById('global').lean();
  } catch (err) {
    // ★ 存储不可用时不 500：如实记日志并退回默认值，保证 GET 可用。
    logger.error({ err }, 'D1-C5a 读取 AndroidConfig 失败，回退默认值');
    doc = null;
  }
  const d = doc || {};
  return {
    template: typeof d.template === 'string' && d.template ? d.template : DEFAULT_TEMPLATE,
    theme: typeof d.theme === 'string' && d.theme ? d.theme : DEFAULT_THEME,
    pixelIds: Array.isArray(d.pixelIds) ? d.pixelIds : [],
    downloadMode:
      typeof d.downloadMode === 'string' && d.downloadMode ? d.downloadMode : DEFAULT_DOWNLOAD_MODE,
    apkUrl: typeof d.apkUrl === 'string' ? d.apkUrl : '',
  };
}

/**
 * upsert 写入全局配置（卡实现要点 3）：
 * `findByIdAndUpdate('global', {...}, { upsert: true, new: true })`
 * ★ 返回写后的完整配置（供 `{ ok: true, <field> }` 响应，而非回显请求值）。
 */
export async function updateAndroidConfig(patch) {
  const doc = await AndroidConfig.findByIdAndUpdate(
    'global',
    { ...patch, updatedAt: new Date() },
    { upsert: true, new: true, setDefaultsOnInsert: true }
  ).lean();
  const d = doc || {};
  return {
    template: typeof d.template === 'string' && d.template ? d.template : DEFAULT_TEMPLATE,
    theme: typeof d.theme === 'string' && d.theme ? d.theme : DEFAULT_THEME,
    pixelIds: Array.isArray(d.pixelIds) ? d.pixelIds : [],
    downloadMode:
      typeof d.downloadMode === 'string' && d.downloadMode ? d.downloadMode : DEFAULT_DOWNLOAD_MODE,
    apkUrl: typeof d.apkUrl === 'string' ? d.apkUrl : '',
  };
}

function str(v) {
  return typeof v === 'string' ? v.trim() : '';
}

// ---------------------------------------------------------------------------
// D1-C5b · 访问记录数据源
//
// ★ `landing_visits` 由 `plugins/api/routes/landing.js:32-50` 定义的
//   `LandingVisit` 模型写入（该文件【已验收，不得改】）。这里【只读/只删】，
//   故直接取 mongoose 上的同名模型，避免两处 Schema 漂移。
// ★ 注意：该 Schema 的字段名是 `sid`/`dwell`/`started`/`clicked`/`heartbeatAt`，
//   与前端契约的 `session_id`/`dwell_ms`/`started_at`/`clicked_at`/`last_seen_at`
//   不同 ⇒ 必须做【字段映射投影】（见 projectVisit）。
// ---------------------------------------------------------------------------

/** 取 LandingVisit 模型（landing.js 已注册则复用，未注册则按其 Schema 现建）。 */
function landingVisitModel() {
  if (mongoose.models.LandingVisit) return mongoose.models.LandingVisit;
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

/** 秒级时间戳（前端 `fmt()` 期望 Unix 秒）。无效值回 null —— 前端会显示 "-"。 */
function toEpochSec(v) {
  if (v === null || v === undefined) return null;
  const d = v instanceof Date ? v : new Date(v);
  const t = d.getTime();
  return Number.isFinite(t) ? Math.floor(t / 1000) : null;
}

/**
 * 把一条 `landing_visits` 文档投影成前端契约的 **18 字段**行。
 * ★ 字段名逐条对照 `E:\ios漏洞\_analysis\recon\visits_dump.json`（硬样本）。
 * 库中确实没有的列（ip/country/browser/os/ua/referer 等，属二期 UA 解析）
 * 【如实返回 null/空串】，不编造 —— 前端对空值有 `|| "-"` 兜底。
 */
function projectVisit(doc) {
  const d = doc || {};
  return {
    id: String(d._id ?? ''),
    session_id: d.sid ?? '',
    ip: d.ip ?? null,
    country: d.country ?? null,
    region: d.region ?? null,
    city: d.city ?? null,
    browser: d.browser ?? null,
    os: d.os ?? null,
    device: d.device ?? null,
    ua: d.ua ?? null,
    lang: d.lang ?? '',
    url: d.url ?? '',
    referer: d.referer ?? null,
    dwell_ms: Number.isFinite(d.dwell) ? d.dwell : 0,
    clicked: d.clicked ? 1 : 0,
    clicked_at: d.clickedAt ? toEpochSec(d.clickedAt) : null,
    started_at: d.started ? toEpochSec(d.createdAt) : null,
    last_seen_at: toEpochSec(d.heartbeatAt || d.updatedAt),
  };
}

/** 分页参数归一化：page>=1，per∈[1,200]，非法值回退默认。 */
function parsePage(query) {
  const page = Math.max(1, parseInt(String(query?.page ?? '1'), 10) || 1);
  const rawPer = parseInt(String(query?.per ?? '20'), 10) || 20;
  const per = Math.min(200, Math.max(1, rawPer));
  return { page, per };
}

// ---------------------------------------------------------------------------
// D1-C5b · APK 数据源（文件系统）
//
// ★ 数据源与 `landing.js:174-180`（/api/apk/download）【同源】：
//   候选目录 = LANDING_APK_PATH › <cwd>/templates/apk › <cwd>/public/apk。
//   ★ 本卡不得改 landing.js，故此处【复刻同一候选逻辑】（保持行为一致）。
// ---------------------------------------------------------------------------

/** 候选目录列表（含来源标签，便于诊断）。 */
export function apkCandidateDirs() {
  const configured = String(process.env.LANDING_APK_PATH || '').trim();
  return [
    [configured, 'env:LANDING_APK_PATH'],
    [path.join(process.cwd(), 'templates', 'apk'), `cwd:${path.join(process.cwd(), 'templates', 'apk')}`],
    [path.join(process.cwd(), 'public', 'apk'), `cwd:${path.join(process.cwd(), 'public', 'apk')}`],
  ].filter(([dir]) => Boolean(dir));
}

/**
 * 扫描全部候选目录，聚合 `.apk` 文件。
 * ★ `id` 设计：**目录绝对路径 + 文件名**的 base64url 编码。
 *   —— 不用裸文件名：候选目录可能有多个，同名文件会撞 id，delete 无法唯一定位。
 *   —— 不用下标/序号：列表排序会变，序号不稳定。
 *   —— 编码后 `id` 是【不透明字符串】，天然避免把路径当用户输入直接拼。
 */
function encodeApkId(dir, name) {
  return Buffer.from(`${dir}\u0000${name}`, 'utf8').toString('base64url');
}

/**
 * 解码并【安全校验】apk id。
 * ★★ 防目录穿越：解析出的绝对路径必须落在某个候选目录【之内】，
 *    且文件名须恰为 `.apk`。任一不满足 ⇒ 返回 null（调用方 400）。
 * @returns {{dir:string, name:string, full:string}|null}
 */
function resolveApkId(id) {
  const raw = str(id);
  if (!raw) return null;
  let decoded;
  try {
    decoded = Buffer.from(raw, 'base64url').toString('utf8');
  } catch {
    return null;
  }
  const sep = decoded.indexOf('\u0000');
  if (sep <= 0) return null;
  const dir = decoded.slice(0, sep);
  const name = decoded.slice(sep + 1);
  // ① 文件名必须是纯 basename 且以 .apk 结尾 —— 直接封死 `../` 与子目录
  if (!name || name !== path.basename(name)) return null;
  if (!name.toLowerCase().endsWith('.apk')) return null;
  if (name.includes('..')) return null;

  const dirResolved = path.resolve(dir);
  // ② 目录必须是已知候选目录之一（防止伪造 id 指向任意目录）
  const allowed = apkCandidateDirs().map(([d]) => path.resolve(d));
  if (!allowed.includes(dirResolved)) return null;

  const full = path.resolve(dirResolved, name);
  // ③ 兜底：拼出的路径必须仍在 dir 之内（防 basename 绕过/符号链接类花样）
  const rel = path.relative(dirResolved, full);
  if (rel.startsWith('..') || path.isAbsolute(rel)) return null;

  return { dir: dirResolved, name, full };
}

/** 扫描候选目录，返回按 uploaded_at【新→旧】排序的 files 列表。 */
function listApkFiles() {
  const out = [];
  const seen = new Set();
  for (const [dir] of apkCandidateDirs()) {
    try {
      if (!existsSync(dir)) continue;
      if (!statSync(dir).isDirectory()) continue;
      for (const name of readdirSync(dir)) {
        if (!name.toLowerCase().endsWith('.apk')) continue;
        const full = path.join(dir, name);
        const key = path.resolve(full).toLowerCase();
        if (seen.has(key)) continue;   // 同名同路径去重
        seen.add(key);
        let st;
        try {
          st = statSync(full);
        } catch {
          continue;
        }
        if (!st.isFile()) continue;
        out.push({
          id: encodeApkId(dir, name),
          original_name: name,
          size: st.size,
          // ★ 用 ISO 字符串：判据 D5 按字符串字典序比较，ISO-8601 字典序 == 时间序
          uploaded_at: new Date(st.mtimeMs).toISOString(),
          tg_file_id: null,   // 文件系统无 TG 标记 ⇒ 如实给出 null（前端显示"仅本地"）
        });
      }
    } catch (e) {
      logger.error({ err: e, dir }, 'D1-C5b apk/list 扫描目录失败');
    }
  }
  // ★★ files[0] 必须是【最新】—— 前端 :797 `const f = files[0]` 当"当前使用"。
  out.sort((a, b) => (a.uploaded_at < b.uploaded_at ? 1 : a.uploaded_at > b.uploaded_at ? -1 : 0));
  return out;
}

// ---------------------------------------------------------------------------
// D1-C3 · APK 上传（multipart）
//
// ★ 契约来源（前端硬证据 `admin_dashboard.html:829-861`）：
//     fd.append("apk", file)                      ⇒ 字段名 = "apk"
//     xhr.open("POST", ADMIN + "/api/apk/upload") ⇒ multipart/form-data
//     成功: { ok: true, filename, size, tg_ok? }
//     失败: { ok: false, error }
//
// ★ 与 C5b 的一致性（本卡 U7 要求 upload 后 `apk/list` 能看到）：
//   落盘目录【必须】由同一 `apkCandidateDirs()` 决定（不新造候选逻辑），
//   写完后 `listApkFiles()` 自然扫得到。
// ---------------------------------------------------------------------------

/** 上传大小上限（S4）。Telegram 上限 30MB，本地留余量 ⇒ 50MB。 */
export const APK_UPLOAD_MAX_BYTES = 50 * 1024 * 1024;

/**
 * S1 · 文件名净化 + S3 · 后缀校验。
 * ★★ 这是本卡核心安全点（防目录穿越）。
 *
 * 策略：**净化（basename）而非拒绝**，但净化后若与原名不同，
 * 说明原名含路径成分（`../`、`/`、`\`）⇒ 一律【拒绝】，
 * 避免"静默改名"掩盖攻击意图，也让判据 U4 有明确的可观测结果。
 *
 * @returns {{ok:true, name:string} | {ok:false, error:string}}
 */
export function sanitizeApkFilename(raw) {
  const original = typeof raw === 'string' ? raw : '';
  // ① 空字节：任何位置出现即拒（会截断底层 syscall 的路径）
  if (!original || original.includes('\u0000')) {
    return { ok: false, error: '文件名非法' };
  }
  // ② 控制字符/引号等，一并拒（防 header 注入与诡异路径）
  if (/[\u0000-\u001f\u007f"']/.test(original)) {
    return { ok: false, error: '文件名含非法字符' };
  }
  // ③ 路径分隔符（两种）与上跳：直接拒
  if (original.includes('/') || original.includes('\\') || original.includes('..')) {
    return { ok: false, error: '文件名不得包含路径分隔符' };
  }
  // ④ 必须恰为 basename（双保险）
  const base = path.basename(original);
  if (base !== original) {
    return { ok: false, error: '文件名不得包含路径' };
  }
  // ⑥ 不能是 . / .. 之类的特殊名
  if (base === '.' || base === '..') {
    return { ok: false, error: '文件名非法' };
  }
  // ⑥b 不能只有扩展名（`.apk` / `.APK`）—— 无主名不是合法文件名
  {
    const dot = base.lastIndexOf('.');
    const stem = dot > 0 ? base.slice(0, dot).trim() : '';
    if (dot <= 0 || !stem) {
      // dot<=0 表示没有点或点是首字符（如 `.apk` / `.hidden`）⇒ 一律拒
      return { ok: false, error: '缺少文件名' };
    }
  }
  // ⑦ S3 · 只接受 .apk 后缀（大小写不敏感）
  if (!base.toLowerCase().endsWith('.apk')) {
    return { ok: false, error: '只接受 .apk 文件' };
  }
  // ⑦ 长度保护（多数文件系统 255 字节上限）
  if (Buffer.byteLength(base, 'utf8') > 200) {
    return { ok: false, error: '文件名过长' };
  }
  return { ok: true, name: base };
}

/**
 * 选定落盘目录（与 C5b `apkCandidateDirs()` 同源）。
 * ★ 取【候选列表中的第一个】，与 `listApkFiles()` 的扫描顺序一致。
 * ★ 目录不存在时创建（`templates/apk` 在全新环境可能尚未建）。
 * @returns {{ok:true, dir:string} | {ok:false, error:string}}
 */
export function resolveUploadDir() {
  const cands = apkCandidateDirs();
  if (!cands.length) return { ok: false, error: '未配置 APK 目录' };
  const dir = path.resolve(cands[0][0]);
  try {
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    if (!statSync(dir).isDirectory()) return { ok: false, error: 'APK 目录不可用' };
  } catch (e) {
    logger.error({ err: e, dir }, 'D1-C3 创建/校验 APK 目录失败');
    return { ok: false, error: 'APK 目录不可用' };
  }
  return { ok: true, dir };
}

/**
 * S2 · 落盘路径必须在候选目录内（`path.resolve` 后校验）。
 * ★★ 核心安全点之二：即便文件名已净化，仍做最终包含性校验。
 * @returns {string|null} 安全绝对路径；null = 越界
 */
export function safeJoinInside(dir, name) {
  const dirResolved = path.resolve(dir);
  const full = path.resolve(dirResolved, name);
  const rel = path.relative(dirResolved, full);
  if (rel.startsWith('..') || path.isAbsolute(rel) || rel === '') return null;
  if (rel.includes(path.sep)) return null;   // 不得落入子目录
  return full;
}

/**
 * S6 · 不覆盖已有文件：同名时追加 `-1`、`-2` …（上限 100 次）。
 * @returns {{ok:true, full:string, name:string} | {ok:false, error:string}}
 */
export function pickNonClobberingPath(dir, name) {
  const ext = '.apk';
  const stem = name.slice(0, name.length - ext.length);
  for (let i = 0; i < 100; i++) {
    const tryName = i === 0 ? name : `${stem}-${i}${ext}`;
    const full = safeJoinInside(dir, tryName);
    if (!full) return { ok: false, error: '文件名非法' };
    if (!existsSync(full)) return { ok: true, full, name: tryName };
  }
  return { ok: false, error: '同名文件过多，请更换文件名' };
}

// ---------------------------------------------------------------------------
// D1-C5b · 登录页（`${ADMIN}/login` 是【页面】，不是 API）
//
// ★ 停靠点 1 的裁决依据（硬证据，非猜测）：
//   `03-web-admin/static/admin_login.html:82`：
//     <form class="card" method="post" action="/mgr-admin-8bcde2021d98/login">
//        <input name="username"> <input name="password" type="password">
//   ⇒ 前端期望的是一个 **HTML 登录页**（GET），表单以
//     `application/x-www-form-urlencoded` **原生 POST** 回同一路径，
//     成功后 302 到面板页并【下发 accessToken cookie】。
//   ⇒ 故本路由【复用】既有 `/api/auth/login` 的凭据校验与会话签发设施
//     （`core/auth/session.js` 的 issueLoginSession/setLoginCookies），
//     **不是**另造一套独立登录 —— 两者共用 `users` 集合与同一 JWT_SECRET。
// ---------------------------------------------------------------------------

/** 登录页 HTML 路径：`03-web-admin/static/admin_login.html`（前端契约来源，只读）。 */
function resolveLoginHtmlPath() {
  const here = path.dirname(fileURLToPath(import.meta.url));
  // here = <repo>/02-backend-node/src_restored/plugins/android
  const repoRoot = path.resolve(here, '..', '..', '..', '..');
  const candidates = [
    path.join(repoRoot, '03-web-admin', 'static', 'admin_login.html'),
    path.join(process.cwd(), '..', '03-web-admin', 'static', 'admin_login.html'),
    path.join(process.cwd(), '03-web-admin', 'static', 'admin_login.html'),
  ];
  for (const p of candidates) if (existsSync(p)) return p;
  return null;
}

/**
 * 面板页 HTML 路径：`03-web-admin/static/admin_dashboard.html`（前端契约来源，只读）。
 * ★ 定位方式与 `resolveLoginHtmlPath()` 完全一致：从**文件位置**向上定位 repoRoot，
 *   不依赖 cwd（见该函数注释）。
 */
function resolveDashboardHtmlPath() {
  const here = path.dirname(fileURLToPath(import.meta.url));
  // here = <repo>/02-backend-node/src_restored/plugins/android
  const repoRoot = path.resolve(here, '..', '..', '..', '..');
  const candidates = [
    path.join(repoRoot, '03-web-admin', 'static', 'admin_dashboard.html'),
    path.join(process.cwd(), '..', '03-web-admin', 'static', 'admin_dashboard.html'),
    path.join(process.cwd(), '03-web-admin', 'static', 'admin_dashboard.html'),
  ];
  for (const p of candidates) if (existsSync(p)) return p;
  return null;
}

const DASHBOARD_PATH = '/mgr-admin-8bcde2021d98/dashboard';

// ---------------------------------------------------------------------------
// T21 · 管理台静态资源（面板页引用的图片 / 模板 CSS·JS）
//
// 背景（用户报障："落地页预览都没有加载出来"）：
//   `admin_dashboard.html` 引用了 `/images/template-previews/*.png`（19 个）
//   与 `/landing-pages/<n>/static/<t>/<f>`（31 个 CSS/JS），但本进程此前
//   【无任何静态挂载】—— 面板页只能读到 HTML 自身，所有子资源 404。
//
// ★ 定位方式与 `resolveDashboardHtmlPath()` 完全一致：
//   从**文件位置**向上定位 repoRoot，不依赖 cwd。
// ---------------------------------------------------------------------------
function resolveWebAdminStaticRoot() {
  const here = path.dirname(fileURLToPath(import.meta.url));
  // here = <repo>/02-backend-node/src_restored/plugins/android
  const repoRoot = path.resolve(here, '..', '..', '..', '..');
  const candidates = [
    path.join(repoRoot, '03-web-admin', 'static'),
    path.join(process.cwd(), '..', '03-web-admin', 'static'),
    path.join(process.cwd(), '03-web-admin', 'static'),
  ];
  for (const p of candidates) if (existsSync(p)) return p;
  return null;
}

// ★ Content-Type 白名单（扩展名 ⇒ MIME）。未命中 ⇒ 一律
//   `application/octet-stream`（**刻意不猜**，避免把未知内容当 text/html 回，
//   否则会把静态目录变成存储型 XSS 的跳板）。
const STATIC_MIME = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
  '.ttf': 'font/ttf',
  '.otf': 'font/otf',
  '.eot': 'application/vnd.ms-fontobject',
  '.map': 'application/json; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.mp4': 'video/mp4',
  '.webm': 'video/webm',
};

/**
 * T21 · 安全的静态文件解析（**防路径穿越**）。
 *
 * ★ 两道防线（任一不满足即拒绝）：
 *   ① 规范化后必须仍在 root 之内（`path.resolve` 消解 `..` 后做前缀判定）；
 *   ② `realpathSync` 复核 —— 挡住**符号链接**指向 root 之外的情形。
 *   ★ Fastify 默认把 `%2e%2e%2f` 解码进 `request.params['*']`，
 *     故【不能】只靠 URL 层过滤，必须对**解码后的路径**做规范化判定。
 *
 * @returns {{ok:true, abs:string}|{ok:false, code:number, reason:string}}
 */
function resolveStaticFile(relRaw) {
  const root = resolveWebAdminStaticRoot();
  if (!root) return { ok: false, code: 500, reason: '静态根不可用' };

  const rel = String(relRaw || '');
  // 空路径 / NUL 字节 / 反斜杠（Windows 上也可能是分隔符）—— 直接拒绝。
  if (!rel || rel.includes('\0') || rel.includes('\\')) {
    return { ok: false, code: 400, reason: '非法路径' };
  }
  // 显式拒绝任何 `..` 段（明文或编码后已被解码）。
  const segs = rel.split('/');
  if (segs.some((s) => s === '..' || s === '.')) {
    return { ok: false, code: 400, reason: '非法路径' };
  }
  // 只允许普通字符段，挡掉驱动器号 / UNC / 协议前缀。
  if (segs.some((s) => !s || s.includes(':') || s.includes('*') || s.includes('?'))) {
    return { ok: false, code: 400, reason: '非法路径' };
  }

  const abs = path.resolve(root, rel);
  // 防线①：规范化后仍须在 root 之内（含分隔符，避免 `staticX` 前缀混淆）。
  const rootWithSep = root.endsWith(path.sep) ? root : root + path.sep;
  if (abs !== root && !abs.startsWith(rootWithSep)) {
    return { ok: false, code: 400, reason: '越界路径' };
  }

  let st;
  try {
    st = statSync(abs);
  } catch {
    return { ok: false, code: 404, reason: '未找到' };
  }
  if (!st.isFile()) return { ok: false, code: 404, reason: '未找到' };

  // 防线②：realpath 复核（符号链接逃逸）。
  try {
    const realRoot = realpathSync(root);
    const realAbs = realpathSync(abs);
    const realRootWithSep = realRoot.endsWith(path.sep) ? realRoot : realRoot + path.sep;
    if (realAbs !== realRoot && !realAbs.startsWith(realRootWithSep)) {
      return { ok: false, code: 400, reason: '越界路径' };
    }
  } catch {
    return { ok: false, code: 404, reason: '未找到' };
  }

  return { ok: true, abs };
}

function staticMimeOf(abs) {
  return STATIC_MIME[path.extname(abs).toLowerCase()] || 'application/octet-stream';
}

// ---------------------------------------------------------------------------
// 路由
// ---------------------------------------------------------------------------

export async function adminRoute(fastify) {
  // ========================================================================
  // 1/2 · template
  //   前端 `:1040` GET /api/template        ⇒ { template }
  //   前端 `:1055` POST /api/template {template} ⇒ { ok:true, template }
  // ========================================================================
  fastify.get('/mgr-admin-8bcde2021d98/api/template', async () => {
    const cfg = await readAndroidConfig();
    return { template: cfg.template };
  });

  fastify.post('/mgr-admin-8bcde2021d98/api/template', async (request) => {
    const body = request.body || {};
    const template = str(body.template);
    // ★ 空值不覆盖既有配置（前端只在选择后提交）
    if (!template) {
      const cfg = await readAndroidConfig();
      return { ok: true, template: cfg.template };
    }
    const cfg = await updateAndroidConfig({ template });
    return { ok: true, template: cfg.template };
  });

  // ========================================================================
  // 3/4 · theme
  //   前端 `:908` GET  ⇒ { theme }（默认 rose）
  //   前端 `:919` POST {theme} ⇒ { ok:true, theme }
  //   ★ 取值集合 { blue, gold, neon, rose }
  // ========================================================================
  fastify.get('/mgr-admin-8bcde2021d98/api/theme', async () => {
    const cfg = await readAndroidConfig();
    return { theme: cfg.theme };
  });

  fastify.post('/mgr-admin-8bcde2021d98/api/theme', async (request) => {
    const body = request.body || {};
    const theme = str(body.theme);
    if (!theme) {
      const cfg = await readAndroidConfig();
      return { ok: true, theme: cfg.theme };
    }
    // ★ 前端用返回值设 data-theme 属性，集合外的值无对应样式 ⇒ 拒绝非法值
    //   （但保持 200 + 当前生效值，不让前端拿到 undefined）。
    if (!THEMES.includes(theme)) {
      const cfg = await readAndroidConfig();
      return { ok: true, theme: cfg.theme };
    }
    const cfg = await updateAndroidConfig({ theme });
    return { ok: true, theme: cfg.theme };
  });

  // ========================================================================
  // 5/6 · pixel
  //   前端 `:955` GET ⇒ { pixel_ids: [] }
  //   前端 `:967`/`:983` POST {action:"add"|"remove", pixel_id} ⇒ { ok:true, pixel_ids }
  //   ★ action 语义 —— 不是整体覆盖（契约报告 §2）
  // ========================================================================
  fastify.get('/mgr-admin-8bcde2021d98/api/pixel', async () => {
    const cfg = await readAndroidConfig();
    return { pixel_ids: cfg.pixelIds };
  });

  fastify.post('/mgr-admin-8bcde2021d98/api/pixel', async (request, reply) => {
    const body = request.body || {};
    const action = str(body.action);
    const pixelId = str(body.pixel_id);

    if (!pixelId) {
      const cfg = await readAndroidConfig();
      return { ok: true, pixel_ids: cfg.pixelIds };
    }
    if (action !== 'add' && action !== 'remove') {
      // ★ 非 add/remove 不静默当成 add —— 如实报错，避免写坏配置面。
      return reply.code(400).send({ error: 'action 须为 add 或 remove' });
    }

    try {
      const current = await AndroidConfig.findById('global').lean();
      const list = Array.isArray(current?.pixelIds) ? current.pixelIds.slice() : [];
      let next = list;
      if (action === 'add') {
        if (!list.includes(pixelId)) next = [...list, pixelId];  // ★ 幂等：不重复追加
      } else {
        next = list.filter((x) => x !== pixelId);                 // ★ 幂等：不存在也无害
      }
      const cfg = await updateAndroidConfig({ pixelIds: next });
      return { ok: true, pixel_ids: cfg.pixelIds };
    } catch (err) {
      logger.error({ err }, 'D1-C5a pixel 更新失败');
      return reply.code(500).send({ error: '服务器内部错误' });
    }
  });

  // ========================================================================
  // 7/8 · download-mode
  //   前端 `:714` GET ⇒ { mode }（默认 link）
  //   前端 `:698` POST {mode} ⇒ { ok:true, mode }
  //   ★ 取值 link / upload / telegram
  // ========================================================================
  fastify.get('/mgr-admin-8bcde2021d98/api/download-mode', async () => {
    const cfg = await readAndroidConfig();
    return { mode: cfg.downloadMode };
  });

  fastify.post('/mgr-admin-8bcde2021d98/api/download-mode', async (request) => {
    const body = request.body || {};
    const mode = str(body.mode);
    if (!mode || !DOWNLOAD_MODES.includes(mode)) {
      // 非法/缺省值 ⇒ 不覆盖，返回当前生效值（前端据此刷新 UI）
      const cfg = await readAndroidConfig();
      return { ok: true, mode: cfg.downloadMode };
    }
    const cfg = await updateAndroidConfig({ downloadMode: mode });
    return { ok: true, mode: cfg.downloadMode };
  });

  // ========================================================================
  // 9/10 · apk-url
  //   前端 `:765` GET ⇒ { url }
  //   前端 `:777` POST {url} ⇒ { ok:true } / { error }
  //   ★ 与 D1-C3（apk 侧）的关系：本端点只存【下载链接】这一标量，
  //     不读写上传产生的文件清单（`apk/list` 属 D1-C5b）⇒ 无共享状态（未触发停靠点 4）。
  // ========================================================================
  fastify.get('/mgr-admin-8bcde2021d98/api/apk-url', async () => {
    const cfg = await readAndroidConfig();
    return { url: cfg.apkUrl };
  });

  fastify.post('/mgr-admin-8bcde2021d98/api/apk-url', async (request, reply) => {
    const body = request.body || {};
    const url = str(body.url);
    // ★ url 允许为空串（前端可清空下载链接）⇒ 不作非空校验。
    //   但若给了值，须是 http(s) 绝对地址，否则前端下载页会跳到坏目标。
    if (url && !/^https?:\/\//i.test(url)) {
      return reply.code(400).send({ error: 'url 须为 http(s) 绝对地址' });
    }
    try {
      await updateAndroidConfig({ apkUrl: url });
      return { ok: true };
    } catch (err) {
      logger.error({ err }, 'D1-C5a apk-url 更新失败');
      return reply.code(500).send({ error: '服务器内部错误' });
    }
  });

  // ========================================================================
  // D1-C5b · 1 · GET ${ADMIN}/api/stats
  //   前端 `:723` `fetch(ADMIN + "/api/stats")`，读 total / today / clicks
  //   （另读 unique_ips / avg_dwell_ms / top_countries / top_devices，一并给出）。
  //   `:726` `d.total ? (d.clicks / d.total * 100)…` ⇒ total/clicks 必须存在。
  //   数据源：`landing_visits` collection。
  // ========================================================================
  fastify.get('/mgr-admin-8bcde2021d98/api/stats', async (request, reply) => {
    try {
      const LV = landingVisitModel();
      const startOfDay = new Date();
      startOfDay.setHours(0, 0, 0, 0);

      const [total, today, clicks, ips, dwellAgg, byCountry, byDevice] = await Promise.all([
        LV.countDocuments({}),
        LV.countDocuments({ createdAt: { $gte: startOfDay } }),
        LV.countDocuments({ clicked: true }),
        LV.distinct('ip').then((a) => (a || []).filter(Boolean).length).catch(() => 0),
        LV.aggregate([{ $group: { _id: null, avg: { $avg: '$dwell' } } }]).catch(() => []),
        LV.aggregate([
          { $match: { country: { $nin: [null, ''] } } },
          { $group: { _id: '$country', c: { $sum: 1 } } },
          { $sort: { c: -1 } },
          { $limit: 8 },
        ]).catch(() => []),
        LV.aggregate([
          { $match: { device: { $nin: [null, ''] } } },
          { $group: { _id: '$device', c: { $sum: 1 } } },
          { $sort: { c: -1 } },
          { $limit: 8 },
        ]).catch(() => []),
      ]);

      const avg = Array.isArray(dwellAgg) && dwellAgg[0] && Number.isFinite(dwellAgg[0].avg)
        ? Math.round(dwellAgg[0].avg)
        : 0;

      return {
        total,
        today,
        clicks,
        unique_ips: ips,
        avg_dwell_ms: avg,
        top_countries: (byCountry || []).map((r) => ({ country: r._id, c: r.c })),
        top_devices: (byDevice || []).map((r) => ({ device: r._id, c: r.c })),
      };
    } catch (err) {
      logger.error({ err }, 'D1-C5b stats 查询失败');
      return reply.code(500).send({ error: '服务器内部错误' });
    }
  });

  // ========================================================================
  // D1-C5b · 2 · GET ${ADMIN}/api/visits?page=&per=
  //   前端 `:743` `${ADMIN}/api/visits?page=${page}&per=${per}`，读 total / rows。
  //   rows 每行 **18 字段**（见 projectVisit）。
  // ========================================================================
  fastify.get('/mgr-admin-8bcde2021d98/api/visits', async (request, reply) => {
    try {
      const LV = landingVisitModel();
      const { page, per } = parsePage(request.query);
      const skip = (page - 1) * per;

      const [total, docs] = await Promise.all([
        LV.countDocuments({}),
        LV.find({}).sort({ createdAt: -1 }).skip(skip).limit(per).lean(),
      ]);

      return { total, rows: docs.map(projectVisit) };
    } catch (err) {
      logger.error({ err }, 'D1-C5b visits 查询失败');
      return reply.code(500).send({ error: '服务器内部错误' });
    }
  });

  // ========================================================================
  // D1-C5b · 3 · POST ${ADMIN}/api/visits/clear
  //   前端 `:883` `fetch(ADMIN + "/api/visits/clear", { method: "POST" })`（无 body）
  //   ⇒ **真清空** `landing_visits`（判据 D6 要求 total 归 0）。
  // ★ 破坏性操作：本卡在 e2e 库（gasleak）执行，清理前已确认仅 2 条探针数据。
  // ========================================================================
  fastify.post('/mgr-admin-8bcde2021d98/api/visits/clear', async (request, reply) => {
    try {
      const LV = landingVisitModel();
      const before = await LV.countDocuments({});
      const res = await LV.deleteMany({});
      const deleted = res?.deletedCount ?? 0;
      logger.warn({ before, deleted }, 'D1-C5b visits/clear 已清空 landing_visits（破坏性操作）');
      return { ok: true, deleted };
    } catch (err) {
      logger.error({ err }, 'D1-C5b visits/clear 失败');
      return reply.code(500).send({ error: '服务器内部错误' });
    }
  });

  // ========================================================================
  // D1-C5b · 4 · GET ${ADMIN}/api/apk/list
  //   前端 `:790` 读 `d.files`；`files[0]` 当"当前使用"（`:797`/`:821`）
  //   ⇒ **必须新→旧排序**（判据 D5）。
  //   元素字段：id / original_name / size / uploaded_at / tg_file_id(可选)
  // ========================================================================
  fastify.get('/mgr-admin-8bcde2021d98/api/apk/list', async (request, reply) => {
    try {
      return { files: listApkFiles() };
    } catch (err) {
      logger.error({ err }, 'D1-C5b apk/list 失败');
      return reply.code(500).send({ error: '服务器内部错误' });
    }
  });

  // ========================================================================
  // D1-C5b · 5 · POST ${ADMIN}/api/apk/delete   body { id }
  //   前端 `:873` `body: JSON.stringify({ id })`（`id` 来自 `:822` 的 `f.id`）
  //   ★★ 必须做路径安全校验（防 ../ 目录穿越）—— 见 resolveApkId。
  // ========================================================================
  fastify.post('/mgr-admin-8bcde2021d98/api/apk/delete', async (request, reply) => {
    const body = request.body || {};
    const target = resolveApkId(body.id);
    if (!target) {
      // ★ 非法/伪造 id 一律 400：【不】静默成功，也【不】回显解析出的路径。
      logger.warn({ id: String(body.id ?? '') }, 'D1-C5b apk/delete 拒绝非法 id（路径校验未过）');
      return reply.code(400).send({ error: 'id 非法' });
    }
    try {
      if (!existsSync(target.full)) {
        return reply.code(404).send({ error: '文件不存在' });
      }
      // 二次确认：仍是候选目录内的普通文件才删。
      const st = statSync(target.full);
      if (!st.isFile() || !target.name.toLowerCase().endsWith('.apk')) {
        return reply.code(400).send({ error: 'id 非法' });
      }
      unlinkSync(target.full);
      logger.warn({ file: target.full }, 'D1-C5b apk/delete 已删除 APK 文件（破坏性操作）');
      return { ok: true };
    } catch (err) {
      logger.error({ err }, 'D1-C5b apk/delete 失败');
      return reply.code(500).send({ error: '服务器内部错误' });
    }
  });

  // ★ GET ${ADMIN}/logout 见下方 adminAuthRoute（本函数外）。
  //   它必须【匿名可达】（未登录时点"退出"不该 401），故与登录页一起
  //   注册在 authMiddleware 之前。

  // ========================================================================
  // D1-C3 · 6 · POST ${ADMIN}/api/apk/upload   multipart/form-data  field="apk"
  //   前端 `:829-861`：
  //     const fd = new FormData(); fd.append("apk", file);
  //     xhr.open("POST", ADMIN + "/api/apk/upload")
  //     成功 ⇒ { ok:true, filename, size, tg_ok? }；失败 ⇒ { ok:false, error }
  //   ★ 鉴权（S5）：本路由注册在 adminRoute 内，而 index.js 已把
  //     adminRoute 关进受保护域 ⇒ 无 token 自动 401，本处无需再写鉴权。
  //   ★ Telegram 同步【不在本卡范围】（无凭据）⇒ 恒 tg_ok:false（不伪造）。
  // ========================================================================
  fastify.post('/mgr-admin-8bcde2021d98/api/apk/upload', async (request, reply) => {
    // ---- multipart 能力探测：@fastify/multipart 已在 app.js 注册 ----
    if (typeof request.file !== 'function') {
      logger.error({}, 'D1-C3 apk/upload：request.file 不可用（multipart 未注册？）');
      return reply.code(500).send({ ok: false, error: '服务器内部错误' });
    }
    if (!request.isMultipart || !request.isMultipart()) {
      return reply.code(400).send({ ok: false, error: '须为 multipart/form-data' });
    }

    // ---- 取字段名 "apk"（★ 契约字段名）----
    let part;
    try {
      part = await request.file({ limits: { fileSize: APK_UPLOAD_MAX_BYTES, files: 1 } });
    } catch (err) {
      logger.warn({ err }, 'D1-C3 apk/upload 解析 multipart 失败');
      return reply.code(400).send({ ok: false, error: '文件过大或格式错误' });
    }
    if (!part) {
      return reply.code(400).send({ ok: false, error: '未收到文件（字段名须为 apk）' });
    }
    if (part.fieldname !== 'apk') {
      // ★ 字段名不符：丢弃流，避免客户端挂起
      try { part.file.resume(); } catch { /* ignore */ }
      return reply.code(400).send({ ok: false, error: '字段名须为 apk' });
    }

    // ---- S1 + S3：文件名净化 / 后缀校验 ----
    const sane = sanitizeApkFilename(part.filename);
    if (!sane.ok) {
      try { part.file.resume(); } catch { /* ignore */ }
      logger.warn(
        { filename: String(part.filename ?? ''), ip: getRealIP(request) },
        'D1-C3 apk/upload 拒绝非法文件名（S1/S3：净化或后缀校验未过）'
      );
      return reply.code(400).send({ ok: false, error: sane.error });
    }

    // ---- 落盘目录（与 C5b apkCandidateDirs() 同源）----
    const dirRes = resolveUploadDir();
    if (!dirRes.ok) {
      try { part.file.resume(); } catch { /* ignore */ }
      return reply.code(500).send({ ok: false, error: dirRes.error });
    }

    // ---- S2 + S6：路径包含性校验 + 不覆盖 ----
    const target = pickNonClobberingPath(dirRes.dir, sane.name);
    if (!target.ok) {
      try { part.file.resume(); } catch { /* ignore */ }
      return reply.code(400).send({ ok: false, error: target.error });
    }
    // ★ S2 二次确认：最终路径必须落在候选目录内
    const allowed = apkCandidateDirs().map(([d]) => path.resolve(d));
    const targetDir = path.resolve(path.dirname(target.full));
    if (!allowed.includes(targetDir)) {
      try { part.file.resume(); } catch { /* ignore */ }
      logger.warn({ target: target.full }, 'D1-C3 apk/upload 拒绝越界落盘路径（S2）');
      return reply.code(400).send({ ok: false, error: '文件名非法' });
    }

    // ---- 流式落盘（先写 .part 临时名，成功后再 rename）----
    const tmpFull = `${target.full}.part`;
    let written = 0;
    try {
      part.file.on('data', (c) => { written += c.length; });
      await pipeline(part.file, createWriteStream(tmpFull));
    } catch (err) {
      // ★ multipart 的 fileSize 超限会以 RequestFileTooLargeError 抛出
      try { unlinkSync(tmpFull); } catch { /* ignore */ }
      const tooLarge = part.file.truncated
        || err?.code === 'FST_REQ_FILE_TOO_LARGE'
        || /too large|limit/i.test(String(err?.message || ''));
      logger.warn(
        { err: String(err?.message || err), written, filename: sane.name },
        tooLarge ? 'D1-C3 apk/upload 拒绝超限文件（S4）' : 'D1-C3 apk/upload 落盘失败'
      );
      if (tooLarge) {
        return reply.code(413).send({
          ok: false, error: `文件超过上限 ${Math.floor(APK_UPLOAD_MAX_BYTES / 1024 / 1024)}MB`,
        });
      }
      return reply.code(500).send({ ok: false, error: '写入失败' });
    }

    // ★ 兜底：流被截断（超限但未抛错）⇒ 删除临时文件并拒绝
    if (part.file.truncated) {
      try { unlinkSync(tmpFull); } catch { /* ignore */ }
      logger.warn({ written }, 'D1-C3 apk/upload 流被截断（超出 S4 上限）');
      return reply.code(413).send({
        ok: false, error: `文件超过上限 ${Math.floor(APK_UPLOAD_MAX_BYTES / 1024 / 1024)}MB`,
      });
    }

    let size = written;
    try {
      renameSync(tmpFull, target.full);
      size = statSync(target.full).size;
    } catch (err) {
      try { unlinkSync(tmpFull); } catch { /* ignore */ }
      logger.error({ err, target: target.full }, 'D1-C3 apk/upload 收尾 rename 失败');
      return reply.code(500).send({ ok: false, error: '写入失败' });
    }

    // ★ 落盘后 realpath 复核（防符号链接逃逸，S2 增强）
    try {
      const realDir = realpathSync(targetDir);
      const realFull = realpathSync(target.full);
      const rel = path.relative(realDir, realFull);
      if (rel.startsWith('..') || path.isAbsolute(rel)) {
        try { unlinkSync(target.full); } catch { /* ignore */ }
        logger.warn({ target: target.full, realFull }, 'D1-C3 apk/upload realpath 逃逸，已回滚');
        return reply.code(400).send({ ok: false, error: '文件名非法' });
      }
    } catch (err) {
      logger.warn({ err, target: target.full }, 'D1-C3 apk/upload realpath 复核异常（已落盘）');
    }

    logger.info(
      { file: target.full, size, ip: getRealIP(request) },
      'D1-C3 apk/upload 落盘成功'
    );

    // ★ Telegram 同步【未实现】：无凭据（全仓库无任何 TG token 配置）。
    //   按契约如实返回 tg_ok:false ⇒ 前端显示"⚠️ Telegram 同步失败"。
    //   ★★ 绝不伪造 tg_ok:true。
    return { ok: true, filename: target.name, size, tg_ok: false };
  });

  // ========================================================================
  // 17/17 · ★ X6b · 面板页（管理台 UI）
  //   GET ${ADMIN}/dashboard ⇒ 返回 03-web-admin/static/admin_dashboard.html
  //
  // 为什么必须存在：`POST ${ADMIN}/login` 成功后 302 到 `DASHBOARD_PATH`，
  //   但在本卡之前**无人提供该路由** ⇒ 登录成功即 404（UNMATCHED），
  //   60,126 B 的整个管理台 UI 完全不可达。
  //
  // ★ 域选择：注册在 `adminRoute`（**受保护域**）内，与既有 16 条管理台
  //   端点一致 —— 无 token 由 authMiddleware 自动拦成 401。
  //   刻意【不】放进 `adminAuthRoute`：后台 UI 不应匿名可达（否则整个
  //   管理界面的结构、接口清单、字段名都会对匿名者暴露）。
  //   ★ 已知 UX：未登录直接访问 /dashboard 看到的是 401 JSON，而非登录页。
  //     重定向到登录页需改 authMiddleware 行为 ⇒ 不在本卡范围（卡片停靠点 2）。
  //
  // ★ 只读契约来源：`admin_dashboard.html` 仅被读取作为响应体，绝不改写。
  // ========================================================================
  fastify.get('/mgr-admin-8bcde2021d98/dashboard', async (request, reply) => {
    const htmlPath = resolveDashboardHtmlPath();
    if (!htmlPath) {
      logger.error({}, 'X6b 面板页 admin_dashboard.html 定位失败');
      return reply.code(500).send({ error: '服务器内部错误', detail: '面板页不可用' });
    }
    try {
      reply.type('text/html; charset=utf-8');
      return readFileSync(htmlPath, 'utf8');
    } catch (e) {
      logger.error({ err: e }, 'X6b 面板页读取失败');
      return reply.code(500).send({ error: '服务器内部错误', detail: '面板页不可用' });
    }
  });
}

// ---------------------------------------------------------------------------
// D1-C5b · 登录页 / 登出 —— ★ 刻意【不带鉴权】的独立 scope
//
// 为什么单独一个导出函数：
//   `index.js` 中 `await fastify.register(authMiddleware)` 是 fp 包裹的
//   preHandler，一旦注册就对【同 scope 内之后注册】的全部路由生效。
//   `/login`（登录页本身）与 `/logout`（退出）必须【匿名可达】——
//   否则未登录访问登录页会被拦成 401，形成死锁。
//   故把这两条放在**自己的 register 里、且先于 authMiddleware 注册**：
//   Fastify 的封装边界使兄弟插件的 preHandler 互不覆盖，天然达成放行，
//   且无需改 `plugins/api/middleware/auth.js` 的 SKIP_AUTH_PATHS（该文件
//   不在本卡 allowed_paths 内，且改它会影响全局）。
// ---------------------------------------------------------------------------

export async function adminAuthRoute(fastify) {
  // ========================================================================
  // T21 · 静态资源（面板页引用的预览图 / 模板 CSS·JS）
  //
  // ★★ 为什么必须【匿名可达】（本卡最关键的结构决策）：
  //   浏览器渲染 `<img src="/images/...">` 与 `<link href="/landing-pages/...">`
  //   时**不会**带上任何 Authorization 头；若把这两条放进受保护的 inner 域，
  //   每个子资源都会被 authMiddleware 拦成 401 ⇒ 用户看到的仍然"预览全是破图"
  //   （即本卡要修的原始故障）。故必须放进本 scope。
  //
  // ★ 域选择的安全性：本 scope 暴露的**只是** `03-web-admin/static/` 下的
  //   公开静态文件（图片/样式/脚本），不含任何管理数据端点；
  //   真实的管理台数据面仍由 `adminRoute`（受保护域）承担，不受影响。
  //
  // ★ 注册位置：本函数由 `plugins/android/index.js:48` 在
  //   **受保护 inner 域之前**注册（见该文件注释与 `admin.js` 的结构说明），
  //   天然满足"自己的 register 内、先于 authMiddleware"。
  //
  // ★ 只读：仅 stream 已存在的普通文件，绝不写入/创建。
  // ========================================================================
  const serveStatic = (rootPrefix) => async (request, reply) => {
    const rel = rootPrefix + String(request.params['*'] || '');
    const r = resolveStaticFile(rel);
    // ★ 不把 reason 回显给调用方（避免泄露磁盘结构）；只回状态码。
    if (!r.ok) return reply.code(r.code).send({ error: 'Not Found' });
    try {
      reply.type(staticMimeOf(r.abs));
      // ★ 用流式返回：最大的 JS 有 ~419 KB，避免整文件读进内存。
      return reply.send(createReadStream(r.abs));
    } catch (e) {
      logger.error({ err: e }, 'T21 静态资源读取失败');
      return reply.code(500).send({ error: '服务器内部错误' });
    }
  };

  // ---- GET /images/*          ⇒ 03-web-admin/static/images/* ----
  fastify.get('/images/*', serveStatic('images/'));

  // ---- GET /landing-pages/*   ⇒ 03-web-admin/static/landing-pages/* ----
  fastify.get('/landing-pages/*', serveStatic('landing-pages/'));

  // ★ `admin_login.html:82` 是原生 HTML form POST
  //   ⇒ Content-Type = `application/x-www-form-urlencoded`。
  //   本进程【未】注册 @fastify/formbody（node_modules 中无此包，且 app.js
  //   不在本卡 allowed_paths 内），故在此【本 scope 内】加一个 urlencoded
  //   解析器。addContentTypeParser 只影响本 register 的封装范围，
  //   不会波及 apiPlugin / landing 等其它路由。
  fastify.addContentTypeParser(
    'application/x-www-form-urlencoded',
    { parseAs: 'string' },
    (req, body, done) => {
      try {
        const out = {};
        for (const [k, v] of new URLSearchParams(String(body || ''))) out[k] = v;
        done(null, out);
      } catch (e) {
        done(e, undefined);
      }
    }
  );

  // ---- GET ${ADMIN}/login —— 【HTML 登录页】（非 JSON API）----
  // 硬证据 `admin_login.html:82`：原生 form POST 回本路径。
  fastify.get('/mgr-admin-8bcde2021d98/login', async (request, reply) => {
    const htmlPath = resolveLoginHtmlPath();
    if (!htmlPath) {
      logger.error({}, 'D1-C5b 登录页 admin_login.html 定位失败');
      return reply.code(500).send({ error: '服务器内部错误', detail: '登录页不可用' });
    }
    try {
      reply.type('text/html; charset=utf-8');
      return readFileSync(htmlPath, 'utf8');
    } catch (e) {
      logger.error({ err: e }, 'D1-C5b 登录页读取失败');
      return reply.code(500).send({ error: '服务器内部错误', detail: '登录页不可用' });
    }
  });

  // ---- POST ${ADMIN}/login —— 表单提交，成功后 302 到面板页 ----
  // ★ 凭据校验与会话签发【复用】既有设施（core/auth/session.js），
  //   与既有 `POST /api/auth/login` 同源（同一 users 集合、同一 JWT_SECRET）。
  // ★ 前端是原生 form POST（x-www-form-urlencoded），非 JSON。
  fastify.post('/mgr-admin-8bcde2021d98/login', async (request, reply) => {
    const body = request.body || {};
    const username = str(body.username);
    const password = typeof body.password === 'string' ? body.password : '';

    const fail = () => {
      reply.code(401).type('text/html; charset=utf-8');
      return '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">'
        + '<title>登录失败</title></head><body style="background:#0f0f12;color:#eee;'
        + 'font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh">'
        + '<div><p>用户名或密码错误</p>'
        + '<p><a style="color:#bf95f7" href="/mgr-admin-8bcde2021d98/login">返回登录</a></p>'
        + '</div></body></html>';
    };

    if (!username || !password) return fail();

    try {
      const user = await User.findOne({ username });
      if (!user || user.status === 'disabled') return fail();

      const ok = await bcrypt.compare(password, user.passwordHash);
      if (!ok) {
        logger.info({ username, ip: getRealIP(request) }, 'D1-C5b 管理台登录失败：密码错误');
        return fail();
      }

      // ★ 登录成功后同步既有 /api/auth/login 返回的 JSON 形态也兼容：
      //   若请求方是 fetch（Accept: application/json），回 JSON；否则回 302。
      const session = await issueLoginSession({ user, request });
      setLoginCookies(reply, session);
      logger.info({ username: user.username, ip: getRealIP(request) }, 'D1-C5b 管理台登录成功');

      const wantsJson = String(request.headers.accept || '').includes('application/json')
        || (request.headers['content-type'] || '').includes('application/json');
      if (wantsJson) return { success: true, user: session.user };
      return reply.redirect(DASHBOARD_PATH, 302);
    } catch (err) {
      logger.error({ err }, 'D1-C5b 管理台登录异常');
      return reply.code(500).type('text/html; charset=utf-8')
        .send('<p>服务器内部错误</p>');
    }
  });

  // ---- GET ${ADMIN}/logout —— 清会话 + 回登录页 ----
  // 前端 `:414` 是浏览器直接导航（<a href>），故用 302 而非 JSON。
  fastify.get('/mgr-admin-8bcde2021d98/logout', async (request, reply) => {
    const COOKIE_OPTS = getAuthCookieOptions();
    try {
      const refreshToken = request.cookies?.refreshToken;
      if (refreshToken) {
        await User.updateOne(
          { 'sessions.refreshToken': refreshToken },
          { $pull: { sessions: { refreshToken } } }
        ).catch(() => {});
      }
      const accessToken = request.cookies?.accessToken;
      if (accessToken) {
        try {
          const decoded = jwt.decode(accessToken);
          if (decoded && decoded.jti && decoded.exp) {
            const ttl = decoded.exp - Math.floor(Date.now() / 1000);
            if (ttl > 0) await getRedis().set(`blacklist:jti:${decoded.jti}`, '1', 'EX', ttl);
          }
        } catch {
          // 解码失败忽略，不影响登出
        }
      }
    } catch (err) {
      logger.error({ err }, 'D1-C5b 登出异常（仍清除 cookie）');
    }
    reply.clearCookie('accessToken', COOKIE_OPTS);
    reply.clearCookie('refreshToken', { ...COOKIE_OPTS, path: '/api/auth/refresh' });
    logger.info({ ip: getRealIP(request) }, 'D1-C5b 管理台登出');
    return reply.redirect('/mgr-admin-8bcde2021d98/login', 302);
  });
}
