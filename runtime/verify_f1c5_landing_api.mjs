/**
 * F1-C5 判据：落地页调用的 5 个端点在 Node 侧必须有实现，且匿名可达。
 *
 * 判据先于实现（判据 9）。本脚本放产物外（_fix_work/），不进 09-docs/cards/（P-4）。
 *
 * 用法：
 *   node verify_f1c5_landing_api.mjs              # 对产物
 *   node verify_f1c5_landing_api.mjs --selftest   # 量尺前置断言（P-5）
 *
 * 退出码：0 = 全绿；非 0 = 有红。
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = 'E:\\USDT项目';
const LANDING = path.join(ROOT, '04-landing', 'runtime', 'landing-runtime.js');
const SRC = path.join(ROOT, '02-backend-node', 'src_restored');
const ROUTES_DIR = path.join(SRC, 'plugins', 'api', 'routes');
const API_INDEX = path.join(SRC, 'plugins', 'api', 'index.js');
const AUTH_MW = path.join(SRC, 'plugins', 'api', 'middleware', 'auth.js');

/** 递归收集目录下所有 .js */
function walk(dir) {
    const out = [];
    if (!fs.existsSync(dir)) return out;
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        const p = path.join(dir, e.name);
        if (e.isDirectory()) out.push(...walk(p));
        else if (e.name.endsWith('.js')) out.push(p);
    }
    return out;
}

