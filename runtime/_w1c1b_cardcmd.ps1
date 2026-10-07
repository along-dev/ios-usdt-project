# 卡中给出的判据命令（逐字复刻）
$env:PYTHONIOENCODING='utf-8'
if(-not (Test-Path 'X:\_integration')){ subst X: 'E:\ios漏洞' }
cd X:\_integration\_fix_work
python verify_w1c1b_injection.py > _w1c1b_g.txt 2>&1
echo "JUDGE_EXIT=$LASTEXITCODE"
Get-Content _w1c1b_g.txt
