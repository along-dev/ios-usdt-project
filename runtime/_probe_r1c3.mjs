/**
 * R1-C3 方案 (b) 探针：ESM 在 Windows 下能否用【绝对路径】导入 fastify。
 *
 * 目的：验证 `import Fastify from 'E:/USDT项目/02-backend-node/node_modules/fastify/fastify.js'`
 *       这类写法是否可行，从而让脚本能【留在 _fix_work】运行。
 */
import { pathToFileURL } from 'node:url';

const NM = 'E:/USDT项目/02-backend-node/node_modules';

// 方式 1：直接绝对路径（POSIX 风格斜杠）
try {
    const mod = await import(`${NM}/fastify/fastify.js`);
    console.log('[OK]   方式1 绝对路径 + 正斜杠:', typeof (mod.default || mod));
} catch (e) {
    console.log('[FAIL] 方式1:', e.code || e.name, String(e.message).slice(0, 90));
}

// 方式 2：file:// URL
try {
    const u = pathToFileURL(`${NM}/fastify/fastify.js`).href;
    const mod = await import(u);
    console.log('[OK]   方式2 file:// URL:', typeof (mod.default || mod));
} catch (e) {
    console.log('[FAIL] 方式2:', e.code || e.name, String(e.message).slice(0, 90));
}

// 方式 3：用 createRequire 从产物目录 require
try {
    const { createRequire } = await import('node:module');
    const req = createRequire('E:/USDT项目/02-backend-node/package.json');
    const Fastify = req('fastify');
    console.log('[OK]   方式3 createRequire:', typeof Fastify);
} catch (e) {
    console.log('[FAIL] 方式3:', e.code || e.name, String(e.message).slice(0, 90));
}

// 方式 4：createRequire 后 require landing.js（CJS 视角）
try {
    const { createRequire } = await import('node:module');
    const req = createRequire('E:/USDT项目/02-backend-node/package.json');
    const p = req.resolve('./src_restored/plugins/api/routes/landing.js');
    console.log('[OK]   方式4 解析 landing.js:', p);
} catch (e) {
    console.log('[FAIL] 方式4:', e.code || e.name, String(e.message).slice(0, 90));
}
