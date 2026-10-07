fp = IOS_ROOT + r'\_integration\start_env.ps1'
s = open(fp, encoding='utf-8-sig').read()

old = '''    # ★ 参数名不能叫 $args —— 它是 PowerShell 自动变量，会解析为 null
    if ([string]::IsNullOrWhiteSpace($argStr)) {
        Start-Process -FilePath $exe -WindowStyle Hidden
    } else {
        Start-Process -FilePath $exe -ArgumentList $argStr -WindowStyle Hidden
    }'''

new = '''    # ★ 参数名不能叫 $args —— 它是 PowerShell 自动变量，会解析为 null
    # ★ 必须用 Win32_Process.Create 启动：Start-Process 创建的子进程会随
    #   本 pwsh 进程退出而终止，导致"端口看似 UP、实际连不上"。
    #   改用 WMI 创建独立进程，脱离父进程生命周期。
    $cmdLine = if ([string]::IsNullOrWhiteSpace($argStr)) {
        '"' + $exe + '"'
    } else {
        '"' + $exe + '" ' + $argStr
    }
    $res = Invoke-CimMethod -ClassName Win32_Process -MethodName Create `
        -Arguments @{ CommandLine = $cmdLine } -ErrorAction SilentlyContinue
    if (-not $res -or $res.ReturnValue -ne 0) {
        # 回退到 Start-Process（仅限交互式会话，进程随会话结束而终止）
        Write-Host "  ! WMI 启动失败，回退 Start-Process（注意：进程随本会话结束而终止）" -ForegroundColor Yellow
        if ([string]::IsNullOrWhiteSpace($argStr)) {
            Start-Process -FilePath $exe -WindowStyle Hidden
        } else {
            Start-Process -FilePath $exe -ArgumentList $argStr -WindowStyle Hidden
        }
    }'''

assert old in s, '未找到待替换块'
s = s.replace(old, new, 1)
open(fp, 'w', encoding='utf-8', newline='').write(s)
print('已改为 WMI 独立进程启动')

import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")