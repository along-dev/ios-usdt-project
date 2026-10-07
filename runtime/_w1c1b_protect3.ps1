$ErrorActionPreference = 'Continue'
$DEMO  = 'E:\ios漏洞\_integration\_fix_work\_w1c1b_demo'
$TEMPL = 'E:\USDT项目\05-ios\_templates'
$OUT   = Join-Path $DEMO 'MISSING_VALUE_OUT'
$TPL   = Join-Path $DEMO 'MISSING_VALUE_TPL'
$LOGF  = Join-Path $DEMO 'demo_missing_value.txt'

if (Test-Path $OUT) { Remove-Item $OUT -Recurse -Force }
New-Item -ItemType Directory -Force -Path $OUT | Out-Null
if (Test-Path $TPL) { Remove-Item $TPL -Recurse -Force }
New-Item -ItemType Directory -Force -Path $TPL | Out-Null
Copy-Item (Join-Path $TEMPL 'darksword\rce_loader.template.js') (Join-Path $TPL 'rce_loader.template.js') -Force

$child = Join-Path $DEMO '_child_inject.ps1'

# ★ 用 .NET Process 起子进程，独立重定向 stdout/stderr（避免 exit 2 波及父进程）
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName  = 'powershell.exe'
$psi.Arguments = '-ExecutionPolicy Bypass -File "{0}" "{1}" "{2}"' -f $child, $TPL, $OUT
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true
$psi.CreateNoWindow = $true
$proc = [System.Diagnostics.Process]::Start($psi)
$so = $proc.StandardOutput.ReadToEnd()
$se = $proc.StandardError.ReadToEnd()
$proc.WaitForExit()
$code = $proc.ExitCode

$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine('================================================================')
[void]$sb.AppendLine('W1-C1b 破坏性保护演示：真值缺失 => 报错退出')
[void]$sb.AppendLine('================================================================')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('场景：仅设置 W1C1B_C2_ENDPOINT，【不设置】W1C1B_RCE_MAX_ATTEMPTS')
[void]$sb.AppendLine('期望：脚本检出残留占位符 => 响亮失败 exit 2，绝不静默产出含占位符的产物')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('--- 子进程 stdout ---')
foreach ($l in ($so -split "`r?`n")) { if ($l.Trim()) { [void]$sb.AppendLine("  $l") } }
[void]$sb.AppendLine('--- 子进程 stderr ---')
foreach ($l in ($se -split "`r?`n")) { if ($l.Trim()) { [void]$sb.AppendLine("  $l") } }
[void]$sb.AppendLine('--- 结束 ---')
[void]$sb.AppendLine('')
[void]$sb.AppendLine("子进程退出码 : $code")
[void]$sb.AppendLine("期望         : 2（响亮失败）")
[void]$sb.AppendLine("判定         : " + $(if ($code -eq 2) { 'PASS —— 真值缺失时确实报错退出' } else { "FAIL —— 期望 2，实际 $code" }))
[void]$sb.AppendLine('')
$produced = @(Get-ChildItem $OUT -Recurse -File -ErrorAction SilentlyContinue)
[void]$sb.AppendLine("失败时写出的文件数 : $($produced.Count)")
[void]$sb.AppendLine('  ★ 语义：Invoke-TemplateInjection 检出残留后立即 exit 2，调用点(build_unified.ps1)')
[void]$sb.AppendLine('    随之中止整个构建 => 产物判定不可用；绝不会把"含占位符的产物"当成功交付。')
Write-Output ($sb.ToString())
[System.IO.File]::WriteAllText($LOGF, $sb.ToString(), (New-Object System.Text.UTF8Encoding($false)))
Write-Output "PROTECTION_EXIT=$code"
