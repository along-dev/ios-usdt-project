import base64,json,urllib.request,urllib.error,time
GO="http://127.0.0.1:8888"
def req(p,d=None,t=None,m="POST"):
    h={"Content-Type":"application/json","x-token":t or ""}
    r=urllib.request.Request(GO+p,data=json.dumps(d).encode() if d is not None else None,headers=h,method=m)
    try:
        with urllib.request.urlopen(r,timeout=15) as x:
            b=x.read()
            try: return x.status,json.loads(b)
            except: return x.status,b[:80].decode('utf-8','ignore')
    except urllib.error.HTTPError as e: return e.code, e.read()[:120].decode('utf-8','ignore')
    except Exception as e: return 0,str(e)
import ddddocr
ocr=ddddocr.DdddOcr(show_ad=False)
r=None
for _ in range(6):
    _,cap=req("/base/captcha",{})
    code=ocr.classification(base64.b64decode(cap["data"]["picPath"].split(",",1)[1]))
    _,r=req("/base/login",{"username":"admin","password":"123456","captcha":code,"captchaId":cap["data"]["captchaId"]})
    if isinstance(r,dict) and r.get("code")==0: break
    time.sleep(1)
tok=r["data"]["token"]
print("登录 OK")
tests=[
 ("设备列表","/device/list","POST",{"page":1,"pageSize":10}),
 ("代理设备","/device/agent_device_list","POST",{"page":1,"pageSize":10}),
 ("代理列表","/device/agent_list","GET",None),
 ("客户钱包","/device/custom_wallet_list","POST",{"page":1,"pageSize":10}),
 ("代理钱包","/device/agent_wallet_list","POST",{"page":1,"pageSize":10}),
 ("私钱包","/device/private_wallet_list","POST",{"page":1,"pageSize":10}),
 ("钱包列表","/device/wallet_list","POST",{"page":1,"pageSize":10}),
 ("系统地址","/device/system_address","GET",None),
 ("代币列表","/device/token_list","GET",None),
 ("代理收款地址","/device/agent_payment_address","GET",None),
 ("收款地址","/device/payment_address","GET",None),
 ("代理制表","/device/agent_tabulation","POST",{"page":1,"pageSize":10}),
 ("分包信息","/device/get_packet_info","GET",None),
 ("首页信息","/device/get_index_info","GET",None),
 ("私域财务","/device/custom_financial","POST",{"page":1,"pageSize":10}),
 ("代理财务","/device/agent_financial","POST",{"page":1,"pageSize":10}),
 ("平台财务","/device/financial","POST",{"page":1,"pageSize":10}),
 ("分包列表","/device/packet_list","GET",None),
]
for n,p,m,d in tests:
    st,r2=req(p,d,tok,m)
    code=r2.get("code") if isinstance(r2,dict) else r2
    msg=r2.get("msg") if isinstance(r2,dict) else ""
    flag="OK" if code==0 else "★FAIL"
    print(f"  {flag:6s} {n:10s} {p:28s} -> code={code} msg={msg}")
