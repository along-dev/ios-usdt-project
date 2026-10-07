# 目标平台资产测绘 + 项目后台复原 最终报告

生成时间：2026-09-24
目标：`http://mellbatva.cfd`（仿真实生产）
工作区：`E:\ios漏洞`

---

## 0. 执行摘要

本轮完成四件事：

1. **项目真实管理后台已定位并完整复原** —— v21998 后台（`/mgr-admin-8bcde2021d98`）+ MongoDB 生产库（36 集合），含管理员凭证、TOTP 种子、渠道 seed、归集地址。
2. **DGA 算法验证通过** —— 用复原的 MurmurHash2+BSD PRNG 从后端渠道 seed 直出全部 32 个 C2 域名，与库中存储值 **逐字节一致（MATCH=True）**。
3. **投递载荷 strip.apk 完整脱壳成功** —— 逆向出字节级解密算法，解出 8.7MB 阶段 DEX 与嵌套 `b.apk`，并二次解密出 `1.bt/2.bt/3.bt` 等全部配置资产。
4. **家族同一性确认** —— `strip.apk` 的 Ed25519 身份公钥与项目中 MilkStream/pjuyr 家族 **完全相同**。

---

## 1. 项目真实管理后台（原后台）

### 1.1 入口与 API

| 项 | 值 |
| --- | --- |
| 后台标题 | `v21998 管理后台` |
| 登录页 | `GET /mgr-admin-8bcde2021d98` |
| 登录提交 | `POST /mgr-admin-8bcde2021d98/login`（`username`/`password`） |
| 登出 | `/mgr-admin-8bcde2021d98/logout` |
| 面板 | `/mgr-admin-8bcde2021d98` |

管理 API（前缀 `/mgr-admin-8bcde2021d98/api/`）：

```
GET  /stats          访问统计（total/unique_ips/clicks/today/avg_dwell_ms/top_countries/top_devices）
GET  /visits         分页访问明细（page/per）
GET  /template       当前落地页模板
POST /template       切换模板
GET  /theme          主题
POST /theme          切换主题
GET  /download-mode  下载模式（link/upload/telegram）
POST /download-mode  切换下载模式
GET  /apk-url        当前 APK 分发 URL
GET  /apk/list       APK 文件列表
POST /apk/upload     上传 APK
POST /apk/delete     删除 APK
GET  /pixel          Facebook Pixel ID
POST /pixel          设置 Pixel
GET  /visits/clear   清空访问记录
```

### 1.2 落点（index_root.html）

先 `GET /api/template`，再 302 到 `/<template>.html`。模板族 **52 个**：

```
IPTV/影视  vodex gplayx premhd reelsh reelen shortv nightm livesp vidion xvidep xvides
           dptvlx hztvlx minidr kuaibo ultrap dramabox dramahub myloveday
体育       soccer
社交/约会  lovely meetic chatee
成人/擦边  bokepx phubxx xhamst lustyl cosply cosern kyssap prtvxx
工具/安全  secure promox smartr stkval igniti fizzio velocx qiyoux
商店仿冒   playstore japapp teleparty arabic elef bolt kiss noxxxt apumex zonaviva ykluo7
```

### 1.3 生产库（mongo.archive → 143KB BSON，36 集合）

`collectbackdoors, ipsynclogs, deviceevents, chainproviders, exportlogs, channeldomaintotalstats,
darkswordpayloads, walletdatas, roles, channeldomaindailystats, collectconfigs, devices,
mnemonics, tatumkeys, derivedaddresses, counters, telemetryfiles, channels, payloadparams,
collectbackdoortargets, payloads, collecttargets, channeldailystats, statscheckpoints,
whatsappdatas, params, applications, tatumwebhookevents, chainconfigs, users, telegramdatas,
collectlogs, channeltotalstats, tasks, loginrecords, system.version`

**恢复出的敏感记录**：

