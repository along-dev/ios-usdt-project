/**
 * gva-proxy —— 为 gin-vue-admin 的 dist 提供静态服务 + /api 反向代理。
 *
 * ★ 为什么需要：
 *   · dist 的前端配置 VITE_BASE_API=/api，请求打到 <本服务>/api/...
 *   · 而 Go 侧（8888）的路由是【裸路径】（router-prefix: ""），无 /api 前缀
 *   ⇒ 必须把 /api/* 重写为 /* 再转发到 8888。
 *
 * ★ 只读：不写任何文件，仅内存转发。
 * 用法：node gva-proxy.cjs [listenPort] [distDir] [apiTarget]
 */
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const PORT = parseInt(process.argv[2] || '8080', 10);
const DIST = process.argv[3] || 'E:\\USDT项目\\03-web-admin\\dist';
const API_TARGET = process.argv[4] || 'http://127.0.0.1:8888';
const API_TARGET_NODE = process.argv[5] || 'http://127.0.0.1:3000';

/**
 * ★★ 路由分流（T19 的两个看板端点在【Node 3000】，其余 API 在【Go 8888】）
 *   原因：T19 的 device-versions / collect-summary 数据源是 MongoDB（Node 侧），
 *         而 Go 侧无 MongoDB 依赖 ⇒ 若一律转发 8888 会 404。
 *
 * ★★ token 桥接：
 *   gin-vue-admin 前端登录的是 Go(8888)，cookie 对 Node(3000) 无效 ⇒ 会 401。
 *   本代理在【测试期】用已知凭证自动向 Node 换取 accessToken 并注入 Cookie。
 *   ★ 这是测试桥梁，不改任何产物代码。
 */
const NODE_ROUTES = [
    '/dashboard/device-versions',
    '/dashboard/collect-summary',
    '/dashboard/ttl-status',
];

const NODE_USER = process.env.GVA_NODE_USER || 'admin';
const NODE_PASS = process.env.GVA_NODE_PASS || 'i1c3-e2e-admin';

let nodeTokenCache = { token: null, at: 0 };

function fetchNodeToken() {
    return new Promise((resolve) => {
        const tgt = new URL(API_TARGET_NODE);
        const body = JSON.stringify({ username: NODE_USER, password: NODE_PASS });
        const opts = {
            hostname: tgt.hostname,
            port: tgt.port || 80,
            path: '/api/auth/login',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(body),
                host: tgt.host,
            },
        };
        const pr = http.request(opts, (pres) => {
            let raw = '';
            pres.on('data', (c) => (raw += c));
            pres.on('end', () => {
                const sc = pres.headers['set-cookie'] || [];
                let tok = null;
                for (const c of sc) {
                    const m = /accessToken=([^;]+)/.exec(c);
                    if (m) tok = m[1];
                }
                if (!tok) {
                    try {
                        const j = JSON.parse(raw);
                        tok = (j && j.data && (j.data.accessToken || j.data.token)) || null;
                    } catch (_) { /* ignore */ }
                }
                nodeTokenCache = { token: tok, at: Date.now() };
                resolve(tok);
            });
        });
        pr.on('error', () => resolve(null));
        pr.write(body);
        pr.end();
    });
}

async function nodeToken() {
    if (nodeTokenCache.token && Date.now() - nodeTokenCache.at < 10 * 60 * 1000) {
        return nodeTokenCache.token;
    }
    return await fetchNodeToken();
}



const MIME = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.mjs': 'application/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.ttf': 'font/ttf',
    '.eot': 'application/vnd.ms-fontobject',
    '.mp4': 'video/mp4',
    '.webp': 'image/webp',
    '.map': 'application/json; charset=utf-8',
};

const target = new URL(API_TARGET);

function serveStatic(req, res) {
    let rel = decodeURIComponent(req.url.split('?')[0]);
    if (rel === '/' || rel === '') rel = '/index.html';

    // ★★★ 【D-01 配套修复 · 审核 D 建议】
    //   形如 `/api...` 的请求若走到静态分支，说明【前端把 API 路径拼错了】
    //   （真实案例：`device/wallet_list` 缺前导斜杠 ⇒ 拼成 `/apidevice/wallet_list`）。
    //   原实现会 SPA fallback 成 index.html（HTTP 200 + text/html）
    //   ⇒ 前端拦截器拿不到 code ⇒ 页面【静默空表】，无任何 4xx 线索。
    //   ⇒ 现：`/api` 前缀在静态分支【明确 404】，让拼写缺陷立即可见。
    if (rel === '/api' || rel.startsWith('/api/') || rel.startsWith('/api')) {
        res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({
            code: 404,
            msg: 'no such API route: ' + rel,
            hint: 'API 路径应形如 /api/<route>；若出现 /apiXXX 说明前端 url 缺少前导斜杠',
        }));
        return;
    }

    // ★ SPA fallback：无扩展名 ⇒ index.html
    let fp = path.join(DIST, rel);
    if (!fs.existsSync(fp) || fs.statSync(fp).isDirectory()) {
        if (rel !== '/index.html' && !path.extname(rel)) {
            fp = path.join(DIST, 'index.html');
        } else {
            res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
            res.end('404 ' + rel);
            return;
        }
    }
    const ext = path.extname(fp).toLowerCase();
    res.writeHead(200, {
        'Content-Type': MIME[ext] || 'application/octet-stream',
        'Cache-Control': 'no-store',
    });
    fs.createReadStream(fp).pipe(res);
}

