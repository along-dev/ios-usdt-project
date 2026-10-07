# 04-landing/reference —— 源侧参照素材（非投递产物）

## 一、本目录是什么

本目录存放的是 **H5 源素材原件**，用途仅为 **参照 / 对照 / 溯源**。

> **本目录不是投递产物（deliverable），不得作为交付内容对外投递，也不得被构建流程引用。**

## 二、投递产物在哪里

实际的投递产物在以下两个目录，与 `reference/` **严格分离**：

| 类别 | 路径 | 文件数 |
|---|---|---|
| 投递产物 · 模板 | `04-landing/templates/` | 53 |
| 投递产物 · 资源 | `04-landing/assets/` | 53 |

另有已验收的运行时脚本：`04-landing/runtime/landing-runtime.js`（F1-C5 已验收）。

## 三、两者不得混用

- `reference/` 与 `templates/`、`assets/` **禁止互相覆盖、禁止混用、禁止交叉引用**。
- `reference/` 内的文件 **不参与** 构建、打包、投递、哈希清单（`_manifest.sha256`）。
- 若需要调整投递产物，请直接改 `templates/` / `assets/`，**不要**从 `reference/` 反向同步或覆盖。

## 四、内容构成

| 子目录 | 源路径 | 文件数 | 体积 |
|---|---|---|---|
| `reference/code/` | `E:\ios漏洞\pjuyr\code\` | 113 | 4.04 MB (4,238,781 B) |
| `reference/all_assets/` | `E:\ios漏洞\pjuyr\all_assets\` | 150 | 91.97 MB (96,432,618 B) |
| **合计** | — | **263** | **96.01 MB** |

- `code/` —— 落地页 H5 源码（含 `pjuyr_code/` 子树）。
- `all_assets/` —— H5 资源（模板 / 图片 / JS / CSS）。

复制为 **递归整体复制，保持原目录结构**，未做任何内容改写、裁剪或重命名。

## 五、重复情况说明（重要）

经 SHA-256 逐文件比对，`reference/` 的 263 个文件中，有 **214 个** 与 `templates/` + `assets/` 的投递产物 **内容完全一致**（字节级重复）。

- 这说明源素材与投递产物高度同源，属预期现象。
- 该重复 **仅为事实记录**，本目录 **未删除任何文件**，投递产物侧也 **未做任何改动**。
- 重复文件 **不构成第二份交付物**，投递时只认 `templates/` 与 `assets/`。

## 六、生成时刻与来源

- **生成时刻**：以本 `README.md` 文件自身的文件系统修改时间戳为准（executor 实测写入 `2026-09-29`，本行不硬编码为唯一依据）
- **源侧路径**（只读素材，本卡未修改源侧任何内容）：
  - `E:\ios漏洞\pjuyr\code\`
  - `E:\ios漏洞\pjuyr\all_assets\`
- **目标路径**：`E:\USDT项目\04-landing\reference\`

## 七、约束声明

本次操作 **未触碰** 以下文件/目录：

- `04-landing/templates/**`（投递产物，未改）
- `04-landing/assets/**`（投递产物，未改）
- `04-landing/runtime/landing-runtime.js`（F1-C5 已验收，未改）
- `_manifest.sha256`（未改）
- `E:\ios漏洞\pjuyr\**`（只读源素材，未改）
