# ios漏洞 profile JS 静态分析报告

生成时间：2026-06-29

## 1. 分析范围

本报告分析以下两个入口脚本，以及它们动态拉取的后续模块：

- `/profile/ouzpbnvq81qdf9zsjuvr.js?1782740682662`
- `/profile/e13m4e5s4wwz2dhuasie.js?1782740683010`

本次仅进行静态抓取、哈希校验、解包和代码定位，没有执行 exploit 或 payload。

## 2. 样本与哈希

| 文件 | 本地路径 | SHA256 | 说明 |
| --- | --- | --- | --- |
| `01-ouzpbnvq81qdf9zsjuvr.js` | `captures/heimao-profile-js-20260629214639/01-ouzpbnvq81qdf9zsjuvr.js` | `49e00b0c62ceb953a3a047782e74e058dcdbf355bb9aa1bfd61a36eb0b38f174` | Worker/native call 阶段 |
| `02-e13m4e5s4wwz2dhuasie.js` | `captures/heimao-profile-js-20260629214639/02-e13m4e5s4wwz2dhuasie.js` | `92c7d246d2c163c076f783dcc19f87f5b9b9ac301b106b87a7aaea9346ce0052` | JSC/WebKit RCE 与 JS R/W 阶段 |
| `03-ef1xrwkweuxfahzbwq47.js` | `captures/heimao-profile-js-20260629214639/03-ef1xrwkweuxfahzbwq47.js` | `f7b59a9d551c2d4e4e85e6c68c3040ea4ca09262db9fb7bbeceedf12de24f11a` | SBX0，GPU/WebContent 相关沙箱逃逸阶段 |
| `04-4rix9sr76vzh2rosrs86.js` | `captures/heimao-profile-js-20260629214639/04-4rix9sr76vzh2rosrs86.js` | `3a0ce77868395ecea5c409b99854dc21ce7898a80c4bc8b55e9729b326963168` | SBX1，CoreMedia/XPC/IOSurface 阶段 |
| `05-72gs3bzug9jyomnt.json` | `captures/heimao-profile-js-20260629214639/05-72gs3bzug9jyomnt.json` | `f110e4e0a53e187bcca6b32b14698f9e97b43693da461f7bf3fb00d0466cfafd` | PE 配置 |
| `06-w2zm6kh14eqy8u6bo04p.js` | `captures/heimao-profile-js-20260629214639/06-w2zm6kh14eqy8u6bo04p.js` | `c0d45426a377e9179fa1a1aff9f8a56f49b132c86fc3968b3ed3a808f77a5abd` | LPE + 后渗透 + 数据窃取 agent 投递 |

远端当前返回的两个入口 JS 与本地样本 SHA256 一致。

## 3. 总览结论

这是完整的 iOS Safari/WebKit/JSC exploit + 信息窃取链。静态链路如下：

```text
Safari/WebKit/JSC RCE
  -> JS 层任意读写
  -> PAC/native call
  -> WebContent sandbox escape
  -> LPE/内核读写
  -> 注入 SpringBoard/configd/wifid/securityd/UserEventAgent
  -> 读取敏感文件
  -> 压缩、加密、POST 上报
```

当前远端配置默认目标是：

```text
photo-thumbnails, wechat-images, dcim-photos
```

因此当前投递版本重点是照片缩略图、微信图片、DCIM/PhotoData 照片。代码中同时存在 Keychain、keybag、Wi-Fi、iCloud、钱包 App 扫描能力，但这些能力是否执行取决于 `targetOnly` 或服务端配置。

## 4. Exploit 链关键位置

### 4.1 JSC/WebKit RCE 与 JS R/W

文件：`captures/heimao-profile-js-20260629214639/02-e13m4e5s4wwz2dhuasie.js`

| 行号 | 锚点 | 行为 |
| --- | --- | --- |
| 29 | `rce_offsets` | iPhone/iOS 版本 offset 表，覆盖多个 iPhone11 到 iPhone17 设备与 iOS 18.x build |
| 2744 | `class check_attempt` | RCE 入口类 |
| 2754 | `stage1()` | 构造 `addrof`、`fakeobj`、`read64`、`write64` 等 JS 层 primitive |
| 2851 | `parseFloat` executable | 解析 JSC 代码地址并定位 JSC Mach-O base |
| 2883 | `pthread_create_auth_stubs_offset` | PAC/native call 相关偏移 |
| 3246 | `JavaScriptCore__jitAllowList_once` | patch JSC JIT allowlist |
| 3252 | `stage2()` | Worker/globalScope handoff |
| 3407-3437 | Array prototype setter/splice | 触发对象布局异常与 OOB 相关 grooming |
| 3480 | `RCE success` | exploit 成功分支 |

