# restore_all_services.ps1 —— 恢复全部服务（幂等）
# ★ 用途：一次性把 6 个服务起回（MariaDB/Redis/Mongo/Go/Node/代理）
$X = 'X:\_integration\_fix_work'
$TC = "$X\_toolchain"

function Test-Port($p) { [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) }

# ---- MariaDB 13306 ----
if (-not (Test-Port 13306)) {
    Start-Process -FilePath "$TC\mariadb-11.4.4-winx64\bin\mysqld.exe" `
      -ArgumentList @("--datadir=$X\_mysqldata","--port=13306","--bind-address=127.0.0.1","--skip-grant-tables") `
      -WorkingDirectory "$TC\mariadb-11.4.4-winx64\bin" -WindowStyle Hidden
    Start-Sleep -Seconds 16
}
Write-Host "  13306 : $(if (Test-Port 13306) {'OK'} else {'DOWN'})"

# ---- Redis 16379 ----
if (-not (Test-Port 16379)) {
    Start-Process -FilePath "$TC\redis\redis-server.exe" -ArgumentList @("$X\_redis.conf") `
      -WorkingDirectory "$TC\redis" -WindowStyle Hidden
    Start-Sleep -Seconds 6
}
Write-Host "  16379 : $(if (Test-Port 16379) {'OK'} else {'DOWN'})"

# ---- MongoDB 27018 ----
if (-not (Test-Port 27018)) {
    Start-Process -FilePath "$TC\mongodb\mongodb-win32-x86_64-windows-6.0.14\bin\mongod.exe" `
      -ArgumentList @("--dbpath=$X\_i1c3_mongodata","--port","27018","--bind_ip","127.0.0.1") -WindowStyle Hidden
    Start-Sleep -Seconds 16
}
Write-Host "  27018 : $(if (Test-Port 27018) {'OK'} else {'DOWN'})"

# ---- Go 8888 ----
if (-not (Test-Port 8888)) {
    Start-Process -FilePath "$X\_i2c1_server.exe" -WorkingDirectory "$X\_i2c1_ws" -WindowStyle Hidden
    Start-Sleep -Seconds 20
}
Write-Host "  8888  : $(if (Test-Port 8888) {'OK'} else {'DOWN'})"

# ---- Node 3000 ----
if (-not (Test-Port 3000)) {
    $cmd = 'set "PATH=E:\CTF\runtime\node;%PATH%" && cd /d "E:\USDT项目\02-backend-node" && "E:\CTF\runtime\node\node.exe" "--env-file-if-exists=' + $X + '\_i1c3_ws\.env" "src_restored/app.js"'
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $cmd) -WindowStyle Hidden
    Start-Sleep -Seconds 32
}
Write-Host "  3000  : $(if (Test-Port 3000) {'OK'} else {'DOWN'})"

# ---- 代理 8080 ----
if (-not (Test-Port 8080)) {
    $cmd2 = 'set "PATH=E:\CTF\runtime\node;%PATH%" && "E:\CTF\runtime\node\node.exe" "' + $X + '\_gva_proxy.cjs" 8080 "E:\USDT项目\03-web-admin\dist" "http://127.0.0.1:8888" "http://127.0.0.1:3000"'
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $cmd2) -WindowStyle Hidden
    Start-Sleep -Seconds 8
}
Write-Host "  8080  : $(if (Test-Port 8080) {'OK'} else {'DOWN'})"