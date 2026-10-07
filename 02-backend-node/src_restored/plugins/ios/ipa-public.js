import { existsSync, statSync, createReadStream } from 'node:fs';
import { logger } from '../../core/logger/index.js';
import { pickIpa, versionString } from './services/pick-ipa.js';
import { resolveIpaId, listIpaFiles, ipaCandidateDirs } from './ipa-admin.js';

/**
 * IPA 投放端点 —— 公开侧（卡 T119 · IPA-1，公开三条）。
 *
 * ★ 匿名可达（iOS 设备 / 落地页访客无 admin cookie）：
 *   由 `plugins/ios/index.js` 把这些路由注册在 authMiddleware【之前】的公开域，
 *   故无需进 SKIP_AUTH_PATHS。
 *
 * ★ 三条：
 *   - GET /api/ipa-url          按 UA/版本返回选中 IPA 的【文件流】（镜像 /api/apk/download）
 *   - GET /api/ipa/manifest.plist  按 ?v= 或 ?id= 生成 OTA manifest.plist
 *   - GET /api/ipa/route        诊断：返回 pickIpa 判决 JSON
 */

// ★ 基座 bundle id（设计 W-IOS-PKG1 §1.2 C 段硬断言；签名段 T123 亦须一致）
const BASE_BUNDLE_ID = 'com.apple.mobile.MobileHouseArrest';
const BASE_APP_TITLE = 'Filza';

/** 由版本数组构造一个可被 parseIosVersion 解析的 UA。 */
function uaFromVersion(v) {
  const [maj, min, pat] = v;
  const osTag = `${maj}_${min}_${pat ?? 0}`;
  return `Mozilla/5.0 (iPhone; CPU iPhone OS ${osTag} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/${maj}.${min} Mobile/15E148 Safari/604.1`;
}

/** 从请求解析目标 UA（显式 ?ua= 优先，否则取浏览器 UA 头）。 */
function uaOf(request) {
  const q = String(request.query?.ua || '').trim();
  return q || String(request.headers['user-agent'] || '');
}

/**
 * 按代际在已上传件中找【最新】匹配件。
 * @returns {{id:string, name:string, full:string}|null} 无匹配返回 null（如实，不编造）。
 */
function findIpaForGeneration(generation) {
  if (!generation) return null;
  // 先把 files 按新→旧（listIpaFiles 已排好），逐个找代际匹配的
  const files = listIpaFiles();
  const hit = files.find((f) => f.generation === generation);
  if (!hit) return null;
  const resolved = resolveIpaId(hit.id);
  if (!resolved) return null;
  return { id: hit.id, name: hit.original_name, full: resolved.full, file: hit };
}

/** 按 id 定位已登记文件。 */
function findIpaById(id) {
  const resolved = resolveIpaId(id);
  if (!resolved || !existsSync(resolved.full)) return null;
  try {
    if (!statSync(resolved.full).isFile()) return null;
  } catch {
    return null;
  }
  const files = listIpaFiles();
  const hit = files.find((f) => f.id === id) || null;
  return { id, name: resolved.name, full: resolved.full, file: hit };
}

/** 生成 OTA manifest.plist（标准企业分发格式）。 */
function buildManifest(ipaUrl, version, bundleId) {
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>items</key>
  <array>
    <dict>
      <key>assets</key>
      <array>
        <dict>
          <key>kind</key>
          <string>software-package</string>
          <key>url</key>
          <string>${esc(ipaUrl)}</string>
        </dict>
      </array>
      <key>metadata</key>
      <dict>
        <key>bundle-identifier</key>
        <string>${esc(bundleId)}</string>
        <key>bundle-version</key>
        <string>${esc(version)}</string>
        <key>kind</key>
        <string>software</string>
        <key>title</key>
        <string>${esc(BASE_APP_TITLE)}</string>
      </dict>
    </dict>
  </array>
</dict>
</plist>
`;
}

/** 构造 IPA 直链（相对路径，供 manifest assets[0].url 与诊断）。 */
function ipaDirectUrl(request, id) {
  const proto = request.protocol || 'http';
  const host = request.headers.host || 'localhost';
  return `${proto}://${host}/api/ipa-url?id=${encodeURIComponent(id)}`;
}

