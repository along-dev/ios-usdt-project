# 重启全部服务（★ 在【同一进程内】先清代理变量，再 Start-Process）
# 根因：NO_PROXY / no_proxy 字典键冲突（PowerShell 环境变量大小写不敏感）

$ErrorActionPreference = 'Continue'

# ★ 关键：在同一进程内清掉代理变量（大小写变体都要清）
foreach ($n in @('no_proxy','NO_PROXY','http_proxy','HTTP_PROXY',
                 'https_proxy','HTTPS_PROXY','all_proxy','ALL_PROXY',
                 'ftp_proxy','FTP_PROXY')) {
    Remove-Item "Env:$n" -ErrorAction SilentlyContinue
}

if (-not (Test-Path 'X:\')) { subst X: 'E:\ios漏洞'; Start-Sleep -Seconds 2 }

$X = 'X:\_integration\_fix_work'
$WS = "$X\_i1c3_ws"

function Start-Svc($name, $exe, $args, $workdir) {
    Write-Output "--- 启动 $name ---"
    try {
        Start-Process -FilePath $exe -ArgumentList $args -WorkingDirectory $workdir `
            -WindowStyle Hidden `
            -RedirectStandardOutput "$X\_svc_$name.out" `
            -RedirectStandardError  "$X\_svc_$name.err"
        Write-Output "  Start-Process 已发出"
    } catch {
        Write-Output "  !! 失败: $($_.Exception.Message)"
    }
}

# 1) MariaDB
Start-Svc 'mariadb' "$X\_toolchain\mariadb-11.4.4-winx64\bin\mysqld.exe" `
    @("--datadir=$WS\mariadb-data", "--port=13306", "--skip-ssl") "$X\_toolchain\mariadb-11.4.4-winx64\bin"

# 2) Redis
$redisExe = "$X\_toolchain\redis\redis-server.exe"
if (-not (Test-Path $redisExe)) { $redisExe = "$X\_toolchain\redis\redis-server" }
Start-Svc 'redis' $redisExe @("--port", "16379", "--dir", "$WS\redis-data") $WS

# 3) MongoDB
Start-Svc 'mongo' "$X\_toolchain\mongodb\bin\mongod.exe" `
    @("--dbpath", "$WS\mongo-data", "--port", "27018") $WS

Start-Sleep -Seconds 20

# 4) Go 8888
Start-Svc 'go' "$X\_i2c1_server.exe" @() (Split-Path "$X\_i2c1_server.exe")

# 5) Node 3000
Start-Svc 'node' "E:\CTF\runtime\node\node.exe" `
    @("--env-file-if-exists=$WS\.env", "src_restored/app.js") "E:\USDT项目\02-backend-node"

Start-Sleep -Seconds 22

Write-Output ""
Write-Output "=== 最终状态 ==="
foreach ($p in @(13306, 16379, 27018, 8888, 3000)) {
    $c = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    Write-Output "  $p : $(if ($c) { 'LISTEN' } else { 'DOWN' })"
}
