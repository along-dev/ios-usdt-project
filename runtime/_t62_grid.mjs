// T62 第2名复核 · 判定表穷举对照（★ 基准逐字转写 vs 受审 JS 逐格比）
// ★ 基准转写自 E:\IOS源码1\server\src\core\collect\auto-collect.ts（sha 5066b973…/9970）L63–L189
import * as J from 'file:///E:/USDT项目/02-backend-node/src_restored/core/collect/auto-collect-judge.js';

// ---- 基准（逐字转写；去掉 async/联网，仅判定） ----
function bShouldCollectTron(address, config) {
    if (!config.collectThreshold || !config.collectAddress) { return false; }
    const usdtBalance = Number(address.usdtBalance) || 0;
    const threshold = Number(config.collectThreshold.usdt) || 0;
    return threshold > 0 && usdtBalance >= threshold && usdtBalance > 0;
}
function bShouldCollectEth(address, config) {
    if (!config.collectThreshold || !config.collectAddress) { return { shouldCollect: false, tokens: [] }; }
    const ethBalance = Number(address.balance) || 0;
    const usdtBalance = Number(address.usdtBalance) || 0;
    const ethThreshold = Number(config.collectThreshold.eth) || 0;
    const usdtThreshold = Number(config.collectThreshold.usdt) || 0;
    const tokens = [];
    if (ethThreshold > 0 && ethBalance >= ethThreshold) { tokens.push('eth'); }
    if (usdtThreshold > 0 && usdtBalance >= usdtThreshold) { tokens.push('usdt'); }
    return { shouldCollect: tokens.length > 0, tokens };
}
function bCheckTronGas(trxBalance) {
    const trx = Number(trxBalance) || 0;          // ★ 基准 L109：Number(balances.balance) || 0（对取回的余额）
    const requiredGas = 15;
    return { hasEnoughGas: trx >= requiredGas, trxBalance: trx, requiredGas };
}
function bCheckEthGas(ethBalance, token, gasPriceGwei = 20) {
    let gasLimit;
    if (token === 'eth') { gasLimit = 21000; } else { gasLimit = 65000; }
    const requiredGas = (gasLimit * gasPriceGwei / 1e9) * 1.2;
    const eth = Number(ethBalance) || 0;          // ★ 基准 L155：Number(balances.balance) || 0
    const hasEnoughGas = token === 'eth' ? eth > requiredGas : eth >= requiredGas;
    return { hasEnoughGas, ethBalance: eth, requiredGas };
}
function bCheckEthGasFallback(ethBalance, token) {
    const fallbackGas = token === 'eth' ? 0.002 : 0.003;
    const eth = Number(ethBalance) || 0;          // ★ 基准 L181：Number(balances.balance) || 0
    return { hasEnoughGas: token === 'eth' ? eth > fallbackGas : eth >= fallbackGas, ethBalance: eth, requiredGas: fallbackGas };
}

const S = (x) => JSON.stringify(x);
let n = 0, bad = 0;
function cmp(label, a, b) {
    n++;
    if (S(a) !== S(b)) { bad++; if (bad <= 25) console.log(`★ 逐格不一致 [${label}]\n   基准=${S(a)}\n   受审=${S(b)}`); }
}

// ---- 输入格 ----
const addrs = [{}, { usdtBalance: 0 }, { usdtBalance: '0' }, { usdtBalance: 10 }, { usdtBalance: 'abc' },
    { usdtBalance: null }, { balance: 0 }, { balance: 0.01 }, { balance: '0.01', usdtBalance: 5 },
    { balance: NaN, usdtBalance: 10 }, { balance: Infinity, usdtBalance: 10 }];
const cfgs = [{}, { collectAddress: '' }, { collectAddress: null },
    { collectThreshold: null, collectAddress: 'x' }, { collectThreshold: {}, collectAddress: 'x' },
    { collectThreshold: { usdt: 0 }, collectAddress: 'x' }, { collectThreshold: { usdt: 10 }, collectAddress: 'x' },
    { collectThreshold: { eth: 0.01, usdt: 10 }, collectAddress: 'x' },
    { collectThreshold: { eth: '0.01', usdt: '10' }, collectAddress: 'x' },
    { collectThreshold: { eth: 0.01, usdt: 10 } }];   // ← 末格：有阈值无地址（守卫）
for (const a of addrs) for (const c of cfgs) {
    cmp(`tron addr=${S(a)} cfg=${S(c)}`, bShouldCollectTron(a, c), J.shouldCollectTron(a, c));
    cmp(`eth  addr=${S(a)} cfg=${S(c)}`, bShouldCollectEth(a, c), J.shouldCollectEth(a, c));
}

const toks = ['eth', 'usdt', 'ETH', 'USDT', '', null, undefined];
const bals = [0, 15, 14.999999, 15.000001, 0.00156, 0.00156001, 0.00155999, 0.002, 0.003, 'x', null, undefined];
for (const t of toks) for (const b of bals) {
    cmp(`tronGas b=${S(b)}`, bCheckTronGas(b), J.checkTronGas(b));
    cmp(`ethGas  t=${S(t)} b=${S(b)}`, bCheckEthGas(b, t), J.checkEthGas(b, t));
    cmp(`ethGasFB t=${S(t)} b=${S(b)}`, bCheckEthGasFallback(b, t), J.checkEthGasFallback(b, t));
}
// 显式 gasPrice 入参（受审专有：基准无此参 ⇒ 只与基准的"同 gasPrice"格比）
for (const gp of [1, 20, 30.5, 0]) cmp(`ethGas gp=${gp}`, bCheckEthGas(0.01, 'usdt', gp), J.checkEthGas(0.01, 'usdt', gp));

// ---- 常量面 ----
cmp('const TRON_GAS_REQUIRED', 15, J.TRON_GAS_REQUIRED);
cmp('const ETH_GAS_FALLBACK', { eth: 0.002, usdt: 0.003 }, J.ETH_GAS_FALLBACK);
cmp('const ETH_GAS_LIMIT', { eth: 21000, usdt: 65000 }, J.ETH_GAS_LIMIT);
cmp('const ETH_GAS_SAFETY_FACTOR', 1.2, J.ETH_GAS_SAFETY_FACTOR);
cmp('const ETH_GAS_PRICE_GWEI_DEFAULT', 20, J.ETH_GAS_PRICE_GWEI_DEFAULT);

// ---- 导出面 ----
console.log('受审导出 =', Object.keys(J).sort().join(','));
console.log(`\nGRID total=${n} mismatches=${bad}`);
console.log(bad === 0 ? 'GRID=MATCH' : 'GRID=MISMATCH');
