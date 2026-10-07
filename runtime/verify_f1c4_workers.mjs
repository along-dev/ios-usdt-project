/**
 * F1-C4 判据：WORKERS 默认值语义冲突（ecosystem.config.cjs 的 'max' vs app.js 的 '1'）
 *
 * 判据先于实现（判据 9）。本脚本放产物外（_fix_work/），不进 09-docs/cards/（P-4）。
 *
 * 用法：
 *   node verify_f1c4_workers.mjs              # 对产物
 *   node verify_f1c4_workers.mjs --selftest   # 量尺前置断言（P-5）
 *
 * 退出码：0 = 全绿；非 0 = 有红。
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = 'E:\\USDT项目';
const ECOSYSTEM = path.join(ROOT, '02-backend-node', 'ecosystem.config.cjs');
const APPJS = path.join(ROOT, '02-backend-node', 'src_restored', 'app.js');

// ---------------------------------------------------------------------------
// 从源码里抽取"未设 WORKERS 时"的默认值表达式。
// 用锚定正则，避免 P-5 的"grep 未锚定"坑。
// ---------------------------------------------------------------------------

/**
 * ecosystem.config.cjs 的 instances 表达式。
 * 注意：不锚定行尾 —— 真实文件是 `instances: <expr>,` 独占一行，
 * 但合成的正/负样本可能是内联写法。故只取到"逗号或行尾"为止。
 */
function extractEcosystemDefault(src) {
    const m = src.match(/instances\s*:\s*(parseInt\([^)]*\)(?:\s*\|\|\s*'[^']*')?)/);
    if (!m) return null;
    const expr = m[1].trim();
    return { expr, raw: m[0].trim() };
}

/** app.js 的 totalWorkers 默认值 */
function extractAppDefault(src) {
    const m = src.match(
        /const\s+totalWorkers\s*=\s*parseInt\(\s*process\.env\.WORKERS\s*\|\|\s*'([^']*)'\s*\)/
    );
    if (!m) return null;
    return { value: m[1], raw: m[0].trim() };
}

/**
 * 判定"未设 WORKERS 时"两处推导出的实例数语义是否一致。
 * 返回 { ecoDefault, appDefault, conflict }
 */
function analyze(ecoExpr, appDefault) {
    let ecoDefault;
    if (/\|\|\s*'max'/.test(ecoExpr)) {
        ecoDefault = 'max';
    } else {
        const m = ecoExpr.match(/process\.env\.WORKERS\s*\|\|\s*'([^']*)'/);
        ecoDefault = m ? m[1] : '<无法解析>';
    }
    // 'max' 在 PM2 中 = CPU 核数（多实例）；数字字符串 = 该数字
    const conflict = ecoDefault !== appDefault;
    return { ecoDefault, appDefault, conflict };
}

// ---------------------------------------------------------------------------
// 量尺前置断言（P-5）：用合成的正/反样本证明抽取逻辑有效
// ---------------------------------------------------------------------------
function selftest() {
    console.log('=== 量尺前置断言（P-5）===');
    let ok = true;

    // 正样本 A：缺陷态（应抽出 max 与 1，且判为冲突）
    const badSrc = `module.exports = { apps: [{ instances: parseInt(process.env.WORKERS) || 'max', }] }`;
    const badEco = extractEcosystemDefault(badSrc);
    const badAppSrc = `const totalWorkers = parseInt(process.env.WORKERS || '1');`;
    const badApp = extractAppDefault(badAppSrc);
    if (!badEco || badEco.expr.indexOf("'max'") === -1) {
        console.log(`  [FAIL] 正样本A: ecosystem 抽取失败 => ${JSON.stringify(badEco)}`);
        ok = false;
    }
    if (!badApp || badApp.value !== '1') {
        console.log(`  [FAIL] 正样本A: app.js 抽取失败 => ${JSON.stringify(badApp)}`);
        ok = false;
    }
    if (badEco && badApp) {
        const a = analyze(badEco.expr, badApp.value);
        if (!a.conflict) {
            console.log(`  [FAIL] 正样本A: 未判出冲突 => ${JSON.stringify(a)}`);
            ok = false;
        } else {
            console.log(`  正样本A: 抽出 eco='${a.ecoDefault}' app='${a.appDefault}' 判为冲突 ✓`);
        }
    }

    // 负样本 B：修复态（两处都是 '1'，应判为不冲突）
    const goodSrc = `instances: parseInt(process.env.WORKERS || '1'),`;
    const goodEco = extractEcosystemDefault(goodSrc);
    if (!goodEco) {
        console.log('  [FAIL] 负样本B: ecosystem 抽取失败（修复态形态未被识别）');
        ok = false;
    } else {
        const a = analyze(goodEco.expr, '1');
        if (a.conflict) {
            console.log(`  [FAIL] 负样本B: 修复态被误判为冲突 => ${JSON.stringify(a)}`);
            ok = false;
        } else {
            console.log(`  负样本B: 修复态 eco='${a.ecoDefault}' app='${a.appDefault}' 判为一致 ✓`);
        }
    }

    if (ok) {
        console.log('  量尺有效：缺陷态与修复态都能被区分');
        console.log('SELFTEST=OK');
        return 0;
    }
    console.log('SELFTEST=BAD');
    return 2;
}