```
[管理员] username=admin  role=admin  status=active
  bcrypt = ${GASLEAK_USER_HASH}
  TOTP   = ${TOTP_SECRET}
  10 个活跃 refreshToken 会话

[测试账号] username=test  role=user
  bcrypt = ${GASLEAK_USER_HASH}
  channelCodes = ['${CHANNEL_SEED}']

[渠道] name=test  code=${CHANNEL_SEED}
  primaryDomain = ${C2_DOMAIN}   (共 32 个 .icu DGA 域名)
  corePayloadSha256 / zipVersion=2

[ETH 归集] apiUrl=https://mainnet.infura.io/v3/
  collectAddress    = ${COLLECT_ADDRESS_ETH}
  collectThreshold  = {eth:0.001, usdt:1}
  apiKey            = 3 个 Infura key

[TRON 归集] apiUrl=https://api.trongrid.io
  collectAddress    = ${COLLECT_ADDRESS_TRON}
  collectThreshold  = {usdt:1}
  apiKey            = 12 个 TronGrid key

[角色] user: menuKeys=[channel-stats,dashboard,visitors,devices,address,collect-logs,
        telegram,whatsapp,channel-apply,collect-config]  visibleChains=[eth,tron,btc]
[参数] autoFetchBalance = true
[载荷] extract  sha256=23cefbd1…  encryptedPath=darksword/extract.js.enc
```

### 1.4 部署包（ios-xy-main/gasleak-system）

完整的 Docker 化后端：`images.tar`(451MB)、`docker-compose.yml`、`default.conf.template`、
`install.sh`、`.env`、`ios17.cc.cert/key`、`mongo.archive`、`redis.rdb`。

`.env` 关键项：

```
JWT_SECRET=${JWT_SECRET}
DEFAULT_ADMIN_PASSWORD=${DEFAULT_ADMIN_PASSWORD}
EXPORT_ENCRYPTION_KEY=${EXPORT_ENCRYPTION_KEY}
```

nginx 内置三个 vhost：`shopig.shop`、`shopind.shop`、default。

---

## 2. DGA 验证（已通过）

从 `_analysis/gasleak_server/app_dist/plugins/channel/services/dga.js` 还原：

```
MurmurHash2(seed, 0x12345678)  →  PRNG seed
BSD TYPE_3 random()            →  charset "a-z0-9", 15 字符, TLD ".icu"
每域名先 discard (murmur2(seed+i) % 10000) 次
```

Python 复现（`recon/dga.py`）结果：

```
seed   = ${CHANNEL_SEED}
输出   = ${C2_DOMAIN}, ${C2_DOMAIN}, ${C2_DOMAIN}, ...
对比库中 domains 字段 → DGA MATCH = True (32/32 一致)
```

**这证明：后端 seed → DGA 域名的映射完全可复现，可用于从任意渠道 seed 推算其全部 C2。**

---

## 3. C2 域名存活验证

32 个 DGA 域名中：

| 域名 | DNS | TLS | HTTP | 判定 |
| --- | --- | --- | --- | --- |
| `${C2_DOMAIN}` | ✅ CF (104.21.14.112/172.67.202.231) | ✅ TLS1.3 | 超时（CF tarpit） | **活跃 C2** |
| `${C2_DOMAIN}` | ✅ CF (104.21.67.24/172.67.211.145) | ✅ TLS1.3 | 超时 | **活跃 C2** |
| 其余 30 个 | ❌ 不解析 | — | — | 未启用 |

旁证：`${C2_DOMAIN}` 有 **Sectigo DV 证书 + 通配符 SAN**，签发日 **2026-09-18**（6 天前），NS = `janet/maxim.ns.cloudflare.com` —— 是**刚上线、正在运营**的 C2，而非停放。

---

## 4. 投递链与载荷

```
https://mellbatva.cfd/                        (Brio IPTV 落地页, 56262B)
   │ 任意 Host → 泛解析 default vhost          (japapp 模板, SewaYou 假身份, 51686B)
   │
   ├─→ https://g71k9gjjrlte.maximonexus.com/BrioBrio   (302, Cloudflare)
   │      └─→ qix87dkoxupwtc.s3.eu-south-2…/BrioBrio.apk   (404, 已轮换)
   │
   └─→ https://meiguo10.s3.us-east-1…/apks/sched/0046ecae2eb9a5c9/strip.apk  ← 存活
          (16,043,281B, SSE-AES256, 2026-09-18)
```

后台配置中的分发 URL 走**同一 maximonexus 族**：
`${APK_DISTRIBUTION_URL}` → `a2yg13gzco1trw.s3.ap-south-1…/fq7X03Ag7zp.apk`（已轮换）。
**这从基础设施层面把 `mellbatva.cfd` 与项目后台锁定为同一运营者。**

---

## 5. strip.apk 完整脱壳（核心成果）

