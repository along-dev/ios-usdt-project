import build from 'pino-abstract-transport';
import SonicBoom from 'sonic-boom';
import { join } from 'node:path';
function getDateStr() {
    const now = new Date(Date.now() + 8 * 3600_000);
    return now.toISOString().slice(0, 10);
}
export default async function (opts) {
    const { logDir, instanceId } = opts;
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
            for (const { boom } of streams.values()) {
                boom.flushSync();
                boom.end();
            }
            cb(err);
        },
    });
}
//# sourceMappingURL=transport.js.map