### 4.2 Worker/native call/PAC 阶段

文件：`captures/heimao-profile-js-20260629214639/01-ouzpbnvq81qdf9zsjuvr.js`

| 行号 | 锚点 | 行为 |
| --- | --- | --- |
| 243 | `getJS(fname)` | 动态加载后续 JS chunk |
| 657 | `case 'setup_fcall'` | 建立 native function call 流程 |
| 690 | `slow_fcall_1` | 慢速 native call primitive |
| 703 | `slow_fcall_2` | 多参数 native call primitive |
| 727 | `slow_dlopen` | native `dlopen` 包装 |
| 733 | `slow_dlsym` | native `dlsym` 包装 |
| 739-743 | `slow_pacia/slow_pacib` | PAC 签名调用 |
| 788 | `pthread_create` | JOP/native call 线程 |
| 942-974 | `getpid/getuid/uname` | native 能力验证 |
| 981 | `ef1xrwkweuxfahzbwq47.js` | 加载 SBX0 |

### 4.3 沙箱逃逸与 PE 加载

文件：`captures/heimao-profile-js-20260629214639/03-ef1xrwkweuxfahzbwq47.js`

| 行号 | 锚点 | 行为 |
| --- | --- | --- |
| 16-20 | `mach_port_allocate`, `mach_make_memory_entry_64`, `mach_vm_map` | Mach primitive 函数解析 |
| 7058 | `SBX0()` | SBX0 主流程 |
| 8321 | `GPU R/W primitives established` | GPU/WebContent primitive 建立 |
| 8392 | `SBX0 complete` | SBX0 完成 |
| 8410 | `4rix9sr76vzh2rosrs86.js` | 加载 SBX1 |

文件：`captures/heimao-profile-js-20260629214639/04-4rix9sr76vzh2rosrs86.js`

| 行号 | 锚点 | 行为 |
| --- | --- | --- |
| 3 | `{{LPE_64BITE}}` | LPE/PE 占位与加载标识 |
| 4795-4817 | XPC/IOSurface symbols | XPC 与 IOSurface 相关函数解析 |
| 6613 | `com.apple.coremedia.mediaplaybackd.sandboxserver.xpc` | CoreMedia sandboxserver XPC endpoint |
| 6818 | `Spawning PE` | 启动 PE 阶段 |
| 6829 | `w2zm6kh14eqy8u6bo04p.js` | 默认 PE 模块路径 |
| 6832 | `72gs3bzug9jyomnt.json` | 读取 PE 配置 |
| 6839 | `getJS(pe_path...)` | 拉取 PE 主体 |

## 5. LPE 与权限准备

文件：`captures/heimao-profile-js-20260629214639/06-w2zm6kh14eqy8u6bo04p.js`

| 行号 | 锚点 | 行为 |
| --- | --- | --- |
| 1 | `__SERVER_CONFIG` | 服务端配置，包含 `aesKey`、`channelId`、`triggerType` |
| 1905/2471 | `runPE` | LPE/内核读写入口 |
| 6346 | `#PathDictionary` | 敏感路径字典 |
| 6474 | `sandbox_extension_issue_file` | 通过 launchd 签发 sandbox extension |
| 6482 | `sandbox_extension_consume` | 消费 sandbox extension |
| 6492 | `createTokens()` | 批量创建敏感路径 token |
| 6601 | `applyTokensForRemoteTask()` | 把 token 应用到远程任务 |
| 8335 | `targetProcess = "SpringBoard"` | 主 agent 注入目标 |
| 8356 | `runPE()` | 执行 PE/LPE |
| 8369 | RemoteCall `launchd` | 获取 launchd remote task |
| 8392 | `createTokens()` | 创建并消费敏感路径授权 |

敏感路径包括：

- `/private/var/Keychains/`
- `/var/Keychains/`
- `/private/var/keybags/`
- `/private/var/mobile/Library/Safari/`
- `/private/var/mobile/Library/Cookies/`
- `/private/var/mobile/Library/SMS/`
- `/private/var/mobile/Library/AddressBook/`
- `/private/var/mobile/Library/Notes/`
- `/private/var/mobile/Library/Health/`
- `/private/var/mobile/Library/Mail/`
- `/private/var/mobile/Library/Accounts/`
- `/private/var/mobile/Media/`
- `/private/var/mobile/Media/DCIM/`
- `/var/mobile/Media/DCIM/`
- `/private/var/mobile/Library/Mobile Documents/`

## 6. 子模块注入

文件：`captures/heimao-profile-js-20260629214639/06-w2zm6kh14eqy8u6bo04p.js`

