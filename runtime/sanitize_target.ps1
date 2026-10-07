param(
    # 对【已存在的产物】补跑脱敏。
    #
    # 为什么需要这个工具：build_unified.ps1 的脱敏发生在"复制进 Target 的路上"，
    # 因此【构建之后新增或被重新同步的文件】永远不会经过脱敏 ——
    # D4 实测 reports/ 目录即因此漏网（其完整 JWT_SECRET 一直留在产物里）。
    # 本工具用于事后补救与回归，不替代构建期脱敏。
    [Parameter(Mandatory = $true)][string]$Target,
    # 默认只演练，必须显式 -Apply 才写入
    [switch]$Apply,
    # 修改前把原文件复制到此处（默认放到 _fix_work 下，不污染产物）
    [string]$BackupDir = "E:\ios漏洞\_integration\_fix_work\_backup_sanitize",
    [string]$AssetsJson = 'E:\ios漏洞\_secrethunt\assets.json'
)

$ErrorActionPreference = 'Continue'

# ---------------------------------------------------------------------------
# 规则推导（与 build_unified.ps1 / acceptance_final.ps1 同源，独立实现）
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
}

# ★ 载体类【不参与替换】：其载体是二进制载荷/夹具，
#   而 gasleak 的 constants.js 等源码若被替换会导致载荷解密运行时失效（见任务 #1）。
#   它们只在自检里登记，用于把命中从"缺陷"降级为"设计取舍"。
$CARRIER_TYPES = @('ARCHIVE_7Z_PASSWORD', 'BCRYPT_PASSWORD_HASH', 'IMPLANT_JWT',
    'FERNET_ENCRYPTED_WEBHOOK', 'ENV_SECRET_MONGO_URI', 'ENV_SECRET_REDIS_URL',
    'CORUNA_COLLECT_GUARD_PASS')

# ★ W1-C15（2026-09-28）：遗留表【只写一份】—— 改由【产物外】单一登记件提供
#   （legacy_replacement_patterns.json，有序数组 [{"value":…,"placeholder":…} × 8]）；
#   本脚本不再内嵌字面表。★ 该件【绝不复制进产物】。
#   ★ 替换顺序【不由登记件的字面次序决定】：下方 Get-Replacements 里按【长度降序】重排
#     （键长 ≥ 12 先、< 12 后，各自 Sort Length -Descending）—— 长键先替，避免 8 位前缀
#     先截断完整明文。两侧（本脚本与 build_unified.ps1）消费【同一顺序】。
$LEGACY_JSON = Join-Path $PSScriptRoot 'legacy_replacement_patterns.json'
$LEGACY = [ordered]@{}
if (-not (Test-Path $LEGACY_JSON)) {
    Write-Host "  !! 未找到遗留登记件：$LEGACY_JSON —— 遗留替换与遗留自检语料均不可用" -ForegroundColor Red
    if ($Apply) { exit 2 }
} else {
    # ★ W1-C15R4（2026-09-28）：判据由【条数】改为【有效条目数】——
    #   登记件为非数组（如 `{}`）或 value 全空串时，ConvertFrom-Json + foreach 仍会产出
    #   1 个空条目 ⇒ 按【条数】判（Count = 1）会漏 ⇒ 静默 fail-open。
    #   故【只把 value 非空且非全空白 的条目并入替换表】，并在表外【单计有效条目数】。
    $legacyValid = 0
    foreach ($__e in (Get-Content -Path $LEGACY_JSON -Raw -Encoding UTF8 | ConvertFrom-Json)) {
        $__v = [string]$__e.value
        if ([string]::IsNullOrWhiteSpace($__v)) { continue }
        $LEGACY[$__v] = [string]$__e.placeholder
        $legacyValid++
    }
    # ★ W1-C15：登记件【缺失】/【空 `[]`】/【非数组 `{}`】/【value 全空串】⇒ 有效条目数 0
    #   同样【响亮失败】（非演练时）—— 语料为空 ⇒ 绝不静默降覆盖。
    if ($legacyValid -eq 0) {
        Write-Host "  !! 遗留登记件无有效条目（0 条）：$LEGACY_JSON —— 语料为空" -ForegroundColor Red
        if ($Apply) { exit 2 }
    }
}

