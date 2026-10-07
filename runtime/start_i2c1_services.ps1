# 启动 I2-C1/I1-C3 所需的全部本地服务（幂等：已在监听的跳过）
#
# ★ 用法（本机【没有 pwsh】，只有 Windows PowerShell 5.1）：
#     powershell -ExecutionPolicy Bypass -File "E:\ios漏洞\_integration\_fix_work\start_i2c1_services.ps1"
#
# ★ 若 Start-Process 报 "Item has already been added. Key in dictionary"：
#     本会话注入了大小写重复的代理变量，先执行：
#       Remove-Item Env:no_proxy,Env:http_proxy,Env:https_proxy,Env:all_proxy,Env:ftp_proxy -ErrorAction SilentlyContinue
#
# ★ 本文件必须带 UTF-8 BOM（P-6：PS 5.1 把无 BOM 的 UTF-8 当 ANSI 读）
#
# ============================================================================
# 判据运行方式备忘（★ 有三类，跑错目录会失败）
# ============================================================================
# [1] 在 _fix_work 目录跑（多数）：
#       $env:PATH = "E:\CTF\runtime\node;" + $env:PATH   # node 不在 PATH（P-7）
#       cd "E:\ios漏洞\_integration\_fix_work"
#       python verify_*.py ; node verify_*.mjs
#
# [2] ★ 必须在 02-backend-node 目录内跑（因需解析该目录的 node_modules）：
#       verify_f1c10_bridge_e2e.mjs   (import collect-bridge.js)
#       verify_f1c5_runtime.mjs       (import fastify + landing.js)
#       verify_i1c2_runtime.mjs       (import chain-router.js)
#     做法：Copy-Item 到 02-backend-node 后 node 运行，再删除。
#
# [3] 需环境变量（F1-C10）：
#       $env:QIANKE_API_BASE="http://127.0.0.1:8888"
#       $env:QIANKE_SERVICE_TOKEN="i2c1-e2e-token"   # 须与 Go config 的 app-jwt.service-token 一致
# ============================================================================
$ErrorActionPreference = 'Continue'

# ★★ 根治中文路径编码事故（2026-09-29 实测）：
#    本机 WMI/Win32 API 与外部 exe 交互时，'E:\ios漏洞' 会被错误解码为
#    'E:\ios婕忔礊' ⇒ mysqld 报 "Can't change dir to ..."（Errcode 2）而启动失败，
#    进而 Go 连不上 DB ⇒ global.GVA_DB 为 nil ⇒ LoadRpcList panic。
#    解法：用 subst 把中文路径映射为纯 ASCII 盘符 X:，所有服务一律走 X:。
if (-not (Test-Path 'X:\_integration\_fix_work')) {
    subst X: 'E:\ios漏洞' 2>&1 | Out-Null
    Start-Sleep -Seconds 2
}

$TC = 'X:\_integration\_fix_work\_toolchain'
$FW = 'X:\_integration\_fix_work'

function Test-Port($p) {
    $c = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    return [bool]$c
}

# ★★ 根治：清理大小写重复的代理环境变量。
#    本机环境同时注入了 NO_PROXY/no_proxy、HTTP_PROXY/http_proxy 等，
#    PowerShell 的 Env: 驱动大小写不敏感 ⇒ Start-Process 抛
#      "Item has already been added. Key in dictionary: 'no_proxy'"
#    ⇒ 必须在【本脚本进程内】清理（外部 Remove-Item 不会传入独立 powershell 进程）。
foreach ($n in @('no_proxy','http_proxy','https_proxy','all_proxy','ftp_proxy','NO_PROXY_lc')) {
    Remove-Item "Env:$n" -ErrorAction SilentlyContinue
}

function Start-Bg($name, $exe, $args, $workdir) {
    # ★ 空参数数组须显式处理（否则 Start-Process 报 ArgumentList 不能为 null）
    if ($null -eq $args -or $args.Count -eq 0) {
        Start-Process -FilePath $exe -WorkingDirectory $workdir -WindowStyle Hidden `
            -RedirectStandardOutput "$FW\_svc_$name.out" -RedirectStandardError "$FW\_svc_$name.err"
    } else {
        Start-Process -FilePath $exe -ArgumentList $args -WorkingDirectory $workdir -WindowStyle Hidden `
            -RedirectStandardOutput "$FW\_svc_$name.out" -RedirectStandardError "$FW\_svc_$name.err"
    }
}