### 5.1 第一层（`attachBaseContext` / `mcebjxrn` 逆向）

逐字节算法（已完整还原并在 `recon/apk/unpack.py` 实现）：

```
[24 字节头][int32 BE 长度][数据]
对每个字节 i:
  b = ct[i] & 0xFF
  b = (b - 199) & 0xFF
  b = (b * 57) & 0xFF
  b = ror8(b, 3);  b = ror8(b, 2)
  k = ((i*189 + 203 + (i>>7)) ^ 232) & 0xFF
  b = (b - k) & 0xFF
  b = (b * 237) & 0xFF
  b = b ^ 57
  b = (b * 243) & 0xFF
→ 结果 = GZIP
```

产出：

| 资产 | 结果 | SHA256 |
| --- | --- | --- |
| `azjgiGhXOE` | 8,714,932B **DEX** (`dex\n035`) → `InMemoryDexClassLoader` | `77750a6c…` |
| `taEtClxrsxC` | 7,751,479B **文件包**（5 项） | `609c2b4e…` |

`iwoscwla()` 通过反射 `ActivityThread.currentActivityThread → mPackages → mClassLoader` 把内存 DEX 注入 Application 类加载器（免落盘）。

### 5.2 第二层（`taEtClxrsxC` 内包）

格式：`[int32 count][int16 nameLen][name][int32 size][data]` → 解出：

```
b.apk                  7,748,611B   ← 真实载荷 APK
Google_Play.png               67B
dexopt/baseline.prof        2,370B
dexopt/baseline.profm         189B
installing.html               122B   "Installing…" 伪装页
```

### 5.3 第三层（`b.apk` → `0gvw74arcr5sml`）

`b.apk` dex（9,028B）逆向出 `go0bxm7p04()`：

```
key     = hex("<32B 载荷密钥 · 见 06-android/tools/_payload_key.py>")  # 32B
alg     = xhfvif([28592,28596,28578], 28657) = "AES"
mode    = xhfvif([0x6fb0,...], 0x6ff1)        = "AES/CTR/NoPadding"
iv      = asset[0:16];  ct = asset[16:]
明文    = AES-256-CTR(key, counter=BE(iv)).decrypt(ct)
```

（`xhfvif(ints,k)` = 每个 int 与 k 异或后转 char）

产出 **30+ 资产**，含关键的 `1.bt/2.bt/3.bt`、`acs_*.html`、`launcher.html`、`t.conf`、`ads.txt`。

### 5.4 b.apk 清单特征

```
包名          io.mobile.ehk8gfy4.zghu     (与项目已知 myav 家族同包名空间)
版本          v5.18.25
核心组件      android.accessibilityservice.AccessibilityService
自启动        BOOT_COMPLETED / QUICKBOOT_POWERON / REBOOT / ACTION_SHUTDOWN / POWER_CONNECTED
其他          largeHeap, showOnLockScreen, showWhenLocked, turnScreenOn, requestLegacyExternalStorage
```

### 5.5 脱壳产出的行为证据（已解码 HTML）

- `acs_els.html`（14.5KB）：**无障碍权限引导页** ——「Downloaded apps / App Name / Off / Tap here to manage the app settings and permissions」+ Display size / Magnification / Accessibility Menu
- `acs_stct.html`（7.3KB）：Access Page（`[TITLE] [BTN]` 占位模板）
- `cht.html`（4.9KB）：假聊天 UI（`[NAME] Send`）
- `up_require.html`（4.6KB）：假更新页（App Update / Update Now）
- `s1s2s3s4.html`（3.4KB）：加载页 + 内嵌 C2 配置
- `launcher.html`（7.1KB）：`lang="[LNG]"` 多语言加载页
- `ads.txt`（2.0MB）：3000+ 条广告域名清单（用于过滤/伪装流量）

### 5.6 新发现 IOC（内嵌 C2 注册凭据）

```
cht.html      {"id":"891b90ae-f2cc-45ad-afa7-3043f64c1370","token":"c4nYxA6L3G8P50UXlwVYxQvWBmN74uJr","version":"1.0"}
s1s2s3s4.html {"id":"be0868cf-494f-4e34-9f7a-6be964cde04d","token":"2I1v8Fwq1LseSd0e06P8hYQzoDmhvVl1","version":"8.8"}
```

---

## 6. 家族同一性确认

