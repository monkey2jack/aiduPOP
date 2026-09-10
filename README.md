# aiduPOP⚕爱嘟泡波卡 — Hermes Agent 飞书泡波卡

<p align="center">
  <img src="docs/images/aidupop-banner-wide.jpg" alt="aiduPOP 爱嘟波泡卡 · 泡波样式横幅" width="100%">
</p>

> **泡波样式（Bubble Wave）——够灵动，够透明，够治愈**
>
> **不只是卡片 — 是对话本身。**

```
简洁不是少放东西，而是每一个元素都有存在的理由；
透明不是打印日志，而是让你看清 AI 每一步在想什么；
美不是装饰，而是信息该在的位置，刚好在那里。
```

[![Version](https://img.shields.io/badge/dynamic/yaml?url=https%3A%2F%2Fraw.githubusercontent.com/monkey2jack/aiduPOP/main/plugin.yaml&query=%24.version&label=version&color=brightgreen)](https://github.com/monkey2jack/aiduPOP)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-yellow.svg)](https://www.python.org/)
[![Built on hermes-lark-streaming](https://img.shields.io/badge/built%20on-hermes--lark--streaming-orange.svg)](https://gitee.com/Aowen-Nowor/hermes-lark-streaming)
[![Aidu](https://img.shields.io/badge/aiduPOP-⚕️爱嘟泡波卡-ff69b4.svg)](https://github.com/monkey2jack/aiduPOP)

**中文** | **[📖 English](README_EN.md)**

<!-- distribution-policy: github-source-only -->
> **分发说明（GitHub/Gitee）**：aiduPOP 不再通过 PyPI 或 GHCR 发布和维护安装包。请使用 Hermes 插件从 GitHub/Gitee 安装；源码目录中的本地开发安装仅用于开发与测试。

---

## aiduPOP 是什么？

**aiduPOP⚕爱嘟泡波卡**是 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的飞书泡波卡插件 —— 让 AI 的回答和思考过程在飞书里实时、清晰、优雅地呈现。

**aiduPOP 是一个独立项目**（不是上游的 fork 镜像）—— 起源并致谢 [Aowen-Nowor/hermes-lark-streaming](https://gitee.com/Aowen-Nowor/hermes-lark-streaming) v1.6.0，在其代码基础之上做了一套完整的**泡波样式（Bubble Wave）改造**：

| 层级 | 做什么 | 核心特性 |
|------|--------|----------|
| 🫧 **泡波** | 出厂即萌化视觉 | v2.2.0 主题层：工具 emoji、思考波浪 🌊、统计气泡 🫧✨，零配置开箱即用 |
| ⚡ **即时** | 第一个 token 就见卡片 | 无「正在输入」提示，无「回复：」狗皮膏药 |
| 🎨 **可视化配置（v2.3.0 新增）** | 挑 emoji / 排布 panel 与 footer 不改代码 | `aidupop studio` 打开可视化工作坊，所见即所得预览飞书卡片，保存后 `/aowen config reload` 生效 |
| 💠 **极简** | 每个元素都有理由 | Answer 在上、Panel 在下，footer 默认清空 |
| 🚦 **状态** | 一眼看清结果 | 绿色完成 / 红色中止 / 黄色报错，颜色编码 |
| 🔍 **透明** | 看清 AI 每一步 | 可展开面板：思考轮次、工具调用、时间戳 |
| 🃏 **交互** | 卡片里直接回答 | 原生 Cardsuit 2.0 clarify 选项卡 + 回调 |
| 🛡️ **韧性** | 失败不掉回纯文本 | Phase 2 原子回滚补救、卡片重建自动重试 |

> 🫧 泡波样式 · 爱嘟波泡卡 —— 让 AI 的每一步思考，都像水面上的泡泡一样清澈可见

---

## 架构

```
┌──────────────────────────────────────────────────┐
│        aiduPOP⚕爱嘟泡波卡                      │
│         Lark (Feishu) Cardsuit 2.0 Streaming     │
├──────────────────────────────────────────────────┤
│  cardkit/     → 卡片渲染引擎（元素、模板）        │
│  controller/  → 线性控制器 + card_id 追踪         │
│  patching/    → 爱嘟定制（模型显示、Phase 2）     │
│  state/       → 流式状态机                        │
│  flush/       → 节流刷新与批量更新                │
│  feishu/      → 飞书 API 客户端                   │
├──────────────────────────────────────────────────┤
│  Hermes Agent 插件钩子（platform_registry）       │
│  aiduMEM 持久记忆（消除上下文焦虑）               │
└──────────────────────────────────────────────────┘
```

---

## 🖼️ 效果展示

### 1. 即时响应

<p align="center">
  <img src="assets/screenshots/01-instant-response.png" width="600" alt="即时响应">
</p>

> **没有「正在输入...」提示，没有「回复：...」狗皮膏药。** 泡波卡即时出现，从第一个 token 开始实时渲染。开箱即享纯正机械打字机（Typewriter）逐字输出效果，敲字频率高达 15ms，没有飞书的 UI 噪音，只有纯粹流畅的对话。

---

### 2. 完成状态 — 绿色面板

<p align="center">
  <img src="assets/screenshots/02-panel-completed.png" width="600" alt="完成状态">
</p>

> **Answer 在上，Panel 在下。** 绿色边框的面板一目了然：模型名称、思考轮次、工具调用、耗时。简洁、美观、信息明确。由 **aiduMEM** 持久记忆加持，消除上下文焦虑。面板支持完全自定义。

---

### 3. 中止/报错状态 — 红色面板

<p align="center">
  <img src="assets/screenshots/03-panel-stopped.png" width="600" alt="中止状态">
</p>

> **颜色编码状态。** 当生成被中止或出错时，面板边框自动变色 — **红色=中止**，**黄色=报错**。一眼就知道状态，无需阅读小字。

---

### 4. 展开面板 — 完整追踪

<p align="center">
  <img src="assets/screenshots/04-panel-expanded.png" width="600" alt="展开面板">
</p>

> **点击展开。** 查看完整的推理追踪 — 每一轮思考、每一次工具调用，附带时间戳。透明是设计原则。没有隐藏的魔法，没有多余的 footer。只在你需要时，提供你需要的信息。

---

### 5. Clarify — 交互式选项卡（Cardkit 2.0）

<p align="center">
  <img src="assets/screenshots/05-clarify-options.png" width="600" alt="Clarify 选项">
</p>

> **原生飞书 Cardkit 2.0 集成。** 当 AI 需要澄清时，直接在对话中呈现交互式选项卡。从下拉菜单选择或输入答案 — 无需切换上下文。

---

### 6. Clarify — 回调与继续

<p align="center">
  <img src="assets/screenshots/06-clarify-callback.png" width="600" alt="Clarify 回调">
</p>

> **无缝回调。** 选择完成后，Agent 收到回调并继续工作。Clarify 卡片更新显示你的选择和确认徽章。简洁、快速、原生。

---

## 🚀 快速开始

### 前置要求

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) 已安装
- 飞书（Lark）机器人已配置
- Python 3.11+

### 安装

方式一 · 作为 Hermes 目录插件（GitHub，推荐）：

```bash
git clone https://github.com/monkey2jack/aiduPOP.git
cp -r aiduPOP ~/.hermes/plugins/hermes-lark-streaming
hermes gateway restart
```

中文用户指南（更新 / 卸载 / 命令 / 配置 / 凭据）见 [docs/USER_GUIDE.md](docs/USER_GUIDE.md)。

### 配置

插件使用与上游 `hermes-lark-streaming` 相同的配置。爱嘟定制部分详见 [docs/CUSTOMIZATIONS.md](docs/CUSTOMIZATIONS.md)。

#### PC / 手机端差异化字号

可在 Hermes 的 `config.yaml` 中按角色设置单一字号，或分别设置 PC、手机和旧客户端兜底字号：

```yaml
hermes_lark_streaming:
  text_sizes:
    body:
      default: normal
      pc: normal
      mobile: large
    panel: notation
    notice:
      default: notation
      pc: notation
      mobile: normal
```

- `body`：AI 回答正文
- `panel`：思考、工具调用和底部统计面板
- `notice`：折叠等提示信息
- 每个角色既可直接填写一个字号，也可填写 `default` / `pc` / `mobile` 设备映射
- 未配置时保持 aiduPOP 现有 `normal_v2` / `notation` 视觉，不影响老用户
- 修改后执行 `/aowen config reload` 或重启 Hermes 网关

可配置字号严格使用飞书 CardKit 官方枚举，包括 `normal`、`notation`、`small`、`x-small`、`medium`、`large`、`x-large` 及官方标题字号。`normal_v2` 只作为 aiduPOP 未配置时的历史默认保留，不用于新配置。无效角色、设备字段或字号会明确报错，不会静默生成异常卡片。

版本号唯一来源是 `plugin.yaml` 的 `version` 字段，`setup.py` / `__init__.py` 动态读取，不会出现多处版本不一致。

---

## 🎨 可视化配置工作坊（v2.3.1 · 可选）

不想手写 YAML？`aidupop studio` 提供一个**纯本地、零第三方依赖**的可视化配置工作坊，让你像挑贴纸一样调整泡波卡外观。

> 🏆 **全网首创**：aiduPOP 是首个为 Hermes Agent 飞书流式卡片插件打造「可视化配置工作坊」的开源项目——纯本地运行、零第三方依赖、内置 1:1 CardKit 2.0 实时仿真预览，改完即见，无需触碰一行代码。

<p align="center">
  <img src="assets/screenshots/07-visual-card-studio.png" width="860" alt="Visual Card Studio 可视化配置工作坊">
  <br>
  <sub>Visual Card Studio 工作坊：品牌区 / 一键预设 / 工具 Emoji 配置 / 1:1 飞书卡片实时预览，保存后 <code>/aowen config reload</code> 生效</sub>
</p>

```bash
aidupop studio                 # 默认 127.0.0.1:8765，自动打开浏览器
aidupop studio --port 8770     # 指定端口
aidupop studio --no-browser    # 不自动打开浏览器
# 或：python -m hermes_lark_streaming studio
```

能配什么：

- **工具 Emoji**：13 个工具图标（读/写/搜/执行/浏览器/子代理…）逐项「当前 → 替换」，手动输入或点选，仅接受 Emoji
- **Panel 统计栏**：模型前缀、轮次、工具数、耗时图标与分隔符
- **Footer 矩阵**：勾选 `model` / `tokens` / `elapsed` / `status` / `context` 的行列排布与标签开关
- **流式与字号**：面板默认展开、打字机步长、刷新节流、CardKit 2.0 字号
- **一键预设**：泡波样式 / 经典工作流 / 极简极客，随时一键换肤或重置
- **所见即所得预览**：内置 1:1 飞书 CardKit 2.0 卡片仿真，改动实时重绘

保存后：写入 `~/.hermes/config.yaml`（先备份、原子写回）。网关是独立进程，在飞书群发送 `/aowen config reload` 或重启网关后，新卡片即按新配置渲染。

安全设计（面向开源用户）：

- 仅监听回环地址（loopback-only），拒绝非本机 `Host` 请求，无通配 CORS，防 CSRF / DNS-rebinding
- 只深合并 UI 管理的键，`feishu` 凭证与其它自定义键**原样保留、绝不覆盖**
- 现有配置无法解析时**拒绝写入**并报错，先备份再原子写回（`~/.hermes/backups/`）
- 服务端复核 Emoji 取值与结构，非法请求返回 400

> 这是**可选工具**：默认生产环境不使用；开源用户按需启用即可。

---

## 🔧 定制说明

相对上游 v1.6.0 的完整定制清单详见 [docs/CUSTOMIZATIONS.md](docs/CUSTOMIZATIONS.md)，版本演进见 [docs/CHANGELOG.md](docs/CHANGELOG.md)。

### 核心特性

- **🫧 泡波样式** — 出厂即萌化视觉，emoji 工具图标 + 水波气泡意象，`aidupop studio` 可视化自定义
- **💠 极简设计** — 简洁美观，没有多余元素
- **⚡ 即时响应** — 没有「正在输入」提示，卡片即时出现
- **🚦 颜色编码面板** — 绿色（完成）、红色（中止）、黄色（报错）
- **🔍 透明追踪** — 可展开面板，显示完整推理和工具调用
- **🤔 aiduMEM 集成** — 持久记忆消除上下文焦虑
- **🃏 Cardsuit 2.0** — 原生飞书交互式 clarify 卡片
- **🛡️ Phase 2 保护** — API 失败时自动回滚补救
- **📊 模型显示** — 稳定的模型名称显示，不会闪烁

---

## 📦 项目结构

```
aiduPOP/
├── cardkit/           # 卡片渲染引擎
├── controller/        # 线性控制器 & card_id 追踪
├── patching/          # 爱嘟定制（模型显示、Phase 2）
├── state/             # 流式状态机
├── flush/             # 节流刷新
├── feishu/            # 飞书 API 客户端
├── config/            # 配置解析
├── assets/            # 截图 & 静态资源
├── tests/             # 测试套件
├── plugin.yaml        # 插件配置（版本唯一来源）
└── ...
```

---

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解贡献指南。

---

## 📄 许可证

本项目基于 MIT 许可证 — 详见 [LICENSE](LICENSE)。

---

## 🙏 致谢

- **上游**：[Aowen-Nowor/hermes-lark-streaming](https://gitee.com/Aowen-Nowor/hermes-lark-streaming) v1.6.0
- **上游作者**：Aowen (敖文)
- **框架**：[Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research
- **定制**：aidu

---

<p align="center">
  <sub>用 💕 制作 by aidu</sub>
</p>

## CHANGELOG

### v2.3.2 (2026-08-21) — 爱嘟波泡卡 · 稳定性与可观测性加固

* 🛡️ **冷启动流式防丢失**：`hermes_adapter` 与 `__init__` 探测逻辑对齐，冷启动期间接收首条消息时同步执行补丁加载，彻底根除冷启动 60s 窗口内偶发降级纯文本的问题。
* 🌊 **长间隙节流优化**：`flush` 阈值 `LONG_GAP_MS` 由 1.0s 放宽至 2.0s，大幅降低上游 LLM 抖动重试时的误切段概率。
* 🔄 **卡片瞬态错误重试补全**：将飞书 CardKit `300309` (streaming_closed) 与 `300317` (sequence_conflict) 纳入瞬态自动重试；`300315` 细分非法属性告警，防止卡片意外回退。
* 📊 **可观测性增强**：监控面板新增「纯文本回退」独立统计格，异常降级实时透明可查。

### v2.3.1 (2026-08-17) — 爱嘟波泡卡 · Studio 审计修复（配置安全与如实文案）

* 🐛 **text_sizes 非法值写入致卡片全灭修复（P0）**：Studio 前端默认字号 `normal_v2` 不在运行时 CardKit 2.0 白名单内，保存后网关建卡抛 `ValueError`、所有消息静默失去流式卡片。服务端新增逐值白名单校验、非法即拒写；前端字号改为下拉框（仅官方字号 +「默认」= 不写入）。
* 📢 **文案如实化（P1）**：`Config().reload()` 仅刷新 Studio 自身进程缓存，网关需 `/aowen config reload` 或重启后生效——toast、按钮与 README 全部改为如实描述。
* 🛡️ **前端 XSS 加固（P2）**：所有动态配置值经 `escapeHtml()` 转义后再进 DOM。
* 🧹 **备份轮转（P3）**：配置备份仅保留最近 20 份，不再无限堆积。
* 🔒 **脱敏补漏**：移除 v2.3.0 新增代码中遗留的内部称呼。
* 🧪 **测试**：`test_v230_studio.py` 新增 5 项（text_sizes 白名单回归守卫、端到端拒写保原文件、备份轮转），全量测试通过。

### v2.3.0 (2026-08-17) — 爱嘟波泡卡 · 可视化配置工作坊（Visual Card Studio）

* 🎨 **可视化配置工作坊 `studio/`**：新增 `aidupop studio` 命令，启动纯本地零第三方依赖的 Web 工作坊。可视化配置工具 Emoji、Panel 统计栏、Footer 矩阵、流式与字号，内置 1:1 飞书 CardKit 2.0 卡片实时仿真预览（所见即所得），品牌视觉对齐 aiduMEI（纯白纸底 + 深蓝点睛 + 三原色随机六边形背景 + 双侧 slogan）。
* ⚡ **保存即热生效**：写入 `~/.hermes/config.yaml` 后触发 `Config().reload()`，秒级生效、无需重启网关；亦提供尽力而为的 `systemctl` 重启入口（如实回报结果）。
* 🛡️ **安全加固（面向开源）**：仅监听回环地址并校验本机 `Host`（防 CSRF / DNS-rebinding），去除通配 CORS；POST 结构与 Emoji 取值服务端复核。
* 🔒 **配置零丢失**：只深合并 UI 管理的键，`feishu` 凭证及 `print_strategy`、`reactions`、用户自定义键原样保留；现有配置无法解析时拒绝写入并报错，先备份、后原子写回。
* 🧪 **测试**：新增 `tests/test_v230_studio.py`（22 项），覆盖深合并保配置、读失败拒写、payload/Emoji 校验、Host 门禁、静态资源与无 Header 残留；全量测试通过。
* 🏗️ **纯增量不改核心**：Studio 为独立可选模块，默认生产环境不加载；泡波样式与五大结构定制守卫全部不动。

### v2.2.1 (2026-08-16) — 爱嘟波泡卡 · 工程卫生加固

* 🐛 **异常吞没可观测性**：15 处裸 `except Exception: pass` 全部治理——12 处核心路径补 `_logger.debug(..., exc_info=True)` 上下文日志，3 处脚本路径补 safe-to-ignore 注释说明，生产静默失败从此可排查。
* ⏱️ **脚本 HTTP timeout 补齐**：`scripts/notify_feishu.py` 的 `urlopen` 补 `timeout=60`，与 `create_release.py` 对齐，杜绝 CI 通知卡线程。
* 📄 **文档版本同步**：README 徽章 / CHANGELOG 与 `plugin.yaml` 单一真相源对齐（修复 v2.2.0 发布流程遗留的文档漂移）。
* 🏗️ **纯加固不改结构**：零触碰 `_model_cache`、贝氏防爆、长文切片、`batch_update` 原子回滚、controller↔patching 延迟导入等稳定核心；泡波样式与五大结构定制守卫不变。

### v2.2.0 (2026-08-16) — 爱嘟波泡卡 · 泡波样式主题化

* 🎨 **泡波样式主题层 `cardkit/theme.py`**：新增 `BUBBLE_WAVE` 出厂默认主题 + `get_theme()` 深度合并机制（配置键 `hermes_lark_streaming.theme` 覆盖）。零配置开箱即用泡波视觉，进阶用户可覆盖任意图标/文本而不改源码。
* 🧰 **工具图标全面 emoji 化**：13 个工具描述符从飞书官方 token 替换为泡波 emoji 图标群（👩🏻‍🏫/👩🏻‍🎨/👩🏻‍💻/🕵🏻‍♀️/👩🏻‍🔬/👮🏻‍♀️/🥷🏻/👷🏻‍♀️/👩🏻‍⚖️/👩🏻‍🎓/🤹🏻‍♀️），`is_emoji_icon()` 分类器智能分流 emoji/token 渲染路径。
* 💬 **i18n 文本泡波化**：5 处中文文本键萌化（`processing_prefix`→`⚕Hermesing…`、`agent_process`→`🫧`、`rounds`→`🫧{}`、`tools_count`→`✨{}`、`round_n`→`第 {} 波`），英文键保持不动。
* 🐛 **工具别名漏配修复**：补齐嘟嘟 Hermes 0.20 真实工具名别名（terminal/execute_code/read_file/patch/search_files/web_extract/browser_exec/delegate_task/vision_analyze/skill_view 等），杜绝 terminal 误显兜底 emoji；移除裸 `search` 前缀歧义别名。
* 🧪 **v2.2.0 锁定测试**：新增 `tests/test_v220.py`，逐字断言泡波决策 + 嘟嘟五大结构定制守卫（无 header / 无 reaction 拦截 / answer 在 panel 之上 / panel 默认收起 / 无 footer）。
* 🏗️ **纯换皮不改结构**：仅触碰 i18n/tooluse/elements/adapter 的图标与文本，零触碰 `_model_cache`、贝氏防爆、长文切片、`batch_update` 原子回滚等稳定核心。

完整版本历史见 [docs/CHANGELOG.md](docs/CHANGELOG.md)。

### v2.1.3 (2026-08-14)

* 🐛 **Hermes CLI 导入死锁根治 (P0)**：修复 `model_tools` 模块级导入与后台插件发现线程之间的 Python `import_lock` 死锁。将 `apply_patches()` 改为异步守护线程延迟执行，彻底消除 `hermes` CLI 终端启动卡死。
* 🏷️ **飞书品牌表述统一**：中英文名称统一为 “Lark (Feishu)”。
* 📱 **设备差异化字号 (Issue #4)**：新增 `hermes_lark_streaming.text_sizes`，支持 PC 与手机端差异化字号。

### v2.1.2 (2026-08-07)

这是 本次的补丁版本，英文名称与卡片视觉保持不变。

* 修复长任务在 Phase 2 / Phase 3 增量更新时可能先于最终安全网触发飞书 `300305` 元素超限的问题；所有面板路径统一预留回答与 loading 元素预算，并在发送前裁剪早期推理/工具记录。
* 修复 24,000 字以上回答调用未导入 `_split_long_text` 导致的隐藏 `NameError`。
* 修复 message/anchor 双键导致的活动会话重复计数和跨话题错误封卡，并为过期 Clarify 卡片恢复 Hermes 原生回退路径。
* 恢复表格扫描兼容接口，收口测试包名、异步任务清理与 885 项回归测试。
* 加固发布链路：候选代码先测试后推送（Docker 发布管道已随 GHCR 停止分发退役）。

完整版本历史见 [docs/CHANGELOG.md](docs/CHANGELOG.md)。

### v2.1.0 (2026-08-05)
* 🛡️ **Markdown 防爆引擎**: 吸收并融合贝氏卡片的高级安全降级机制，彻底根治飞书卡片 `300314` (格式错误) 与 `200860` (卡片过载) 的死穴。
* 📊 **无损表格降级 (Compact Mode)**: 当卡片中 Markdown 表格数量超出飞书单卡限制 (最大 5-20 个) 时，不再粗暴转为代码块，而是无损压扁为带有黑体子标题和字段列表的 `Table N · Row M` 形式，彻底杜绝复杂表格引发的崩溃。
* ✂️ **智能长文断层保护**: 当内容超过飞书安全红线 (24KB+) 触发截断时，算法将智能回退至段落或闭合符边缘，严密保护 Markdown 代码块围栏 (` ``` `) 以及行内变量 (\` \`)，坚决杜绝代码块“腰斩”与排版错乱。
* 💎 **aiduPOP 核心守护**: 所有截断与降级拦截均在底层 (`md.py` 与 `linear_mixin.py` 的最后一公里) 进行，0 侵入，0 UI 改变，完美保持 aiduPOP 定制的 `_model_cache` 及 (⚕️💭🛠️⏱) 原生布局。
