// 条件③ 反向断言：加 export 前后 auth.js 运行时行为不变 —— 登录限流仍生效
// ★ 用伪造 IP（X-Real-IP: 10.99.99.99）⇒ 键 ratelimit:login:10.99.99.99
//   与共享的 127.0.0.1 键**隔离**，不会打断其他线在该 Redis 上的登录。
//   （getRealIP 实现：cf-connecting-ip > x-real-ip > x-forwarded-for > request.ip）
import http from 'node:http';
import Redis from 'file:///E:/USDT%E9%A1%B9%E7%9B%AE/02-backend-node/node_modules/ioredis/built/index.js';

const HOST = '127.0.0.1', PORT = Number(process.env.AD_PORT || 3001);
const SPOOF = '10.99.99.99';
const KEY = `ratelimit:login:${SPOOF}`;

function login() {
  return new Promise((resolve, reject) => {
    const payload = Buffer.from(JSON.stringify({ username: 'admin', password: 'definitely-wrong-password' }));
    const r = http.request({ host: HOST, port: PORT, method: 'POST', path: '/api/auth/login',
      headers: { host: `${HOST}:${PORT}`, 'Content-Type': 'application/json', 'Content-Length': payload.length, 'X-Real-IP': SPOOF } },
      (res) => { const c = []; res.on('data', (x) => c.push(x));
        res.on('end', () => resolve({ status: res.statusCode, body: Buffer.concat(c).toString('utf8').slice(0, 80) })); });
    r.on('error', reject); r.write(payload); r.end();
  });
}

const redis = new Redis({ host: '127.0.0.1', port: 16379 });
await redis.del(KEY);  // 清理，保证可重复

console.log(`RL_LOGIN_MAX=10 / 900s；用伪造 IP ${SPOOF}（键 ${KEY}）发 12 次【错误口令】登录：`);
const codes = [];
for (let i = 1; i <= 12; i++) {
  const r = await login();
  codes.push(r.status);
  console.log(`  第 ${String(i).padStart(2)} 次: HTTP ${r.status}  ${r.body}`);
}
const limited = codes.filter((c) => c === 429).length;
const limitAt = codes.indexOf(429) + 1;
console.log(`\n429 次数 = ${limited}；首次出现于第 ${limitAt} 次`);
console.log(`计数器最终值 = ${await redis.get(KEY)}`);

const pass = limited > 0 && limitAt >= 10;   // 10 次之后才应触发
console.log(`${pass ? 'PASS' : 'FAIL'}  条件③：登录限流仍生效（前 10 次放行、之后 429）`);

await redis.del(KEY);   // ★ 清理伪造键（不留痕）
console.log('（已清理伪造键；共享的 ratelimit:login:127.0.0.1 全程未被触碰）');
await redis.quit();
process.exit(pass ? 0 : 1);