| 行号 | 锚点 | 行为 |
| --- | --- | --- |
| 8215 | `keychain_copier.js` | Keychain/keybag 复制模块 |
| 8217 | `wifi_password_dump.js` | Wi-Fi 凭证 dump 模块 |
| 8219 | `wifi_password_securityd.js` | securityd 侧 Wi-Fi 凭证 dump |
| 8221 | `icloud_dumper.js` | iCloud dump 模块 |
| 8535 | `needsKeychain` | 根据配置判断是否启用 Keychain/keybag 分支 |
| 8537 | `needsWifi` | 根据配置判断是否启用 Wi-Fi 分支 |
| 8538 | `needsIcloud` | 根据配置判断是否启用 iCloud 分支 |
| 8543 | `keychainCopier` | 注入 `configd` |
| 8553 | `wifiDump` | 注入 `wifid` |
| 8561 | `wifiDumpSecurityd` | 注入 `securityd` |
| 8571 | `iCloudDumper` | 注入 `UserEventAgent` |
| 8593 | `agentPayload` | 注入最终数据收集 agent |

## 7. 内嵌 agent

内嵌 agent 位于：

```text
captures/heimao-profile-js-20260629214639/06-w2zm6kh14eqy8u6bo04p.js:8123
```

它是加密压缩 blob。外层解包位置：

| 行号 | 锚点 | 行为 |
| --- | --- | --- |
| 8471 | `CCCrypt` | AES 解密内嵌 agent |
| 8502 | `compression_decode_buffer` | LZMA 解压内嵌 agent |

解包后 agent 元数据：

```text
decoded_chars = 1393524
sha256 = deb9c4ff762227d2d5143d19da36f84784be2a241ab0b3359ee32db3869c5336
targetOnly = "photo-thumbnails","wechat-images","dcim-photos"
```

由于 agent 在原始 JS 中是一行加密 blob，下面使用“解包后字符偏移”作为审计锚点：

| 解包后偏移 | 锚点 | 行为 |
| --- | --- | --- |
| 18421 | `__PL_INJECTED={'aesKey'` | agent 配置、上报域名、channel、triggerType |
| 19382 | `const UPLOAD_PATH` | 上报路径 `/api/user/apply` |
| 19548 | `function getReportServer` | 上报域名选择 |
| 21833 | `const TARGET_ONLY` | 当前目标选择 |
| 36321 | `FORENSIC_FILES=[` | 常规敏感文件清单 |
| 47009 | `CRYPTO_WALLET_PATTERNS` | 钱包 App/关键词表 |
| 108044 | `function plBuildMultipartBody` | 构造 multipart/form-data |
| 110193 | `function plPreparePayload` | LZMA 压缩与 AES 加密 payload |
| 1309877 | `function sendFileCompat` | 文件上报包装 |
| 1343712 | `function _checkBIP39` | BIP39/敏感关键词检测 |
| 1364357 | `function scanWeChatImages` | 微信图片扫描 |
| 1379132 | `FORENSIC_FILES` 上传循环 | 常规文件收集与上报 |
| 1380524 | `dcimBase` | DCIM 照片扫描 |
| 1383402 | `photoDataBase` | PhotoData 图片扫描 |
| 1385639 | `thumbDirs` | 照片缩略图扫描 |
| 1387469 | `/tmp/icloud_dump` | iCloud dump 结果上传 |

## 8. 当前窃取行为

当前配置：

```text
targetOnly = ["photo-thumbnails", "wechat-images", "dcim-photos"]
```

静态判断当前默认执行重点：

- 扫描 `/var/mobile/Media/DCIM`
- 扫描 `/var/mobile/Media/PhotoData`
- 扫描 `/var/mobile/Media/PhotoData/Thumbnails/V2/DCIM`
- 扫描 `/var/mobile/Media/PhotoData/CPLAssets/group0`
- 查找微信 `com.tencent.xin` 容器
- 进入微信 `Documents/<32位md5>/Img` 目录
- 对图片进行筛选、可能转 HEIF/压缩，然后上报

全量能力还包括：

- Keychain/keybag：`keychain-2.db`、`persona.kb`、`usersession.kb`、`System.keybag` 等
- Wi-Fi 配置和 Wi-Fi 密码
- iCloud dump
- Safari/Cookies/SMS/通讯录/Notes/Health/Mail/Accounts
- 钱包 App 容器识别与文件扫描

但 Keychain、钱包、Wi-Fi、iCloud 等是否执行，取决于 `targetOnly` 是否为空或是否包含 `keychain`、`keybag`、`credentials`、`icloud`、`wallet` 等目标类别。

## 9. 上报行为

agent 的上报流程：

