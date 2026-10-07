// 对比不同 UA 的响应（诊断用）
import crypto from 'node:crypto';

const uas = {
  'iOS16.5': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15',
  'iOS18.4': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_4 like Mac OS X) AppleWebKit/605.1.15',
  'iOS17.5': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15',
  'iOS13.0': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_0 like Mac OS X) AppleWebKit/605.1.15',
  'Win': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
};

for (const [k, ua] of Object.entries(uas)) {
  const r = await fetch('http://127.0.0.1:3000/details/show.html', {
    headers: { 'User-Agent': ua },
  });
  const buf = Buffer.from(await r.arrayBuffer());
  const md5 = crypto.createHash('md5').update(buf).digest('hex').slice(0, 12);
  console.log(`${k.padEnd(9)} HTTP=${r.status} bytes=${buf.length} md5=${md5}`);
}