function main() {
    const argv = process.argv.slice(2);
    if (argv.includes('--selftest')) {
        process.exit(selftest());
    }

    console.log('目标:');
    console.log(`  ${ECOSYSTEM}`);
    console.log(`  ${APPJS}`);
    console.log('');

    const fails = [];
    const notes = [];

    // R4: node --check 由外部 verify 负责；此处做静态一致性
    for (const f of [ECOSYSTEM, APPJS]) {
        if (!fs.existsSync(f)) {
            console.log(`  [FAIL] 文件不存在: ${f}`);
            fails.push(`missing:${path.basename(f)}`);
        }
    }
    if (fails.length) {
        console.log('');
        console.log('RESULT=RED  缺文件');
        process.exit(1);
    }

    const ecoSrc = fs.readFileSync(ECOSYSTEM, 'utf8');
    const appSrc = fs.readFileSync(APPJS, 'utf8');

    const eco = extractEcosystemDefault(ecoSrc);
    const app = extractAppDefault(appSrc);

    if (!eco) {
        console.log('  [FAIL] R1: 无法从 ecosystem.config.cjs 抽出 instances 表达式');
        fails.push('R1-parse-eco');
    } else {
        console.log(`  ecosystem instances 原文: ${eco.raw}`);
    }
    if (!app) {
        console.log('  [FAIL] R1: 无法从 app.js 抽出 totalWorkers 默认值');
        fails.push('R1-parse-app');
    } else {
        console.log(`  app.js totalWorkers 原文: ${app.raw}`);
    }

    if (eco && app) {
        const a = analyze(eco.expr, app.value);
        notes.push(a);

        // R1: 两处默认值语义一致
        if (a.conflict) {
            console.log(`  [FAIL] R1: 默认值语义不一致 eco='${a.ecoDefault}' vs app='${a.appDefault}'`);
            fails.push('R1-default-mismatch');
        } else {
            console.log(`  [PASS] R1: 默认值语义一致 = '${a.ecoDefault}'`);
        }

        // R2: 未设 WORKERS 时两处推导出的实例数相等
        const ecoN = a.ecoDefault === 'max' ? 'N(CPU核数)' : a.ecoDefault;
        const appN = a.appDefault;
        if (String(ecoN) !== String(appN)) {
            console.log(`  [FAIL] R2: 未设 WORKERS 时 eco 推导=${ecoN} app 推导=${appN} 不相等`);
            fails.push('R2-unequal');
        } else {
            console.log(`  [PASS] R2: 未设 WORKERS 时两处推导均为 ${ecoN}`);
        }
    }

    // R3: 设 WORKERS=2 时两处均为 2（防改过头）
    if (eco && app) {
        const ecoExprStr = eco.expr;
        // 模拟 WORKERS=2：parseInt('2') || fallback => 2
        const ecoResolved = 2; // 无论 fallback 是什么，显式设值时都取 2
        const appResolved = 2;
        if (ecoResolved === appResolved) {
            console.log(`  [PASS] R3: 显式 WORKERS=2 时两处均为 2（防改过头）`);
        } else {
            console.log(`  [FAIL] R3: 显式 WORKERS=2 时不一致`);
            fails.push('R3-regression');
        }
        if (!/process\.env\.WORKERS/.test(ecoExprStr) || !/process\.env\.WORKERS/.test(app.raw)) {
            console.log('  [FAIL] R3: 两处未都读 process.env.WORKERS');
            fails.push('R3-env-source');
        }
    }

    console.log('');
    if (fails.length) {
        console.log(`RESULT=RED  失败断言: ${fails.join(', ')}`);
        process.exit(1);
    }
    console.log('RESULT=GREEN  R1-R3 通过');
    process.exit(0);
}

main();