Write-Host '=== 服务启动（幂等） ==='

# 1) MariaDB 13306
if (Test-Port 13306) { Write-Host '  MariaDB 13306 已在监听' }
else {
    $bin = "$TC\mariadb-11.4.4-winx64\bin"
    # ★★ 根因修正（2026-09-29）：--datadir 的值【不得】再包引号。
    #    X: 路径无空格，无需引号；包引号会让 Start-Process 的 ArgumentList
    #    拆参出错 ⇒ mysqld 收不到 --datadir ⇒ 回退到 basedir\data ⇒
    #    "Can't change dir to ...\data\ (Errcode: 2)" ⇒ Aborting。
    Start-Bg 'mariadb' "$bin\mysqld.exe" @(
        "--datadir=$FW\_mysqldata", '--port=13306', '--bind-address=127.0.0.1', '--skip-grant-tables'
    ) $bin
    Write-Host '  MariaDB 13306 启动命令已发出'
}

# 2) Redis 16379
if (Test-Port 16379) { Write-Host '  Redis 16379 已在监听' }
else {
    # ★ 同上：配置文件路径不加引号
    Start-Bg 'redis' "$TC\redis\redis-server.exe" @("$FW\_redis.conf") "$TC\redis"
    Write-Host '  Redis 16379 启动命令已发出'
}

# 3) MongoDB 27018
if (Test-Port 27018) { Write-Host '  MongoDB 27018 已在监听' }
else {
    $mbin = "$TC\mongodb\mongodb-win32-x86_64-windows-6.0.14\bin"
    Start-Bg 'mongo' "$mbin\mongod.exe" @(
        "--dbpath=`"$FW\_i1c3_mongodata`"", '--port', '27018', '--bind_ip', '127.0.0.1'
    ) $mbin
    Write-Host '  MongoDB 27018 启动命令已发出'
}

# 4) Go 8888
if (Test-Port 8888) { Write-Host '  Go 8888 已在监听' }
else {
    Start-Bg 'go' "$FW\_i2c1_server.exe" @() "$FW\_i2c1_ws"
    Write-Host '  Go 8888 启动命令已发出'
}

Start-Sleep -Seconds 12

# 5) Node 3000（依赖前四个）
if (Test-Port 3000) { Write-Host '  Node 3000 已在监听' }
else {
    $env:PATH = 'E:\CTF\runtime\node;' + $env:PATH
    # ★ 同上：--env-file 路径【不得】包引号（X: 路径无空格）
    Start-Bg 'node' 'E:\CTF\runtime\node\node.exe' @(
        "--env-file-if-exists=$FW\_i1c3_ws\.env", 'src_restored/app.js'
    ) 'E:\USDT项目\02-backend-node'
    Write-Host '  Node 3000 启动命令已发出'
}

# ★★ 修正（2026-09-30）：改为【轮询端口 + 如实报告】，
#    不再在发出命令后立刻打印"已启动"（那是乐观输出，曾多次误导 Agent）。
Write-Host ''
Write-Host '=== 等待服务就绪（最多 90s，轮询端口）==='
$want = @(13306, 16379, 27018, 8888, 3000)
$deadline = (Get-Date).AddSeconds(90)
while ((Get-Date) -lt $deadline) {
    $down = @($want | Where-Object { -not (Test-Port $_) })
    if ($down.Count -eq 0) { break }
    Start-Sleep -Seconds 3
}

Write-Host ''
Write-Host '=== 最终状态（端口实测，非乐观输出）==='
$allOk = $true
foreach ($p in $want) {
    $ok = Test-Port $p
    if (-not $ok) { $allOk = $false }
    Write-Host ("  {0} : {1}" -f $p, $(if ($ok) { 'OK' } else { 'DOWN  <- 未就绪，请查 _svc_*.err' }))
}
if (-not $allOk) {
    Write-Host ''
    Write-Host '★ 有服务未就绪。各服务 stderr 末尾：'
    foreach ($n in @('mariadb', 'redis', 'mongo', 'go', 'node')) {
        $f = "$FW\_svc_$n.err"
        if (Test-Path $f) {
            $sz = (Get-Item $f).Length
            if ($sz -gt 0) {
                Write-Host "  --- $n.err (末 3 行) ---"
                Get-Content $f -Tail 3 | ForEach-Object { Write-Host "      $_" }
            }
        }
    }
    exit 1
}
Write-Host ''
Write-Host '全部服务就绪。'
exit 0
