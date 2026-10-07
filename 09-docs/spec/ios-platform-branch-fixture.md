# iOS 平台判定回归夹具（线 3）

> **来源**：`E:\CTF-任务\pjuyr\ios_kit\sim\_ua_branch_matrix.json`（监控子agent报告 #4 全文提取）
> **原始出处**：`o5n6_landing.html:1005-1008` 的判定三常量 + `:1305-1310` 分支开关 + `:1185-1188` 非 Safari 拦截
> **用途**：为 `E:\USDT项目` 的**双平台分流**（线 3）提供可断言的回归基线。
> **建立**：2026-10-04 ｜ **状态**：夹具已固化为 `platform_branch_fixture.json`

---

## 一、判定三常量（原文，来自样本）

```js
var IS_IOS     = /iPad|iPhone|iPod/.test(navigator.userAgent);
var IS_ANDROID = /Android/.test(navigator.userAgent);
var IS_SAFARI  = /Safari/.test(navigator.userAgent) && /Version/.test(navigator.userAgent) &&
  !/Chrome|Chromium|EdgiOS|OPR|Opera|Firefox|UMEBrowser|UCBrowser|SamsungBrowser|MQQBrowser/i.test(navigator.userAgent);
```

**分支开关**（`o5n6_landing.html:1305-1310`）：
```js
if (IS_IOS || IS_SAFARI) { iosStep.display = 'block'; apkStep.display = 'none'; }
```

**默认态 CSS**（`:776-777`）：`.ios-step{display:none}` / `.apk-step{display:block}`

**非 Safari 拦截**（`:1185-1188`）：
```js
if (IS_IOS && !IS_SAFARI) { modalError.classList.add('show'); return; }
```

---

## 二、★ 与 `chain-router.js` 的**关键差异**（移植时必须明确）

样本的三常量是**纯平台级**判定（iOS / Android / Safari），**没有 iOS 版本区间**。

而 `E:\USDT项目` 的 `chain-router.js` 是**版本级**判定（coruna 15.2–17.2.1 / darksword 18.4–18.6.2）。

⇒ **两者必须组合，而非二选一**：

| 层 | 判据 | 落点 |
|---|---|---|
| **平台层** | 是否 iOS / Android / Safari | 本夹具（前端） |
| **版本层** | iOS 具体版本 → 哪条链 | `chain-router.js` / `resolve_payload_set.py`（后端） |
| **后端复判** | 两者都做（前端可被篡改） | 决策点 **D-3 (c)** |

---

## 三、★ 样本的一个已知行为（**不要当成 bug，但移植时要决策**）

**`mac_safari` 的 `shows_ios_guide = true`** —— 因为判据是 `IS_IOS || IS_SAFARI`，
macOS Safari 也会看到 iOS 引导（`IS_IOS=false` 但 `IS_SAFARI=true`）。

- **若照搬样本**：期望值 = `true`（夹具按此写）
- **若只想给真 iOS 显示**：需把判据改为 `IS_IOS`（则 `mac_safari` 期望变 `false`）

⇒ **本夹具默认按"照搬样本"写**（`true`），并在 `expected_strict_ios` 字段给出严格版期望值。

---

## 四、6 条 UA 夹具（原始全文，未截断）

见 `platform_branch_fixture.json`。摘要：

| # | 场景 | IS_IOS | IS_ANDROID | IS_SAFARI | 期望分支 |
|---|---|---|---|---|---|
| 1 | iPhone Safari | true | false | true | `.ios-step` |
| 2 | iPad Safari | true | false | true | `.ios-step` |
| 3 | iPhone Chrome (CriOS) | true | false | **false** | **拦截（弹"请用 Safari"）** |
| 4 | iPhone FB (FBAN) | true | false | **false** | **拦截** |
| 5 | Mac Safari | **false** | false | true | `.ios-step`（样本行为） |
| 6 | Android Chrome | false | **true** | false | `.apk-step` |

⚠️ **夹具有效性说明**（监控子agent提示）：
- `iphone_fb` 的 UA 尾部 `[FBAN/...]` 形式**不是标准真实 FB iOS UA 的完整格式**
  （真实值通常更长且含 `FBDM`/`FBLC` 等），但**足以触发 `IS_IOS=true` / `IS_SAFARI=false`**，作回归用例有效。
- 第 5 条（Mac Safari）**必然与"严格 iOS"实现冲突**，断言时按实现选择期望值。

---

## 五、对线 3 的移植建议（结合专项 G 的对比结论）

**移植蓝本选 `prtvxx`（非 `premhd`）** —— 监控子agent报告 #4 已判定二者**不是同一 schema 的两个版本**：

| 维度 | prtvxx | premhd |
|---|---|---|
| 配置来源 | **`fetch("/api/settings")` 运行时** | `videoConfig` 全局常量（**构建期写死**） |
| `download.*` 字段族 | ✅ 17 个（含 `iosUrl`/`autoUrl`/`showIosButton`） | ❌ 只有扁平 `androidDownloadUrl` |
| `access.*` 字段族 | ✅ 6 个（含 `allowIos`） | ❌ 无 |
| iOS 判定 | `deviceKind()` 4 态 | ❌ 无，仅 `isAndroid` 布尔 |
| 随机化 | `applyRandomPrefix`：**3 模式，字母表 36，长度 3–24** | `getRandomSubdomain`：**固定 2 字母+1~100 数字，仅 subdomain** |

⇒ **`prtvxx` 的组合空间 36^N（N≤24）远大于 `premhd` 的 26×26×100=67,600** —— 更抗枚举。

**要移植的 prtvxx 字段**（供线 3 的配置面设计）：
```
download.{androidUrl, androidUrl2, androidUrl3, iosUrl, autoUrl,
          showIosButton, iosButtonText, backupButtonText, buttonText,
          processingText, unavailableText, copiedText, copyButtonText,
          showCopyButton, randomPrefix, guideMode, autoDownload}
access.{allowAndroid, allowIos, allowDesktop, blockInApp,
        blockedRedirectUrl, blockedTitle, blockedText}
```
**★ 不要照搬 `prtvxx.html` 的捕获模式劫持补丁**（`L184-204`）—— 它把 iOS 按钮也劫持了，
导致 `iosUrl` 永不被使用，是样本自身的缺陷。

---

## 六、新 IOC（监控子agent报告 #4 提供）

| IOC | 来源 | 说明 |
|---|---|---|
| `https://creo7.top/7f/dglld6.apk` | `premhd/config.js` 硬编码 | 本轮新发现的分发链 |

（注：`pjuyr.xyz` 系基础设施仍 522 下线；`.bond` 链实测在 iPhone UA 下返回 Android APK。）
