// 打印三种路径的真实响应尾部
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';

const RC = 'E:\\ios漏洞\\_integration\\_fix_work\\_toolchain\\redis\\redis-cli.exe';

function flush() {
  try {
    const keys = execFileSync(RC, ['-h', '127.0.0.1', '-p', '16379', 'KEYS', 'payload_config:*'], { encoding: 'utf-8' }).trim();
    for (const k of keys.split('\n')) if (k.trim()) execFileSync(RC, ['-h', '127.0.0.1', '-p', '16379', 'DEL', k.trim()]);
  } catch { }
}

const cases = {
  'coruna(iOS16.5)': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15',
  'darksword(iOS18.4)': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_4 like Mac OS X) AppleWebKit/605.1.15',
  '空白区(iOS17.5)': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15',
};

for (const [k, ua] of Object.entries(cases)) {
  flush();
  const r = await fetch('http://127.0.0.1:3000/details/show.html', { headers: { 'User-Agent': ua } });
  const buf = Buffer.from(await r.arrayBuffer());
  const ct = r.headers.get('content-type') || '';
  console.log(`--- ${k} [${r.status}] ${buf.length}B ${ct}`);
  if (ct.includes('json')) {
    console.log('    BODY: ' + buf.toString('utf-8'));
  } else {
    console.log('    (加密 buffer，前 24 字节: ' + buf.subarray(0, 24).toString('hex') + ')');
  }
}
