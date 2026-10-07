import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

# 1) gasleak 后台菜单/路由规模
d = IOS_ROOT + r'\_analysis\gasleak_server\app_dist'
menus = os.path.join(d, 'app_dist_config_menus.js')
for cand in ['app_dist_config_menus.js', 'app_dist_plugins_api_routes_index.js']:
    fp = os.path.join(d, cand)
    if os.path.isfile(fp):
        s = open(fp, encoding='utf-8', errors='replace').read()
        print('=== %s (%d bytes)' % (cand, len(s)))
        # 菜单项 label
        labels = re.findall(r"(?:label|title|name)\s*:\s*['\"]([^'\"]{2,30})['\"]", s)
        print('   菜单/标签数:', len(labels))
        print('   样例:', labels[:30])
        print()

# 2) 路由文件清点
print('=== gasleak API 路由文件 ===')
rs = sorted(f for f in os.listdir(d) if f.startswith('app_dist_plugins_api_routes_'))
print('   数量:', len(rs))
for f in rs:
    print('     ', f.replace('app_dist_plugins_api_routes_', '').replace('.js', ''))

# 3) 潜客业务 service 规模
q = QIANKE_SRC + r'\qianke\service\system\sys_qianke.go'
if os.path.isfile(q):
    s = open(q, encoding='utf-8', errors='replace').read()
    print()
    print('=== sys_qianke.go: %d bytes, %d lines' % (len(s), s.count('\n') + 1))
    funcs = re.findall(r'^func\s+(?:\([^)]*\)\s*)?(\w+)\s*\(', s, re.M)
    print('   函数数:', len(funcs))
    print('   ', funcs[:40])
