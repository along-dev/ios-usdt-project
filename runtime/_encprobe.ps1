# 诊断：PYTHONIOENCODING=utf-8 重定向下，检查符 U+2713 是否可编码
$env:PYTHONIOENCODING = 'utf-8'
python -c "import sys,locale; print('pyio=',sys.stdout.encoding); print('fs=',sys.getfilesystemencoding()); print('pref=',locale.getpreferredencoding(False))"
Write-Output '--- redirect test ---'
python -c "print('check=\u2713 ok')" > _enc_probe.txt 2>&1
Write-Output "exit=$LASTEXITCODE"
Get-Content _enc_probe.txt
Write-Output '--- no-redirect test ---'
python -c "print('check=\u2713 ok')"
Write-Output "exit=$LASTEXITCODE"
