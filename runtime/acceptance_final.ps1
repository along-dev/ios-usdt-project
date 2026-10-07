# ===========================================================================
# ★ 门禁分工边界（2026-09-27，W1-C8 规格 4；见台账 L019）
#
#   本脚本 acceptance_final.ps1 —— 【产物内无残留】门禁
#     · 管什么：产物内是否残留【已知敏感值】。模式集 =
#         _secrethunt 资产集（按 assets.json 派生）  ＋  $LEGACY（显式登记的集外值）。
#       ★ W1-C10（2026-09-27）：$LEGACY 的【集外】部分（3 条）已迁出到产物外的
#         单一登记层 _fix_work\extra_credentials.json（四读取方共用）；本脚本只【读】它。
#     · 何时跑：**构建后**，可对【任意】产物随时复检（用 -Target 指向该产物）。
#     · 退出码：有缺陷残留 => exit 2；干净 => exit 0（另：目标不存在 => exit 2）。
#
#   _fix_work\verify_w1c1_credentials.py —— 【集外凭据】专项门禁
#     · 管什么：只判【3 个集外凭据】（手工登记，逐值报处数）；不覆盖资产集内的值。
#     · 何时跑：**构建前 / 后均可**。
#     · 退出码：有残留 => 1；全 0 => 0。
#
#   ★ 为什么必须写清：在本卡（W1-C8）之前，二者对【同一批集外值】给出【相反信号】
#     （本脚本 EXIT=0「看不见」 / verify_w1c1_credentials.py EXIT=1），
#     而读者会【信绿的那个】（"验收过了"）。=> 二者【专责不同、互不替代】：
#     任一为红都表示产物内仍有残留。
# ===========================================================================
param(
    # ★ 2026-09-27：原脚本把目标硬编码为 E:\ios漏洞\_buildtest，导致【构建后新增的文件
    #   永远无法复检】—— D4 实测 reports/ 目录就因此漏网（其完整 JWT_SECRET 一直在产物里）。
    [string]$Target = 'E:\USDT项目',
    # 与 build_unified.ps1 保持独立的第二实现：验证器不与被验证者共享代码，
    # 否则同一个逻辑错误会在两边一起"通过"。
    [string]$AssetsJson = 'E:\ios漏洞\_secrethunt\assets.json'
)

$ErrorActionPreference = 'Continue'

# ---------------------------------------------------------------------------
# 占位符表 / 载体类型（与 build_unified.ps1 同源但独立维护）
# ---------------------------------------------------------------------------
$PLACEHOLDER_BY_TYPE = @{
    'CHANNEL_CODE' = '${CHANNEL_SEED}'; 'CHANNEL_DOMAINS' = '${C2_DOMAIN}'
    'MAIN_COLLECT_ADDRESS_ETH' = '${COLLECT_ADDRESS_ETH}'; 'BACKDOOR_TARGET_ETH' = '${COLLECT_ADDRESS_ETH}'
    'COLLECT_TARGET_ETH' = '${COLLECT_ADDRESS_ETH}'; 'COLLECT_BACKDOOR_ETH' = '${COLLECT_ADDRESS_ETH}'
    'MAIN_COLLECT_ADDRESS_TRON' = '${COLLECT_ADDRESS_TRON}'; 'BACKDOOR_TARGET_TRON' = '${COLLECT_ADDRESS_TRON}'
    'COLLECT_TARGET_TRON' = '${COLLECT_ADDRESS_TRON}'; 'COLLECT_BACKDOOR_TRON' = '${COLLECT_ADDRESS_TRON}'
    'GASLEAK_ADMIN_PASSWORD' = '${GASLEAK_ADMIN_PASSWORD}'; 'GASLEAK_USER_HASH' = '${GASLEAK_USER_HASH}'
    'TOTP_SECRET' = '${TOTP_SECRET}'; 'LIVE_APK_DISTRIBUTION_URL' = '${APK_DISTRIBUTION_URL}'
    'CORUNA_COLLECT_GUARD_PASS' = '${CORUNA_CONSOLE_PASS}'; 'GEN_PASSWORD' = '${CORUNA_CONSOLE_PASS}'
    'CHAIN_APIKEY_ETH' = '${ETH_RPC_KEY}'; 'CHAIN_APIKEY_TRON' = '${TRON_RPC_KEY}'
    'TATUM_KEY_POOL_TRON' = '${TRON_RPC_KEY}'
    'ENV_SECRET_JWT_SECRET' = '${JWT_SECRET}'; 'ENV_SECRET_EXPORT_ENCRYPTION_KEY' = '${EXPORT_ENCRYPTION_KEY}'
    'ENV_SECRET_DEFAULT_ADMIN_PASSWORD' = '${DEFAULT_ADMIN_PASSWORD}'
    'IMPLANT_JWT' = '${IMPLANT_JWT}'; 'BCRYPT_PASSWORD_HASH' = '${BCRYPT_PASSWORD_HASH}'
    'FERNET_ENCRYPTED_WEBHOOK' = '${FERNET_WEBHOOK}'
    'ARCHIVE_7Z_PASSWORD' = '${SEVEN_ZIP_PASSWORD}'
    'ENV_SECRET_MONGO_URI' = '${MONGO_URI}'; 'ENV_SECRET_REDIS_URL' = '${REDIS_URL}'
}