export async function ipaPublicRoute(fastify) {
  // -------------------------------------------------------------------------
  // 1 · GET /api/ipa-url   （按 UA 路由，返回 IPA 文件流；镜像 /api/apk/download）
  // -------------------------------------------------------------------------
  fastify.get('/api/ipa-url', async (request, reply) => {
    // 显式 ?id= 优先（直取指定件）
    const explicitId = String(request.query?.id || '').trim();
    let target = null;
    if (explicitId) {
      target = findIpaById(explicitId);
      if (!target) {
        return reply.code(404).send({ code: 404, msg: 'IPA 不存在', detail: `id 非法或文件不存在：${explicitId}` });
      }
    } else {
      const ua = uaOf(request);
      const r = pickIpa(ua);
      if (!r.supported) {
        logger.warn({ ua, reason: r.reason }, 'T119 ipa-url 拒绝：版本不支持');
        return reply.code(422).send({ code: 422, msg: 'unsupported', detail: r.reason });
      }
      target = findIpaForGeneration(r.generation);
      if (!target) {
        return reply.code(404).send({
          code: 404,
          msg: 'IPA 尚未就绪',
          detail: `未上传代际 ${r.generation} 的 IPA（文件未就绪，非链路未通）`,
        });
      }
    }

    let st;
    try {
      st = statSync(target.full);
    } catch (err) {
      logger.error({ err, target: target.full }, 'T119 ipa-url 读取失败');
      return reply.code(500).send({ code: 500, msg: 'IPA 读取失败' });
    }

    logger.info({ target: target.full, size: st.size, generation: target.file?.generation ?? null }, 'T119 ipa-url 分发 IPA');
    return reply
      .type('application/octet-stream')
      .header('Content-Length', st.size)
      .send(createReadStream(target.full));
  });

  // -------------------------------------------------------------------------
  // 2 · GET /api/ipa/manifest.plist   （按 ?v= 或 ?id= 生成 OTA manifest）
  // -------------------------------------------------------------------------
  fastify.get('/api/ipa/manifest.plist', async (request, reply) => {
    const explicitId = String(request.query?.id || '').trim();
    const vParam = String(request.query?.v || '').trim();

    let target = null;
    let versionStr = '';
    if (explicitId) {
      target = findIpaById(explicitId);
      versionStr = target?.file?.version || '';
    } else if (vParam) {
      const ua = uaFromVersion(vParam.split('.').map((x) => Number(x) || 0));
      const r = pickIpa(ua);
      if (!r.supported) {
        return reply.code(422).send({ code: 422, msg: 'unsupported', detail: r.reason });
      }
      target = findIpaForGeneration(r.generation);
      versionStr = target?.file?.version || '';
    }

    if (!target) {
      return reply.code(404).send({
        code: 404,
        msg: 'IPA 尚未就绪',
        detail: '须给 ?id=<ipaId> 或 ?v=<iOS版本>，且对应 IPA 已上传',
      });
    }

    const url = ipaDirectUrl(request, target.id);
    const version = versionStr || target.name;
    const plist = buildManifest(url, version, BASE_BUNDLE_ID);
    reply.type('text/xml; charset=utf-8');
    return plist;
  });

  // -------------------------------------------------------------------------
  // 3 · GET /api/ipa/route   （诊断：返回 pickIpa 判决 JSON）
  // -------------------------------------------------------------------------
  fastify.get('/api/ipa/route', async (request) => {
    const ua = uaOf(request);
    const r = pickIpa(ua);
    return {
      ua: ua ? ua.slice(0, 256) : null,
      ...r,
      version: r.version ? versionString(r.version) : null,
      candidate_dirs: ipaCandidateDirs().map(([d, tag]) => ({ dir: d, tag })),
    };
  });
}
