# 重启广告线的 3001 验证实例：先杀掉占用 3001 的进程，再用指定的 env 文件起
# 用法: powershell -File _ad_restart_3001.ps1 -EnvFile <env file>
param([Parameter(Mandatory=$true)][string]$EnvFile)
$ErrorActionPreference = 'Stop'
$node = 'E:\CTF\runtime\node\node.exe'
$wd   = 'E:\USDT项目\02-backend-node'

$conn = Get-NetTCPConnection -LocalPort 3001 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    foreach ($pid2 in ($conn.OwningProcess | Select-Object -Unique)) {
        Write-Output "killing pid=$pid2 on 3001"
        Stop-Process -Id $pid2 -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

$p = Start-Process -FilePath $node `
    -ArgumentList @("--env-file-if-exists=$EnvFile", 'src_restored/app.js') `
    -WorkingDirectory $wd -WindowStyle Hidden `
    -RedirectStandardOutput 'X:\_integration\_fix_work\_ad3001.out' `
    -RedirectStandardError  'X:\_integration\_fix_work\_ad3001.err' -PassThru
Write-Output "started pid=$($p.Id) with env=$EnvFile"
