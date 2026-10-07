$env:PYTHONIOENCODING = 'utf-8'
$t = 'E:\ios漏洞\_buildtest'

Write-Output '=== A) 全产物明文扫描（正确的 -Recurse 写法）==='
$files = @(Get-ChildItem -Path $t -Recurse -File -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
Write-Output "扫描文件数: $($files.Count)"

$pats = @(
    '58684001',
    'HCRs35JH',
    'DEFAULT_ADMIN_PASSWORD=admin'
)
$total = 0
foreach ($p in $pats) {
    $hit = @(Select-String -Path $files -Pattern $p -SimpleMatch -ErrorAction SilentlyContinue)
    Write-Output ("  模式 {0,-32} 命中 {1}" -f $p, $hit.Count)
    $total += $hit.Count
    foreach ($h in $hit) { Write-Output "      $($h.Path):$($h.LineNumber)" }
}
Write-Output "A) 明文总命中: $total  (期望 0)"

Write-Output ''
Write-Output '=== B) qianke.sql INSERT 计数 ==='
$sql = Join-Path $t '07-db\schema\qianke.sql'
$c = 0
$m = Select-String -Path $sql -Pattern 'INSERT INTO' -AllMatches -ErrorAction SilentlyContinue
if ($m) { foreach ($x in $m) { $c += $x.Matches.Count } }
Write-Output "B) INSERT INTO 命中: $c  (期望 0)"

Write-Output ''
Write-Output '=== E) 源文件未被改动（只改产物）==='
$srcJwt = @(Select-String -Path 'E:\ios漏洞\_integration\整合复刻方案.md' -Pattern '58684001' -SimpleMatch).Count
Write-Output "源 整合复刻执行方案_主方案.md 仍含明文 JWT: $srcJwt 处（预期 >0，证明源未被改动）"

Write-Output ''
Write-Output '=== F) 被脱敏的产物行确认 ==='
$f = Join-Path $t '09-docs\analysis\android-admin-recovery.md'
foreach ($ln in 113..117) {
    $line = (Get-Content $f -Encoding UTF8)[$ln - 1]
    Write-Output ("  L{0}: {1}" -f $ln, $line)
}
