fp = IOS_ROOT + r'\_integration\start_env.ps1'
s = open(fp, encoding='utf-8-sig').read()

old = "function Start-Svc($name, $exe, $args, $port) {"
new = "function Start-Svc($name, $exe, $argStr, $port) {"
assert old in s, '未找到函数签名'
s = s.replace(old, new, 1)

old2 = """    Start-Process -FilePath $exe -ArgumentList $args -WindowStyle Hidden"""
new2 = """    # ★ 参数名不能叫 $args —— 它是 PowerShell 自动变量，会解析为 null
    if ([string]::IsNullOrWhiteSpace($argStr)) {
        Start-Process -FilePath $exe -WindowStyle Hidden
    } else {
        Start-Process -FilePath $exe -ArgumentList $argStr -WindowStyle Hidden
    }"""
assert old2 in s, '未找到 Start-Process 行'
s = s.replace(old2, new2, 1)

open(fp, 'w', encoding='utf-8', newline='').write(s)
print('已修复 $args 阴影问题')

import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")