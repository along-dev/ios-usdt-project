# -*- coding: utf-8 -*-
"""T32 V2 judge: /device/list authorization reading on the isolated instance.
Unauthorized authority 1234 must be code=7; authorized authority 888 must be code=0.
Retries each call until it gets a JSON body (local 10054 resets are known flaky)."""
import importlib.util, os, sys, time
_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("rbac", os.path.join(_here, "rbac_login.py"))
rbac = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(rbac)
API = os.environ.get("DSH_API", "http://127.0.0.1:8900")
rbac.GO = API
UNAUTH = rbac.mint(101, "agentA", "代理商A", "1234", "11111111-1111-1111-1111-111111111111")
ADMIN  = rbac.mint(8, "admin", "超级管理员", "888", "b059de9e-be0c-11f1-9ed6-14755b847ee7")
PATH_ = "/device/list"
BODY = {"page": 1, "pageSize": 10, "status": -1, "agent_id": -1}

def reading(tok, tries=10):
    last = None
    for i in range(tries):
        s, b = rbac.call(PATH_, tok, BODY)
        if isinstance(b, dict) and b.get("code") is not None:
            return s, b.get("code"), (b.get("msg") or "")[:40], i + 1
        last = (s, b)
        time.sleep(0.4)
    return last[0], None, repr(last[1])[:60], tries

sa, ca, ma, ia = reading(UNAUTH)
sb, cb, mb, ib = reading(ADMIN)
print("UNAUTH(1234): HTTP=%s code=%s msg=%s attempts=%d" % (sa, ca, ma, ia))
print("AUTH(888):    HTTP=%s code=%s msg=%s attempts=%d" % (sb, cb, mb, ib))
ok = (ca == 7 and cb == 0)
print("V2_DEVICE_LIST=" + ("GREEN" if ok else "RED"))
sys.exit(0 if ok else 1)
