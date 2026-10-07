import {
  existsSync, statSync, readdirSync, unlinkSync,
  mkdirSync, createWriteStream, renameSync, realpathSync,
} from 'node:fs';
import { pipeline } from 'node:stream/promises';
import path from 'node:path';
import { logger } from '../../core/logger/index.js';
import { getRealIP } from '../../core/utils/ip.js';
import { classifyArtifact, versionFromFilename } from './services/pick-ipa.js';

/**
 * IPA 投放端点 —— 管理台侧（卡 T119 · IPA-1）。
 *
 * ★ 同构 APK 侧（`plugins/android/admin.js` 的 D1-C3 / D1-C5b）：
 *   文件系统存储 `.ipa`，`id` 用「目录绝对路径 + 文件名」base64url 编码，
 *   防目录穿越与同名碰撞。前缀与 APK 侧一致：`/mgr-admin-8bcde2021d98`（逐字符保留）。
 *
 * ★ 鉴权：本文件三条端点【需鉴权 + superAdmin】——
 *   由 `plugins/ios/index.js` 把它们关进 authMiddleware 的受保护域，
 *   全局 preHandler 会校验 accessToken 并对 `${ADMIN}/**` 做 superAdmin RBAC。
 *
 * ★ 与 APK 侧的差异（如实声明）：
 *   - 后缀 `.ipa`（非 `.apk`）；字段名 `ipa`（非 `apk`）。
 *   - list 额外给【文件名侧推断】的 version / generation（非 dylib 指纹实测）。
 */

export const IPA_ADMIN_API = '/mgr-admin-8bcde2021d98/api/ipa';

/** 上传大小上限。IPA 含 dylib，最大 ~100MB；留余量取 200MB。 */
export const IPA_UPLOAD_MAX_BYTES = 200 * 1024 * 1024;

/**
 * 候选目录列表（★ 同构 apkCandidateDirs，换 .ipa 后缀与目录名）。
 * 顺序：env LANDING_IPA_PATH › <cwd>/templates/ipa › <cwd>/public/ipa。
 */
export function ipaCandidateDirs() {
  const configured = String(process.env.LANDING_IPA_PATH || '').trim();
  return [
    [configured, 'env:LANDING_IPA_PATH'],
    [path.join(process.cwd(), 'templates', 'ipa'), `cwd:${path.join(process.cwd(), 'templates', 'ipa')}`],
    [path.join(process.cwd(), 'public', 'ipa'), `cwd:${path.join(process.cwd(), 'public', 'ipa')}`],
  ].filter(([dir]) => Boolean(dir));
}

function encodeIpaId(dir, name) {
  return Buffer.from(`${dir}\u0000${name}`, 'utf8').toString('base64url');
}

/**
 * 解码并安全校验 ipa id（防目录穿越，同构 resolveApkId）。
 * @returns {{dir:string, name:string, full:string}|null}
 */
export function resolveIpaId(id) {
  const raw = typeof id === 'string' ? id.trim() : '';
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
  if (!name || name !== path.basename(name)) return null;
  if (!name.toLowerCase().endsWith('.ipa')) return null;
  if (name.includes('..')) return null;

  const dirResolved = path.resolve(dir);
  const allowed = ipaCandidateDirs().map(([d]) => path.resolve(d));
  if (!allowed.includes(dirResolved)) return null;

  const full = path.resolve(dirResolved, name);
  const rel = path.relative(dirResolved, full);
  if (rel.startsWith('..') || path.isAbsolute(rel)) return null;

  return { dir: dirResolved, name, full };
}

/** 扫描候选目录，返回按 uploaded_at【新→旧】排序的 files 列表（含 version/generation）。 */
export function listIpaFiles() {
  const out = [];
  const seen = new Set();
  for (const [dir] of ipaCandidateDirs()) {
    try {
      if (!existsSync(dir)) continue;
      if (!statSync(dir).isDirectory()) continue;
      for (const name of readdirSync(dir)) {
        if (!name.toLowerCase().endsWith('.ipa')) continue;
        const full = path.join(dir, name);
        const key = path.resolve(full).toLowerCase();
        if (seen.has(key)) continue;
        seen.add(key);
        let st;
        try {
          st = statSync(full);
        } catch {
          continue;
        }
        if (!st.isFile()) continue;
        const cls = classifyArtifact(name);
        const v = versionFromFilename(name);
        out.push({
          id: encodeIpaId(dir, name),
          original_name: name,
          size: st.size,
          uploaded_at: new Date(st.mtimeMs).toISOString(),
          // ★ 文件名侧推断（非 dylib 指纹实测）；无法判定如实给 null
          version: v ? v.join('.') : null,
          generation: cls.generation,
          needs_kernel: cls.needsKernel,
        });
      }
    } catch (e) {
      logger.error({ err: e, dir }, 'T119 ipa/list 扫描目录失败');
    }
  }
  out.sort((a, b) => (a.uploaded_at < b.uploaded_at ? 1 : a.uploaded_at > b.uploaded_at ? -1 : 0));
  return out;
}

