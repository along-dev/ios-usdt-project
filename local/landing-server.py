#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地落地页服务器（核心闭环用）—— 复刻生产 nginx 的「静态托管 + /api 反代」。

生产链路（08-infra/nginx/default.conf.template 的默认 server）：
    /            -> 静态 HTML（落地页模板）
    /api/...     -> Node:3000

本机 Node 跑在 3313（Windows 保留区覆盖 3000），故此处 /api 反代到 3313。
落地页资源在产物中被扁平化：URL /landing-pages/<n>/<sub> -> assets/landing-pages__<n>__<sub 以 __ 连接>。
仅本地沙箱用途，监听 8080。
"""
import os
import sys
import re
import http.server
import socketserver
import urllib.request
import urllib.error
from pathlib import Path

LANDING_ROOT = Path(__file__).resolve().parent.parent / "04-landing"
NODE_API = os.environ.get("NODE_API_BASE", "http://127.0.0.1:3313")
PORT = int(os.environ.get("LANDING_PORT", "8080"))


class Handler(http.server.BaseHTTPRequestHandler):
    def _send_file(self, path: Path, ctype: str = None):
        try:
            data = path.read_bytes()
        except Exception:
            self._err(404)
            return
        self.send_response(200)
        if ctype:
            self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _err(self, code):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"{code}\n".encode())

    def _proxy(self, body=None):
        url = NODE_API + self.path
        req = urllib.request.Request(url, data=body, method=self.command)
        for k, v in self.headers.items():
            if k.lower() not in ("host", "content-length", "connection"):
                req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                payload = r.read()
                self.send_response(r.status)
                ct = r.headers.get("Content-Type", "application/json")
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
        except urllib.error.HTTPError as e:
            payload = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as ex:
            self._err(502)

    def _handle(self, body=None):
        p = self.path.split("?", 1)[0]
        if p.startswith("/api/"):
            return self._proxy(body)
        if p == "/landing-runtime.js":
            return self._send_file(LANDING_ROOT / "runtime/landing-runtime.js", "application/javascript")
        # /landing-pages/<name>/ 或 /landing-pages/<name>
        m = re.match(r"^/landing-pages/([^/]+)/?$", p)
        if m:
            tmpl = LANDING_ROOT / "templates" / f"{m.group(1)}.html"
            if tmpl.exists():
                return self._send_file(tmpl, "text/html; charset=utf-8")
            # 也可能是目录 index
        # /landing-pages/<name>/<sub...>  -> assets/landing-pages__<name>__<sub 以 __ 连接>
        m2 = re.match(r"^/landing-pages/(.+)$", p)
        if m2:
            flat = "landing-pages__" + m2.group(1).strip("/").replace("/", "__")
            cand = LANDING_ROOT / "assets" / flat
            if cand.exists():
                return self._send_file(cand)
            return self._err(404)
        if p == "/" or p == "":
            idx = LANDING_ROOT / "runtime/index_root.html"
            if idx.exists():
                return self._send_file(idx, "text/html; charset=utf-8")
        # 根级模板：/<name>.html -> 04-landing/templates/<name>.html
        mm = re.match(r"^/([^/]+)\.html$", p)
        if mm:
            tmpl = LANDING_ROOT / "templates" / f"{mm.group(1)}.html"
            if tmpl.exists():
                return self._send_file(tmpl, "text/html; charset=utf-8")
        # 其它静态文件直接按路径找（assets/reference 根下）
        cand = LANDING_ROOT / p.lstrip("/")
        if cand.exists() and cand.is_file():
            return self._send_file(cand)
        return self._err(404)

    def do_GET(self):
        self._handle()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None
        self._handle(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    os.chdir(str(LANDING_ROOT))
    with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"[landing] serving {LANDING_ROOT} on :{PORT}, /api -> {NODE_API}", flush=True)
        httpd.serve_forever()
