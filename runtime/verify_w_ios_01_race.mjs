// W-IOS-01 / D3-C5 反向可复现测试
//   被测物：05-ios/coruna/group.html（真实文本，非副本）
//   断言：① 静态——整页导航调用点唯一且受 D3-C5 守卫；② 运行——利用链在飞期间
//         无论并发触发多少次 admin 入口，导航计数恒为 0；结束兑现后才至多 1 次。
//   用法：node verify_w_ios_01_race.mjs <group.html 路径>
import { readFileSync } from 'node:fs';

const target = process.argv[2];
if (!target) { console.error('usage: node verify_w_ios_01_race.mjs <group.html>'); process.exit(2); }
const src = readFileSync(target, 'utf8');

let failures = 0;
const ok = (cond, label, detail) => {
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${label}${detail ? '  — ' + detail : ''}`);
  if (!cond) failures++;
};

// ---------- 静态断言 ----------
// 提取 c2AdminUrl + 三守卫函数的**连续真实文本区间**（不复制、不改写）
const regionStart = src.indexOf('function c2AdminUrl');
const regionEnd = src.indexOf('window.c2FlushPendingAdmin = c2FlushPendingAdmin;');
const region = src.slice(regionStart, src.indexOf('\n', regionEnd));

ok(region.includes('function c2NavigateAdmin'), '静态: c2NavigateAdmin 存在');
ok(region.includes('window.__ADMIN_PATH'), '静态: c2AdminUrl 使用 __ADMIN_PATH');

// 全文件整页导航点：location.reload / location.replace / location.href=(在导航函数内)
const reloadHits = (src.match(/location\.reload/g) || []).length;
ok(reloadHits === 0, '静态: location.reload 计数为 0', `count=${reloadHits}`);

// 每个 location.replace( / location.href = 赋值必须落在 c2NavigateAdmin 守卫区内
const blockStart = src.indexOf('function c2NavigateAdmin');
const blockEnd = src.indexOf('window.c2FlushPendingAdmin = c2FlushPendingAdmin;');
const navAssign = [...src.matchAll(/location\.(?:replace\(|href\s*=)/g)].map(m => m.index);
ok(navAssign.length > 0 && navAssign.every(i => i >= blockStart && i <= blockEnd),
   '静态: 全部整页导航点位于 c2NavigateAdmin 内',
   `points=${navAssign.length}, zone=[${blockStart},${blockEnd}]`);

// 利用链入口设置/清除运行态，且清除在 finally 中
const entry = src.slice(src.indexOf('window.__C2_EXPLOIT_RUNNING = true'));
ok(/window\.__C2_EXPLOIT_RUNNING = true/.test(src), '静态: 入口设置 __C2_EXPLOIT_RUNNING = true');
ok(/finally\s*\{[\s\S]*?window\.__C2_EXPLOIT_RUNNING = false[\s\S]*?c2FlushPendingAdmin\(\)/.test(src),
   '静态: finally 中清除运行态并兑现挂起导航');

// ---------- 运行断言（注入假 window，执行真实函数文本） ----------
function makeHarness() {
  const nav = [];
  const win = {
    __ADMIN_PATH: '/mgr-admin-8bcde2021d98',
    __C2_BASE: 'https://example.test',
    log: () => {},
    location: {
      origin: 'https://example.test',
      pathname: '/details/show.html',
      replace: (u) => nav.push(u),
      set href(u) { nav.push(u); },
      get href() { return ''; },
    },
  };
  const code = `${region}\nreturn { c2OpenAdmin, c2FlushPendingAdmin };`;
  const f = new Function('window', code);
  const api = f(win);
  return { win, nav, api };
}

// S1 基线：非在飞 → 立即导航一次
{
  const { win, nav, api } = makeHarness();
  api.c2OpenAdmin();
  ok(nav.length === 1, '运行 S1 基线: 非在飞时导航 1 次', `nav=${nav.length}`);
  ok(nav[0] === 'https://example.test/mgr-admin-8bcde2021d98', '运行 S1: 目标路径逐字符正确', nav[0]);
}

// S2 反向（核心判据）：在飞期间并发触发 N 次 → 导航恒为 0
{
  const { win, nav, api } = makeHarness();
  win.__C2_EXPLOIT_RUNNING = true;
  for (let i = 0; i < 5; i++) api.c2OpenAdmin();   // 模拟并发 Stage 重入 + 多入口
  ok(nav.length === 0, '运行 S2 反向: 在飞期间 5 次触发导航计数恒为 0', `nav=${nav.length}`);
  ok(win.__C2_ADMIN_PENDING === 'https://example.test/mgr-admin-8bcde2021d98', '运行 S2: 导航被挂起（pending 已记录）');
}

// S3 兑现：结束态后 flush → 恰好 1 次
{
  const { win, nav, api } = makeHarness();
  win.__C2_EXPLOIT_RUNNING = true;
  api.c2OpenAdmin(); api.c2OpenAdmin();
  win.__C2_EXPLOIT_RUNNING = false;   // 模拟 finally
  api.c2FlushPendingAdmin();
  ok(nav.length === 1, '运行 S3: 结束后兑现恰好 1 次导航', `nav=${nav.length}`);
}

// S4 幂等：非在飞连点 3 次 → 全生命周期至多 1 次
{
  const { nav, api } = makeHarness();
  api.c2OpenAdmin(); api.c2OpenAdmin(); api.c2OpenAdmin();
  ok(nav.length === 1, '运行 S4 幂等: 连点 3 次仅导航 1 次', `nav=${nav.length}`);
}

// S5 无挂起时 flush → 不导航
{
  const { nav, api } = makeHarness();
  api.c2FlushPendingAdmin();
  ok(nav.length === 0, '运行 S5: 无挂起时 flush 不导航', `nav=${nav.length}`);
}

console.log(failures === 0 ? '\nRESULT: ALL PASS' : `\nRESULT: ${failures} FAILED`);
process.exit(failures === 0 ? 0 : 1);
