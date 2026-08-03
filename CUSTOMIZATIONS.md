# Customizations — aiduPOP v1.0.0 Crystal

This document details all customizations applied on top of [Aowen-Nowor/hermes-lark-streaming](https://gitee.com/Aowen-Nowor/hermes-lark-streaming) v1.6.0.

## Overview

| Customization | Version | Description |
|---------------|---------|-------------|
| Model Display | v22.2 | Stable model name from card birth via module-level global dict |
| Panel Position | — | Answer on top, collapsible stats panel at bottom |
| Footer Removal | — | Model moved to panel header; footer default empty |
| Model Formatting | — | Clean `⚕model` format with path/date stripping |
| Phase 2 Protection | v22.3 | Rollback protection for atomic batch_update failures |
| Adapter Patching | v1.5.4 | Three-class identity resolution for FeishuAdapter |
| Clarify Fix | v1.6.0 | Card delivery for clarify responses |
| Loading Hint | — | Hidden by default; replaced with loading icon |
| Card Recreation | — | Auto-retry on API failure (card cache invalidation) |

---

## v22.2 — Stable Model Display

### Problem

Model name flickered or disappeared because `threading.local()` does not propagate across `asyncio.create_task` boundaries. The model was written in task A but read in task B, where `_thread_local_ctx` was a fresh empty instance.

### Solution

Module-level global dictionary `_model_cache` — survives any task/thread/contextvar boundary:

```
Files changed:
  patching/__init__.py     — _model_cache dict definition + __all__ export
  patching/callbacks.py    — _maybe_wrap_callbacks writes _model_cache["current"]
  controller/linear_mixin.py — _get_model_from_ctx() reads _model_cache first
```

### Reading Priority

1. 🥇 `_model_cache.get("current")` — module-level global dict
2. 🥈 `ctx["_agent_ref"].model` — fallback (same-task only)

---

## v22.3 — Phase 2 Rollback Protection

### Problem

Feishu `batch_update` is atomic — deleting a non-existent element (error 300314) rolls back the entire batch, preventing answer and panel creation.

### Solution

Track `existing_elements` precisely. On 300314:
1. Discard stale hint tracking
2. Reset `_first_flush_done` to trigger immediate retry
3. Next flush: hint not in `existing_elements` → pure `add_elements` → success

```
Files changed:
  controller/linear_mixin.py — Phase 2 rollback rescue logic
```

---

## Panel Layout Customization

### Element Order

Answer element first, panel second (both in initial creation and updates):

```
[0] answer — streaming text
[1] panel  — collapsible stats (💭 🛠️ ⏱)
```

### Panel Header Format

```
⚕ModelName · 💭N · 🛠️N · ⏱elapsed
```

- `⚕`紧贴 model name, no space
- Model name cleaned: path prefixes removed, date suffixes stripped, truncated at 28 chars

### Footer

Default: **empty** (no footer rendered). Model displayed in panel header instead.

---

## Adapter Patching (v1.5.2 → v1.5.4)

### Three-Class Identity Problem

Python multiple import paths create **three** `FeishuAdapter` class objects. The original patching only covered two, leaving the gateway's `_status_adapter` unpatched.

### Solution

Hook `GatewayRunner._authorization_adapter` — intercept before use, check class identity, auto-patch if needed. No condition guards (idempotent function called unconditionally).

---

## Files Modified (relative to upstream v1.6.0)

| File | Changes |
|------|---------|
| `cardkit/elements.py` | `_format_model_display()`, panel header format, footer default `[]` |
| `cardkit/i18n.py` | `⚕` no-space processing hint |
| `cardkit/cards.py` | Panel position after answer |
| `controller/core.py` | Pre-create unified_state to prevent async race |
| `controller/linear_mixin.py` | `_get_model_from_ctx()`, `_build_session_panel()`, Phase 2 protection, loading hint hidden |
| `feishu/client.py` | Auto-detect receive_id_type, retry on send_card_by_id |
| `patching/__init__.py` | `_model_cache`, `_authorization_adapter` hook |
| `patching/callbacks.py` | `_model_cache["current"]` write, fine-grained callback wrapping |

---

## Upgrade Guide

When upgrading from upstream:

1. Create backup branch: `git checkout -b backup-aidu-v22.3`
2. Merge upstream tag: `git merge v1.7.0` (or whatever the new version is)
3. Re-apply customizations: `grep -rn "Aidu v22" patching/ controller/`
4. Verify: `pytest tests/`
5. **Do NOT restart gateway without confirmation**

---

## Debugging

### Model not showing

```bash
grep -rn "Aidu v22.2" /path/to/plugin/
# Should find _model_cache in patching/__init__.py, callbacks.py, linear_mixin.py
```

### Card falls back to plain text

```bash
# Check if card elements use valid tags
grep -rn '"tag":.*"markdown"' /path/to/plugin/
# Should find NONE — must be "div" + "lark_md"

# Check for missing header
grep -rn 'build_cron_card\|build_gateway_card' /path/to/plugin/cardkit/special.py
```

### Panel not rendering

```bash
# Panel is forced to always render in v22+
grep -n "if True:" /path/to/plugin/controller/linear_mixin.py
# Should find the panel rendering line
```
