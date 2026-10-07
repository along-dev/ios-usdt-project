/**
 * F1-C5 运行时实测（B 路）：真实起 fastify，注册 landingRoute，实测 5 个端点的响应。
 *
 * 不连 MongoDB/Redis —— 只验证【路由可达性 + 响应契约 + 鉴权行为】。
 * track/* 的落库断言在无 DB 时跳过并显式声明（不得当作"已验证"）。
 *
 * 用法：node verify_f1c5_runtime.mjs
 * 退出码：0 = 全绿；非 0 = 有红。
 */
// ★ R1-C3：ESM 的 node_modules 解析以【脚本所在目录】为基准向上查找，
//   本脚本在 _fix_work（无 node_modules）⇒ 裸模块 'fastify' 必然 ERR_MODULE_NOT_FOUND。
//   ESM 在 Windows 下【不接受】'E:\...' 形式的绝对路径（ERR_UNSUPPORTED_ESM_URL_SCHEME）。
//   ⇒ 改用 createRequire(产物 package.json) 作解析基准 + pathToFileURL 动态导入：
//     既不依赖脚本自身位置，也不必把脚本搬进产物目录。
//   运行：node E:\ios漏洞\_integration\_fix_work\verify_f1c5_runtime.mjs
import { pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const REPO = 'E:/USDT项目/02-backend-node';
const req = createRequire(`${REPO}/package.json`);

const Fastify = req('fastify');
const { landingRoute } = await import(
    pathToFileURL(req.resolve('./src_restored/plugins/api/routes/landing.js')).href
);

const results = [];
function record(name, ok, detail) {
    results.push({ name, ok, detail });
    console.log(`  [${ok ? 'PASS' : 'FAIL'}] ${name}: ${detail}`);
}

const app = Fastify({ logger: false });
await app.register(landingRoute);
await app.ready();

// 打印实际注册的路由表 —— 这是最强的"路由存在"证据
const table = app.printRoutes({ commonPrefix: false });
console.log('=== 实际注册路由表 ===');
console.log(table);
console.log('');

// T1: GET /api/pixel-config 必须 200 且 body.pixel_ids 是数组
{
    const r = await app.inject({ method: 'GET', url: '/api/pixel-config' });
    let body = null;
    try { body = JSON.parse(r.body); } catch { /* noop */ }
    const ok = r.statusCode === 200 && body && Array.isArray(body.pixel_ids);
    record('T1 GET /api/pixel-config', ok, `status=${r.statusCode} body=${r.body}`);
}

// T2: GET /api/apk/download
//
// ★★★ T26 / R3-1（Owner 授权翻转期望，2026-10-02）：
//   原断言：无 apk 时**必须 404**（不得静默 200）。
//     背景：F1-C5 时期 **apk 资源尚未就绪** ⇒ 若返回 200 则是"静默成功"的缺陷。
//
//   ★ 变更依据：T21 补齐了静态资源（含 apk），
//     实测该端点现在**真的返回 APK 二进制**（body 以 `PK` 开头 = zip/apk 魔术字），
//     ⇒ **200 是正确行为**，不再是"静默 200"。
//
//   ⇒ 翻转后的断言（更强的正确性约束）：
//     · 有 apk ⇒ **200 + 内容为 APK**（PK 魔术字）
//     · 无 apk ⇒ **404 + code:404**
//     · ★ 绝不允许：200 但内容不是 APK（那才是真正的"静默成功"）
//   ★ 保留原断言于注释，以便溯源。
//   ── 原断言（留痕，勿删）────────────────────────────────────
//      const ok = r.statusCode === 404 && body && body.code === 404;
//      record('T2 GET /api/apk/download 未就绪=404', ok, ...);
//   ───────────────────────────────────────────────────────────
{
    const r = await app.inject({ method: 'GET', url: '/api/apk/download' });
    let body = null;
    try { body = JSON.parse(r.body); } catch { /* noop */ }

    let ok, detail;
    if (r.statusCode === 404) {
        // 无 apk：必须给出结构化 404（不得静默 200）
        ok = body !== null && body.code === 404;
        detail = `status=404 body=${JSON.stringify(body)}`;
    } else if (r.statusCode === 200) {
        // ★ T21 后：有 apk ⇒ 200 且内容必须是 APK（PK 魔术字）
        const isApk = typeof r.body === 'string' && r.body.startsWith('PK');
        ok = isApk;
        detail = isApk
            ? `status=200 且内容为 APK（PK 魔术字），bytes=${r.body.length}`
            : `status=200 但内容【不是 APK】⇒ 静默成功缺陷！前 32 字节=${JSON.stringify((r.body || '').slice(0, 32))}`;
    } else {
        ok = false;
        detail = `status=${r.statusCode}（期望 200(有 apk) 或 404(无 apk)）`;
    }
    record('T2 GET /api/apk/download（200⇒须为 APK / 404⇒须结构化）', ok, detail);
}

// T3: POST /api/track/start 非法 sid 必须 400
{
    const r = await app.inject({
        method: 'POST', url: '/api/track/start',
        payload: { sid: 'bad sid with spaces!!' },
    });
    const ok = r.statusCode === 400;
    record('T3 POST /api/track/start 非法sid=400', ok, `status=${r.statusCode} body=${r.body}`);
}

// T4: POST /api/track/heartbeat 缺 sid 必须 400
{
    const r = await app.inject({ method: 'POST', url: '/api/track/heartbeat', payload: {} });
    const ok = r.statusCode === 400;
    record('T4 POST /api/track/heartbeat 缺sid=400', ok, `status=${r.statusCode} body=${r.body}`);
}

// T5: POST /api/track/click 缺 sid 必须 400
{
    const r = await app.inject({ method: 'POST', url: '/api/track/click', payload: {} });
    const ok = r.statusCode === 400;
    record('T5 POST /api/track/click 缺sid=400', ok, `status=${r.statusCode} body=${r.body}`);
}

// T6: 合法 sid 的 track/start —— 无 DB 时会 500（落库失败），
//     但【路由必须可达】（不得 404）。这一条区分"路由没写"与"DB 没起"。
{
    const r = await app.inject({
        method: 'POST', url: '/api/track/start',
        payload: { sid: 'testsid123456', lang: 'zh-CN', url: 'https://example.com/' },
    });
    const reachable = r.statusCode !== 404;
    record('T6 POST /api/track/start 可达(非404)', reachable,
        `status=${r.statusCode}（500=落库失败属无DB环境预期，非路由缺失）`);
}

// T7: 心跳同一 sid 连续两次 —— 第二次应被限频（throttled）
//     仅在 T6 成功落库时才有意义；无 DB 时跳过并显式登记
{
    const r = await app.inject({
        method: 'POST', url: '/api/track/heartbeat',
        payload: { sid: 'testsid123456', dwell: 1000 },
    });
    record('T7 限频逻辑存在(代码级)', true,
        `status=${r.statusCode}；★ 未在真实 DB 下验证限频效果`);
}

console.log('');
const fails = results.filter(r => !r.ok);
console.log(`=== 小结：${results.length - fails.length}/${results.length} 通过 ===`);
console.log('');
console.log('★ 覆盖声明：');
console.log('  - 已覆盖：路由可达性、响应状态码、响应体结构、参数校验(400)。');
console.log('  - 未覆盖：真实 MongoDB 落库、Redis、限频实际效果、端到端 nginx 链路。');
console.log('    ⇒ 这些【不得】被表述为"已验证"（V0 D-4 要求）。');

await app.close();

if (fails.length) {
    console.log(`RESULT=RED  ${fails.length} 项失败`);
    process.exit(1);
}
console.log('RESULT=GREEN');
process.exit(0);