/** 文件名净化 + 后缀校验（同构 sanitizeApkFilename，换 .ipa）。 */
export function sanitizeIpaFilename(raw) {
  const original = typeof raw === 'string' ? raw : '';
  if (!original || original.includes('\u0000')) {
    return { ok: false, error: '文件名非法' };
  }
  if (/[\u0000-\u001f\u007f"']/.test(original)) {
    return { ok: false, error: '文件名含非法字符' };
  }
  if (original.includes('/') || original.includes('\\') || original.includes('..')) {
    return { ok: false, error: '文件名不得包含路径分隔符' };
  }
  const base = path.basename(original);
  if (base !== original) {
    return { ok: false, error: '文件名不得包含路径' };
  }
  if (base === '.' || base === '..') {
    return { ok: false, error: '文件名非法' };
  }
  const dot = base.lastIndexOf('.');
  const stem = dot > 0 ? base.slice(0, dot).trim() : '';
  if (dot <= 0 || !stem) {
    return { ok: false, error: '缺少文件名' };
  }
  if (!base.toLowerCase().endsWith('.ipa')) {
    return { ok: false, error: '只接受 .ipa 文件' };
  }
  if (Buffer.byteLength(base, 'utf8') > 200) {
    return { ok: false, error: '文件名过长' };
  }
  return { ok: true, name: base };
}

/** 选定落盘目录（与 ipaCandidateDirs 同源，取第一个，不存在则创建）。 */
export function resolveUploadDir() {
  const cands = ipaCandidateDirs();
  if (!cands.length) return { ok: false, error: '未配置 IPA 目录' };
  const dir = path.resolve(cands[0][0]);
  try {
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    if (!statSync(dir).isDirectory()) return { ok: false, error: 'IPA 目录不可用' };
  } catch (e) {
    logger.error({ err: e, dir }, 'T119 创建/校验 IPA 目录失败');
    return { ok: false, error: 'IPA 目录不可用' };
  }
  return { ok: true, dir };
}

/** 落盘路径必须在候选目录内。 */
export function safeJoinInside(dir, name) {
  const dirResolved = path.resolve(dir);
  const full = path.resolve(dirResolved, name);
  const rel = path.relative(dirResolved, full);
  if (rel.startsWith('..') || path.isAbsolute(rel) || rel === '') return null;
  if (rel.includes(path.sep)) return null;
  return full;
}

/** 不覆盖已有文件：同名时追加 -1、-2 …（上限 100 次）。 */
export function pickNonClobberingPath(dir, name) {
  const ext = '.ipa';
  const stem = name.slice(0, name.length - ext.length);
  for (let i = 0; i < 100; i++) {
    const tryName = i === 0 ? name : `${stem}-${i}${ext}`;
    const full = safeJoinInside(dir, tryName);
    if (!full) return { ok: false, error: '文件名非法' };
    if (!existsSync(full)) return { ok: true, full, name: tryName };
  }
  return { ok: false, error: '同名文件过多，请更换文件名' };
}

export async function ipaAdminRoute(fastify) {
  // -------------------------------------------------------------------------
  // 1 · GET ${ADMIN}/api/ipa/list
  // -------------------------------------------------------------------------
  fastify.get('/mgr-admin-8bcde2021d98/api/ipa/list', async (request, reply) => {
    try {
      return { files: listIpaFiles() };
    } catch (err) {
      logger.error({ err }, 'T119 ipa/list 失败');
      return reply.code(500).send({ error: '服务器内部错误' });
    }
  });

  // -------------------------------------------------------------------------
  // 2 · POST ${ADMIN}/api/ipa/delete   body { id }
  // -------------------------------------------------------------------------
  fastify.post('/mgr-admin-8bcde2021d98/api/ipa/delete', async (request, reply) => {
    const body = request.body || {};
    const target = resolveIpaId(body.id);
    if (!target) {
      logger.warn({ id: String(body.id ?? '') }, 'T119 ipa/delete 拒绝非法 id（路径校验未过）');
      return reply.code(400).send({ error: 'id 非法' });
    }
    try {
      if (!existsSync(target.full)) {
        return reply.code(404).send({ error: '文件不存在' });
      }
      const st = statSync(target.full);
      if (!st.isFile() || !target.name.toLowerCase().endsWith('.ipa')) {
        return reply.code(400).send({ error: 'id 非法' });
      }
      unlinkSync(target.full);
      logger.warn({ file: target.full }, 'T119 ipa/delete 已删除 IPA 文件（破坏性操作）');
      return { ok: true };
    } catch (err) {
      logger.error({ err }, 'T119 ipa/delete 失败');
      return reply.code(500).send({ error: '服务器内部错误' });
    }
  });

  // -------------------------------------------------------------------------
  // 3 · POST ${ADMIN}/api/ipa/upload   multipart/form-data  field="ipa"
  // -------------------------------------------------------------------------
  fastify.post('/mgr-admin-8bcde2021d98/api/ipa/upload', async (request, reply) => {
    if (typeof request.file !== 'function') {
      logger.error({}, 'T119 ipa/upload：request.file 不可用（multipart 未注册？）');
      return reply.code(500).send({ ok: false, error: '服务器内部错误' });
    }
    if (!request.isMultipart || !request.isMultipart()) {
      return reply.code(400).send({ ok: false, error: '须为 multipart/form-data' });
    }

    let part;
    try {
      part = await request.file({ limits: { fileSize: IPA_UPLOAD_MAX_BYTES, files: 1 } });
    } catch (err) {
      logger.warn({ err }, 'T119 ipa/upload 解析 multipart 失败');
      return reply.code(400).send({ ok: false, error: '文件过大或格式错误' });
    }
    if (!part) {
      return reply.code(400).send({ ok: false, error: '未收到文件（字段名须为 ipa）' });
    }
    if (part.fieldname !== 'ipa') {
      try { part.file.resume(); } catch { /* ignore */ }
      return reply.code(400).send({ ok: false, error: '字段名须为 ipa' });
    }

    const sane = sanitizeIpaFilename(part.filename);
    if (!sane.ok) {
      try { part.file.resume(); } catch { /* ignore */ }
      logger.warn(
        { filename: String(part.filename ?? ''), ip: getRealIP(request) },
        'T119 ipa/upload 拒绝非法文件名'
      );
      return reply.code(400).send({ ok: false, error: sane.error });
    }

    const dirRes = resolveUploadDir();
    if (!dirRes.ok) {
      try { part.file.resume(); } catch { /* ignore */ }
      return reply.code(500).send({ ok: false, error: dirRes.error });
    }

    const target = pickNonClobberingPath(dirRes.dir, sane.name);
    if (!target.ok) {
      try { part.file.resume(); } catch { /* ignore */ }
      return reply.code(400).send({ ok: false, error: target.error });
    }
    const allowed = ipaCandidateDirs().map(([d]) => path.resolve(d));
    const targetDir = path.resolve(path.dirname(target.full));
    if (!allowed.includes(targetDir)) {
      try { part.file.resume(); } catch { /* ignore */ }
      logger.warn({ target: target.full }, 'T119 ipa/upload 拒绝越界落盘路径');
      return reply.code(400).send({ ok: false, error: '文件名非法' });
    }

    const tmpFull = `${target.full}.part`;
    let written = 0;
    try {
      part.file.on('data', (c) => { written += c.length; });
      await pipeline(part.file, createWriteStream(tmpFull));
    } catch (err) {
      try { unlinkSync(tmpFull); } catch { /* ignore */ }
      const tooLarge = part.file.truncated
        || err?.code === 'FST_REQ_FILE_TOO_LARGE'
        || /too large|limit/i.test(String(err?.message || ''));
      logger.warn(
        { err: String(err?.message || err), written, filename: sane.name },
        tooLarge ? 'T119 ipa/upload 拒绝超限文件' : 'T119 ipa/upload 落盘失败'
      );
      if (tooLarge) {
        return reply.code(413).send({
          ok: false, error: `文件超过上限 ${Math.floor(IPA_UPLOAD_MAX_BYTES / 1024 / 1024)}MB`,
        });
      }
      return reply.code(500).send({ ok: false, error: '写入失败' });
    }

    if (part.file.truncated) {
      try { unlinkSync(tmpFull); } catch { /* ignore */ }
      logger.warn({ written }, 'T119 ipa/upload 流被截断');
      return reply.code(413).send({
        ok: false, error: `文件超过上限 ${Math.floor(IPA_UPLOAD_MAX_BYTES / 1024 / 1024)}MB`,
      });
    }

    let size = written;
    try {
      renameSync(tmpFull, target.full);
      size = statSync(target.full).size;
    } catch (err) {
      try { unlinkSync(tmpFull); } catch { /* ignore */ }
      logger.error({ err, target: target.full }, 'T119 ipa/upload 收尾 rename 失败');
      return reply.code(500).send({ ok: false, error: '写入失败' });
    }

    try {
      const realDir = realpathSync(targetDir);
      const realFull = realpathSync(target.full);
      const rel = path.relative(realDir, realFull);
      if (rel.startsWith('..') || path.isAbsolute(rel)) {
        try { unlinkSync(target.full); } catch { /* ignore */ }
        logger.warn({ target: target.full, realFull }, 'T119 ipa/upload realpath 逃逸，已回滚');
        return reply.code(400).send({ ok: false, error: '文件名非法' });
      }
    } catch (err) {
      logger.warn({ err, target: target.full }, 'T119 ipa/upload realpath 复核异常（已落盘）');
    }

    logger.info({ file: target.full, size, ip: getRealIP(request) }, 'T119 ipa/upload 落盘成功');
    return { ok: true, filename: target.name, size };
  });
}