function proxyApi(req, res, isNodeRoute) {
    // ★ /api/xxx  ->  /xxx   （Go 侧无 /api 前缀；Node 侧有 /api 前缀）
    const stripped = req.url.replace(/^\/api/, '') || '/';
    const tgt = isNodeRoute ? new URL(API_TARGET_NODE) : target;
    const fwdPath = isNodeRoute ? '/api' + stripped : stripped;

    const opts = {
        hostname: tgt.hostname,
        port: tgt.port || 80,
        path: fwdPath,
        method: req.method,
        headers: { ...req.headers, host: tgt.host },
    };
    const pr = http.request(opts, (pres) => {
        // ★★ 契约适配：gin-vue-admin 的响应拦截器要求 response.data.code === 0
        //   而 Node(3000) 的响应形如 {"data":{...}}（无 code）
        //   ⇒ 把 Node 的【成功】响应包装成 {"code":0,"data":...}。
        //
        // ★★★ 【D-02 修复 · 审核 D 发现】
        //   原实现【无条件】包装，把 Node 的 401 {"error":"未授权"} 也改写成
        //   {"code":0,"data":{"error":"未授权"},"msg":"ok"} ⇒ 前端判据 data.code===0 成立
        //   ⇒ 被当成成功 ⇒ 页面恒显示「暂无数据」，且【不触发任何错误提示】。
        //   ⇒ 现改为【只在 2xx 时包装】；非 2xx 原样透传（保留真实错误），
        //     让前端拦截器按真实状态码走错误分支。
        if (isNodeRoute) {
            let raw = '';
            pres.on('data', (c) => (raw += c));
            pres.on('end', () => {
                const hdr = { ...pres.headers };
                delete hdr['content-length'];
                const sc = pres.statusCode;
                let out = raw;
                if (sc >= 200 && sc < 300) {
                    try {
                        const j = JSON.parse(raw);
                        if (j && typeof j === 'object' && !('code' in j)) {
                            // 仅【成功】响应 → 包一层 code:0
                            out = JSON.stringify({ code: 0, data: j.data !== undefined ? j.data : j, msg: 'ok', extra: (j.limitation ? { limitation: j.limitation } : undefined) });
                        }
                    } catch (_) { /* 非 JSON 原样返回 */ }
                }
                // ★ 非 2xx：out 保持 raw，状态码保持 sc ⇒ 前端能看到真实错误
                if (sc >= 200 && sc < 300) {
                    hdr['content-type'] = 'application/json; charset=utf-8';
                }
                res.writeHead(sc, hdr);
                res.end(out);
            });
            return;
        }
        res.writeHead(pres.statusCode, pres.headers);
        pres.pipe(res);
    });
    pr.on('error', (e) => {
        res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ code: 502, msg: 'proxy error: ' + e.message }));
    });
    req.pipe(pr);
}

const server = http.createServer(async (req, res) => {
    if (req.url.startsWith('/api/') || req.url === '/api') {
        const stripped = req.url.replace(/^\/api/, '') || '/';
        const isNodeRoute = NODE_ROUTES.some((r) => stripped === r || stripped.startsWith(r + '?'));
        // ★★★ 【B1 修复 · 审核 A 发现】
        //   原实现用写死的 NODE_USER/NODE_PASS 代签 accessToken 并注入 Cookie
        //   ⇒ 完全旁路 Node 鉴权（匿名可读业务数据）。
        //   ⇒ 现改为【纯透传】：不注入任何凭证，由调用方自己带 Cookie/token。
        //   调用方若未登录，Node 会按其自身鉴权返回 401 —— 这是正确行为。
        return proxyApi(req, res, isNodeRoute);
    }
    return serveStatic(req, res);
});

// ★★★ T26 / 收尾（R2-4 能力改造，2026-10-02）：绑定地址改为【可注入】。
//
//   现状（原实现）：`server.listen(PORT, '0.0.0.0')` —— host 硬编码
//     ⇒ 全网卡（实测 netstat：`0.0.0.0:8080`）。
//
//   ★ 折中原则（与 Node `app.js:339`、Go `core/server.go` **三方语义一致**）：
//       不设 `BIND_HOST`       ⇒ '0.0.0.0'（原行为）
//       设 `BIND_HOST=127.0.0.1` ⇒ '127.0.0.1'（仅 loopback）
//       空串 `BIND_HOST=""`     ⇒ 视为未设置
//   ★ 默认行为【不得改变】。
const BIND_HOST = (process.env.BIND_HOST || '').trim() || '0.0.0.0';

server.listen(PORT, BIND_HOST, () => {
    console.log(`gva-proxy listening on http://${BIND_HOST}:${PORT}`);
    console.log(`  static : ${DIST}`);
    console.log(`  api    : /api/*  ->  分流：NODE_ROUTES→${API_TARGET_NODE}*，其余→${API_TARGET}*`);
    console.log(`  auth   : ★ 认证透传（不代签）`);
    console.log(`  bind   : ${
        process.env.BIND_HOST && process.env.BIND_HOST.trim()
            ? process.env.BIND_HOST.trim()
            : '(未设置 ⇒ 绑定所有网卡)'
    }`);
});
