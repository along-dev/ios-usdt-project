// _ad_audit_bypass.mjs —— 自查①：匿名模板放行口有没有可绕过的路径形态
// 判据：除【白名单内的小写裸名 [+ 良性查询串]】外，任何形态都不得以 200 返回模板正文。
import http from 'node:http';

const HOST = '127.0.0.1';
const PORT = Number(process.env.AD_PORT || 3001);

function get(path) {
  return new Promise((resolve, reject) => {
    const r = http.request({ host: HOST, port: PORT, method: 'GET', path, headers: { host: `${HOST}:${PORT}` } },
      (res) => {
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => resolve({ status: res.statusCode, length: Buffer.concat(chunks).length }));
      });
    r.on('error', reject);
    r.end();
  });
}

// [路径, 期望, 说明]
const CASES = [
  ['/japapp.html',            'PUBLIC',  '基线：白名单内'],
  ['/vodex.html',             'PUBLIC',  'fallback 目标'],
  ['/arabic.html',            'PUBLIC',  '白名单内'],
  ['/japapp.html?x=1',        'PUBLIC',  '带良性查询串（中间件按 ? 截断）'],
  ['/japapp.html?a=/etc/passwd', 'PUBLIC', '查询串里放路径（不应影响取模板）'],

  ['/.html',                  'BLOCKED', '空名'],
  ['/',                       'BLOCKED', '根路径'],
  ['/japapp',                 'BLOCKED', '无 .html 后缀'],
  ['/japapp.htm',             'BLOCKED', '错后缀'],
  ['/JAPAPP.html',            'BLOCKED', '大写名'],
  ['/Japapp.html',            'BLOCKED', '混合大小写'],
  ['/japapp.HTML',            'BLOCKED', '大写后缀'],
  ['/VODEX.html',             'BLOCKED', '大写默认名'],
  ['//japapp.html',           'BLOCKED', '双斜杠'],
  ['/../japapp.html',         'BLOCKED', '相对上跳'],
  ['/a/../japapp.html',       'BLOCKED', '多段 + 上跳'],
  ['/./japapp.html',          'BLOCKED', '当前目录段'],
  ['/japapp.html/',           'BLOCKED', '尾斜杠'],
  ['/japapp.html/../x.html',  'BLOCKED', '尾段上跳'],
  ['/a/japapp.html',          'BLOCKED', '多段路径'],
  ['/api/japapp.html',        'BLOCKED', 'api 前缀'],
  ['/%6Aapapp.html',          'BLOCKED', '百分号编码首字母'],
  ['/japapp%2Ehtml',          'BLOCKED', '百分号编码点'],
  ['/japapp%2ehtml',          'BLOCKED', '百分号编码点（小写 hex）'],
  ['/japapp.html%00',         'BLOCKED', 'NUL 尾'],
  ['/japapp.html%20',         'BLOCKED', '尾随空格编码'],
  ['/notatemplate.html',      'BLOCKED', '名字不在白名单'],
  ['/index_root.html',        'BLOCKED', 'runtime 文件不在白名单'],
];

let bad = 0;
for (const [path, expect, note] of CASES) {
  const r = await get(path);
  const isPublic = r.status === 200 && r.length > 1000; // 200 且真的回了模板正文
  const ok = expect === 'PUBLIC' ? isPublic : !isPublic;
  if (!ok) bad++;
  console.log(`${ok ? 'ok  ' : '!!  '} ${String(r.status).padEnd(4)} len=${String(r.length).padEnd(7)} ${path.padEnd(28)} [${expect}] ${note}`);
}
console.log(`\n绕过面自查：${CASES.length - bad}/${CASES.length} 符合预期${bad ? `  ⚠️ ${bad} 项异常` : '  ✅ 未发现绕过'}`);
process.exit(bad ? 1 : 0);
