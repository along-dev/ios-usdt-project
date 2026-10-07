# X2 停靠点 1 证据：`${ADMIN}/logout` 的确切期望值【无法确定 —— 卡与实际冲突】

> 执行 Agent 现场实测，2026-09-30。**未改任何判据**（先取证后动手）。

## 1. 卡的说法

卡 `X2-修判据弱断言.md:60-69` 与任务书均称：

```
logout(带 token): HTTP=302
logout(无 token): HTTP=302
```
⇒ 「确切期望值 = `302`」⇒ 断言改为 `st7 == 302`。

## 2. 现场实测（真实服务，port 3000 在听）

用**与 `verify_d1c5b_admin_data.py` 完全一致**的 `req()`（Cookie `accessToken=<JWT>`）：

```
D7 ${ADMIN}/logout 可达（非 404）: HTTP=200      ← 判据自身输出
```

独立探针（`_x2_probe2.py`，201 行 login 逻辑同判据）：

```
ADMIN/logout   with-token  => HTTP=200 final_url=.../mgr-admin-8bcde2021d98/login
ADMIN/logout   no-token    => HTTP=200 final_url=.../mgr-admin-8bcde2021d98/login
bare /logout   with-token  => HTTP=404
bare /logout   no-token    => HTTP=404
ADMIN/login    with-token  => HTTP=200
```

★ 关键：`ADMIN = "/mgr-admin-8bcde2021d98"`（判据 `:53`），
路径**不是**裸 `/logout`（裸路径确实 404）。带 ADMIN 前缀的真路径 = **200**。

★ `login()` 在本机环境返回 token（`token len=281`，见 `_x2_probe_logout.py`）——
首次探针 `token len=0` 是探针自身 bug（取了 `token` 字段，而响应是 `accessToken`），
已修正；修正后 token 正常，结论不变。

## 3. 源码佐证

`E:\USDT项目\02-backend-node\src_restored\plugins\android\admin.js:1033-1064`：

```js
  // ---- GET ${ADMIN}/logout —— 清会话 + 回登录页 ----
  // 前端 `:414` 是浏览器直接导航（<a href>），故用 302 而非 JSON。
  fastify.get('/mgr-admin-8bcde2021d98/logout', async (request, reply) => {
    ...
    logger.info({ ip: getRealIP(request) }, 'D1-C5b 管理台登出');
    return reply.redirect('/mgr-admin-8bcde2021d98/login', 302);   // ★ 源码确为 302
  });
```

**源码确为 302**，但 **HTTP 观测为 200** —— 两者不矛盾：

`reply.redirect(url, 302)` 发出的 302 带 `Location` 头。
而 `verify_d1c5b_admin_data.py` 的 `req()` 用 `urllib.request.urlopen()`，
**urllib 默认自动跟随 3xx 重定向** ⇒ 最终读到的是重定向目标
`/mgr-admin-8bcde2021d98/login` 的 **200**。

⇒ **`st7` 这个变量拿到的值取决于"是否自动跟随重定向"**。

## 4. 结论：停靠点 1 触发

| 口径 | `${ADMIN}/logout` 的可见状态码 |
|---|---|
| 不跟随重定向（raw） | **302** |
| 跟随重定向（当前 `req()` 实际行为） | **200** |

⇒ **"确切期望值"取决于 `req()` 的重定向语义，卡未指明**。

- 若照卡写 `st7 == 302` ⇒ **当前 `req()` 下必然 FAIL** ⇒ `verify_d1c5b_admin_data.py` **由绿变红**
  ⇒ 同时撞**停靠点 3**（"改造导致判据由绿变红 ⇒ 停下报告"）。
- 若写 `st7 == 200` ⇒ 与卡的「确切期望值 = 302」**直接矛盾**，且 200 只是重定向兜底页的状态码，
  **判别力弱于 302**（任意能渲染登录页的响应都是 200）⇒ **反而是一种新的弱断言**。

★ 两条路都不可接受 ⇒ **按卡要求"停下报告，不要猜"**。

## 5. 最小正确修法（需卡方/Scheduler 裁决后再实施）

要断言 `302`，必须**关闭自动重定向**，让 302 可见。两种等价实现：

**方案 A（推荐，改 `req()` 加一个可选参数，不影响其他调用点）**

```python
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None

def req(method, path, body=None, token=None, timeout=15, follow=True):
    ...
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(_NoRedirect())
    ...
```

然后 D7 改：

```python
st7, _ = req("GET", f"{ADMIN}/logout", token=tok, follow=False)
rec("D7 ${ADMIN}/logout ⇒ 302（清会话后重定向）", st7 == 302, f"HTTP={st7}")
```

**方案 B（零侵入）**：保留 `follow=True`，改为断言**重定向目标**：

```python
st7, b7 = req("GET", f"{ADMIN}/logout", token=tok)
rec("D7 ${ADMIN}/logout ⇒ 200 且落在登录页", st7 == 200, f"HTTP={st7}")
```

★ 方案 B 的判别力弱（不能区分"清会话"与"没清会话"）。
★ 判据 Z1/Z2 的静态扫描**对 A/B 均能通过**（两者都不再是 `!= 404` 或无条件 `True`）。

**⇒ 本停靠点要的裁决只有一句：采用 A 还是 B。**
A 需要动 `req()` 签名（属"改判据强度"允许范围，未动业务逻辑）；
B 不动 `req()` 但断言较弱。

## 6. 未受影响项

#2–#6（`_fix_work` 其余 4 个脚本）**不依赖此裁决**，已按卡实施。
详见 `_x2_report.md`。
