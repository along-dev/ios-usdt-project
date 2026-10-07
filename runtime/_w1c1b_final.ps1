# =============================================================================
# W1-C1b 收尾：把破坏性保护演示落到交付区 + J1 全量载荷扫描
# =============================================================================
$ErrorActionPreference = 'Continue'
$DEMO  = 'E:\ios漏洞\_integration\_fix_work\_w1c1b_demo'
$TEMPL = 'E:\USDT项目\05-ios\_templates'
$ROOT  = 'E:\USDT项目'
$IOS   = 'E:\ios漏洞'

function Log($msg, $color = 'Gray') { Write-Host $msg -ForegroundColor $color }
function EnsureDir($path) { if (-not (Test-Path $path)) { New-Item -ItemType Directory -Force -Path $path | Out-Null } }

# ---- A. 破坏性保护演示 ----
# ★ 注意：缺失真值时【必定残留占位符】，故该输出必须落在【交付区之外】，
#   否则会污染 J4 对 _w1c1b_demo 树的"无残留占位符"扫描。
$WORK  = 'E:\ios漏洞\_integration\_fix_work\_w1c1b_demo_work'
$pout  = Join-Path $WORK 'MISSING_VALUE_OUT'
$pwork = Join-Path $WORK 'MISSING_VALUE_TPL'
if (Test-Path $pout)  { Remove-Item $pout -Recurse -Force }
if (Test-Path $pwork) { Remove-Item $pwork -Recurse -Force }
EnsureDir $pout
EnsureDir $pwork
Copy-Item (Join-Path $TEMPL 'darksword\rce_loader.template.js') (Join-Path $pwork 'rce_loader.template.js') -Force

$child = Join-Path $WORK '_child_inject.ps1'
$childOut = Join-Path $WORK '_child_out.txt'

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName  = 'powershell.exe'
$psi.Arguments = '-ExecutionPolicy Bypass -File "{0}" "{1}" "{2}"' -f $child, $pwork, $pout
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true
$psi.CreateNoWindow = $true
$psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
$psi.StandardErrorEncoding  = [System.Text.Encoding]::UTF8
$proc = [System.Diagnostics.Process]::Start($psi)
$so = $proc.StandardOutput.ReadToEnd()
$se = $proc.StandardError.ReadToEnd()
$proc.WaitForExit()
$code = $proc.ExitCode

$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine('================================================================')
[void]$sb.AppendLine('W1-C1b 破坏性保护演示：真值缺失 => 报错退出（非静默产出）')
[void]$sb.AppendLine('================================================================')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('场景：仅设置 W1C1B_C2_ENDPOINT；【故意不设置】W1C1B_RCE_MAX_ATTEMPTS')
[void]$sb.AppendLine('期望：脚本检出残留占位符 => 响亮失败 exit 2，绝不静默产出含占位符的产物')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('--- 子进程 stdout（保留原始输出，含乱码为 PS 控制台编码所致）---')
foreach ($l in ($so -split "`r?`n")) { if ($l.Trim()) { [void]$sb.AppendLine("  $l") } }
[void]$sb.AppendLine('--- 子进程 stderr ---')
foreach ($l in ($se -split "`r?`n")) { if ($l.Trim()) { [void]$sb.AppendLine("  $l") } }
[void]$sb.AppendLine('--- 结束 ---')
[void]$sb.AppendLine('')
[void]$sb.AppendLine("子进程退出码 : $code")
[void]$sb.AppendLine("期望         : 2（响亮失败）")
[void]$sb.AppendLine("判定         : " + $(if ($code -eq 2) { 'PASS —— 真值缺失时确实报错退出' } else { "FAIL —— 期望 2，实际 $code" }))
[void]$sb.AppendLine('')
[void]$sb.AppendLine('语义：Invoke-TemplateInjection 检出残留占位符后立即 exit 2，')
[void]$sb.AppendLine('      调用点（build_unified.ps1 [6/9]）随之中止整个构建 => 产物判定不可用。')
[void]$sb.AppendLine('      ★ 绝不把"含占位符的产物"当作成功交付。')
[System.IO.File]::WriteAllText((Join-Path $DEMO 'demo_missing_value.txt'), $sb.ToString(), (New-Object System.Text.UTF8Encoding($false)))
Write-Output "PROTECTION_EXIT=$code"

# ---- B. J1 全量载荷扫描：05-ios 下全部 .js/.dylib 是否与备份/基线一致 ----
Write-Output ''
Write-Output '=== J1 全量载荷扫描（05-ios 下全部 .js / .dylib）==='
$baseList = Join-Path $IOS '_integration\_fix_work\_w1c1b_payload_baseline.txt'
$curList  = Join-Path $IOS '_integration\_fix_work\_w1c1b_payload_current.txt'

$files = Get-ChildItem (Join-Path $ROOT '05-ios') -Recurse -File -Include '*.js','*.dylib' -ErrorAction SilentlyContinue |
         Where-Object { $_.FullName -notlike '*\_templates\*' } | Sort-Object FullName
$lines = foreach ($f in $files) {
    "{0}  {1}" -f (Get-FileHash $f.FullName -Algorithm SHA256).Hash.ToLower(), $f.FullName.Substring($ROOT.Length + 1)
}
[System.IO.File]::WriteAllLines($curList, $lines, (New-Object System.Text.UTF8Encoding($false)))
Write-Output ("载荷文件数（不含 _templates）: " + $files.Count)
Write-Output ("清单: $curList")