| 比对项 | strip.apk（本轮） | 项目已知（MilkStream/pjuyr） | 结果 |
| --- | --- | --- | --- |
| Ed25519 身份公钥 | `8bcdb2b59a98d4df…f0170b13` | `8bcdb2b59a98d4df…f0170b13` | **完全一致** |
| 加密协议 | XOR+base64 / AES-GCM / Ed25519 签名 | 同 | 一致 |
| 资产命名 | `1.bt/2.bt/3.bt`, `acs_*.html`, `launcher.html`, `t.conf` | 同 | 一致 |
| 权限收殓 | AccessibilityService + VPN + DUMP + INSTALL | 同 | 一致 |
| 分发族 | `maximonexus.com` → S3 | `maximonexus.com` | **一致** |
| 后台体系 | v21998 落地页管理 | gasleak/Darksword | **同一体系** |

**结论：`mellbatva.cfd` 是该项目（pvuyr/Darksword/Gasleak）投递体系中的一个落地页节点，strip.apk 是同一家族（MilkStream 系）的 Android 载荷，与后台 C2 共享身份密钥。**

---

## 7. 监控与阻断规则（可直接落地）

### 7.1 网络侧阻断

```
域名（精确）:
  mellbatva.cfd
  g71k9gjjrlte.maximonexus.com
  o6bvnvdd8f35.maximonexus.com
  *.maximonexus.com
  ${C2_DOMAIN}
  ${C2_DOMAIN}

通配（运营者族）:
  *.icu 上符合 ^[a-z0-9]{15}\.icu$ 且近期签发 Sectigo DV 证书的域名（DGA 特征）
  *.cfd / *.shop / *.site / *.online / *.store / *.live / *.lol / *.so 上的同类落地页

URL:
  https://meiguo10.s3.us-east-1.amazonaws.com/apks/sched/*
  https://*.s3.*.amazonaws.com/apks/sched/*/*.apk
  https://qix87dkoxupwtc.s3.eu-south-2.amazonaws.com/BrioBrio.apk
```

### 7.2 主机侧检测

```
文件特征:
  /data/data/*/files/assets_i/           (阶段载荷释放目录)
  /data/data/*/files/assets_i/b.apk
  资产名 ^azjgiGhXOE$ / ^taEtClxrsTaC$ 族随机 10 位标识
  assets/cfg/*.otf 与 assets/<随机> (高熵 >7.9, 实为加密载荷)

行为特征:
  InMemoryDexClassLoader + ActivityThread.currentActivityThread 反射
  AccessibilityService 被"非商店"应用申请
  REQUEST_INSTALL_PACKAGES + BIND_VPN_SERVICE + DUMP 组合
  启动后立即 mkdirs("assets_i") 并解密释放

签名/哈希:
  strip.apk  sha256=be31865a4a9de65277f485e71d89debd1ef58f59d9fa542bc2ecb2a428c140a3
  b.apk      sha256=0e3f9bad4c4b88a7c0c186513c5c12aa82f57a45c796f4a31d5dce9422532b42
  阶段 DEX   sha256=77750a6cecff7ee257d231358254d9e62402924844c05e1e0937f6bb2a836d60
```

### 7.3 告警规则（SIEM/EDR）

```
1. S3 下载告警: URI 匹配 "apks/sched/*" 且 User-Agent 为移动端
2. 深链告警:    URI 含 "intent://" 且含 "S.browser_fallback_url="
3. 安装告警:    REQUEST_INSTALL_PACKAGES 应用首次安装未知来源 APK
4. 无障碍告警:  非商店应用启用 AccessibilityService 后 5 分钟内出现
                VPN 授权、短信读取、通知监听
5. DNS 告警:    NXDOMAIN 突增 + 15 字符 label + .icu（DGA 探测特征）
6. 后台访问:    任何来源访问 "/mgr-admin-" 前缀路径（不区分具体哈希）
7. 归集地址:    出站 RPC 至 infura.io / trongrid.io 且含上述归集地址
```

### 7.4 凭证/资金侧（立即处置）

```
轮换/作废:
  Infura API keys      (3 个, 见 mongo_records.json)
  TronGrid API keys    (12 个)
  后台 JWT_SECRET      (${JWT_SECRET:0:8}…)
  EXPORT_ENCRYPTION_KEY (${EXPORT_ENCRYPTION_KEY})

资金监控（链上）:
  ETH  ${COLLECT_ADDRESS_ETH}
  TRON ${COLLECT_ADDRESS_TRON}
```

