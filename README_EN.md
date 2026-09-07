# aiduPOP⚕爱嘟泡波卡 — Hermes Aidu Streaming Card

> **Bubble Wave style — lively enough, transparent enough, soothing enough.**
>
> **Not just a card — the conversation itself.**

```
Clean is not putting less on screen, but every element having a reason to exist;
Transparent is not dumping logs, but letting you see what the AI is thinking at each step;
Beautiful is not decoration, but the right information being exactly where it belongs.
```

[![Version](https://img.shields.io/badge/dynamic/yaml?url=https%3A%2F%2Fraw.githubusercontent.com/monkey2jack/aiduPOP/main/plugin.yaml&query=%24.version&label=version&color=brightgreen)](https://github.com/monkey2jack/aiduPOP)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-yellow.svg)](https://www.python.org/)
[![Built on hermes-lark-streaming](https://img.shields.io/badge/built%20on-hermes--lark--streaming-orange.svg)](https://gitee.com/Aowen-Nowor/hermes-lark-streaming)
[![Aidu](https://img.shields.io/badge/aiduPOP-⚕️爱嘟泡波卡-ff69b4.svg)](https://github.com/monkey2jack/aiduPOP)

**[📖 中文文档](README.md)** | **English**

<!-- distribution-policy: github-source-only -->
> **Distribution (GitHub/Gitee):** aiduPOP no longer publishes or maintains packages on PyPI or GHCR. Install it as a Hermes plugin from GitHub/Gitee. Local editable installs from a cloned source tree are for development and testing only.

---

## What is aiduPOP?

**aiduPOP⚕爱嘟泡波卡** is a streaming card plugin for [Hermes Agent](https://github.com/NousResearch/hermes-agent) on Feishu/Lark — rendering the AI's answer and reasoning process in real time, clearly and elegantly.

**aiduPOP is an independent project** (not an upstream fork mirror). It originates from — and credits — [Aowen-Nowor/hermes-lark-streaming](https://gitee.com/Aowen-Nowor/hermes-lark-streaming) v1.6.0, on top of which it adds a complete **Bubble Wave** styling layer:

| Layer | What it does | Key feature |
|-------|-------------|-------------|
| ⚡ **Instant** | Card appears on the first token | No typing indicator, no "replying to…" patch |
| 🎨 **Visual config (new in v2.3.0)** | Pick emoji / arrange panel & footer without editing code | `aidupop studio` opens a visual studio with a live 1:1 Feishu card preview; takes effect after `/aowen config reload` |
| 💠 **Minimal** | Every element has a reason | Answer on top, panel below, footer empty by default |
| 🚦 **State** | Result at a glance | Color-coded: green done / red stopped / yellow error |
| 🔍 **Transparent** | See every step | Expandable panel: thought rounds, tool calls, timestamps |
| 🃏 **Interactive** | Answer inside the card | Native Cardsuit 2.0 clarify options + callback |
| 🛡️ **Resilient** | Never falls back to plain text | Phase 2 rollback recovery, auto card recreation |

> 🫧 Bubble Wave · aiduPOP — every step of the AI's thinking, as clear as bubbles on water

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│      aiduPOP⚕爱嘟泡波卡                          │
├──────────────────────────────────────────────────┤
│  cardkit/     → Card rendering engine             │
│  controller/  → Linear controller + card_id track │
│  patching/    → Aidu customizations (model, P2)   │
│  state/       → Streaming state machine           │
│  flush/       → Throttled flush & batch update    │
│  feishu/      → Feishu API client                 │
├──────────────────────────────────────────────────┤
│  Hermes Agent plugin hooks (platform_registry)    │
│  aiduMEM persistent memory (no context anxiety)   │
└──────────────────────────────────────────────────┘
```

---

## 🖼️ Screenshots

### 1. Instant Response

<p align="center">
  <img src="assets/screenshots/01-instant-response.png" width="600" alt="Instant Response">
</p>

> **No typing indicators. No "replying to…" patches.** The streaming card appears instantly — you see the response forming in real time from the very first token, featuring an out-of-the-box mechanical typewriter effect (`print_step=1`, `print_frequency_ms=15`). No Feishu UI noise, just pure conversation.

---

### 2. Completed State — Green Panel

<p align="center">
  <img src="assets/screenshots/02-panel-completed.png" width="600" alt="Completed State">
</p>

> **Answer above, panel below.** The green-bordered panel shows execution stats at a glance: model name, thinking rounds, tool calls, and elapsed time. Clean, minimal, and informative — powered by **aiduMEM** to eliminate context anxiety. The panel is fully customizable.

---

### 3. Stopped / Error State — Red Panel

<p align="center">
  <img src="assets/screenshots/03-panel-stopped.png" width="600" alt="Stopped State">
</p>

> **Color-coded states.** When generation is stopped or errors occur, the panel border changes color — **red for stopped**, **yellow for errors**. You always know the status at a glance without reading fine print.

---

### 4. Expanded Panel — Full Trace

<p align="center">
  <img src="assets/screenshots/04-panel-expanded.png" width="600" alt="Expanded Panel">
</p>

> **Click to expand.** See the full reasoning trace — every thought round, every tool call, with timestamps. Transparent by design. No hidden magic, no footer clutter. Just the information you need, when you need it.

---

### 5. Clarify — Interactive Options (Cardkit 2.0)

<p align="center">
  <img src="assets/screenshots/05-clarify-options.png" width="600" alt="Clarify Options">
</p>

> **Native Feishu Cardkit 2.0 integration.** When the AI needs clarification, it presents interactive option cards right in the chat. Select from dropdowns or type your answer — no context switching required.

---

### 6. Clarify — Callback & Continuation

<p align="center">
  <img src="assets/screenshots/06-clarify-callback.png" width="600" alt="Clarify Callback">
</p>

> **Seamless callback.** After selection, the agent receives the callback and continues working. The clarify card updates to show your choice with a confirmation badge. Clean, fast, native.

---

## 🚀 Quick Start

### Prerequisites

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) installed
- Lark (Feishu) bot configured
- Python 3.11+

### Installation

Option 1 · as a Hermes directory plugin (GitHub, recommended):

```bash
git clone https://github.com/monkey2jack/aiduPOP.git
cp -r aiduPOP ~/.hermes/plugins/hermes-lark-streaming
hermes gateway restart
```

### Configuration

The plugin uses the same configuration as the upstream `hermes-lark-streaming`. See [docs/CUSTOMIZATIONS.md](docs/CUSTOMIZATIONS.md) for Aidu-specific additions.

#### Device-specific text sizes

Configure a single size per role, or map desktop/mobile sizes in Hermes `config.yaml`:

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

The supported roles are `body` (answer), `panel` (reasoning/tools/stats), and `notice` (folding and status notices). Each role accepts either one official CardKit text size or a `default` / `pc` / `mobile` mapping. Omitting this option preserves the existing `normal_v2` / `notation` appearance; `normal_v2` remains a legacy default and is not accepted in new configuration. Apply changes with `/aowen config reload` or restart the Hermes gateway. Invalid roles, device keys, or sizes fail explicitly instead of producing malformed cards.

The single source of truth for the version is the `version` field in `plugin.yaml`; `setup.py` and `__init__.py` read it dynamically, so versions never drift between files.

---

## 🎨 Visual Card Studio (v2.3.1 · optional)

Don't want to hand-edit YAML? `aidupop studio` launches a **fully local, zero-third-party-dependency** visual studio to tune the Bubble Wave look like picking stickers.

> 🏆 **A first on the web**: aiduPOP is the first open-source project to ship a visual configuration studio for a Hermes Agent Feishu streaming-card plugin — fully local, zero third-party dependencies, with a built-in 1:1 CardKit 2.0 live preview. What you see is what you get, without touching a single line of code.

<p align="center">
  <img src="assets/screenshots/07-visual-card-studio.png" width="860" alt="Visual Card Studio">
  <br>
  <sub>Visual Card Studio: brand banner / one-click presets / tool-emoji config / 1:1 live Feishu card preview — takes effect after <code>/aowen config reload</code></sub>
</p>

```bash
aidupop studio                 # default 127.0.0.1:8765, opens the browser
aidupop studio --port 8770     # custom port
aidupop studio --no-browser    # do not open the browser
# or: python -m hermes_lark_streaming studio
```

What you can configure:

- **Tool emoji**: 13 tool icons (read/write/search/exec/browser/agent…) with a per-slot "current → replacement" swap; type an emoji or pick one (emoji-only)
- **Panel stats bar**: model prefix, rounds, tool count, elapsed icons and separator
- **Footer matrix**: toggle `model` / `tokens` / `elapsed` / `status` / `context` row/column layout and labels
- **Streaming & sizes**: panel default-expand, typewriter step, flush throttle, CardKit 2.0 text sizes
- **One-click presets**: Bubble Wave / Classic Workflow / Cyber Minimal, re-skin or reset anytime
- **WYSIWYG preview**: built-in 1:1 Feishu CardKit 2.0 card simulator that redraws in real time

On save: writes `~/.hermes/config.yaml` (backup first, atomic write). The gateway is a separate process — send `/aowen config reload` in Feishu or restart the gateway, and new cards render with the new config.

Security by design (for open-source users):

- Loopback-only; rejects non-local `Host` requests; no wildcard CORS (guards against CSRF / DNS-rebinding)
- Deep-merges only UI-managed keys; `feishu` credentials and any custom keys are **preserved, never clobbered**
- Refuses to write when the existing config cannot be parsed; backs up first, then writes atomically (`~/.hermes/backups/`)
- Server-side re-validation of emoji values and payload structure; invalid requests return 400

> This is an **optional tool**: production environments do not load it by default; open-source users enable it on demand.

---

## 🔧 Customizations

See [docs/CUSTOMIZATIONS.md](docs/CUSTOMIZATIONS.md) for the full list of customizations over upstream v1.6.0, and [docs/CHANGELOG.md](docs/CHANGELOG.md) for version history.

### Key Features

- **🫧 Bubble Wave Style** — Cute-by-default visuals: emoji tool icons + water/bubble motifs, customizable via `aidupop studio`
- **💠 Minimal Design** — Clean, minimal UI with no unnecessary elements
- **⚡ Instant Response** — No typing indicators, cards appear immediately
- **🚦 Color-Coded Panels** — Green (completed), Red (stopped), Yellow (error)
- **🔍 Transparent Trace** — Expandable panel shows full reasoning and tool calls
- **🤔 aiduMEM Integration** — Eliminates context anxiety with persistent memory
- **🃏 Cardsuit 2.0** — Native Feishu interactive clarify cards
- **🛡️ Phase 2 Protection** — Automatic rollback recovery on API failures
- **📊 Model Display** — Stable model name display without flickering

---

## What's new in 2.3.2

- **🛡️ Cold-start patch guard**: Synchronized `hermes_adapter` detection logic to greedily patch direct agent runners on first incoming message, eliminating plain-text fallback during the 60s cold-start window.
- **🌊 Flush gap tolerance**: Raised `LONG_GAP_MS` from 1.0s to 2.0s to prevent unintentional message segmentation during upstream model retries.
- **🔄 Transient error retry**: Added Feishu CardKit `300309` (streaming_closed) and `300317` (sequence_conflict) to transient retries; refined `300315` logging for invalid schema attributes.
- **📊 Observability**: Added a dedicated `text_fallbacks` counter in the aowen monitor panel to track fallback events cleanly.

## What's new in 2.3.1

Studio audit fixes — config safety and honest messaging.

- **🐛 Fix: invalid `text_sizes` value broke all cards (P0)**: The Studio UI defaulted the body text size to `normal_v2`, which the runtime CardKit 2.0 whitelist rejects — saving it made the gateway raise `ValueError` on card creation, silently dropping streaming cards for every message. The server now validates every `text_sizes` value against the runtime whitelist and refuses invalid writes; the UI uses dropdowns limited to official sizes plus "default" (= do not write the key).
- **📢 Honest messaging (P1)**: `Config().reload()` only clears the Studio process's own cache; the gateway picks up changes after `/aowen config reload` or a restart — toasts, buttons and READMEs now say so.
- **🛡️ Frontend XSS hardening (P2)**: All dynamic config values pass through `escapeHtml()` before entering the DOM.
- **🧹 Backup rotation (P3)**: Config backups keep only the newest 20 copies.
- **🔒 Desensitization**: Removed internal nicknames left in v2.3.0 code.
- **🧪 Tests**: 5 new cases in `test_v230_studio.py` (text_sizes whitelist regression guard, end-to-end refuse-write preserves the file, backup rotation); full suite passing.

## What's new in 2.3.0

Visual Card Studio — an optional, fully local visual configuration UI.

- **🎨 Visual Card Studio (`studio/`)**: New `aidupop studio` command launches a zero-third-party-dependency local web studio. Visually configure tool emoji, the panel stats bar, the footer matrix, and streaming/sizes, with a built-in 1:1 Feishu CardKit 2.0 live card preview (WYSIWYG). Brand visuals align with aiduMEI (paper-white base + deep-blue accents + tri-color random hexagon backdrop + bilateral slogans).
- **⚡ Save = hot apply**: Writes `~/.hermes/config.yaml` then triggers `Config().reload()` — applies within seconds, no gateway restart; a best-effort `systemctl` restart entry is also provided (honestly reported).
- **🛡️ Security hardening (open-source)**: Loopback-only with local `Host` validation (guards CSRF / DNS-rebinding), no wildcard CORS; server-side re-validation of POST structure and emoji values.
- **🔒 Zero config loss**: Deep-merges only UI-managed keys; `feishu` credentials plus `print_strategy`, `reactions`, and user-authored keys are preserved; refuses to write when the existing config is unparseable; backs up then writes atomically.
- **🧪 Tests**: New `tests/test_v230_studio.py` (22 cases) covering merge-preserves-config, refuse-write-on-read-error, payload/emoji validation, Host gate, static assets, and no-header residue; full suite passing.
- **🏗️ Additive, non-invasive**: Studio is an independent optional module; production environments do not load it by default. Bubble Wave theme and the five structural guards are untouched.

## What's new in 2.2.1

Engineering hygiene hardening — no structural changes.

- **🐛 Exception-swallow observability**: All 15 bare `except Exception: pass` sites remediated — 12 core paths now log `_logger.debug(..., exc_info=True)` context; 3 script paths annotated as safe-to-ignore. Silent production failures are now diagnosable.
- **⏱️ Script HTTP timeout**: `scripts/notify_feishu.py` `urlopen` gains `timeout=60`, aligned with `create_release.py` — no more hung CI notification threads.
- **📄 Doc version sync**: README badges / CHANGELOG aligned with the `plugin.yaml` single source of truth (fixes the doc drift left by the v2.2.0 release flow).
- **🏗️ Zero structural change**: `_model_cache`, Bayesian fallback, long-text fence splitting, `batch_update` atomic rollback, and lazy imports untouched; Bubble Wave theme and the five structural guards unchanged.

## What's new in 2.2.0

Bubble Wave theme — a configurable theming layer for emoji/text customization.

- **🎨 Bubble Wave theme layer (`cardkit/theme.py`)**: Adds `BUBBLE_WAVE` factory default theme + `get_theme()` deep-merge (config key `hermes_lark_streaming.theme` overrides). Zero-config bubble visuals out of the box; advanced users override any icon/text without touching source.
- **🧰 Tool icons emoji-ified**: 13 tool descriptors (read/write/exec/web_search/grep/glob/browser/agent/check/analyze/skill) swapped from official Feishu tokens to bubble-wave emoji set. `is_emoji_icon()` classifier routes emoji through text rendering and tokens through `standard_icon`, zero conflict.
- **💬 i18n bubble text**: 5 Chinese text keys萌化 (`processing_prefix`→`⚕Hermesing…`, `agent_process`→`🫧`, `rounds`→`🫧{}`, `tools_count`→`✨{}`, `round_n`→`第 {} 波`); English keys untouched (i18n safety).
- **🐛 Tool alias leak fix**: Added 嘟嘟 Hermes 0.20 real tool-name aliases (`terminal`/`execute_code`→exec, `read_file`→read, `patch`→write, `search_files`→glob, `web_extract`→web_fetch, `browser_exec`→browser, `delegate_task`→agent, `vision_analyze`→analyze, `skill_view`/`skill_manage`/`skills_list`→skill); removed bare `search` alias that prefix-matched `search_files` to the wrong descriptor.
- **🧪 v2.2.0 lock tests**: `tests/test_v220.py` locks every bubble decision + the five structural guards (no header / no reaction interception / answer-above-panel / panel-collapsed-by-default / no footer).
- **🏗️ Open-source principle**: Factory default = Bubble Wave. v2.2.0 only swaps icons/text; the stable core (`_model_cache`, Bayesian fallback, long-text fence splitting, `batch_update` atomic rollback, lazy imports) is untouched.

## What's new in 2.1.3

- 🐛 **Hermes CLI import-lock deadlock fix (P0)**: `apply_patches()` now runs in a daemon thread with deferred execution, eliminating the `import_lock` deadlock between `model_tools` module-level import and the background plugin-discovery thread that froze `hermes` CLI startup.
- 🏷️ **Lark (Feishu) branding unification**: Chinese and English brand copy unified to "Lark (Feishu)".
- 📱 **Device-specific text sizes (Issue #4)**: New `hermes_lark_streaming.text_sizes` config supporting `body`/`panel`/`notice` roles with `default`/`pc`/`mobile` device differentiation via CardKit JSON 2.0.

## What's new in 2.1.2

This is a patch release of aiduPOP; the English name and card design remain unchanged.

- Prevents Feishu `300305` element-limit failures during incremental Phase 2/3 panel updates by enforcing a shared pre-send element budget.
- Fixes a hidden `NameError` for responses longer than 24,000 characters.
- Deduplicates message/anchor session aliases, preserves unrelated topic cards, and safely falls back for stale Clarify actions.
- Restores the table-scanner compatibility API and makes the 885-test suite portable and warning-clean.
- Adds test gates before GitHub synchronization (the GHCR/Docker publication pipeline was retired when distribution stopped).

See [docs/CHANGELOG.md](docs/CHANGELOG.md) for the complete history.

---

## 📦 Project Structure

```
aiduPOP/
├── cardkit/           # Card rendering engine
├── controller/        # Linear controller & card_id tracking
├── patching/          # Aidu customizations (model display, Phase 2)
├── state/             # Streaming state machine
├── flush/             # Throttled flush
├── feishu/            # Feishu API client
├── config/            # Configuration parsing
├── assets/            # Screenshots & static resources
├── tests/             # Test suite
├── plugin.yaml        # Plugin config (single source of version truth)
└── ...
```

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Credits

- **Upstream**: [Aowen-Nowor/hermes-lark-streaming](https://gitee.com/Aowen-Nowor/hermes-lark-streaming) v1.6.0
- **Upstream author**: Aowen
- **Framework**: [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research
- **Customization**: Aidu

---

<p align="center">
  <sub>Made with 💕 by aidu</sub>
</p>
