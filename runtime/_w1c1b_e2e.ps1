# =============================================================================
# W1-C1b 端到端集成测试：实跑【真实 build_unified.ps1】的 [6/9] 注入链路
#   目的：证明"模板层归集 -> 注入 -> 写出产物"在真实脚本上下文里跑通，
#         而不是只在抽函数的演示里跑通。
# =============================================================================
$ErrorActionPreference = 'Continue'
$BUILD  = 'E:\ios漏洞\_integration\build_unified.ps1'
$TARGET = 'E:\ios漏洞\_integration\_fix_work\_w1c1b_e2e_target'
$LOG    = 'E:\ios漏洞\_integration\_fix_work\_w1c1b_demo\e2e_integration.txt'

if (Test-Path $TARGET) { Remove-Item $TARGET -Recurse -Force }
New-Item -ItemType Directory -Force -Path $TARGET | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $TARGET '05-ios') | Out-Null

function Log($msg, $color = 'Gray') { Write-Host $msg -ForegroundColor $color }
function EnsureDir($path) { if (-not (Test-Path $path)) { New-Item -ItemType Directory -Force -Path $path | Out-Null } }
$DryRun = $false
$script:Copied = 0; $script:Skipped = 0; $script:Redacted = 0; $script:Missing = 0
$script:Hashes = New-Object System.Collections.Generic.List[string]

$EXCLUDE_DIRS = @('node_modules','.idea','.git','__pycache__','_sdk','hashcat','john','_pylibs')
$EXCLUDE_FILES = @('server','ios17.cc.cert','ios17.cc.key','redis.rdb','mongo.archive','.DS_Store')
$SANITIZE_TEXT_EXTS = @('.md','.txt','.json','.yaml','.yml','.go','.mod','.sum','.js','.html','.htm','.py','.sh','.conf','.template','.example','.css','.xml','.ini','.cfg','.properties')
$TEMPLATE_ROOT_NAME = '_templates'
$INJECT_ENV_BY_PLACEHOLDER = [ordered]@{
    '__C2_ENDPOINT__'      = 'W1C1B_C2_ENDPOINT'
    '__RCE_MAX_ATTEMPTS__' = 'W1C1B_RCE_MAX_ATTEMPTS'
}
$INJECT_KNOWN_PLACEHOLDERS = @('__C2_ENDPOINT__','__RCE_MAX_ATTEMPTS__')
$SRC_USDT = 'E:\USDT项目'

# ★ 从真实脚本抽取全部相关函数（含 Copy-Tree，走真实归集逻辑）
$src = [System.IO.File]::ReadAllText($BUILD, [System.Text.UTF8Encoding]::new($true))
$ast = [System.Management.Automation.Language.Parser]::ParseInput($src, [ref]$null, [ref]$null)
$want = @('Log','EnsureDir','Copy-Tree','Test-TextArtifact','Sanitize-Text','Get-InjectValues','Invoke-TemplateInjection')
$loaded = @()
foreach ($f in $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true)) {
    if ($want -contains $f.Name) {
        . ([scriptblock]::Create($f.Extent.Text))
        $loaded += $f.Name
    }
}

# 设真值
$env:W1C1B_C2_ENDPOINT      = 'https://e2e-c2.example.invalid'
$env:W1C1B_RCE_MAX_ATTEMPTS = '5'

$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine('================================================================')
[void]$sb.AppendLine('W1-C1b 端到端集成测试：实跑 build_unified.ps1 的 [6/9] 注入链路')
[void]$sb.AppendLine('================================================================')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('从真实 build_unified.ps1 抽取的函数：' + ($loaded -join ', '))
[void]$sb.AppendLine("真值：W1C1B_C2_ENDPOINT=$($env:W1C1B_C2_ENDPOINT)  W1C1B_RCE_MAX_ATTEMPTS=$($env:W1C1B_RCE_MAX_ATTEMPTS)")
[void]$sb.AppendLine('')

