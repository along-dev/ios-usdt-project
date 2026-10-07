// _ad_verify_e2e.mjs —— 广告线 W-AD-01 / 04 / 05 / 06 判据（正向 + 反向）
// ★ 为什么用 node:http 而不是 fetch：Host 头要显式设置（测 Host→渠道 解析），
//   而 undici 的 fetch 禁止覆盖 Host。
// 目标：第二实例 http://127.0.0.1:3001（不动共享的 3000）
import http from 'node:http';
import { createHash } from 'node:crypto';
import { MongoClient, ObjectId } from 'file:///E:/USDT%E9%A1%B9%E7%9B%AE/02-backend-node/node_modules/mongodb/lib/index.js';

const HOST = '127.0.0.1';
const PORT = Number(process.env.AD_PORT || 3001);
const ADMIN_USER = 'admin';
const ADMIN_PASS = process.env.AD_ADMIN_PASS || 'i1c3-e2e-admin';
const TS = Date.now().toString(36);

const results = [];
function check(id, name, pass, detail) {
  results.push({ id, name, pass: !!pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${id.padEnd(6)} ${name}${detail ? '  | ' + detail : ''}`);
}

function req(method, path, { cookie, body, host, acceptJson = true } = {}) {
  return new Promise((resolve, reject) => {
    const payload = body === undefined ? null : Buffer.from(JSON.stringify(body));
    const headers = {};
    if (payload) { headers['Content-Type'] = 'application/json'; headers['Content-Length'] = payload.length; }
    if (cookie) headers.cookie = cookie;
    if (host) headers.host = host;
    else headers.host = `${HOST}:${PORT}`;
    const r = http.request({ host: HOST, port: PORT, method, path, headers }, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => {
        const buf = Buffer.concat(chunks);
        let json = null;
        if (acceptJson) { try { json = JSON.parse(buf.toString('utf8')); } catch { /* 非 JSON */ } }
        resolve({ status: res.statusCode, headers: res.headers, buf, json });
      });
    });
    r.on('error', reject);
    if (payload) r.write(payload);
    r.end();
  });
}

async function login(username, password) {
  const r = await req('POST', '/api/auth/login', { body: { username, password } });
  const raw = r.headers['set-cookie'] || [];
  const cookie = raw.map((c) => c.split(';')[0]).join('; ');
  return { status: r.status, cookie, json: r.json };
}

const mongo = new MongoClient('mongodb://127.0.0.1:27018');
await mongo.connect();
const db = mongo.db('gasleak');

console.log('=== 0 · 基线（当场重测）===');
// 先清掉【本脚本上一轮】留下的夹具，使脚本可重复运行（只删自己造的：name/用户名/角色名带 ad-e2e 前缀）
const doomed = await db.collection('channels').find({ name: { $regex: '^ad-e2e-' } }, { projection: { code: 1 } }).toArray();
const doomedCodes = doomed.map((d) => d.code);
if (doomedCodes.length) {
  await db.collection('channeltotalstats').deleteMany({ channelCode: { $in: doomedCodes } });
  await db.collection('channels').deleteMany({ code: { $in: doomedCodes } });
}
await db.collection('channels').deleteMany({ name: { $regex: '^ad-bad-' } });
await db.collection('users').deleteMany({ username: { $regex: '^ad[a-z0-9]{6}$' } });
await db.collection('roles').deleteMany({ name: { $regex: '^ad-e2e-role-' } });
if (doomedCodes.length) console.log(`（已清理上一轮夹具：${doomedCodes.length} 个渠道）`);

const channelsBefore = await db.collection('channels').countDocuments();
const totalsBefore = await db.collection('channeltotalstats').countDocuments();
console.log(`channels=${channelsBefore}  channeltotalstats=${totalsBefore}  @${new Date().toISOString()}`);

const admin = await login(ADMIN_USER, ADMIN_PASS);
check('S0', 'admin 登录', admin.status === 200, `HTTP ${admin.status}`);
if (admin.status !== 200) { console.log(JSON.stringify(admin.json)); process.exit(2); }

// ---------------------------------------------------------------------------
console.log('\n=== 1 · W-AD-01 建渠道 + 绑定 packet/agent ===');
const nameA = `ad-e2e-a-${TS}`;
const nameB = `ad-e2e-b-${TS}`;
const rA = await req('POST', '/api/channels', { cookie: admin.cookie, body: {
  name: nameA, groupId: 'ch_ad_e2e_a', packetId: 1, agentId: 101, landingTemplate: 'japapp',
} });
const codeA = rA.json?.data?.code;
check('1.1', '建渠道 A（带 groupId/packetId/agentId/landingTemplate）', rA.status === 200 && !!codeA,
  `HTTP ${rA.status} code=${codeA} ${rA.status !== 200 ? JSON.stringify(rA.json) : ''}`);

const rB = await req('POST', '/api/channels', { cookie: admin.cookie, body: {
  name: nameB, groupId: 'ch_ad_e2e_b', packetId: 1, agentId: 999, landingTemplate: 'arabic',
} });
const codeB = rB.json?.data?.code;
check('1.2', '建渠道 B（另一 agent）', rB.status === 200 && !!codeB, `HTTP ${rB.status} code=${codeB}`);

const channelsAfter = await db.collection('channels').countDocuments();
check('1.3', 'Mongo channels 条数 0 → >0（可观测）', channelsAfter > channelsBefore,
  `${channelsBefore} → ${channelsAfter}`);

const gotA = await req('GET', `/api/channels/${codeA}`, { cookie: admin.cookie });
const bA = gotA.json?.data?.binding;
check('1.4', 'GET /api/channels/:code 能反查到所属包与代理商',
  gotA.status === 200 && bA?.groupId === 'ch_ad_e2e_a' && bA?.packetId === 1 && bA?.agentId === 101,
  `HTTP ${gotA.status} binding=${JSON.stringify(bA)}`);

// 反向：非法绑定字段必须被拒（写入期挡住，不留"写了但读不到"的假象）
const badBinding = await req('POST', '/api/channels', { cookie: admin.cookie, body: { name: `ad-e2e-bad-${TS}`, agentId: 'abc' } });
check('1.5r', '反向：agentId 非整数 ⇒ 400', badBinding.status === 400, `HTTP ${badBinding.status}`);
const badTpl = await req('POST', '/api/channels', { cookie: admin.cookie, body: { name: `ad-e2e-bad2-${TS}`, landingTemplate: 'not-a-template' } });
check('1.6r', '反向：landingTemplate 不在白名单 ⇒ 400', badTpl.status === 400, `HTTP ${badTpl.status}`);
const badPatch = await req('PATCH', `/api/channels/${codeA}`, { cookie: admin.cookie, body: { landingTemplate: 'zzz-nope' } });
check('1.7r', '反向：PATCH 非法模板名 ⇒ 400', badPatch.status === 400, `HTTP ${badPatch.status}`);

// ---------------------------------------------------------------------------
console.log('\n=== 2 · W-AD-01/06 代理商隔离（反向）===');
const roleRes = await req('POST', '/api/roles', { cookie: admin.cookie, body: {
  name: `ad-e2e-role-${TS}`, menuKeys: ['channels', 'channel-stats'], visibleChains: [], visibleSocialTypes: [],
} });
// ★ User.username 模型上限 10 字符（实测 500 的根因）⇒ 测试用户名必须短
const uName = `ad${TS.slice(-6)}`;
const uPass = 'AdE2ePass123';
const roleId = roleRes.json?.data?._id || roleRes.json?.data?.id;
const grantedKeys = roleRes.json?.data?.menuKeys || [];
check('2.0', '建角色（请求 channels + channel-stats）', roleRes.status === 200 && !!roleId, `HTTP ${roleRes.status}`);

// ★ 设计事实（本轮实测，不是缺陷）：`/api/channels` 挂在 menus.js 的
//   `admin-group`（adminOnly:true）之下 ⇒ getAssignableMenuKeys() 会把 'channels' 滤掉
//   ⇒ 该 key **不可能**分配给任何角色；非管理员访问 /api/channels 会先被 RBAC 拦成 403。
check('2.0b', '设计事实：adminOnly 组下的 channels key 不可分配（被 roles.js:55 过滤）',
  grantedKeys.includes('channel-stats') && !grantedKeys.includes('channels'),
  `实际授予=${JSON.stringify(grantedKeys)}`);

// 「代理商能查自己的渠道吗」在本设计下由 RBAC 直接否掉（403）。
// 为验证我写在 channels.js 里的【范围收口】本身成立，这里直接插一个带 channels key 的
// 角色（**夹具**：绕过 API 的 adminOnly 过滤，现实中不会存在）——
// 它回答的是「若该 key 将来落到非管理员身上，收口是否兜得住」。
const fixtureRoleId = new ObjectId();
await db.collection('roles').insertOne({
  _id: fixtureRoleId, name: `ad-e2e-role-fx-${TS}`, menuKeys: ['channels', 'channel-stats'],
  visibleChains: [], visibleSocialTypes: [], createdAt: new Date(), updatedAt: new Date(),
});

const userRes = await req('POST', '/api/users', { cookie: admin.cookie, body: {
  username: uName, password: uPass, roleId: String(fixtureRoleId), channelCodes: [codeA],
} });
check('2.1', '建 user（channelCodes=[渠道A]）', userRes.status === 200, `HTTP ${userRes.status} ${JSON.stringify(userRes.json).slice(0, 160)}`);

const ag = await login(uName, uPass);
check('2.2', '代理商登录', ag.status === 200, `HTTP ${ag.status} role=${ag.json?.user?.role}`);

const listAsAgent = await req('GET', '/api/channels', { cookie: ag.cookie });
const codesSeen = (listAsAgent.json?.data || []).map((c) => c.code);
check('2.3', '代理商 A 的列表只含自己的渠道', listAsAgent.status === 200 && codesSeen.length === 1 && codesSeen[0] === codeA,
  `HTTP ${listAsAgent.status} 看到=${JSON.stringify(codesSeen)}`);

const otherAsAgent = await req('GET', `/api/channels/${codeB}`, { cookie: ag.cookie });
check('2.4r', '反向：代理商 A 查代理商 B 的渠道 ⇒ 404', otherAsAgent.status === 404, `HTTP ${otherAsAgent.status}`);

// 造统计夹具：两个渠道各一条 channeltotalstats（否则 user/admin 都是空集，分不出"隔离"与"无数据"）
await db.collection('channeltotalstats').updateOne(
  { channelCode: codeA }, { $set: { channelCode: codeA, visitsTotal: 7, devicesTotal: 3, dataCountsTotal: {}, collectAmountTotal: {} } }, { upsert: true });
await db.collection('channeltotalstats').updateOne(
  { channelCode: codeB }, { $set: { channelCode: codeB, visitsTotal: 99, devicesTotal: 9, dataCountsTotal: {}, collectAmountTotal: {} } }, { upsert: true });

const statsAdmin = await req('GET', '/api/channel-stats?pageSize=50', { cookie: admin.cookie });
const statsAgent = await req('GET', '/api/channel-stats?pageSize=50', { cookie: ag.cookie });
const adminCodes = (statsAdmin.json?.data?.items || []).map((r) => r.channelCode);
const agentCodes = (statsAgent.json?.data?.items || []).map((r) => r.channelCode);
check('2.5', '统计面：admin 看到两个渠道', statsAdmin.status === 200 && adminCodes.includes(codeA) && adminCodes.includes(codeB),
  `HTTP ${statsAdmin.status} 看到=${JSON.stringify(adminCodes)}`);
check('2.6r', '反向：代理商只看到自己的统计（看不到 B）', statsAgent.status === 200 && agentCodes.includes(codeA) && !agentCodes.includes(codeB),
  `HTTP ${statsAgent.status} 看到=${JSON.stringify(agentCodes)}`);

// ---------------------------------------------------------------------------
console.log('\n=== 3 · W-AD-04 APK 按渠道分发（_BINDING.md §5）===');
const APK_SHA = '30d6701dd6ed010ce842a7d521fed10e4284356270c0214f44aa4fd0792765a5';
const apkOk = await req('GET', `/api/apk/download?channel=${codeA}`, { acceptJson: false });
const apkSha = createHash('sha256').update(apkOk.buf).digest('hex');
check('3.1', '已绑定渠道 ⇒ 分发 japapp.apk（sha256 与登记一致）',
  apkOk.status === 200 && apkSha === APK_SHA, `HTTP ${apkOk.status} bytes=${apkOk.buf.length} sha=${apkSha.slice(0, 16)}`);

const apkNoChannel = await req('GET', '/api/apk/download', { host: 'no-such-host.invalid' });
check('3.2r', '反向：未绑定渠道 ⇒ 404（不回退取 files[0]）', apkNoChannel.status === 404,
  `HTTP ${apkNoChannel.status} ${JSON.stringify(apkNoChannel.json)?.slice(0, 120)}`);

const apkUnknown = await req('GET', '/api/apk/download?channel=does-not-exist');
check('3.3r', '反向：渠道不存在 ⇒ 404', apkUnknown.status === 404, `HTTP ${apkUnknown.status}`);

const apkChild = await req('GET', `/api/apk/download?channel=${codeA}&file=child_milkstream.apk`);
check('3.4r', '反向：链内载荷 child_milkstream.apk ⇒ 404', apkChild.status === 404, `HTTP ${apkChild.status}`);

const apkEvil = await req('GET', `/api/apk/download?channel=${codeA}&file=evil.apk`);
check('3.5r', '反向：文件名不在库存内 ⇒ 404', apkEvil.status === 404, `HTTP ${apkEvil.status}`);

// ---------------------------------------------------------------------------
console.log('\n=== 4 · W-AD-05 落地页模板 ↔ 渠道 ===');
const chA = await db.collection('channels').findOne({ code: codeA });
const hostA = chA.primaryDomain;
const tplByHost = await req('GET', '/api/template', { host: hostA });
check('4.1', 'Host 命中渠道 ⇒ /api/template 返回该渠道绑定的模板',
  tplByHost.status === 200 && tplByHost.json?.template === 'japapp',
  `host=${hostA} HTTP ${tplByHost.status} template=${tplByHost.json?.template}`);

const tplUnknownHost = await req('GET', '/api/template', { host: 'unknown.example' });
check('4.2', 'Host 不命中 ⇒ 回退默认 vodex', tplUnknownHost.status === 200 && tplUnknownHost.json?.template === 'vodex',
  `template=${tplUnknownHost.json?.template}`);

const chB = await db.collection('channels').findOne({ code: codeB });
const tplB = await req('GET', '/api/template', { host: chB.primaryDomain });
check('4.3', '另一渠道 ⇒ 另一个模板（渠道间独立）', tplB.json?.template === 'arabic', `template=${tplB.json?.template}`);

const patchTpl = await req('PATCH', `/api/channels/${codeA}`, { cookie: admin.cookie, body: { landingTemplate: 'kiss' } });
const tplAfter = await req('GET', '/api/template', { host: hostA });
check('4.4', '改渠道绑定 ⇒ 落地页模板实际切换（kiss）', patchTpl.status === 200 && tplAfter.json?.template === 'kiss',
  `PATCH ${patchTpl.status} → template=${tplAfter.json?.template}`);

// 模板页路由（旧实现：只有 /vodex.html 一条字面路由 ⇒ 其余 404）
const pageJapapp = await req('GET', '/japapp.html', { acceptJson: false });
const pageKiss = await req('GET', '/kiss.html', { acceptJson: false });
const pageVodex = await req('GET', '/vodex.html', { acceptJson: false });
check('4.5', '模板页可取：/japapp.html（旧实现 404）', pageJapapp.status === 200 && pageJapapp.buf.length > 1000,
  `HTTP ${pageJapapp.status} bytes=${pageJapapp.buf.length}`);
check('4.6', '模板页可取：/kiss.html（旧实现 404）', pageKiss.status === 200 && pageKiss.buf.length > 1000,
  `HTTP ${pageKiss.status} bytes=${pageKiss.buf.length}`);
check('4.7', '/vodex.html 仍是匿名可达的 fallback 目标', pageVodex.status === 200, `HTTP ${pageVodex.status}`);

// 反向：名字不在白名单 ⇒ 不放行（既不放行匿名，也不会拿它去读任意文件）
const pageEvil = await req('GET', '/notatemplate.html');
check('4.8r', '反向：名字不在白名单 ⇒ 匿名被拒（401），不泄露模板内容',
  pageEvil.status === 401, `HTTP ${pageEvil.status}`);

console.log('\n=== 5 · 台账变更（当场）===');
const channelsFinal = await db.collection('channels').countDocuments();
const totalsFinal = await db.collection('channeltotalstats').countDocuments();
console.log(`channels=${channelsFinal}  channeltotalstats=${totalsFinal}  @${new Date().toISOString()}`);
console.log(`本轮留下的夹具：渠道 ${codeA} / ${codeB}，统计行 2 条，用户 ${uName}，角色 ad-e2e-role-${TS}`);

const failed = results.filter((r) => !r.pass);
console.log(`\n=== 汇总：${results.length - failed.length}/${results.length} PASS ===`);
if (failed.length) {
  console.log('失败项：');
  for (const f of failed) console.log(`  - ${f.id} ${f.name} | ${f.detail}`);
}
await mongo.close();
process.exit(failed.length ? 1 : 0);
