import build from 'pino-abstract-transport';
import SonicBoom from 'sonic-boom';
import { join } from 'node:path';
import { readdir, stat, unlink, mkdir } from 'node:fs/promises';

function getDateStr() {
    const now = new Date(Date.now() + 8 * 3600_000);
    return now.toISOString().slice(0, 10);
}

// ★★★ T26 / R3-3（审核 E 的 E-07 + 主审复核残留 B）：日志【保留期清理】。
//
// 原实现：按天分文件（`w0-system-YYYY-MM-DD.log`）—— 这一步本身是"轮转"，
//   但【没有删除策略】⇒ 日志无限增长。
//   ★ 且 `.env` 里的 `LOG_RETAIN_DAYS=1` 【从未被任何代码读取】。
//
// 现实现：
//   ① 启动时清理一次（清掉超过保留期的旧文件）
//   ② 每 6 小时再清一次（长跑进程不至于堆积）
//
// ★ 保留期来源：`LOG_RETAIN_DAYS`（默认 30 天）。
// ★ 只删本目录下【匹配本进程文件名模式】的文件，绝不误删其他文件。
const RETAIN_DAYS = Number.parseInt(process.env.LOG_RETAIN_DAYS || '30', 10) || 30;
const CLEAN_INTERVAL_MS = 6 * 3600 * 1000;

/** ★ 文件名模式：`w<instanceId>-<name>-YYYY-MM-DD.log[.N]` */
function makeFilePattern(instanceId) {
    // 允许轮转后缀（sonic-boom 可能追加 .1 .2）
    return new RegExp(`^w${instanceId}-[A-Za-z0-9_-]+-\\d{4}-\\d{2}-\\d{2}\\.log(\\.\\d+)?$`);
}

async function cleanOldLogs(logDir, instanceId) {
    const pat = makeFilePattern(instanceId);
    const cutoff = Date.now() - RETAIN_DAYS * 86400_000;
    let removed = 0;
    let scanned = 0;
    try {
        const files = await readdir(logDir);
        for (const f of files) {
            if (!pat.test(f)) continue;       // ★ 只处理本进程的日志文件
            scanned++;
            const fp = join(logDir, f);
            try {
                const st = await stat(fp);
                if (st.mtimeMs < cutoff) {
                    await unlink(fp);
                    removed++;
                }
            } catch { /* 单文件失败不影响整体 */ }
        }
    } catch { /* 目录不存在等 ⇒ 静默 */ }
    return { scanned, removed };
}

export default async function (opts) {
    const { logDir, instanceId } = opts;

    // ★ 确保目录存在（SonicBoom 的 mkdir 只在写第一个文件时生效；
    //   若进程从未写日志，目录可能不存在 ⇒ 清理会静默失败）
    try {
        await mkdir(logDir, { recursive: true });
    } catch { /* ignore */ }

    // ★ 启动清理 + 定时清理
    cleanOldLogs(logDir, instanceId)
        .then(({ scanned, removed }) => {
            process.stdout.write(JSON.stringify({
                level: 30,
                time: new Date().toISOString(),
                stream: 'system',
                msg: 'log retention sweep',
                logDir, retainDays: RETAIN_DAYS, scanned, removed,
            }) + '\n');
        })
        .catch(() => { /* ignore */ });

    const timer = setInterval(() => {
        cleanOldLogs(logDir, instanceId).catch(() => { /* ignore */ });
    }, CLEAN_INTERVAL_MS);
    if (typeof timer.unref === 'function') timer.unref();   // 不阻塞退出

    const streams = new Map();
    function getStream(name) {
        const date = getDateStr();
        const existing = streams.get(name);
        if (existing && existing.date === date) {
            return existing.boom;
        }
        if (existing) {
            existing.boom.end();
        }
        const fileName = `w${instanceId}-${name}-${date}.log`;
        const boom = new SonicBoom({
            dest: join(logDir, fileName),
            append: true,
            sync: false,
            mkdir: true,
        });
        streams.set(name, { boom, date });
        return boom;
    }
    return build(async function (source) {
        for await (const obj of source) {
            const line = JSON.stringify(obj) + '\n';
            const stream = obj.stream || 'system';
            getStream(stream).write(line);
            if (obj.level >= 40) {
                getStream('error').write(line);
            }
            // stdout 输出
            process.stdout.write(line);
        }
    }, {
        enablePipelining: false,
        close(err, cb) {
            clearInterval(timer);
            for (const { boom } of streams.values()) {
                boom.flushSync();
                boom.end();
            }
            cb(err);
        },
    });
}
//# sourceMappingURL=transport.js.map