# W1-C1b 判据运行器（红/绿两态通用）
$env:PYTHONIOENCODING = 'utf-8'
if (-not (Test-Path 'X:\_integration')) { subst X: 'E:\ios漏洞' }
Set-Location 'X:\_integration\_fix_work'
$out = $args[0]
if (-not $out) { $out = '_w1c1b_g.txt' }
python verify_w1c1b_injection.py > $out 2>&1
Write-Output "JUDGE_EXIT=$LASTEXITCODE"
Get-Content $out
