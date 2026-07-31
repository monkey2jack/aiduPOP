# Changelog — aiduSTR 💎

All notable changes to this project will be documented in this file.
本文件记录 aiduSTR 的所有重要变更。

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) · SemVer with gem codenames.
版本号遵循语义化版本，每个大版本配一个宝石代号（Crystal 水晶 → …）。

Single source of truth: the `version` field in `plugin.yaml`.
版本号唯一来源：`plugin.yaml` 的 `version` 字段。

---

## [1.0.0 · Crystal 水晶] — 2026-07-31

### Initial Release — Crystal 🌟

First public release of Aidu-customized hermes-lark-streaming.

Based on [Aowen-Nowor/hermes-lark-streaming](https://gitee.com/Aowen-Nowor/hermes-lark-streaming) v1.6.0 with the following customizations:

### Added
- **v22.2 Model Display** — Stable model name from card birth via module-level global `_model_cache` dict
- **v22.3 Phase 2 Protection** — Rollback protection for Feishu atomic `batch_update` failures (300314)
- **Model Formatting** — Clean `⚕model` display with path prefix/date suffix stripping
- **Panel Position** — Answer on top, collapsible stats panel at bottom
- **Footer Removal** — Model moved to panel header; footer default empty
- **Card Recreation** — Auto-retry on API failure (card cache invalidation after gateway restart)
- **Loading Hint Hidden** — Replaced with loading icon for cleaner streaming experience
- **receive_id_type Auto-detection** — `ou_` → open_id, `oc_` → chat_id
- **send_card_by_id Retry** — Transient error retry wrapper for card creation API
- **Three-Class Identity Resolution** — Auto-patch FeishuAdapter regardless of import path

### Changed
- Panel header format: `⚕model · 💭N · 🛠️N · ⏱elapsed` (紧凑格式)
- Footer default fields: `[]` (empty, model in panel header)
- Processing hint: `⚕Hermesing…` (no space after ⚕️)
- Panel always renders (even for pure conversations without tools/reasoning)

### Fixed
- Model name flickering/disappearing across asyncio task boundaries
- Phase 2 300314 error causing card to fall back to plain text
- Clarify responses delivered as plain text instead of cards
- Three FeishuAdapter class identities causing patch gaps
- send_card_by_id missing retry wrapper
- Panel appearing above answer (now below)

---

## Upstream History

### [1.6.0] — 2026-07-21 (Aowen-Nowor)
- Fix clarify card fallback to text
- Hook `platform_registry.create_adapter` for adapter patching

### [1.5.5] — 2026-07-13 (Aowen-Nowor)
- Fix Phase 2 300314 existing_elements tracking

### [1.5.0] — 2026-07-09 (Aowen-Nowor)
- Major refactoring and optimizations
- Cron card delivery mechanism

### [0.7.0] — (Cheerwhy)
- Original streaming card plugin for Hermes Agent
