---
id: D1-C2
mode: 验证
wave: D1
depends: [D1-C1]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  ★ **本卡的裁决结果是"无需实现"** —— Owner 已裁 (a) 复用，而实测表明
    **既有实现已完整满足 Android 需求**（字段级一致）⇒ 本卡转为**验证卡**。
  门禁强度自知：须用**真 HTTP 证明三条 track 对 Android 场景可用**，
  且**证明未新增重复注册**（否则 Fastify 启动失败）。
来源: `完整版本开发方案_终版.md:220`（D1-C2 原描述）
      + Owner 裁决 (a) 复用
      + ★ 调度实测：`04-landing/templates/vodex.html:485-492` 已按既有字段调用三条 track
base:
  - path: 02-backend-node\src_restored\plugins\api\routes\landing.js
    sha256: 3208c207bf423c8d99577c0508e9b6cc809f471dcd590ee0e96b87906e7de632
    bytes: 8381
    eol: LF
  - path: 04-landing\templates\vodex.html
    sha256: 6f2e2a1969703d2e9a3e008774b0fd16271172e12695d2911b6072de5e05bc4d
    bytes: 31008
    eol: LF
allowed_paths:
  - E:\ios漏洞\_integration\_fix_work\verify_d1c2_track_reuse.py
forbidden_paths:
  - "★ 全部产物代码（本卡为纯验证卡，不修改任何产物文件）"
  - "02-backend-node\\src_restored\\plugins\\api\\routes\\landing.js（已验收，只读）"
  - "04-landing\\templates\\**（模板，只读）"
  - "09-docs\\spec\\contracts.md"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_d1c2_track_reuse.py    # 须【绿】，退出码 0
packages: {}
---

# D1-C2 [R2] track 三条路径的**复用验证**（结论：无需新建）

## ★★ 结论先行：**本卡无需实现任何代码**

### 依据

1. **Owner 已裁 (a) 复用** ⇒ 不新建 `plugins/android/track.js`；
2. **实测：Android 的落地页模板已按既有字段调用这三条**：

`04-landing/templates/vodex.html:485-492`（**Android 侧模板**）：
```js
postJSON('/api/track/start', {sid: sid, lang: navigator.language||'', url: location.href});   // :485
setInterval(function(){ tick(); postJSON('/api/track/heartbeat', {sid: sid, dwell: dwell}); }, 15000);  // :486
a.addEventListener('click', function(){ tick(); postJSON('/api/track/click', {sid: sid, dwell: dwell}); });  // :492
```

3. **既有 `landing.js` 的字段与之**完全一致**：
```
:96   sid = normalizeSid(body.sid)
:107  lang: String(body.lang || '')
:108  url:  String(body.url || '')
:129  dwell = Number(body.dwell)
```

**⇒ 字段级 1:1 对应，**无缺字段、无形态差异**。**

4. **方案原话**：「3 条 track **硬冲突**，须先裁决复用」
   ⇒ **新建才会冲突；不新建即无冲突**。

**⇒ 复用的实质 = **保持现状 + 验证其可用性**。**

---

## 本卡的验证目标

| # | 断言 | 方法 |
|---|---|---|
| T1 | ★ **三条 track 对 Android 场景可用** | 真 HTTP，按 `vodex.html` 的**确切 body**构造 |
| T2 | ★ **`sid` 往返一致** | start 返回 sid，heartbeat/click 用它 |
| T3 | ★ **`dwell` 被记录** | heartbeat 传 dwell，验证不报错且语义正确 |
| T4 | ★ **未新增重复注册** | 扫源码确认 `/api/track/*` **只有一处**注册 |
| T5 | ★ **Fastify 未因重复路由启动失败** | 服务存活 + 端点可达 |
| T6 | ★ **限频未被动过**（`TOUCH_THROTTLE_MS` 仍为 3000） | 读源码 |
| T7 | **守护**：`landing.js`、模板、`_manifest.sha256` 未改 | sha256 比对 |

★ **T4/T5 是本卡的"防重复注册"核心** —— 若有人在 D1 阶段新增了 track 路由，
**Fastify 会启动失败**（或静默覆盖），本卡须能抓到。

## 不在范围

- **不改任何产物代码**（纯验证）
- 不新建 `plugins/android/track.js`

## 证据要求

- 判据的真实退出码
- ★ **T1–T3 的真 HTTP 响应原文**
- **T4 的源码扫描结果**（`/api/track/*` 注册点清单）
- **T6 的 `TOUCH_THROTTLE_MS` 值**

## 停靠点

1. 若发现 **`vodex.html` 的调用字段与既有实现不一致** ⇒ **停下升级**
   （说明 Android 确需不同的 track 实现）
2. 若发现 **`/api/track/*` 有多处注册** ⇒ **停下升级**（重复路由风险）