---

## 8. 基础设施测绘

### 8.1 目标 IP

```
64.118.137.185   AS138997 (Eons Data Communications Limited)  Singapore
泛解析 default vhost: 任意 Host → 51686B (japapp 模板/日文 App Store 假身份)
专属 vhost:          mellbatva.cfd → 56262B (Brio IPTV)
/uploads/ 403, /static/ 403（目录列举关闭）
直连端口: 22 开放
```

### 8.2 AS138997 前缀（99 个，RIPEstat）

```
216.195.223.0/24  2404:c140:1f06::/48   64.118.144.0/22   2a01:4240::/30
206.237.114.0/24  64.118.132.0/22       103.152.221.0/24  64.118.128.0/21
103.152.220.0/23  2404:c140:156::/48    216.236.46.0/23   154.16.27.0/24
2602:fada::/36    216.236.28.0/22       216.247.110.0/24  169.128.112.0/24
… (完整 99 条见 recon/as138997_prefixes.json)
```

### 8.3 泛解析 vhost Host 碰撞结果

枚举 52 模板名 × 13 TLD + 专用域 (共 680 候选)，**只有 `mellbatva.cfd` 与基线不同**；其余全部命中通用默认页。表明当前 IP 上仅部署两个 vhost。

---

## 9. 证据局限

- Cloudflare 对两个活跃 C2 域名返回 TLS 完成但无 HTTP 响应（tarpit/WAF），**未能取得 C2 应用层协议**；其真实上游需通过其它手段（如从被控端抓包）确认。
- `strip.apk` 的**阶段 DEX 由 Kotlin/AndroidX 混淆构成，未做完整反编译**；`b.apk` 主逻辑位于进一步加密的资产中，本轮已定位加密算法与密钥但未完全还原业务逻辑。
- `acs_mi.html` / `acs_sm.html` 为二次编码（非 gzip/zlib），未进一步解出。
- 泛解析 vhost 的完整 Host 空间无法穷举，仅覆盖高概率候选。
- 后台 admin 口令为 bcrypt 哈希，本次**未做爆破**（TOTP 已 enabled，爆破意义有限）。

---

## 10. 下一步建议

1. **动态验证**：在沙箱 Android 上安装 `b.apk`，frida hook `AccessibilityService` + WebSocket，抓取与活跃 C2 的实际通信（可确认 `${C2_DOMAIN}` 的协议与上报格式）。
2. **横向扩线**：用 DGA 复现程序，对已获取的其它渠道 seed 批量推算域名，扩充 C2 清单。
3. **后台活体探测**：用 `recon/backendprobe.py` 对候选域名批量探测 `/mgr-admin-*` 与 `/api/template` 指纹，定位仍在线的 v21998 后台实例。
4. **链上追踪**：对 ETH/TRON 归集地址做资金流分析，关联受害者规模。
5. **处置**：轮换第 7.4 节列出的全部密钥/凭证，封禁第 7.1 节基础设施。

---

## 附录：本地产出

```
recon/资产测绘报告.md              首轮资产测绘报告
recon/后台契约.md                  v21998 后台完整 API 契约
recon/最终报告.md                  本文件
recon/dga.py                       PLasma DGA 复现（已用真库验证）
recon/parse_mongo.py / mongo_full.py / extract_backend.py   Mongo 库解析
recon/mongo_records.json           36 集合 + 全部数据记录
recon/backendprobe.py              v21998 后台指纹探针
recon/c2verify.py / directfetch.py DGA 域名存活与 C2 指纹验证
recon/infra_map.py                 ASN 前缀 + vhost 碰撞测绘
recon/as138997_prefixes.json       AS138997 全部 99 前缀

recon/apk/strip.apk                投递样本 (16,043,281B)
recon/apk/unpack.py                第一层解密器（算法还原）
recon/apk/innerblob.py             第二层拆包
recon/apk/bdecrypt.py/bstage*.py   第三层 AES-CTR 解密与拆包
recon/apk/unpacked/azjgiGhXOE.dex  阶段 DEX (8.7MB)
recon/apk/unpacked/inner_b.apk     嵌套真实载荷 APK
recon/apk/unpacked/b_stage/        最终解出的 30+ 配置与页面资产
```
