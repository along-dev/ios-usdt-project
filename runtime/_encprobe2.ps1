# 诊断 2：环境变量是否真的到达 python 进程
$env:PYTHONIOENCODING = 'utf-8'
Write-Output ("PS sees PYTHONIOENCODING=" + $env:PYTHONIOENCODING)
python -c @"
import os, sys, locale
print('env PYTHONIOENCODING =', repr(os.environ.get('PYTHONIOENCODING')))
print('env PYTHONUTF8      =', repr(os.environ.get('PYTHONUTF8')))
print('stdout.encoding     =', sys.stdout.encoding)
print('locale preferred    =', locale.getpreferredencoding(False))
"@
Write-Output "exit=$LASTEXITCODE"
