// 精确探针：每次请求前清缓存，逐 UA 请求，打印响应特征
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';

const RC = 'E:\\ios漏洞\\_integration\\_fix_work\\_toolchain\\redis\\redis-cli.exe';

function flushCache() {
  try {
    const keys = execFileSync(RC, ['-h', '127.0.0.1', '-p', '16379', 'KEYS', 'payload_config:*'],
      { encoding: 'utf-8' }).trim();
    if (keys) {
      for (const k of keys.split('\n')) {
        if (k.trim()) execFileSync(RC, ['-h', '127.0.0.1', '-p', '16379', 'DEL', k.trim()]);
      }
    }
  } catch (e) { /* ignore */ }
}

const uas = {
  'iOS16.5(coruna)': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15',
  'iOS18.4(darksword)': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_4 like Mac OS X) AppleWebKit/605.1.15',
  'iOS17.5(空白区)': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15',
  'iOS13.0(coruna下界)': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_0 like Mac OS X) AppleWebKit/605.1.15',
  'Windows': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
};

console.log('=== 逐 UA 请求（每次请求前清缓存）===');
for (const [k, ua] of Object.entries(uas)) {
  flushCache();
  const r = await fetch('http://127.0.0.1:3000/details/show.html', {
    headers: { 'User-Agent': ua },
  });
  const buf = Buffer.from(await r.arrayBuffer());
  const md5 = crypto.createHash('md5').update(buf).digest('hex').slice(0, 12);
  const ct = r.headers.get('content-type');
  console.log(`${k.padEnd(20)} HTTP=${r.status} bytes=${buf.length} md5=${md5} ct=${ct}`);
}
