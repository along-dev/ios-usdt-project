// T25-C5 注入校验单测
const assertSafeChannelToken = (channel, fieldName = 'channel') => {
    if (typeof channel !== 'string' || channel.length === 0 || channel.length > 128) {
        throw new Error(`${fieldName} 非法：长度必须在 1..128`);
    }
    if (!/^[A-Za-z0-9_-]+$/.test(channel)) {
        throw new Error(`${fieldName} 非法：仅允许 [A-Za-z0-9_-]`);
    }
    return channel;
};

const bad = [
    'abc; rm -rf /',
    'abc$(whoami)',
    'abc`id`',
    '../../etc',
    'a b',
    'a|b',
    'a>b',
    'a&b',
    'x$IFS$9y',
    '',
    'a'.repeat(200),
    'a\nb',
    'a"b',
    "a'b",
];

const good = ['gplayx', 'my_channel-1', 'ABC123', 'a', 'ch-001'];

let rejected = 0, wronglyAccepted = 0, accepted = 0, wronglyRejected = 0;

console.log('  --- 恶意输入（应全部被拒）---');
for (const x of bad) {
    try {
        assertSafeChannelToken(x);
        console.log('    ★ 未拒绝: %s', JSON.stringify(x));
        wronglyAccepted++;
    } catch (e) {
        rejected++;
    }
}

console.log('  --- 合法输入（应全部通过）---');
for (const x of good) {
    try {
        assertSafeChannelToken(x);
        accepted++;
    } catch (e) {
        console.log('    ★ 误伤: %s', JSON.stringify(x));
        wronglyRejected++;
    }
}

console.log('');
console.log('  恶意输入: %d 条 → 拒绝 %d / 漏放 %d', bad.length, rejected, wronglyAccepted);
console.log('  合法输入: %d 条 → 通过 %d / 误伤 %d', good.length, accepted, wronglyRejected);
console.log('  RESULT=%s', (wronglyAccepted === 0 && wronglyRejected === 0) ? 'PASS ✅' : 'FAIL ★');