function Get-Replacements {
    $map = [ordered]@{}
    # 1) 遗留完整明文
    foreach ($k in @($LEGACY.Keys | Where-Object { ([string]$_).Length -ge 12 } | Sort-Object -Property Length -Descending)) { $map[$k] = $LEGACY[$k] }
    # 2) 派生（长键优先）
    if (Test-Path $AssetsJson) {
        $assets = Get-Content -Path $AssetsJson -Raw -Encoding UTF8 | ConvertFrom-Json
        $derived = New-Object System.Collections.Generic.List[object]
        # ★ 载体必须按【值】判定，不能按 type：同一值可能同时挂在载体与非载体
        #   type 下（7z 口令既是 ARCHIVE_7Z_PASSWORD 又作为 GEN_PASSWORD 出现）。
        #   按 type 判会把它替换进 constants.js → 载荷解密运行时失效。
        $carrierVals = New-Object System.Collections.Generic.HashSet[string]
        foreach ($a in $assets) {
            if ($CARRIER_TYPES -notcontains [string]$a.type) { continue }
            foreach ($v in (([string]$a.secret) -split "`n")) {
                $v = $v.Trim()
                if ($v.Length -ge 12) { [void]$carrierVals.Add($v) }
            }
        }

        foreach ($a in $assets) {
            if ($a.category -eq 'false-positive') { continue }
            $ph = $PLACEHOLDER_BY_TYPE[[string]$a.type]
            if (-not $ph) { continue }
            $val = [string]$a.secret
            if ([string]::IsNullOrWhiteSpace($val)) { continue }
            if ($val -match '^[\u2500\u2014\-=_·\s]+$') { continue }
            if ($val -match '^[A-Za-z_][A-Za-z0-9_.]*\($') { continue }
            foreach ($v in ($val -split "`n")) {
                $v = $v.Trim()
                if ($v.Length -ge 12) {
                    if ($carrierVals.Contains($v)) { continue }   # 载体值不参与替换
                    $derived.Add([pscustomobject]@{ P = $v; H = $ph })
                }
            }
        }
        foreach ($d in ($derived | Sort-Object -Property @{ Expression = { $_.P.Length }; Descending = $true })) {
            if (-not $map.Contains($d.P)) { $map[$d.P] = $d.H }
        }
    } else {
        Write-Host "  !! 未找到 $AssetsJson —— 仅使用遗留模式" -ForegroundColor Yellow
    }
    # 3) 遗留短键
    foreach ($k in @($LEGACY.Keys | Where-Object { ([string]$_).Length -lt 12 } | Sort-Object -Property Length -Descending)) { $map[$k] = $LEGACY[$k] }
    return $map
}

# ---------------------------------------------------------------------------
$EXTS = @('.md', '.txt', '.example', '.yaml', '.yml', '.json', '.html', '.js',
          '.py', '.go', '.vue', '.sql', '.sh', '.conf', '.env')

# ★ W1-C15（2026-09-28）：本工具自己的【取值源】落在 .json 扩展名内 ⇒ 必须显式排除，
#   否则对含 _fix_work\ 的目录跑 -Apply 时会【抹掉自己的登记件】（⇒ 静默降覆盖 / fail-open）。
$SKIP_SELF_SOURCES = @('legacy_replacement_patterns.json')

Write-Host ('=' * 78)
Write-Host "对已有产物补跑脱敏"
Write-Host ('=' * 78)
Write-Host "目标  : $Target"
Write-Host "模式  : $(if ($Apply) { 'APPLY（写入）' } else { 'DRY-RUN（仅演练，加 -Apply 才写）' })"
if (-not (Test-Path $Target)) { Write-Host "目标不存在" -ForegroundColor Red; exit 2 }

$map = Get-Replacements
Write-Host "替换项: $($map.Count)"
Write-Host ''

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$bkDir = Join-Path $BackupDir $stamp
$changed = 0; $totalRep = 0; $scanned = 0

foreach ($f in (Get-ChildItem -Path $Target -Recurse -File -ErrorAction SilentlyContinue)) {
    # ★ W1-C15：登记件是【取值源】—— 绝不能被本工具自己抹掉（见 $SKIP_SELF_SOURCES）
    if ($SKIP_SELF_SOURCES -contains $f.Name) { continue }
    if ($EXTS -notcontains $f.Extension.ToLower()) { continue }
    $scanned++
    $text = Get-Content -Path $f.FullName -Raw -Encoding UTF8
    if ($null -eq $text) { continue }
    $orig = $text
    $n = 0
    foreach ($kv in $map.GetEnumerator()) {
        if ($text.Contains($kv.Key)) {
            $c = ([regex]::Matches($text, [regex]::Escape($kv.Key))).Count
            $text = $text.Replace($kv.Key, $kv.Value)
            $n += $c
        }
    }
    if ($n -gt 0) {
        $rel = $f.FullName.Substring($Target.Length).TrimStart('\')
        Write-Host ("  {0,-62} 抹除 {1} 处" -f $rel, $n)
        $changed++; $totalRep += $n
        if ($Apply) {
            $dst = Join-Path $bkDir $rel
            New-Item -ItemType Directory -Force -Path (Split-Path $dst -Parent) | Out-Null
            Copy-Item $f.FullName $dst -Force
            Set-Content -Path $f.FullName -Value $text -Encoding UTF8 -NoNewline
        }
    }
}

Write-Host ''
Write-Host ('=' * 78)
Write-Host "扫描文件: $scanned   命中文件: $changed   合计抹除: $totalRep 处"
if ($Apply -and $changed -gt 0) {
    Write-Host "原文件已备份到: $bkDir" -ForegroundColor Green
    Write-Host "★ 下一步：跑 acceptance_final.ps1 -Target 复检，并对改动的代码文件做语法校验"
} elseif (-not $Apply -and $changed -gt 0) {
    Write-Host "（演练模式，未写入。加 -Apply 执行）" -ForegroundColor Yellow
}
