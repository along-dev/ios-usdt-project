# 诊断 3：在 _fix_work 目录下按卡的命令逐字复现
Set-Location 'X:\_integration\_fix_work'
$env:PYTHONIOENCODING = 'utf-8'
Write-Output ("PYTHONIOENCODING=" + $env:PYTHONIOENCODING)
python verify_w1c1b_injection.py > _w1c1b_g_base.txt 2>&1
Write-Output "JUDGE_EXIT=$LASTEXITCODE"
Write-Output '--- file ---'
Get-Content _w1c1b_g_base.txt -Encoding UTF8
