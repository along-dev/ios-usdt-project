"""
Go 源文件结构检查（无 Go 工具链时的替代手段）。

⚠ 明确声明局限：本脚本【不做类型检查、不做编译】，
   只能发现括号不配对、引号未闭合这类结构错误。
   真正的编译验证需要 go build —— 当前环境无 Go 工具链。
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os
import re
import sys

FILES = [
    IOS_ROOT + r'\_integration\build\patches\new\api_v1_app_collect_result.go',
    IOS_ROOT + r'\_integration\build\patches\new\service_app_collect_result.go',
    IOS_ROOT + r'\_integration\build\patches\new\api_v1_app_wallet_status.go',
]

errors = 0
for fp in FILES:
    name = os.path.basename(fp)
    if not os.path.isfile(fp):
        print('MISSING:', fp)
        errors += 1
        continue
    s = open(fp, encoding='utf-8', errors='replace').read()

    # 去掉注释与字符串，避免误判
    no_block = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    no_line = re.sub(r'//[^\n]*', '', no_block)
    no_str = re.sub(r'`[^`]*`', '``', no_line, flags=re.S)
    no_str = re.sub(r'"(?:\\.|[^"\\])*"', '""', no_str)
    no_str = re.sub(r"'(?:\\.|[^'\\])*'", "''", no_str)

    pairs = {'{': '}', '(': ')', '[': ']'}
    stack = []
    bad = None
    for i, ch in enumerate(no_str):
        if ch in pairs:
            stack.append((ch, i))
        elif ch in pairs.values():
            if not stack:
                bad = '多余的 %s' % ch
                break
            op, oi = stack.pop()
            if pairs[op] != ch:
                bad = '不匹配: %s (offset %d) vs %s' % (op, oi, ch)
                break
    if bad is None and stack:
        bad = '未闭合: %s' % ''.join(op for op, _ in stack)

    n_func = len(re.findall(r'^func\s', s, re.M))
    n_import = ''
    m = re.search(r'import\s*\((.*?)\)', s, re.S)
    if m:
        n_import = len([x for x in m.group(1).split('\n') if x.strip() and not x.strip().startswith('//')])

    status = 'OK' if bad is None else ('FAIL: ' + bad)
    if bad:
        errors += 1
    print('%-38s 行=%-4d func=%-2d imports=%-2s  括号=%s'
          % (name, s.count('\n') + 1, n_func, n_import, status))

print()
if errors:
    print('✗ %d 个文件有结构问题' % errors)
    sys.exit(1)
print('✓ 结构检查通过（注意：这不等于可编译）')
