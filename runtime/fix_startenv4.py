fp = IOS_ROOT + r'\_integration\start_env.ps1'
s = open(fp, encoding='utf-8-sig').read()

# 在脚本头部说明中加入"沙箱环境请用后台作业"的指引
old = '''# 停止：直接结束对应进程（见脚本末尾提示）
# ============================================================================='''

new = '''# 停止：直接结束对应进程（见脚本末尾提示）
#
# ⚠ 受限/沙箱环境重要提示
#   WMI（Win32_Process.Create）被拒绝时，本脚本回退 Start-Process，
#   而该方式创建的子进程会【随本 pwsh 进程退出而终止】。
#   表现：脚本内两轮探测显示 UP，但脚本结束后立即连不上。
#   → 在受限环境中，请改用【后台作业】方式托管各服务，例如：
#       Start-Job { & "<mysqld>" --defaults-file=... --port=13306 --console }
#     或由外部进程管理器（nssm / 计划任务 / 容器）托管。
#   在正常交互式 PowerShell 窗口中运行本脚本则不受此限制。
# ============================================================================='''

assert old in s
s = s.replace(old, new, 1)

# 末尾追加【后台作业托管】备用方案
old2 = '''Log "`n=== 停止方式 ===" 'Cyan'
Log "  Get-Process mysqld,redis-server,mongod,_server -ErrorAction SilentlyContinue | Stop-Process" 'Gray'
Log "  或逐个: Stop-Process -Name mysqld" 'Gray\''''

new2 = '''Log "`n=== 若服务不稳定（沙箱环境）===" 'Cyan'
Log "  改用后台作业托管，示例：" 'Yellow'
Log "    Start-Job { & `"$mysqld`" --defaults-file=`"$dataDir\\my.ini`" --port=13306 --console }" 'Gray'
Log "    Start-Job { & `"$(Join-Path $TOOL 'redis\\redis-server.exe')`" `"$(Join-Path $FIX '_redis.conf')`" }" 'Gray'
Log "    Get-Job | Receive-Job   # 查看输出；Stop-Job / Remove-Job 停止" 'Gray'

Log "`n=== 停止方式 ===" 'Cyan'
Log "  Get-Process mysqld,redis-server,mongod,_server -ErrorAction SilentlyContinue | Stop-Process" 'Gray'
Log "  或逐个: Stop-Process -Name mysqld" 'Gray\''''

if old2 in s:
    s = s.replace(old2, new2, 1)
    print('已追加后台作业托管说明')
else:
    print('! 未找到停止方式块，跳过')

open(fp, 'w', encoding='utf-8', newline='').write(s)
print('start_env.ps1 更新完成')

import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")