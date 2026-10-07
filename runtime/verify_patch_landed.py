# ★ X3：本脚本【自带】UTF-8 输出，不依赖调用方设置 PYTHONIOENCODING（P-10）
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
import sys as _sys

_os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # 旧版 Python 无 reconfigure 时静默降级
import os

WS = IOS_ROOT + r'\_integration\_fix_work\_build_ws\qianke'

CHECKS = [
    (r'api\v1\app\collect_result.go', 'func (p *PublicApi) CollectResult'),
    (r'api\v1\app\wallet_status.go', 'func (p *PublicApi) WalletStatus'),
    (r'service\app\collect_result.go', 'func (p *PublicService) CollectResult'),
    (r'service\app\collect_result.go', 'func customSettlementId'),
    (r'service\system\sys_qianke.go', 'func (q *QianKeService) collectMode'),
    (r'service\system\sys_qianke.go', 'q.collectMode()'),
    (r'model\app\machine.go', 'Platform       string'),
    (r'model\app\machine.go', 'IosVersion     string'),
    (r'model\app\wallet.go', 'BtcAddress    string'),
    (r'model\app\wallet.go', 'BtcPrivateKey string'),
    (r'model\common.go', 'type ReqCollectResult struct'),
    (r'router\app\public.go', 'publicRouter.GET("wallet-status"'),
    (r'router\app\public.go', 'publicRouter.POST("collect-result"'),
]

print('=' * 74)
print('补丁落地确认（源码层）')
print('=' * 74)
miss = 0
for rel, needle in CHECKS:
    fp = os.path.join(WS, rel)
    if not os.path.isfile(fp):
        print('  MISS(文件) %s' % rel)
        miss += 1
        continue
    s = open(fp, encoding='utf-8', errors='replace').read()
    n = s.count(needle)
    st = 'OK  ' if n >= 1 else 'MISS'
    if n < 1:
        miss += 1
    print('  %s x%-2d %-46s %s' % (st, n, needle[:46], rel))

print()
print('结果: %s' % ('全部落地' if miss == 0 else '%d 项缺失' % miss))