# 二进制载荷 / 演示夹具：命中属"设计取舍"，不计失败
$CARRIER_TYPES = @('ARCHIVE_7Z_PASSWORD', 'BCRYPT_PASSWORD_HASH', 'IMPLANT_JWT',
    'FERNET_ENCRYPTED_WEBHOOK', 'ENV_SECRET_MONGO_URI', 'ENV_SECRET_REDIS_URL',
    'CORUNA_COLLECT_GUARD_PASS')

$LEGACY = @(
    '586840011f5435723fdfb28b849b53c31dbb91a858c2137fa7fb9f7e7b904e03',
    'HCRs35JHX7kuKHWh4ZBZBsPH3EiiBH4u',
    'DEFAULT_ADMIN_PASSWORD=admin',
    '586840011f', '58684001', 'HCRs35JH',
    '0b8a4f36-90f4-49d5-98e2-2f772cd23e24', '0b8a4f36'   # A5 signing-key
    # ★ W1-C10（2026-09-27）：原 W1-C8 在此【内嵌】的 3 条【集外】凭据已【迁出】——
    #   改由产物外的单一登记层 _fix_work\extra_credentials.json 提供（见下方读取块）；
    #   本表不再重复维护（该 JSON 与本脚本同目录，故用 $PSScriptRoot 定位）。
)

