# -*- coding: utf-8 -*-
"""T15：更正 需求文档.md 的 P2-4 条目。二进制读写保持 eol（P-36/P-37）。"""
p = USDT_ROOT + r'\09-docs\analysis\需求文档.md'

b = open(p, 'rb').read()
crlf0 = b.count(b'\r\n')
lone0 = b.count(b'\r') - crlf0
t = b.decode('utf-8')

old = '| P2-4 | `WalletData`/`device-event` 30 天 TTL 未纳入设计 | 凭证超期静默消失 | 二期 |'
new = (
    '| P2-4 | ~~`WalletData`/`device-event` 30 天 TTL 未纳入设计~~ '
    '（**前提不准确，T15 更正**）★ 实为 **已实现但未在文档中声明**：'
    '`wallet-data.js:16` / `device-event.js:10` 均已有 `expireAfterSeconds: 30 * 24 * 3600`；'
    '真正缺口是 **可观测性**（TTL 静默删除：无告警、无日志） '
    '| 凭证超期静默消失（★ 风险仍真实：TTL 固有行为即静默删除，超期 **不可追溯**） '
    '| **✅ T15 已补可观测性**（`schedules/ttl-inspect.js` 每 6h `logger.warn` '
    '+ 只读端点 `/api/dashboard/ttl-status`；**TTL 数值未改**，仍 30 天） |'
)

assert t.count(old) == 1, 'anchor count=%d' % t.count(old)
t = t.replace(old, new)
nb = t.encode('utf-8')

crlf1 = nb.count(b'\r\n')
lone1 = nb.count(b'\r') - crlf1
assert (crlf1, lone1) == (crlf0, lone0), 'EOL CHANGED (%d,%d)->(%d,%d)' % (crlf0, lone0, crlf1, lone1)

open(p, 'wb').write(nb)
print('OK bytes %d->%d CRLF %d->%d LONE_CR %d->%d' % (len(b), len(nb), crlf0, crlf1, lone0, lone1))

import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))