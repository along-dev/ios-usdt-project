// _ad_verify_sha_guard.mjs —— 只验 _BINDING.md §5-4：APK 被替换时必须【拒绝分发】
// 前提：3001 实例以 LANDING_APK_PATH 指向假 APK 目录启动。
import http from 'node:http';
import { MongoClient } from 'file:///E:/USDT%E9%A1%B9%E7%9B%AE/02-backend-node/node_modules/mongodb/lib/index.js';

const HOST = '127.0.0.1';
const PORT = Number(process.env.AD_PORT || 3001);

function get(path) {
  return new Promise((resolve, reject) => {
    const r = http.request({ host: HOST, port: PORT, method: 'GET', path, headers: { host: `${HOST}:${PORT}` } }, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => resolve({ status: res.statusCode, body: Buffer.concat(chunks) }));
    });
    r.on('error', reject);
    r.end();
  });
}

const mongo = new MongoClient('mongodb://127.0.0.1:27018');
await mongo.connect();
const ch = await mongo.db('gasleak').collection('channels').findOne({ groupId: { $ne: '' } });
await mongo.close();

if (!ch) { console.log('FAIL  找不到已绑定渠道，无法测 §5-4'); process.exit(2); }

const r = await get(`/api/apk/download?channel=${ch.code}`);
const body = r.body.toString('utf8').slice(0, 200);
const pass = r.status === 503;
console.log(`${pass ? 'PASS' : 'FAIL'}  §5-4  假 APK ⇒ 拒绝分发（期望 503）  | HTTP ${r.status} ${body}`);
process.exit(pass ? 0 : 1);
