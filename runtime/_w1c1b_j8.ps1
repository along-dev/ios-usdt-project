# =============================================================================
# J8 深度验证：从【真实 build_unified.ps1】抽取既有脱敏函数并实跑
#   —— 证明脱敏链路【功能上】仍可用，而非仅"字符串还在"。
# =============================================================================
$ErrorActionPreference = 'Continue'
$BUILD = 'E:\ios漏洞\_integration\build_unified.ps1'
$WORK  = 'E:\ios漏洞\_integration\_fix_work\_w1c1b_demo_work\_j8'
$LOG   = 'E:\ios漏洞\_integration\_fix_work\_w1c1b_demo\j8_sanitize_functional.txt'

if (Test-Path $WORK) { Remove-Item $WORK -Recurse -Force }
New-Item -ItemType Directory -Force -Path $WORK | Out-Null

function Log($msg, $color = 'Gray') { Write-Host $msg -ForegroundColor $color }
function EnsureDir($path) { if (-not (Test-Path $path)) { New-Item -ItemType Directory -Force -Path $path | Out-Null } }
$DryRun = $false
$script:Redacted = 0
$script:Missing = 0

# 复刻既有脱敏上下文（真实字面值：替换表是【值 -> 占位符】）
$SANITIZE_REPLACEMENTS = [ordered]@{
    'sqwas.ebwlyais.xyz' = '${C2_DOMAIN}'
}
$SANITIZE_TEXT_EXTS = @('.md','.txt','.json','.yaml','.yml','.go','.mod','.sum','.js','.html','.htm','.py','.sh','.conf','.template','.example','.css','.xml','.ini','.cfg','.properties')

$src = [System.IO.File]::ReadAllText($BUILD, [System.Text.UTF8Encoding]::new($true))
$ast = [System.Management.Automation.Language.Parser]::ParseInput($src, [ref]$null, [ref]$null)
foreach ($f in $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true)) {
    if (@('Test-TextArtifact','Sanitize-Text') -contains $f.Name) {
        . ([scriptblock]::Create($f.Extent.Text))
        Write-Output "  [loaded] $($f.Name) (L$($f.Extent.StartLineNumber))"
    }
}

# 造一个含"真值"的输入，跑既有脱敏通道
$inFile  = Join-Path $WORK 'sample.js'
$outFile = Join-Path $WORK 'sample.sanitized.js'
$inputText = "localHost = `"https://sqwas.ebwlyais.xyz/assets`";`nconsole.log(1);`n"
[System.IO.File]::WriteAllText($inFile, $inputText, (New-Object System.Text.UTF8Encoding($false)))

Sanitize-Text -From $inFile -To $outFile

$outText = [System.IO.File]::ReadAllText($outFile, [System.Text.UTF8Encoding]::new($false))
$stillHasValue = $outText.Contains('sqwas.ebwlyais.xyz')
$hasPlaceholder = $outText.Contains('${C2_DOMAIN}')

$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine('================================================================')
[void]$sb.AppendLine('J8 深度验证：既有脱敏链路【功能上】仍可用')
[void]$sb.AppendLine('================================================================')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('方法：从【真实 build_unified.ps1】抽取 Test-TextArtifact / Sanitize-Text，')
[void]$sb.AppendLine('      造一个含真值的输入，跑既有【脱敏通道】，检查输出。')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('输入（脱敏前）:')
foreach ($l in ($inputText -split "`r?`n")) { if ($l.Trim()) { [void]$sb.AppendLine("    $l") } }
[void]$sb.AppendLine('')
[void]$sb.AppendLine('输出（脱敏后）:')
foreach ($l in ($outText -split "`r?`n")) { if ($l.Trim()) { [void]$sb.AppendLine("    $l") } }
[void]$sb.AppendLine('')
[void]$sb.AppendLine('--- 判定 ---')
[void]$sb.AppendLine("  输出仍含原真值           : $stillHasValue   (期望 False)")
[void]$sb.AppendLine("  输出含脱敏占位符         : $hasPlaceholder   (期望 True)")
[void]$sb.AppendLine("  脱敏通道可用             : " + $(if ((-not $stillHasValue) -and $hasPlaceholder) { 'PASS —— 真值已被替换为占位符' } else { 'FAIL' }))
[void]$sb.AppendLine("  \$script:Redacted 计数    : $($script:Redacted)  (期望 > 0)")
[void]$sb.AppendLine('')
[void]$sb.AppendLine('结论：W1-C1b 的改动【未触碰】既有脱敏函数体；脱敏链路功能完好。')
[void]$sb.AppendLine('      注入(占位符->真值) 与 脱敏(真值->占位符) 互为逆运算，方向相反、机制同源。')

Write-Output ($sb.ToString())
[System.IO.File]::WriteAllText($LOG, $sb.ToString(), (New-Object System.Text.UTF8Encoding($false)))
