# =============================================================================
# 服务恢复脚本（T26 合并版）—— 2026-10-02
# =============================================================================
# ★★ 本脚本是【唯一权威】的服务恢复入口（合并了 restore_all_services.ps1）。
#
# 依据（均为实证）：
#   E-05：原两个脚本不一致 ⇒ 合并为一个，覆盖【六端口】。
#   E-06：★ Node(3000) 冷启动实测需 ~135 秒，原脚本只等 25 秒 ⇒ 永远误报 DOWN
#         ⇒ 改为【轮询等待，上限 180 秒】。
#   P-30：Start-Process 会因 NO_PROXY / no_proxy 字典键冲突而失败
#         ⇒ 必须在【同一进程内】先清掉代理变量。
#   P-42：启动 Node 的重定向必须写在 cmd 命令内部
#         （用 PowerShell 的 -RedirectStandardOutput 会静默失败）。
#   E-11：X: 是 subst 映射 ⇒ 必须自举（会话级，重启失效）。
#
# 端口：13306 MariaDB / 16379 Redis / 27018 MongoDB / 8888 Go / 3000 Node / 8080 代理
# =============================================================================

# ---- 0) 清代理变量（P-30）---------------------------------------------------
foreach ($n in @('no_proxy','NO_PROXY','http_proxy','HTTP_PROXY',
                 'https_proxy','HTTPS_PROXY','all_proxy','ALL_PROXY')) {
    Remove-Item "Env:$n" -ErrorAction SilentlyContinue
}

# ---- 1) subst 自举（E-11）★ 已降级为【兼容兜底】----------------------------
#   ★★★ T26 / 收尾（清单项 13，2026-10-02）：本脚本已改为【全 E:\ 真实路径】
#     ⇒ **不再依赖 `X:`**。subst 自举**仅保留**，以防：
#       · 某个外部命令/旧脚本仍引用 `X:`；
#       · 人工在本脚本外做 `X:` 相关操作。
#   ★ 依据 P-45：`subst` 只在【交互会话】有效，Job/cmd 子进程看不到
#     ⇒ **依赖 `X:` 是脆弱设计**，必须以真实路径为主。
$REAL_ROOT = 'E:\ios漏洞'
$REAL_X    = 'E:\ios漏洞\_integration\_fix_work'
if (-not (Test-Path 'X:\')) {
    subst X: $REAL_ROOT
    Start-Sleep -Seconds 2
    Write-Output "[subst] 已建立 X: -> $REAL_ROOT（仅兼容兜底；本脚本主路径用 E:\）"
}

# ★ 主路径一律用真实盘符（P-45）
$X  = $REAL_X
$TC = "$X\_toolchain"
$WS = "$X\_i1c3_ws"

function Is-Up($port) {
    return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

# ★ E-06：轮询等待（上限 180 秒），而非固定 sleep
function Wait-Port($port, $timeoutSec = 180, $label = '') {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Is-Up $port) {
            $elapsed = [int]((Get-Date) - $deadline.AddSeconds($timeoutSec)).TotalSeconds
            Write-Output "  [OK] $port $label LISTEN at t=${elapsed}s"
            return $true
        }
        Start-Sleep -Seconds 5
    }
    Write-Output "  [!!] $port $label 在 ${timeoutSec}s 内未 LISTEN"
    return $false
}

# ---- 2) MariaDB 13306 -------------------------------------------------------
if (-not (Is-Up 13306)) {
    Write-Output "--- MariaDB 13306 ---"
    Start-Process -FilePath "$TC\mariadb-11.4.4-winx64\bin\mysqld.exe" `
        -ArgumentList @("--datadir=$X\_mysqldata", '--port=13306',
                        '--bind-address=127.0.0.1', '--skip-grant-tables') `
        -WorkingDirectory "$TC\mariadb-11.4.4-winx64\bin" -WindowStyle Hidden `
        -RedirectStandardOutput "$X\_svc_my.out" -RedirectStandardError "$X\_svc_my.err"
}
Wait-Port 13306 120 'MariaDB' | Out-Null

# ---- 3) Redis 16379 ---------------------------------------------------------
if (-not (Is-Up 16379)) {
    Write-Output "--- Redis 16379 ---"
    Start-Process -FilePath "$TC\redis\redis-server.exe" `
        -ArgumentList @("$X\_redis.conf") -WorkingDirectory "$TC\redis" `
        -WindowStyle Hidden `
        -RedirectStandardOutput "$X\_svc_rd.out" -RedirectStandardError "$X\_svc_rd.err"
}
Wait-Port 16379 30 'Redis' | Out-Null