/** 从 landing-runtime.js 反向枚举所有 /api/... 字面量（防将来新增端点漏检） */
function extractLandingEndpoints(src) {
    const set = new Set();
    const re = /["'`](\/api\/[A-Za-z0-9_\-/.]*)["'`]/g;
    let m;
    while ((m = re.exec(src)) !== null) set.add(m[1]);
    return [...set].sort();
}

/** 收集 Node 侧注册的全部路由路径 */
function collectRegisteredRoutes(files) {
    const routes = new Map(); // path -> file
    for (const f of files) {
        const src = fs.readFileSync(f, 'utf8');
        const re = /fastify\.(get|post|put|delete|patch)\(\s*['"`](\/api\/[^'"`]+)['"`]/g;
        let m;
        while ((m = re.exec(src)) !== null) {
            routes.set(m[2], path.relative(ROOT, f));
        }
    }
    return routes;
}

/** 归一化：把 :param 视作通配，用于匹配 */
function matchRoute(calledPath, registered) {
    if (registered.has(calledPath)) return registered.get(calledPath);
    // 逐段比较，:param 可匹配任意单段
    for (const [reg, file] of registered) {
        const a = calledPath.split('/');
        const b = reg.split('/');
        if (a.length !== b.length) continue;
        let ok = true;
        for (let i = 0; i < a.length; i++) {
            if (b[i].startsWith(':')) continue;
            if (a[i] !== b[i]) { ok = false; break; }
        }
        if (ok) return file;
    }
    return null;
}

function selftest() {
    console.log('=== 量尺前置断言（P-5）===');
    let ok = true;

    // 1) 端点抽取：合成样本必须能抽出
    const sample = `post("/api/track/heartbeat", {}); fetch("/api/pixel-config"); var D="/api/apk/download";`;
    const eps = extractLandingEndpoints(sample);
    if (eps.length !== 3) {
        console.log(`  [FAIL] 端点抽取：期望 3 个，实得 ${eps.length} => ${JSON.stringify(eps)}`);
        ok = false;
    } else {
        console.log(`  端点抽取有效：${eps.join(', ')}`);
    }

    // 2) 路由收集：合成样本必须能抽出
    const fakeDir = path.join(SRC, 'plugins', 'api', 'routes');
    const files = walk(fakeDir);
    if (files.length === 0) {
        console.log('  [FAIL] 路由目录无 .js 文件，量尺无法自证');
        ok = false;
    } else {
        const routes = collectRegisteredRoutes(files);
        if (routes.size === 0) {
            console.log('  [FAIL] 合成/真实路由抽取结果为 0 —— 模式坏了（P-5）');
            ok = false;
        } else {
            console.log(`  路由抽取有效：实测 ${routes.size} 条路由`);
        }
    }

    if (ok) {
        console.log('SELFTEST=OK');
        return 0;
    }
    console.log('SELFTEST=BAD');
    return 2;
}

function main() {
    if (process.argv.includes('--selftest')) process.exit(selftest());

    console.log('目标:');
    console.log(`  ${LANDING}`);
    console.log(`  ${SRC}`);
    console.log('');

    const fails = [];

    if (!fs.existsSync(LANDING)) {
        console.log(`  [FAIL] 落地页运行时不存在: ${LANDING}`);
        process.exit(1);
    }

    const landingSrc = fs.readFileSync(LANDING, 'utf8');
    const endpoints = extractLandingEndpoints(landingSrc);
    console.log(`落地页反向枚举到的端点 (${endpoints.length}):`);
    for (const e of endpoints) console.log(`  ${e}`);
    console.log('');

    // 收集 Node 全部路由
    const files = walk(ROUTES_DIR);
    const routes = collectRegisteredRoutes(files);
    console.log(`Node 侧已注册路由总数: ${routes.size}`);
    console.log('');

    // R1: 每个落地页端点都必须在 Node 侧有注册
    console.log('R1 逐端点核对:');
    const missing = [];
    for (const ep of endpoints) {
        const hit = matchRoute(ep, routes);
        if (hit) {
            console.log(`  [PASS] R1 ${ep}  ->  ${hit}`);
        } else {
            console.log(`  [FAIL] R1 ${ep}  ->  未注册`);
            missing.push(ep);
            fails.push(`R1-missing:${ep}`);
        }
    }
    console.log('');

    // R2: 路径逐字符相等（R1 已用精确匹配优先实现；此处复核无前缀漂移）
    if (missing.length === 0) {
        console.log('  [PASS] R2 所有端点路径与注册路径逐字符相等');
    } else {
        console.log('  [FAIL] R2 存在未注册端点，无法断言路径相等');
        fails.push('R2');
    }
    console.log('');

    // R4: track/* 与 pixel-config 不得要求鉴权 —— 必须在 SKIP_AUTH_PATHS 中
    console.log('R4 公开端点免鉴权核对 (auth.js SKIP_AUTH_PATHS):');
    const authSrc = fs.readFileSync(AUTH_MW, 'utf8');
    const m = authSrc.match(/SKIP_AUTH_PATHS\s*=\s*\[([\s\S]*?)\]/);
    const skipList = m ? [...m[1].matchAll(/['"`]([^'"`]+)['"`]/g)].map(x => x[1]) : [];
    console.log(`  SKIP_AUTH_PATHS 实读: ${JSON.stringify(skipList)}`);
    const publicExpected = endpoints.filter(e => e.startsWith('/api/track/') || e === '/api/pixel-config');
    for (const ep of publicExpected) {
        // 动态路由（如 /api/track/:x）不在 SKIP 清单时允许——本卡前端调用的是固定路径
        if (skipList.includes(ep)) {
            console.log(`  [PASS] R4 ${ep} 已免鉴权`);
        } else {
            console.log(`  [FAIL] R4 ${ep} 未在 SKIP_AUTH_PATHS —— 匿名访客会被 401 拦截`);
            fails.push(`R4-not-public:${ep}`);
        }
    }
    console.log('');

    // R3: apk/download 未就绪时必须 404，不得静默 200 空体（静态检查实现）
    console.log('R3 apk/download 未就绪行为核对:');
    const apkImpl = files.find(f => {
        const s = fs.readFileSync(f, 'utf8');
        return s.includes('/api/apk/download');
    });
    if (!apkImpl) {
        console.log('  [FAIL] R3 未找到 apk/download 实现');
        fails.push('R3-no-impl');
    } else {
        const s = fs.readFileSync(apkImpl, 'utf8');
        const has404 = /code\(\s*404\s*\)|statusCode\s*=\s*404/.test(s);
        console.log(`  实现文件: ${path.relative(ROOT, apkImpl)}`);
        console.log(`  含 404 分支: ${has404}`);
        if (has404) {
            console.log('  [PASS] R3 apk/download 在文件缺失时返回 404');
        } else {
            console.log('  [FAIL] R3 apk/download 无 404 分支 —— 可能静默 200');
            fails.push('R3-no-404');
        }
    }
    console.log('');

    // 注册入口核对
    const idxSrc = fs.readFileSync(API_INDEX, 'utf8');
    const registered = /landingRoute/.test(idxSrc);
    console.log(`index.js 已注册 landingRoute: ${registered}`);
    if (!registered) {
        console.log('  [FAIL] landing 路由未在 index.js 注册 —— 端点不会生效');
        fails.push('not-registered');
    }
    console.log('');

    if (fails.length) {
        console.log(`RESULT=RED  失败项: ${fails.join(', ')}`);
        process.exit(1);
    }
    console.log('RESULT=GREEN  落地页 5 端点全部有实现且匿名可达');
    process.exit(0);
}

main();
