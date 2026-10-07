// 探针：Fastify 5 / find-my-way 是否支持「参数 + 静态后缀」路由 `/:name.html`
// 目的：避免 53 条字面路由，也避免用 `/:file` 通吃（会误捕 /login 等单段路径）
// ★ Windows 坑：ESM 的绝对路径 import 必须写成 file:// URL（'e:' 会被判为非法 scheme）
import Fastify from 'file:///E:/USDT%E9%A1%B9%E7%9B%AE/02-backend-node/node_modules/fastify/fastify.js';

const app = Fastify({ logger: false });

async function tryRegister(path, label) {
  try {
    app.get(path, async (request) => ({ hit: label, params: request.params }));
    return { path, ok: true };
  } catch (e) {
    return { path, ok: false, err: String(e.message).slice(0, 160) };
  }
}

const results = [];
results.push(await tryRegister('/:name.html', 'param-suffix'));

console.log(JSON.stringify(results, null, 2));

if (results[0].ok) {
  app.get('/api/template', async () => ({ template: 'vodex' }));
  await app.ready();
  for (const url of ['/vodex.html', '/japapp.html', '/api/template', '/login']) {
    const r = await app.inject({ method: 'GET', url });
    console.log(`${url.padEnd(16)} -> ${r.statusCode} ${r.body.slice(0, 80)}`);
  }
  // 反向：非法段应不匹配该路由（落到 404）
  for (const url of ['/a/b.html', '/.html', '/x.html']) {
    const r = await app.inject({ method: 'GET', url });
    console.log(`${url.padEnd(16)} -> ${r.statusCode} ${r.body.slice(0, 80)}`);
  }
}
await app.close().catch(() => {});