# ---- 4) MongoDB 27018 -------------------------------------------------------
if (-not (Is-Up 27018)) {
    Write-Output "--- MongoDB 27018 ---"
    Start-Process -FilePath "$TC\mongodb\mongodb-win32-x86_64-windows-6.0.14\bin\mongod.exe" `
        -ArgumentList @("--dbpath=$X\_i1c3_mongodata", '--port', '27018',
                        '--bind_ip', '127.0.0.1') -WindowStyle Hidden `
        -RedirectStandardOutput "$X\_svc_mg.out" -RedirectStandardError "$X\_svc_mg.err"
}
Wait-Port 27018 120 'MongoDB' | Out-Null

# ---- 5) Go 8888（★ cwd = _i2c1_ws，那里有 config.yaml）----------------------
if (-not (Is-Up 8888)) {
    Write-Output "--- Go 8888 ---"
    Start-Process -FilePath "$X\_i2c1_server.exe" -WorkingDirectory "$X\_i2c1_ws" `
        -WindowStyle Hidden `
        -RedirectStandardOutput "$X\_svc_go.out" -RedirectStandardError "$X\_svc_go.err"
}
Wait-Port 8888 120 'Go' | Out-Null

# ---- 6) Node 3000（★ P-42：重定向写在 cmd 内部；★ E-06：等 180s）-----------
if (-not (Is-Up 3000)) {
    Write-Output "--- Node 3000（冷启动实测需 ~135s，请耐心）---"
    $nodeCmd = 'set "PATH=E:\CTF\runtime\node;%PATH%" && cd /d "E:\USDT项目\02-backend-node" && ' +
               '"E:\CTF\runtime\node\node.exe" "--env-file-if-exists=' + $WS + '\.env" ' +
               '"src_restored/app.js" > "' + $X + '\_svc_node.out" 2>&1'
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $nodeCmd) -WindowStyle Hidden
}
Wait-Port 3000 180 'Node' | Out-Null

# ---- 7) 代理 8080（T19/T22 的跨体系桥接）-----------------------------------
if (-not (Is-Up 8080)) {
    Write-Output "--- 代理 8080 ---"
    $pxCmd = 'set "PATH=E:\CTF\runtime\node;%PATH%" && ' +
             '"E:\CTF\runtime\node\node.exe" "' + $X + '\_gva_proxy.cjs" 8080 ' +
             '"E:\USDT项目\03-web-admin\dist" "http://127.0.0.1:8888" "http://127.0.0.1:3000" ' +
             '> "' + $X + '\_svc_proxy.out" 2>&1'
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $pxCmd) -WindowStyle Hidden
}
Wait-Port 8080 60 'Proxy' | Out-Null

# ---- 8) 终检 -----------------------------------------------------------------
Write-Output ""
Write-Output "=== 六端口终检 ==="
$allOk = $true
foreach ($p in @(13306, 16379, 27018, 8888, 3000, 8080)) {
    $up = Is-Up $p
    if (-not $up) { $allOk = $false }
    Write-Output "  $p : $(if ($up) { 'LISTEN' } else { 'DOWN' })"
}

Write-Output ""
Write-Output "=== 健康检查 ==="
foreach ($u in @('http://127.0.0.1:8888/health', 'http://127.0.0.1:3000/healthz')) {
    try {
        $r = Invoke-WebRequest $u -TimeoutSec 10 -UseBasicParsing
        Write-Output "  $u => $($r.StatusCode)"
    } catch {
        Write-Output "  $u => FAIL"
        $allOk = $false
    }
}

Write-Output ""
Write-Output "RESTORE_RESULT=$(if ($allOk) { 'OK' } else { 'PARTIAL' })"
