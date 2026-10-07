# -*- coding: utf-8 -*-
"""R3-1 · 核实 Node 静态图片的 Content-Type（V2 失败的真根因）。"""
import urllib.request

TESTS = [
    "http://127.0.0.1:3000/images/template-previews/vodex.png",
    "http://127.0.0.1:3000/images/template-previews/apumex.png",
    "http://127.0.0.1:3000/landing-pages/velocx/static/css/all.min.css",
    "http://127.0.0.1:3000/landing-pages/premhd/static/js/main.js",
    "http://127.0.0.1:8888/images/template-previews/vodex.png",  # 对照：Go 侧
]

for url in TESTS:
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            h = dict(r.headers)
            b = r.read()
        ct = h.get("Content-Type", "")
        print("  %-62s" % url)
        print("      status=%s  Content-Type=%r  bytes=%d" % (r.status, ct, len(b)))
        print("      全部头: %s" % ", ".join(sorted(h.keys())))
    except Exception as e:
        print("  %-62s => ERR %s %s" % (url, type(e).__name__, e))
    print("")
