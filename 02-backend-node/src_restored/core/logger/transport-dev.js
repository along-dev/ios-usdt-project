import build from 'pino-abstract-transport';
const LEVELS = { 10: 'TRACE', 20: 'DEBUG', 30: 'INFO', 40: 'WARN', 50: 'ERROR', 60: 'FATAL' };
const LEVEL_COLORS = {
    10: '\x1b[90m', // gray
    20: '\x1b[36m', // cyan
    30: '\x1b[32m', // green
    40: '\x1b[33m', // yellow
    50: '\x1b[31m', // red
    60: '\x1b[35m', // magenta
};
const RESET = '\x1b[0m';
const DIM = '\x1b[2m';
const CYAN = '\x1b[36m';
const YELLOW = '\x1b[33m';
const MAGENTA = '\x1b[35m';
const BLUE = '\x1b[34m';
const ORANGE = '\x1b[38;5;172m';
// pino 内部字段，不作为额外数据输出
const INTERNAL_KEYS = new Set(['level', 'time', 'pid', 'hostname', 'msg', 'stream', 'traceId', 'deviceId', 'channelCode', 'realIP', 'username']);
export default async function () {
    return build(async function (source) {
        for await (const obj of source) {
            const time = obj.time || '';
            const level = obj.level || 30;
            const levelTag = LEVELS[level] || 'INFO';
            const levelColor = LEVEL_COLORS[level] || '';
            // 上下文标签：有值才显示，各自带颜色
            const tags = [];
            if (obj.traceId)
                tags.push(`${CYAN}[tid=${obj.traceId}]${RESET}`);
            if (obj.deviceId)
                tags.push(`${YELLOW}[udid=${obj.deviceId}]${RESET}`);
            if (obj.channelCode)
                tags.push(`${MAGENTA}[channel=${obj.channelCode}]${RESET}`);
            const tagStr = tags.length ? ' ' + tags.join(' ') : '';
            // stream 标签（放在时间后面）
            const stream = obj.stream || 'system';
            const streamTag = `${ORANGE}[${stream}]${RESET}`;
            // 消息
            const msg = obj.msg || '';
            // 额外字段
            const extra = {};
            for (const key of Object.keys(obj)) {
                if (!INTERNAL_KEYS.has(key))
                    extra[key] = obj[key];
            }
            const extraStr = Object.keys(extra).length > 0 ? ` ${CYAN}${JSON.stringify(extra)}${RESET}` : '';
            const line = `${DIM}[${time}]${RESET} ${streamTag}${tagStr} ${levelColor}${levelTag}${RESET} ${BLUE}${msg}${RESET}${extraStr}\n`;
            process.stdout.write(line);
        }
    }, {
        enablePipelining: false,
    });
}
//# sourceMappingURL=transport-dev.js.map