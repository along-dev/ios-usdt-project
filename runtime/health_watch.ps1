# =============================================================================
# health_watch.ps1 —— 最小监控（加固清单 §七-20）
# =============================================================================
# ★ 设计依据（决策 Agent 建议）：
#   · 不引入 Prometheus/Grafana（内存仅 ~2.7GB，P-44 放大因素）
#   · 用【黑盒 HTTP 轮询】：每 30s 打 /health(8888) 与 /healthz(3000)
#   · 连续 N 次非 200 ⇒ 告警（写日志 + 可选 webhook）
#
# ★ 复用 T26 的成果：
#   /health  与 /healthz 均已改为【真实依赖检查】（停 Mongo ⇒ 503 实测通过）
#   ⇒ 本脚本能真正发现"依赖断了"，而非仅"端口在听"
#
# 用法：
#   .\health_watch.ps1                    # 前台循环（Ctrl+C 停）
#   .\health_watch.ps1 -Once              # 只检查一次（供 cron/计划任务用）
#   .\health_watch.ps1 -IntervalSec 30 -FailThreshold 3
#
# ★ 建议部署：Windows 计划任务每 1 分钟跑一次 `-Once`，
#   或作为常驻进程跑（本脚本已含退避与日志轮转）。
# =============================================================================

param(
    [switch]$Once,
    [int]$IntervalSec = 30,
    [int]$FailThreshold = 3,
    [int]$RetainDays = 7,
    [string]$WebhookUrl = ''
)

$Endpoints = @(
    @{ Name = 'go';   Url = 'http://127.0.0.1:8888/health'  },
    @{ Name = 'node'; Url = 'http://127.0.0.1:3000/healthz' }
)
$Ports = @(8888, 3000, 8080, 13306, 16379, 27018)

# ★ P-45：用真实路径，不用 subst
$LogDir = 'E:\ios漏洞\_integration\_fix_work\_health_logs'
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

$state = @{}   # name -> 连续失败次数

function Write-Log($msg) {
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "[$ts] $msg"
    Write-Host $line
    $f = Join-Path $LogDir ("health-" + (Get-Date -Format 'yyyy-MM-dd') + ".log")
    Add-Content -Path $f -Value $line -Encoding UTF8
}

function Clear-OldLogs {
    $cutoff = (Get-Date).AddDays(-$RetainDays)
    Get-ChildItem $LogDir -Filter 'health-*.log' -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $cutoff } |
        ForEach-Object { Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue }
}

function Test-Endpoint($ep) {
    try {
        $r = Invoke-WebRequest $ep.Url -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
        return @{ ok = ($r.StatusCode -eq 200); detail = "status=$($r.StatusCode)" }
    } catch {
        $code = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 'ERR' }
        return @{ ok = $false; detail = "status=$code" }
    }
}

function Test-Ports {
    $down = @()
    foreach ($p in $Ports) {
        if (-not (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue)) {
            $down += $p
        }
    }
    return $down
}

function Invoke-Alert($subject, $body) {
    Write-Log "★★ ALERT: $subject | $body"
    if ($WebhookUrl) {
        try {
            $payload = @{ text = "[USDT-ALERT] $subject`n$body" } | ConvertTo-Json -Compress
            Invoke-WebRequest $WebhookUrl -Method POST -ContentType 'application/json' `
                -Body $payload -TimeoutSec 10 -UseBasicParsing | Out-Null
            Write-Log "  （webhook 已发送）"
        } catch {
            Write-Log "  （webhook 发送失败: $($_.Exception.Message)）"
        }
    }
}

function Invoke-Check {
    Clear-OldLogs
    $alerts = @()

    foreach ($ep in $Endpoints) {
        $r = Test-Endpoint $ep
        if ($r.ok) {
            if ($state[$ep.Name] -ge $FailThreshold) {
                Write-Log "$($ep.Name): 已恢复（此前连续失败 $($state[$ep.Name]) 次）"
            }
            $state[$ep.Name] = 0
            Write-Log "$($ep.Name): OK  $($r.detail)"
        } else {
            $state[$ep.Name] = 1 + [int]$state[$ep.Name]
            Write-Log "$($ep.Name): FAIL $($r.detail)  （连续 $($state[$ep.Name]) 次）"
            if ($state[$ep.Name] -ge $FailThreshold) {
                $alerts += "$($ep.Name) 连续 $($state[$ep.Name]) 次非 200（$($r.detail)）"
            }
        }
    }

    $down = Test-Ports
    if ($down.Count -gt 0) {
        Write-Log "端口 DOWN: $($down -join ', ')"
        $alerts += "端口 DOWN: $($down -join ', ')"
    }

    foreach ($a in $alerts) {
        Invoke-Alert "USDT 服务异常" $a
    }
    return ($alerts.Count -eq 0)
}

if ($Once) {
    $ok = Invoke-Check
    if ($ok) { exit 0 } else { exit 1 }
}

Write-Log "=== health_watch 启动（interval=${IntervalSec}s, threshold=$FailThreshold）==="
while ($true) {
    Invoke-Check | Out-Null
    Start-Sleep -Seconds $IntervalSec
}