# =============================================================================
# ★ W1-C10：集外凭据的【单一登记层】（★ 在产物外）
#   · 四读取方共用：build_unified.ps1 / 本脚本 / verify_redaction_reverse.py / verify_w1c1_credentials.py
#   · 只【读】、绝不复制进产物；读不到【告警】而不静默降覆盖。
# =============================================================================
$ExtraCredentialsJson = Join-Path $PSScriptRoot 'extra_credentials.json'
if (Test-Path $ExtraCredentialsJson) {
    try {
        $extra = Get-Content -Path $ExtraCredentialsJson -Raw -Encoding UTF8 | ConvertFrom-Json
        $n = 0
        foreach ($p in $extra.PSObject.Properties) {
            $v = [string]$p.Value
            if (-not [string]::IsNullOrWhiteSpace($v) -and $LEGACY -notcontains $v) { $LEGACY += $v; $n++ }
        }
        Write-Host ("  集外凭据登记层: {0} 条（{1}）" -f $n, $ExtraCredentialsJson)
    } catch {
        Write-Host "  !! 集外凭据登记层解析失败：$($_.Exception.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  !! 未找到集外凭据登记层：$ExtraCredentialsJson —— 集外凭据将不再被检查" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 派生模式（含与 D4 同源的三层噪声排除）
# ---------------------------------------------------------------------------
function Get-Patterns {
    $defect = New-Object System.Collections.Generic.List[string]
    $carrier = New-Object System.Collections.Generic.List[string]
    foreach ($k in $LEGACY) { if (-not $defect.Contains($k)) { $defect.Add($k) } }

    if (-not (Test-Path $AssetsJson)) {
        Write-Host "  !! 未找到 $AssetsJson —— 仅使用遗留模式（覆盖度不足）" -ForegroundColor Yellow
        return @{ Defect = $defect; Carrier = $carrier }
    }
    $assets = Get-Content -Path $AssetsJson -Raw -Encoding UTF8 | ConvertFrom-Json
    # ★ 载体按【值】判定，不按 type —— 同一值可能同时挂在载体与非载体 type 下
    #   （7z 口令既是 ARCHIVE_7Z_PASSWORD 又作为 GEN_PASSWORD 出现）。
    $carrierVals = New-Object System.Collections.Generic.HashSet[string]
    foreach ($a in $assets) {
        if ($CARRIER_TYPES -notcontains [string]$a.type) { continue }
        foreach ($v in (([string]$a.secret) -split "`n")) {
            $v = $v.Trim()
            if ($v.Length -ge 12) { [void]$carrierVals.Add($v) }
        }
    }
    foreach ($a in $assets) {
        if ($a.category -eq 'false-positive') { continue }                  # ① hashcat/john 向量
        if (-not $PLACEHOLDER_BY_TYPE[[string]$a.type]) { continue }
        $val = [string]$a.secret
        if ([string]::IsNullOrWhiteSpace($val)) { continue }
        if ($val -match '^[\u2500\u2014\-=_·\s]+$') { continue }             # ② 分隔符噪声
        if ($val -match '^[A-Za-z_][A-Za-z0-9_.]*\($') { continue }          # ③ 代码片段
        foreach ($v in ($val -split "`n")) {
            $v = $v.Trim()
            if ($v.Length -lt 12) { continue }
            if ($carrierVals.Contains($v)) { if (-not $carrier.Contains($v)) { $carrier.Add($v) } }
            else { if (-not $defect.Contains($v)) { $defect.Add($v) } }
        }
    }
    return @{ Defect = $defect; Carrier = $carrier }
}

Write-Host ('=' * 78)
Write-Host "脱敏验收（可对任意产物随时复检）"
Write-Host ('=' * 78)
Write-Host "目标: $Target"
$t = $Target
if (-not (Test-Path $t)) { Write-Host "目标不存在: $t" -ForegroundColor Red; exit 2 }

$pf = Get-Patterns
$defectPat = @($pf.Defect)
$carrierPat = @($pf.Carrier)
Write-Host ("  模式数: 缺陷 {0} / 已知载体 {1}" -f $defectPat.Count, $carrierPat.Count)
Write-Host ''

# ---------------------------------------------------------------------------
# A 组：明文残留（单次遍历，全部模式合成一个正则）
# ---------------------------------------------------------------------------
Write-Host '################ 验收 A：明文残留 ################'
$files = @(Get-ChildItem -Path $t -Recurse -File -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
Write-Host "扫描文件数: $($files.Count)"
$all = @($defectPat) + @($carrierPat)
$combined = (($all | Sort-Object -Property Length -Descending | ForEach-Object { [regex]::Escape($_) }) -join '|')
$hits = @()
if ($files.Count -gt 0 -and $combined.Length -gt 0) {
    $hits = @(Select-String -Path $files -Pattern $combined -ErrorAction SilentlyContinue)
}
$defectHits = @(); $carrierHits = @()
foreach ($h in $hits) {
    $line = [string]$h.Line
    $m = @($all | Where-Object { $line.Contains($_) })
    $nonCarrier = @($m | Where-Object { $carrierPat -notcontains $_ })
    if ($m.Count -gt 0 -and $nonCarrier.Count -eq 0) { $carrierHits += $h } else { $defectHits += $h }
}
Write-Host "A1) 缺陷命中: $($defectHits.Count)   期望 0"
# ★ 只打印位置，不打印命中的明文本身 —— 否则验收输出会二次泄漏（原脚本会打印整行）
foreach ($h in $defectHits) { Write-Host "      $($h.Path):$($h.LineNumber)" -ForegroundColor Red }
Write-Host "A2) 已知载体命中: $($carrierHits.Count)  （二进制载荷/演示夹具，§8.4 设计取舍）" -ForegroundColor Yellow
Write-Host ''

# ---------------------------------------------------------------------------
# B 组：qianke.sql 无 INSERT
# ---------------------------------------------------------------------------
Write-Host '################ 验收 B：qianke.sql ################'
$sql = Join-Path $t '07-db\schema\qianke.sql'
$bad = 0
if (Test-Path $sql) {
    $ins = 0
    $m = Select-String -Path $sql -Pattern 'INSERT INTO' -AllMatches -ErrorAction SilentlyContinue
    if ($m) { foreach ($x in $m) { $ins += @($x.Matches).Count } }
    $ddl = 0
    $m2 = Select-String -Path $sql -Pattern 'CREATE TABLE' -AllMatches -ErrorAction SilentlyContinue
    if ($m2) { foreach ($x in $m2) { $ddl += @($x.Matches).Count } }
    Write-Host "B1) INSERT INTO 命中数: $ins   期望 0"
    Write-Host "B2) CREATE TABLE 保留: $ddl   期望 27"
    if ($ins -gt 0) { $bad += $ins }
} else { Write-Host "  !! 未找到 $sql" -ForegroundColor Yellow }
Write-Host ''

# ---------------------------------------------------------------------------
# C 组：.env.example 无明文口令
# ---------------------------------------------------------------------------
Write-Host '################ 验收 C：.env.example ################'
$envf = Join-Path $t '.env.example'
if (Test-Path $envf) {
    Get-Content $envf -Encoding UTF8 | Where-Object { $_ -match 'JWT|EXPORT|ADMIN_PASSWORD' } |
        ForEach-Object { Write-Host "   $_" }
} else { Write-Host "  !! 未找到 $envf" -ForegroundColor Yellow }
Write-Host ''

# ---------------------------------------------------------------------------
# D 组：源素材未被改动（only-target 原则）
# ---------------------------------------------------------------------------
Write-Host '################ 验收 D：源素材未被改动 ################'
foreach ($p in @(
        @{ n = '_integration\整合复刻执行方案_主方案.md'; f = 'E:\ios漏洞\_integration\整合复刻执行方案_主方案.md' },
        @{ n = 'recon\最终报告.md'; f = 'E:\ios漏洞\recon\最终报告.md' })) {
    if (Test-Path $p.f) {
        $sc = @(Select-String -Path $p.f -Pattern '58684001' -SimpleMatch).Count
        Write-Host ("D) 源 {0} 仍含明文: {1} 处（>0 证明源未动）" -f $p.n, $sc)
    }
}
Write-Host ''

# ---------------------------------------------------------------------------
Write-Host ('=' * 78)
if ($defectHits.Count -gt 0 -or $bad -gt 0) {
    Write-Host ("X 脱敏验收失败：缺陷命中 {0} 行 / SQL {1} 处" -f $defectHits.Count, $bad) -ForegroundColor Red
    exit 2
}
Write-Host "OK 脱敏验收通过" -ForegroundColor Green