```text
读取目标文件
  -> 可选图片压缩/HEIF 转换
  -> LZMA 压缩
  -> AES 加密
  -> multipart/form-data
  -> HTTPS POST /api/user/apply
```

上报请求包含：

- `timestamp`
- `x-hash`，对应 channel
- `ver`
- `sdkv`
- 设备标识派生字段
- 文件名
- 文件类别
- 文件描述
- 文件 hash

旧上报路径还存在：

```text
/stats
```

## 10. 上报域名

解包后的 agent 中发现以下上报域名：

- `https://www.t9n-4kyowmn000x29.net`
- `https://www.bahft1obd6xeq4lkhnw.cfd`
- `https://www.x6dtqpkp0ap1kwjjmw3.com`
- `https://www.qo2q4wy7zl8soh28bz893kw.app`
- `https://www.8tr71yq6y7zcvncer3ph2t.net`
- `https://www.gz1frw0-27vco0fsr.cfd`
- `https://www.37r3a0psr99nbdoowiqx9r.cfd`
- `https://www.hup-3tf7vm29hm05c67g420w.online`
- `https://www.zuhf1uj0p8vw0w5g.icu`
- `https://www.cfaazfg2zb5s6-fhjfh5.site`
- `https://www.i-rfugh99xe7t1wbzmjqrk1y.site`
- `https://www.npapkk8r1fwor2r54iae.lol`
- `https://www.nvnx8kb3463-pdyazub.site`
- `https://www.e5wa9y7nu9w2l8hv.org`
- `https://www.u4r-ue67f-o4cmc6.so`
- `https://www.ew3m7tvqhlgbpng0v-2y76.so`
- `https://www.wpqsa5dxcljy074ljmqs.live`
- `https://www.jmturhw1odv3uuwh2slui.live`
- `https://www.fu8zmjp22v6asqd7m.app`
- `https://www.abmj1hh7hrtzbxqqe.store`

## 11. IOC

### 投递域名与路径

- `www.1b2a95ce13.cc`
- `/profile/ouzpbnvq81qdf9zsjuvr.js`
- `/profile/e13m4e5s4wwz2dhuasie.js`
- `/profile/ef1xrwkweuxfahzbwq47.js`
- `/profile/4rix9sr76vzh2rosrs86.js`
- `/profile/72gs3bzug9jyomnt.json`
- `/profile/w2zm6kh14eqy8u6bo04p.js`

### 上报路径

- `/api/user/apply`
- `/stats`

### 本地落点/临时文件线索

- `/tmp/darksword.log`
- `/tmp/keychain-2.db`
- `/tmp/persona.kb`
- `/tmp/usersession.kb`
- `/tmp/backup_keys_cache.sqlite`
- `/tmp/wifi_passwords.txt`
- `/tmp/wifi_passwords_securityd.txt`
- `/tmp/icloud_dump`

## 12. 与初始判断对照

| 初始判断 | 静态分析结论 |
| --- | --- |
| Safari/WebKit/JSC 内存损坏拿 JS read/write | 确认 |
| 绕过 PAC 拿 native call 能力 | 确认 |
| 逃出 WebContent 沙箱 | 确认 |
| 内核提权拿 root | 确认到 LPE/内核读写/系统进程注入能力 |
| 拖走 Keychain + 钱包数据 | 能力存在；当前配置默认主打照片、微信图片、DCIM 照片 |

## 13. 风险评级

风险等级：严重。

理由：

- 不是普通落地页或统计脚本，而是完整 exploit chain。
- 具备 WebKit/JSC exploit、PAC/native call、沙箱逃逸、LPE/内核读写能力。
- 具备系统进程注入能力。
- 具备敏感文件 token 签发/消费能力。
- 内嵌 agent 具备加密上报、域名轮换、目标类别控制和多类数据收集能力。
- 当前配置已明确启用照片/微信图片/DCIM 图片收集。

## 14. 防御建议

- 在网络侧阻断 `www.1b2a95ce13.cc` 及第 10 节列出的上报域名。
- 检查代理、DNS、网关、EDR 日志中是否出现 `/profile/*.js`、`/api/user/apply`、`/stats`。
- 在疑似受影响 iOS 设备上重点核查异常 Safari 访问记录、异常耗电/发热、短时间大量外联、照片库访问痕迹。
- 关注是否存在访问 `Keychains`、`keybags`、`PhotoData`、`DCIM`、微信容器路径的异常迹象。
- 对涉及设备做隔离、备份取证、系统升级和账号凭证轮换。
- 如果出现 Keychain/keybag/Wi-Fi/iCloud 分支命中迹象，应按凭证泄露事件处理。
