fp = IOS_ROOT + r'\_integration\start_env.ps1'
s = open(fp, encoding='utf-8-sig').read()

old = '''    if (-not $res -or $res.ReturnValue -ne 0) {
        # 回退到 Start-Process（仅限交互式会话，进程随会话结束而终止）
        Write-Host "  ! WMI 启动失败，回退 Start-Process（注意：进程随本会话结束而终止）" -ForegroundColor Yellow
        if ([string]::IsNullOrWhiteSpace($argStr)) {
            Start-Process -FilePath $exe -WindowStyle Hidden
        } else {
            Start-Process -FilePath $exe -ArgumentList $argStr -WindowStyle Hidden
        }
    }'''

new = '''    if (-not $res -or $res.ReturnValue -ne 0) {
        # 回退到 Start-Process
        # ⚠ 已知限制：本脚本若在【受限沙箱】中运行，Start-Process 创建的子进程
        #   会随本 pwsh 进程退出而终止，表现为"端口探测 UP 但随后连不上"。
        #   正常交互式 PowerShell 会话中不会有此问题。
        Write-Host "  ! WMI 不可用（受限环境），回退 Start-Process" -ForegroundColor Yellow
        Write-Host "    若本脚本在沙箱/非交互环境中运行，启动的服务会在脚本结束时终止；" -ForegroundColor Yellow
        Write-Host "    请在正常 PowerShell 窗口中运行本脚本，或用后台作业方式托管。" -ForegroundColor Yellow
        if ([string]::IsNullOrWhiteSpace($argStr)) {
            Start-Process -FilePath $exe -WindowStyle Hidden
        } else {
            Start-Process -FilePath $exe -ArgumentList $argStr -WindowStyle Hidden
        }
    }'''

assert old in s, '未找到回退块'
s = s.replace(old, new, 1)

# 增加启动后【真实连通性】校验（不只是端口探测）
old2 = '''Log "`n=== 状态 ===" 'Cyan'
foreach ($p in @(13306, 16379, 27018)) {
    $t = Test-NetConnection 127.0.0.1 -Port $p -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    Log ("  {0,-6} -> {1}" -f $p, $(if ($t.TcpTestSucceeded) { 'UP' } else { 'DOWN' })) $(if ($t.TcpTestSucceeded) { 'Green' } else { 'Red' })
}'''

new2 = '''Log "`n=== 状态（含真实连通性复核）===" 'Cyan'
# ★ 仅探测端口会误判：进程可能在探测后即被回收。
#   故此处做两轮探测，间隔 3 秒，确认服务确实【持续】存活。
function Test-SvcAlive($port, $name) {
    $t1 = (Test-NetConnection 127.0.0.1 -Port $port -WarningAction SilentlyContinue -ErrorAction SilentlyContinue).TcpTestSucceeded
    Start-Sleep -Seconds 3
    $t2 = (Test-NetConnection 127.0.0.1 -Port $port -WarningAction SilentlyContinue -ErrorAction SilentlyContinue).TcpTestSucceeded
    if ($t1 -and $t2) {
        Log ("  {0,-10} :{1} -> UP（两轮探测均通过）" -f $name, $port) 'Green'
        return $true
    } elseif ($t1 -and -not $t2) {
        Log ("  {0,-10} :{1} -> 不稳定（首轮 UP 次轮 DOWN，多为沙箱回收子进程）" -f $name, $port) 'Yellow'
        return $false
    } else {
        Log ("  {0,-10} :{1} -> DOWN" -f $name, $port) 'Red'
        return $false
    }
}
$alive = 0
if (Test-SvcAlive 13306 'MariaDB') { $alive++ }
if (Test-SvcAlive 16379 'Redis')   { $alive++ }
if (Test-SvcAlive 27018 'MongoDB') { $alive++ }
Log ("  存活: {0}/3" -f $alive) $(if ($alive -eq 3) { 'Green' } else { 'Yellow' })'''

assert old2 in s, '未找到状态块'
s = s.replace(old2, new2, 1)

open(fp, 'w', encoding='utf-8', newline='').write(s)
print('已加入：受限环境告警 + 两轮连通性复核')

import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")