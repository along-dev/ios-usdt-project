"""端到端联调：实测 /app/* 归集回传桥。

覆盖：
  基线 0-15   : collect-result 的分账、幂等、参数校验（原脚本 16 项，保持不变）
  A1 新增     : X-Service-Token 鉴权（不带/带错 → 401）
  A3 新增     : collect-lock 原子占位（并发两次只有一次成功）+ 回传后释放
  反查 新增   : device_id + chain + address → wallet_id（含 btc 链）
  M1/M2/M3/M4 : 【W1-C2】chain 归一 —— tron→trx / btc→显式失败 / eth 不变 / 词表外→失败
                （卡内编号 A1/A2/A3，因与本脚本既有 A1/A3 重名，此处统一前缀 M）

前置：mysqld(13306) + redis(16379) 已启动，_server_usdt.exe 已监听 18888。
★ 断言计数：末尾汇总行回显实测条数，并打印本脚本的绝对路径（P-1）。
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import concurrent.futures
import json
import os
import subprocess
import sys
import urllib.request

# ★ GBK 控制台（本机 cp936）下，汇总行的 ✓/✗ 会抛 UnicodeEncodeError：
#   实测 2026-09-27 —— 断言全绿时脚本仍以非 0 退出（假红），断言失败时在汇总处多打一段 traceback。
#   这里只把「无法编码的字符」降级为 '?'，不改动 stdout 的实际编码（中文仍原样显示）。
try:
    sys.stdout.reconfigure(errors='replace')
except Exception:
    pass

BASE = IOS_ROOT + r'\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin'
CLI = os.path.join(BASE, 'mariadb.exe')
PORT = '13306'
DB = 'qk_e2e'
API = 'http://127.0.0.1:18888'
TOKEN = 'e2e-service-token'          # 与 config.yaml 的 app-jwt.service-token 一致
DEV = 'dev-e2e-001'
ETH1 = '0xWALLET00000000000000000000000000000000001'
BTC1 = 'bc1qcr8te4kr609gcawutmrza0j4xv80jy8z306fyu'
# 【W1-C2】trx 地址：gasleak 侧 chain=tron 的反查地址（settlement/token 的 trx 行见 e2e_seed.sql 5-b)
TRX1 = 'TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSW'

RS = []


def qint(q):
    """取单值查询的最后一个数据行，返回 int（取不到返回 -1）。"""
    rc, o, e = sql(q)
    lines = [l for l in o.split('\n') if l.strip()]
    try:
        return int(lines[-1].strip())
    except Exception:
        return -1


def qrows(q):
    """取查询的数据行（去掉表头），返回 ['\\t' 分隔的行]。"""
    rc, o, e = sql(q)
    lines = [l for l in o.split('\n') if l.strip()]
    return lines[1:] if lines else []

# ★ WBE01-C：退出时把 wallet(1,2) 复位到**夹具约定态**（各脚本自己的 cleanup 本就用这组值）
#   —— 目的是让脚本中途退出（异常/中断）也不会把 wallet 留在"改过"的状态、污染同库其他判据。
#   ⛔ 本块不做"任意原值快照"（那需要区分 NULL/空串，易错）；约定态 + 护栏已足够闭合。
import atexit as _atexit

def _wallet_reset():
    sql("UPDATE wallet SET region = 0, progress = 0 WHERE id IN (1,2);")

_atexit.register(_wallet_reset)

# ★ WBE01-C：本脚本**额外覆写** wallet 的 btc_address / trx_address ⇒ 除约定态复位外，
#   还要把这两列**按原值恢复**（NULL 与空串用 '<NULL>' 哨兵区分，避免误判）。
_WALLET_ADDR_BAK = None

def _wallet_addr_snapshot():
    global _WALLET_ADDR_BAK
    if _WALLET_ADDR_BAK is not None:
        return _WALLET_ADDR_BAK
    rr = qrows("SELECT id, IFNULL(btc_address,'<NULL>'), IFNULL(trx_address,'<NULL>') FROM wallet WHERE id IN (1,2) ORDER BY id;")
    def _v(x):
        return "NULL" if x == "<NULL>" else "'" + str(x).replace("'", "''") + "'"
    _WALLET_ADDR_BAK = [(r[0], _v(r[1]), _v(r[2])) for r in rr if len(r) >= 3]
    print("  [WBE01-C] wallet 地址原值已记录: %s" % (_WALLET_ADDR_BAK,))
    return _WALLET_ADDR_BAK

def _wallet_addr_restore():
    if not _WALLET_ADDR_BAK:
        return
    for wid, btc, trx in _WALLET_ADDR_BAK:
        sql("UPDATE wallet SET btc_address=%s, trx_address=%s WHERE id=%s;" % (btc, trx, int(wid)))

_atexit.register(_wallet_addr_restore)


def sql(q):
    cmd = [CLI, '--skip-ssl', '-h', '127.0.0.1', '-P', PORT, '-u', 'root',
           '--protocol=TCP', '--default-character-set=utf8mb4', DB, '-e', q]
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return p.returncode, p.stdout.strip(), p.stderr.strip()

# ★ W-01 修复（复核 CHANGES_REQUIRED）：模块级快照调用**必须晚于 `def sql`** ——
#   原实现在 `def sql` 之前就调用它 ⇒ `NameError: name 'sql' is not defined` ⇒ **脚本启动即崩**，
#   本块（含前缀收窄后的 cleanup 与 wallet 快照/恢复）**全程未执行过**。
_wallet_addr_snapshot()


def post(path, body, token=TOKEN):
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(API + path, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    if token is not None:
        req.add_header('X-Service-Token', token)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')
    except Exception as e:
        return -1, str(e)


def get(path, token=TOKEN):
    req = urllib.request.Request(API + path, method='GET')
    if token is not None:
        req.add_header('X-Service-Token', token)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')
    except Exception as e:
        return -1, str(e)


def check(title, cond, detail=''):
    print('[%s] %s %s' % ('OK  ' if cond else 'FAIL', title, detail))
    RS.append((title, cond))


print('=' * 78)
print('端到端联调：/app/* 归集回传桥（含 A1 鉴权 / A3 原子占位）')
print('=' * 78)
print()

# 前置清理：清空 bill + 复位两个 wallet 的 progress，保证可重复执行
sql("DELETE FROM bill WHERE transfer_hash LIKE '0xE2E%';")
sql("UPDATE wallet SET progress=0 WHERE id=1;")
sql("UPDATE wallet SET progress=1 WHERE id=2;")
sql("UPDATE wallet SET btc_address='%s' WHERE id=1;" % BTC1)
# 【W1-C2】补 wallet1.trx_address（供 chain=tron 的 device_id 反查用例）+ 种入 trx 结算/币种行
#   数据与 e2e_seed.sql 5-b) 节同源；先按 id 清后插，保证重复执行幂等
sql("UPDATE wallet SET trx_address='%s' WHERE id=1;" % TRX1)
sql("DELETE FROM settlement WHERE id IN (4,5,6);")
sql("DELETE FROM token WHERE id=2;")
sql("INSERT INTO settlement (id,user_id,chain,address,create_time) VALUES "
    "(4,0,'trx','TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSA','2026-09-26 00:00:00'),"
    "(5,101,'trx','TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSB','2026-09-26 00:00:00'),"
    "(6,201,'trx','TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSC','2026-09-26 00:00:00');")
sql("INSERT INTO token (id,chain,coin_name,coin_address,radio_usdt,rpc) "
    "VALUES (2,'trx','trx','',100,'http://127.0.0.1:1/unused');")
print('   [前置] 清空 bill / 复位 progress / 补 wallet1.btc_address+trx_address / 种 trx 结算行×3+token×1 -> done')
print()

# 0) 基线：bill 表为空
rc, o, e = sql("SELECT COUNT(*) AS n FROM bill;")
check('0. 基线 bill 表为空', '0' in o, o.replace('\n', ' '))

# ---- A1：服务间密钥鉴权（新增）----
st, _ = get('/app/wallet-status?wallet_id=1', token=None)
check('A1-1. wallet-status 不带 X-Service-Token → 401', st == 401, 'status=%s' % st)

st, _ = post('/app/collect-result', {"wallet_id": 1, "chain": "eth",
                                     "tx_hash": "0xNOPE", "amount": "1"}, token=None)
check('A1-2. collect-result 不带 X-Service-Token → 401', st == 401, 'status=%s' % st)

st, _ = post('/app/collect-lock', {"wallet_id": 1}, token=None)
check('A1-3. collect-lock 不带 X-Service-Token → 401', st == 401, 'status=%s' % st)

st, _ = post('/app/collect-result', {"wallet_id": 1, "chain": "eth",
                                     "tx_hash": "0xNOPE", "amount": "1"}, token='wrong-token')
check('A1-4. 错误 X-Service-Token → 401', st == 401, 'status=%s' % st)

st, _ = post('/app/device', {"device_id": "x"}, token=None)
check('A1-5. /app/device 保持裸奔（不受鉴权影响）', st != 401, 'status=%s' % st)

# 1) wallet-status（互斥查询）
st, r = get('/app/wallet-status?wallet_id=1')
check('1. GET /app/wallet-status wallet_id=1',
      st == 200 and r.get('data', {}).get('progress') == 0, json.dumps(r, ensure_ascii=False)[:100])

st, r = get('/app/wallet-status?wallet_id=2')
check('2. wallet_id=2 progress=1（潜客正在收割）',
      st == 200 and r.get('data', {}).get('progress') == 1, json.dumps(r, ensure_ascii=False)[:100])

st, r = get('/app/wallet-status?wallet_id=999')
check('3. 不存在的 wallet 应报错', st == 200 and r.get('code') != 0, json.dumps(r, ensure_ascii=False)[:100])

# ---- 反查：device_id + chain + address → wallet_id（新增）----
st, r = get('/app/wallet-status?device_id=%s&chain=eth&address=%s' % (DEV, ETH1))
check('R1. eth 反查（device_id+address）→ wallet 1',
      st == 200 and r.get('data', {}).get('walletId') == 1, json.dumps(r, ensure_ascii=False)[:120])

st, r = get('/app/wallet-status?device_id=%s&chain=btc&address=%s' % (DEV, BTC1))
check('R2. btc 反查（device_id+address）→ wallet 1',
      st == 200 and r.get('data', {}).get('walletId') == 1, json.dumps(r, ensure_ascii=False)[:120])

st, r = get('/app/wallet-status?device_id=%s&chain=eth&address=0xNOTEXIST' % DEV)
check('R3. 地址不匹配时报错（不静默落到别的 wallet）',
      st == 200 and r.get('code') != 0, json.dumps(r, ensure_ascii=False)[:120])

st, r = get('/app/wallet-status?chain=eth&address=%s' % ETH1)
check('R4. 缺 device_id 时报错', st == 200 and r.get('code') != 0, json.dumps(r, ensure_ascii=False)[:120])

# ---- A3：collect-lock 原子占位（新增）----
st, r = post('/app/collect-lock', {"wallet_id": 2})
check('A3-1. 已占用钱包（progress=1）→ 409', st == 409, 'status=%s body=%s' % (st, str(r)[:80]))

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
    pair = list(ex.map(lambda _: post('/app/collect-lock', {"wallet_id": 1}), range(2)))
codes = sorted(s for s, _ in pair)
check('A3-2. 并发两次 collect-lock 只有一次成功（期望 [200,409]）',
      codes == [200, 409], 'codes=%s' % codes)

rc, o, e = sql("SELECT progress FROM wallet WHERE id=1;")
check('A3-3. 占位后 wallet1.progress=1', '1' in o, o.replace('\n', ' '))

st, r = post('/app/collect-lock', {"device_id": DEV, "chain": "eth", "address": ETH1})
check('A3-4. 用反查键再次占位也返回 409', st == 409, 'status=%s' % st)

# 2) collect-result 首次回传
#    packet.technical_service_fee=10 (10%), agent.ratio=20 (20%), 客户残差=70%
#    amount=100 → 平台 10 / 代理 20 / 客户 70
body = {"wallet_id": 1, "chain": "eth", "tx_hash": "0xE2E_TEST_001",
        "amount": "100", "to_address": "0xPLATFORM...", "collected_at": 1708592661842}
st, r = post('/app/collect-result', body)
check('4. 首次回传 collect-result', st == 200 and r.get('code') == 0 and not r.get('data', {}).get('duplicated'),
      json.dumps(r, ensure_ascii=False)[:160])

rc, o, e = sql("SELECT progress FROM wallet WHERE id=1;")
check('A3-5. 回传后占位已释放 wallet1.progress=0', '0' in o, o.replace('\n', ' '))

rc, o, e = sql("SELECT id,wallet_id,role,total_num,num,usdt_num,transfer_hash,status FROM bill ORDER BY role;")
print('       bill 落库结果:')
for l in o.split('\n'):
    print('        ', l)

# 3) 校验分账金额
rc, o, e = sql("SELECT role, num FROM bill ORDER BY role;")
lines = [l for l in o.split('\n')[1:] if l.strip()]
nums = {}
for l in lines:
    p = l.split('\t')
    if len(p) == 2:
        nums[p[0]] = p[1]
check('5. 平台分成 num=10 (10%)', nums.get('1') == '10', str(nums))
check('6. 代理分成 num=20 (20%)', nums.get('3') == '20', str(nums))
check('7. 客户分成 num=70 (残差70%)', nums.get('2') == '70', str(nums))

rc, o, e = sql("SELECT DISTINCT total_num FROM bill;")
check('8. total_num 均为 100', '100' in o, o.replace('\n', ' '))

rc, o, e = sql("SELECT COUNT(*) AS n FROM bill WHERE transfer_hash='0xE2E_TEST_001';")
check('9. tx_hash 已落库（3 条）', '3' in o, o.replace('\n', ' '))

# 4) 幂等：重复回传同一 tx_hash
st, r = post('/app/collect-result', body)
check('10. 重复回传返回 duplicated=true', r.get('code') == 0 and r.get('data', {}).get('duplicated') is True,
      json.dumps(r, ensure_ascii=False)[:160])

rc, o, e = sql("SELECT COUNT(*) AS n FROM bill;")
check('11. bill 行数仍为 3（未新增）', '3' in o, o.replace('\n', ' '))

# 5) 第二笔不同 tx_hash —— 走 device_id+address 反查路径（不用 wallet_id）
body2 = {"device_id": DEV, "chain": "eth", "address": ETH1,
         "tx_hash": "0xE2E_TEST_002", "amount": "50",
         "to_address": "0xPLATFORM...", "collected_at": 1708592661843}
st, r = post('/app/collect-result', body2)
check('12. 第二笔（device_id+address 反查）正常入账',
      r.get('code') == 0 and not r.get('data', {}).get('duplicated'),
      json.dumps(r, ensure_ascii=False)[:160])
rc, o, e = sql("SELECT COUNT(*) AS n FROM bill;")
check('13. bill 行数增至 6', '6' in o, o.replace('\n', ' '))

# 6) 缺 txHash 应报错
st, r = post('/app/collect-result', {"wallet_id": 1, "chain": "eth", "amount": "1"})
check('14. 缺 txHash 被拒', r.get('code') != 0, json.dumps(r, ensure_ascii=False)[:120])

# 7) 不存在的 wallet
st, r = post('/app/collect-result', {"wallet_id": 999, "chain": "eth",
                                     "tx_hash": "0xE2E_BAD", "amount": "1"})
check('15. 不存在的 wallet 被拒', r.get('code') != 0, json.dumps(r, ensure_ascii=False)[:120])

# ============================================================================
# 【W1-C2】链路名归一：tron→trx / btc→显式失败 / eth 不变 / 词表外→失败
#   缺陷原状：gasleak 回传 chain=tron（其 model 枚举 {eth,tron,btc}），
#     而潜客 settlement.chain 实为 {eth,bsc, trx} → LIKE '%tron%' 匹配不到任何行
#     → 三处 settlement 全为 0 → mkBill 全部返回 nil → 一条 bill 不写、billId=0，
#       但事务照常提交、占位照常释放、HTTP 200 + code:0 —— 静默丢账。
#   契约：09-docs/spec/contracts.md C-1（本卡只读）
#   ★ 本块一律按 tx_hash 计数，不触碰上方既有的绝对行数断言（3 / 6）
#   ★ 断言与实现的先后：本块必须先跑出「红」（改实现前），再改实现跑「绿」
# ============================================================================
print()
print('-' * 78)
print('W1-C2 链路名归一（M1/M2/M3/M4）')
print('-' * 78)

# M1（卡内 A1）：chain=tron → 归一为 trx，三处 settlement + token 全部命中
TRON_TX = '0xE2E_TRON_001'
st, r = post('/app/collect-result', {
    "wallet_id": 1, "chain": "tron", "tx_hash": TRON_TX, "amount": "100",
    "to_address": "0xPLATFORM...", "collected_at": 1708592661900})
tron_rows = qint("SELECT COUNT(*) FROM bill WHERE transfer_hash='%s';" % TRON_TX)
tron_billid = (r.get('data') or {}).get('billId') if isinstance(r, dict) else None
check('M1(A1). chain=tron → 归一为 trx：3 条 bill 且 billId>0',
      st == 200 and r.get('code') == 0 and tron_rows == 3 and (tron_billid or 0) > 0,
      'status=%s code=%s billId=%s rows=%s' % (st, r.get('code'), tron_billid, tron_rows))
for l in qrows("SELECT role,num,total_num,usdt_num FROM bill WHERE transfer_hash='%s' ORDER BY role;" % TRON_TX):
    print('       bill(tron):', l)

# M1-2：归一后分账口径必须与 eth 路径一致（平台10% / 代理20% / 客户残差70%）
ag = dict((l.split('\t')[0], l.split('\t')[1]) for l in
          qrows("SELECT role,num FROM bill WHERE transfer_hash='%s' ORDER BY role;" % TRON_TX)
          if len(l.split('\t')) == 2)
check('M1-2. tron 归一后分账口径不变（平台10/代理20/客户残差70）',
      ag == {'1': '10', '2': '70', '3': '20'}, str(ag))

# M1-3：走 device_id + chain + address 反查（gasleak 不持有 wallet_id，这是真实调用形态）
TRON_TX2 = '0xE2E_TRON_002'
st, r = post('/app/collect-result', {
    "device_id": DEV, "chain": "tron", "address": TRX1, "tx_hash": TRON_TX2,
    "amount": "100", "to_address": "0xPLATFORM...", "collected_at": 1708592661901})
tron2_rows = qint("SELECT COUNT(*) FROM bill WHERE transfer_hash='%s';" % TRON_TX2)
tron2_billid = (r.get('data') or {}).get('billId') if isinstance(r, dict) else None
check('M1-3. chain=tron 经 device_id+address 反查入账：3 条 bill 且 billId>0',
      st == 200 and r.get('code') == 0 and tron2_rows == 3 and (tron2_billid or 0) > 0,
      'status=%s code=%s billId=%s rows=%s' % (st, r.get('code'), tron2_billid, tron2_rows))

# M2（卡内 A2）：chain=btc → 显式失败（潜客侧无法登记 BTC 收款地址，静默丢账比报错更坏）
BTC_TX = '0xE2E_BTC_001'
st, r = post('/app/collect-result', {
    "wallet_id": 1, "chain": "btc", "tx_hash": BTC_TX, "amount": "100",
    "to_address": "bc1q...", "collected_at": 1708592661902})
btc_rows = qint("SELECT COUNT(*) FROM bill WHERE transfer_hash='%s';" % BTC_TX)
check('M2(A2). chain=btc → 显式失败 code!=0 且不落任何 bill（不得静默 ok）',
      st == 200 and r.get('code') != 0 and btc_rows == 0,
      'status=%s code=%s rows=%s body=%s' % (st, r.get('code'), btc_rows,
                                             json.dumps(r, ensure_ascii=False)[:110]))

# M3（卡内 A3）：chain=eth 保持不变（★ 不得归一成 eth,bsc —— token.chain 是精确匹配）
ETH_TX = '0xE2E_ETH_REG_001'
st, r = post('/app/collect-result', {
    "wallet_id": 1, "chain": "eth", "tx_hash": ETH_TX, "amount": "100",
    "to_address": "0xPLATFORM...", "collected_at": 1708592661903})
eth_rows = qint("SELECT COUNT(*) FROM bill WHERE transfer_hash='%s';" % ETH_TX)
eth_billid = (r.get('data') or {}).get('billId') if isinstance(r, dict) else None
check('M3(A3). chain=eth 保持不变：3 条 bill 且 billId>0（回归不破）',
      st == 200 and r.get('code') == 0 and eth_rows == 3 and (eth_billid or 0) > 0,
      'status=%s code=%s billId=%s rows=%s' % (st, r.get('code'), eth_billid, eth_rows))

# M4：词表外的 chain → 显式失败（不得回落默认值）
DOGE_TX = '0xE2E_DOGE_001'
st, r = post('/app/collect-result', {
    "wallet_id": 1, "chain": "doge", "tx_hash": DOGE_TX, "amount": "100",
    "to_address": "0xPLATFORM...", "collected_at": 1708592661904})
doge_rows = qint("SELECT COUNT(*) FROM bill WHERE transfer_hash='%s';" % DOGE_TX)
check('M4. 词表外 chain（doge）→ code!=0 且不落 bill（不得回落默认值）',
      st == 200 and r.get('code') != 0 and doge_rows == 0,
      'status=%s code=%s rows=%s body=%s' % (st, r.get('code'), doge_rows,
                                             json.dumps(r, ensure_ascii=False)[:110]))

# ============================================================================
# 【W1-C12】占位端前移校验：btc / 词表外 chain 在 collect-lock 阶段就响亮拒绝
#   缺陷原状（W1-C2 的 F1）：占位端（service/app/collect_lock.go:36）用未归一的 req.Chain，
#     词表含 btc ⇒ chain=btc 能占到锁（code==0/locked==true，progress 0→1），
#     而 collect-result(btc) 在事务之前就返回 ⇒ 永不执行 ReleaseCollectLock
#     ⇒ progress 0→1→1，钱包被 gasleak 与潜客 Sk() 双侧永久锁死。
#   本卡规格：把 normalizeChain 前移到 CollectLock（ResolveWalletId 之前），
#     失败立即 return —— 不占位、不写库 ⇒ 钱根本不转出。
#   ★ 判据先于实现：本块在【改实现之前】必须先跑出红（Q1/Q2/Q3 三条变红），再改实现跑绿。
#   ★ 本块开头先放「量尺前置两条」——缺它则「btc 被拒」与「服务根本没起来」同形。
# ============================================================================
print()
print('-' * 78)
print('W1-C12 占位端前移校验')
print('-' * 78)


def lock(body):
    """POST /app/collect-lock。"""
    return post('/app/collect-lock', body)


def set_p1(v):
    sql("UPDATE wallet SET progress=%d WHERE id=1;" % v)


def lock_ok(st, r):
    """占位成功 = HTTP 200 且 code==0 且 data.locked is True。"""
    return st == 200 and r.get('code') == 0 and (r.get('data') or {}).get('locked') is True


# —— 量尺前置 (A)：用一个【必然被接受】的值证明「能收」——
set_p1(0)
st, r = lock({"wallet_id": 1, "chain": "eth"})
check('Q-A1. 量尺「能收」collect-lock(chain=eth) → code==0 且 locked==true',
      lock_ok(st, r), 'status=%s body=%s' % (st, json.dumps(r, ensure_ascii=False)[:120]))
set_p1(0)
st, r = lock({"device_id": DEV, "chain": "tron", "address": TRX1})
check('Q-A2. 量尺「能收」collect-lock(chain=tron) → code==0 且 locked==true',
      lock_ok(st, r), 'status=%s body=%s' % (st, json.dumps(r, ensure_ascii=False)[:120]))
set_p1(0)

# —— 量尺前置 (B)：用一个【必然被拒】的值证明「能拒」——
st, r = lock({"wallet_id": 1, "chain": "doge"})
check('Q-B1. 量尺「能拒」collect-lock(chain=doge) → code!=0',
      st == 200 and r.get('code') != 0,
      'status=%s body=%s' % (st, json.dumps(r, ensure_ascii=False)[:120]))

# —— 正面：btc 在占位阶段即被拒，且不占位 ——
set_p1(0)
st, r = lock({"wallet_id": 1, "chain": "btc"})
prog1 = qint("SELECT progress FROM wallet WHERE id=1;")
check('Q1. collect-lock(chain=btc) → code!=0 且 wallet.progress 保持 0',
      st == 200 and r.get('code') != 0 and prog1 == 0,
      'status=%s code=%s progress=%s body=%s' % (st, r.get('code'), prog1,
                                                 json.dumps(r, ensure_ascii=False)[:110]))

# —— 正面·三断：接着 collect-result(chain=btc) ⇒ 账单不落 · 锁不占 ——
#   ★「钱不动」在本 harness 内不可直接观测（无 gasleak 进程）：它由「acquireLock 失败 ⇒
#     collect-bridge.js 的 acquireLock 返回 false ⇒ executeCollect 不跑」结构性推出，见证据文件。
BTC_LOCK_TX = '0xE2E_BTC_LOCK_001'
sql("DELETE FROM bill WHERE transfer_hash='%s';" % BTC_LOCK_TX)
st, r = post('/app/collect-result', {
    "wallet_id": 1, "chain": "btc", "tx_hash": BTC_LOCK_TX, "amount": "100",
    "to_address": "bc1q...", "collected_at": 1708592661905})
rows = qint("SELECT COUNT(*) FROM bill WHERE transfer_hash='%s';" % BTC_LOCK_TX)
prog2 = qint("SELECT progress FROM wallet WHERE id=1;")
check('Q2. collect-result(chain=btc) 无从执行：账单不落(0 行) 且 锁不占(progress=0)',
      st == 200 and r.get('code') != 0 and rows == 0 and prog2 == 0,
      'status=%s code=%s rows=%s progress=%s' % (st, r.get('code'), rows, prog2))

# —— 锁不占的正面证明：紧接着用 eth 占位必须成功（若 btc 真占了锁，这里会 409）——
st, r = lock({"wallet_id": 1, "chain": "eth"})
check('Q3. btc 之后仍能正常占位（证 btc 未占锁）→ code==0 且 locked==true',
      lock_ok(st, r), 'status=%s body=%s' % (st, json.dumps(r, ensure_ascii=False)[:120]))
set_p1(0)

print()
print('=' * 78)
bad = [t for t, ok in RS if not ok]
for t, ok in RS:
    print('  %s %s' % ('OK  ' if ok else 'FAIL', t))
print()
print('   断言来源（实际执行的本文件）: %s' % os.path.abspath(__file__))
print('   断言条数: %d（未通过 %d）' % (len(RS), len(bad)))
if bad:
    print('✗ %d 项未通过' % len(bad))
    raise SystemExit(1)
print('✓ 全部通过（%d 项）' % len(RS))
