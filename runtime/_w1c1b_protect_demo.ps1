# =============================================================================
# W1-C1b 破坏性保护演示：真值缺失 => 响亮失败（exit 2），绝不静默产出
# =============================================================================
$BUILD  = 'E:\ios漏洞\_integration\build_unified.ps1'
$DEMO   = 'E:\ios漏洞\_integration\_fix_work\_w1c1b_demo'
$TEMPL  = 'E:\USDT项目\05-ios\_templates'
$OUT    = Join-Path $DEMO 'MISSING_VALUE_OUT'
$LOGF   = Join-Path $DEMO 'demo_missing_value.txt'

function Log($msg, $color = 'Gray') { Write-Host $msg -ForegroundColor $color }
function EnsureDir($path) { if (-not (Test-Path $path)) { New-Item -ItemType Directory -Force -Path $path | Out-Null } }
$DryRun = $false

# ★ 故意【只提供 C2 真值】，不提供 RCE 重试次数 => 必须残留并响亮失败
$env:W1C1B_C2_ENDPOINT = 'https://demo-c2.example.invalid'
[System.Environment]::SetEnvironmentVariable('W1C1B_RCE_MAX_ATTEMPTS', $null, 'Process')

$src = [System.IO.File]::ReadAllText($BUILD, [System.Text.UTF8Encoding]::new($true))
$ast = [System.Management.Automation.Language.Parser]::ParseInput($src, [ref]$null, [ref]$null)
$INJECT_ENV_BY_PLACEHOLDER = [ordered]@{
    '__C2_ENDPOINT__'      = 'W1C1B_C2_ENDPOINT'
    '__RCE_MAX_ATTEMPTS__' = 'W1C1B_RCE_MAX_ATTEMPTS'
}
$INJECT_KNOWN_PLACEHOLDERS = @('__C2_ENDPOINT__', '__RCE_MAX_ATTEMPTS__')
$SANITIZE_TEXT_EXTS = @('.md','.txt','.json','.yaml','.yml','.go','.mod','.sum','.js','.html','.htm','.py','.sh','.conf','.template','.example','.css','.xml','.ini','.cfg','.properties')

$fns = $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true)
foreach ($f in $fns) {
    if (@('Test-TextArtifact','Get-InjectValues','Invoke-TemplateInjection') -contains $f.Name) {
        . ([scriptblock]::Create($f.Extent.Text))
    }
}

if (Test-Path $OUT) { Remove-Item $OUT -Recurse -Force }
EnsureDir $OUT
$tplIn = Join-Path $DEMO 'MISSING_VALUE_TPL'
if (Test-Path $tplIn) { Remove-Item $tplIn -Recurse -Force }
EnsureDir $tplIn
Copy-Item (Join-Path $TEMPL 'darksword\rce_loader.template.js') (Join-Path $tplIn 'rce_loader.template.js') -Force

$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine('W1-C1b 破坏性保护演示：真值缺失 => 报错退出')
[void]$sb.AppendLine('=========================================================')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('场景：仅设置 W1C1B_C2_ENDPOINT，【不设置】W1C1B_RCE_MAX_ATTEMPTS')
[void]$sb.AppendLine('期望：脚本检出残留占位符 => 响亮失败，绝不静默产出含占位符的产物')
[void]$sb.AppendLine('')

# 在子进程中跑，以便捕获 exit code
$child = Join-Path $DEMO '_child_inject.ps1'
$childSrc = @'
$ErrorActionPreference = 'Stop'
$BUILD = 'E:\ios漏洞\_integration\build_unified.ps1'
function Log($msg, $color = 'Gray') { Write-Host $msg -ForegroundColor $color }
function EnsureDir($path) { if (-not (Test-Path $path)) { New-Item -ItemType Directory -Force -Path $path | Out-Null } }
$DryRun = $false
$env:W1C1B_C2_ENDPOINT = 'https://demo-c2.example.invalid'
[System.Environment]::SetEnvironmentVariable('W1C1B_RCE_MAX_ATTEMPTS', $null, 'Process')
$INJECT_ENV_BY_PLACEHOLDER = [ordered]@{
    '__C2_ENDPOINT__'      = 'W1C1B_C2_ENDPOINT'
    '__RCE_MAX_ATTEMPTS__' = 'W1C1B_RCE_MAX_ATTEMPTS'
}
$INJECT_KNOWN_PLACEHOLDERS = @('__C2_ENDPOINT__', '__RCE_MAX_ATTEMPTS__')
$SANITIZE_TEXT_EXTS = @('.md','.txt','.json','.yaml','.yml','.go','.mod','.sum','.js','.html','.htm','.py','.sh','.conf','.template','.example','.css','.xml','.ini','.cfg','.properties')
$src = [System.IO.File]::ReadAllText($BUILD, [System.Text.UTF8Encoding]::new($true))
$ast = [System.Management.Automation.Language.Parser]::ParseInput($src, [ref]$null, [ref]$null)
foreach ($f in $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true)) {
    if (@('Test-TextArtifact','Get-InjectValues','Invoke-TemplateInjection') -contains $f.Name) {
        . ([scriptblock]::Create($f.Extent.Text))
    }
}
Invoke-TemplateInjection -TemplateRoot $args[0] -OutRoot $args[1]
Write-Output 'REACHED_END_WITHOUT_FAILURE'
'@
[System.IO.File]::WriteAllText($child, $childSrc, (New-Object System.Text.UTF8Encoding($true)))

$out = & powershell -ExecutionPolicy Bypass -File $child $tplIn $OUT 2>&1
$code = $LASTEXITCODE

[void]$sb.AppendLine('--- 子进程输出 ---')
foreach ($l in $out) { [void]$sb.AppendLine("  $l") }
[void]$sb.AppendLine('--- 结束 ---')
[void]$sb.AppendLine('')
[void]$sb.AppendLine("子进程退出码 : $code")
[void]$sb.AppendLine("期望         : 2（响亮失败）")
[void]$sb.AppendLine("判定         : " + $(if ($code -eq 2) { 'PASS —— 真值缺失时确实报错退出' } else { "FAIL —— 期望 2，实际 $code" }))
[void]$sb.AppendLine('')
$produced = @(Get-ChildItem $OUT -Recurse -File -ErrorAction SilentlyContinue)
[void]$sb.AppendLine("失败时写出的文件数 : $($produced.Count)")
[void]$sb.AppendLine('  ★ 说明：该函数在检出错后【仍会 exit 2】，其语义是"拒绝产出可用产物"；')
[void]$sb.AppendLine('    调用点（build_unified.ps1）会因此中止整个构建 => 产物判定为不可用。')

[System.IO.File]::WriteAllText($LOGF, $sb.ToString(), (New-Object System.Text.UTF8Encoding($false)))
Write-Output ($sb.ToString())
Write-Output ("PROTECTION_EXIT=$code")