# ---- 复刻 [6/9] 的注入三步 ----
[void]$sb.AppendLine('--- 复刻脚本 [6/9] 步骤 ---')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('① Copy-Tree: 模板层归集 -> 产物树 05-ios\_templates')
Copy-Tree -From (Join-Path $SRC_USDT "05-ios\$TEMPLATE_ROOT_NAME") -To (Join-Path $TARGET "05-ios\$TEMPLATE_ROOT_NAME")
$tplSrc = Join-Path $TARGET "05-ios\$TEMPLATE_ROOT_NAME"
$tplExists = Test-Path $tplSrc
[void]$sb.AppendLine("   模板层已归集: $tplExists  ($tplSrc)")

[void]$sb.AppendLine('')
[void]$sb.AppendLine('② Invoke-TemplateInjection: 注入真值 -> 写出 05-ios\')
Invoke-TemplateInjection -TemplateRoot $tplSrc -OutRoot (Join-Path $TARGET '05-ios')

# ---- 检查产物 ----
$prod = Join-Path $TARGET '05-ios\darksword\rce_loader.js'
[void]$sb.AppendLine('')
[void]$sb.AppendLine('--- 产物检查 ---')
$prodExists = Test-Path $prod
[void]$sb.AppendLine("  产物存在 : $prodExists")
[void]$sb.AppendLine("  路径     : $prod")
if ($prodExists) {
    $sha = (Get-FileHash $prod -Algorithm SHA256).Hash.ToLower()
    [void]$sb.AppendLine("  sha256   : $sha")
    $txt = [System.IO.File]::ReadAllText($prod, [System.Text.UTF8Encoding]::new($false))
    $lo = @()
    foreach ($ph in $INJECT_KNOWN_PLACEHOLDERS) { if ($txt.Contains($ph)) { $lo += $ph } }
    [void]$sb.AppendLine("  残留占位符: " + $(if ($lo.Count -eq 0) { '无' } else { $lo -join ', ' }))
    [void]$sb.AppendLine("  含 C2 真值: " + $txt.Contains('https://e2e-c2.example.invalid'))
    [void]$sb.AppendLine("  含重试真值: " + $txt.Contains('var RCE_MAX_ATTEMPTS = 5;'))
    # 抽查若干行
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('  产物抽查（前 10 行 + 含真值的行）：')
    $lines = $txt -split "`n"
    for ($i = 0; $i -lt [Math]::Min(10, $lines.Count); $i++) {
        [void]$sb.AppendLine("    L" + ($i+1) + ": " + $lines[$i].TrimEnd())
    }
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match 'RCE_MAX_ATTEMPTS = ') {
            [void]$sb.AppendLine("    L" + ($i+1) + ": " + $lines[$i].TrimEnd())
        }
    }
}

# ---- 载荷本体是否被写回 ----
[void]$sb.AppendLine('')
[void]$sb.AppendLine('--- 隔离检查 ---')
[void]$sb.AppendLine("  产物树内载荷目录 05-ios\darksword\ 存在 : " + (Test-Path (Join-Path $TARGET '05-ios\darksword')))
[void]$sb.AppendLine("  注：本 E2E 只跑注入链路，未复制载荷本体（那由 Copy-Tree 的既有步骤负责）")
[void]$sb.AppendLine("  载荷本体是否被本次测试改动 : 见 e2e 后 J1 复核")

# ---- 幂等：再注入一次 ----
[void]$sb.AppendLine('')
[void]$sb.AppendLine('--- 幂等：对同一产物树再注入一次 ---')
if ($prodExists) {
    $before = (Get-FileHash $prod -Algorithm SHA256).Hash.ToLower()
    # 用产物自身作为模板再注入（模拟重复运行构建）
    $tmpTpl = Join-Path $TARGET '_re_inject_tpl'
    EnsureDir $tmpTpl
    Copy-Item $prod (Join-Path $tmpTpl 'rce_loader.template.js') -Force
    Invoke-TemplateInjection -TemplateRoot $tmpTpl -OutRoot $tmpTpl
    $after = (Get-FileHash (Join-Path $tmpTpl 'rce_loader.js') -Algorithm SHA256).Hash.ToLower()
    [void]$sb.AppendLine("  注入前 sha256 : $before")
    [void]$sb.AppendLine("  再注入后 sha256: $after")
    [void]$sb.AppendLine("  幂等成立      : " + ($before -eq $after))
}

Write-Output ($sb.ToString())
[System.IO.File]::WriteAllText($LOG, $sb.ToString(), (New-Object System.Text.UTF8Encoding($false)))
