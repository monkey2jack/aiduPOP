"""CardKit 主题层 — 泡波 (Bubble-Wave) 默认主题 + 配置覆盖.

v2.2.0 新增: 全部 emoji/图标文本集中到这一层，可配置、可换肤。

- 出厂默认 = 泡波样式 (BUBBLE_WAVE)，即猴哥拍板的 emoji 方案
- 开源用户可在 config.yaml 的 ``hermes_lark_streaming.theme`` 段覆盖任意键
- 飞书 ``standard_icon`` 只接受官方 token（emoji 放进 token 会渲染成空白），
  所以 emoji 图标一律走 lark_md / plain_text 文本渲染（生产 i18n 用法已验证）。
  判断走哪条渲染路径用 :func:`is_emoji_icon`。
"""

from __future__ import annotations

import copy
import re
from typing import Any

__all__ = [
    "BUBBLE_WAVE",
    "get_theme",
    "is_emoji_icon",
]

# ── 出厂默认主题: 泡波样式 ────────────────────────────────────────────
BUBBLE_WAVE: dict[str, Any] = {
    # ── 工具步图标（决策表①；key = 描述符首别名，见 state/tooluse.py）──
    "tool_icons": {
        "skill": "🤹🏻‍♀️",       # Load skill
        "read": "👩🏻‍🏫",        # Read
        "write": "👩🏻‍🎨",       # Edit
        "web_search": "🕵🏻‍♀️",  # Search
        "web_fetch": "👩🏻‍🚀",   # Fetch web page
        "grep": "👩🏻‍🔬",        # Search text
        "glob": "👮🏻‍♀️",        # Search files
        "exec": "👩🏻‍💻",        # Run command
        "browser": "🥷🏻",       # Browser
        "agent": "👷🏻‍♀️",       # Run sub-agent
        "check": "👩🏻‍⚖️",       # Check
        "analyze": "👩🏻‍🎓",     # Analyze
        "fallback": "👩🏻‍🔧",    # 未识别工具
    },
    # ── 推理轮标题图标（决策表① #33）──
    "round_icon": "🌊",
    # ── Panel header 统计行（嘟嘟专属纯正配置：👸🏻模型 · 🌊思考 · 🫧工具 · ✨时间）──
    "panel": {
        "model_prefix": "👸🏻",
        "rounds_icon": "🌊",
        "tools_icon": "🫧",
        "elapsed_icon": "✨",
        "separator": " · ",
    },
    # ── 折叠提示图标（决策表③: ⚡→💦；文案结构不变）──
    "collapse_icon": "💦",
    # ── Footer（决策表③: ⚕/↑↓ 保持，推理 token 💭→🫧）──
    "footer": {
        "model_prefix": "⚕",
        "reasoning_icon": "🫧",
    },
    # ── Reaction → 状态标签（决策表③；拦截默认关闭 — 嘟嘟定制，数据供开源启用方使用）──
    "reactions": {
        "👩🏻‍🏫": "Reading",
        "🙆🏻‍♀️": "Done",
        "🧏🏻‍♀️": "Thinking",
        "💆🏻‍♀️": "Processing",
        "🙋🏻‍♀️": "Completed",
        "🙅🏻‍♀️": "Refreshing",
        "💁🏻‍♀️": "Composing",
    },
}

# 飞书官方 standard_icon token 形如 "tool_02" / "edit_outlined" / "down-small-ccm_outlined"
_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]*$")


def is_emoji_icon(value: Any) -> bool:
    """True = 该图标值是 emoji（须走文本渲染），False = 官方 token（走 standard_icon）."""
    if not value or not isinstance(value, str):
        return False
    return _TOKEN_RE.match(value) is None


def _config_theme_overlay() -> dict[str, Any]:
    """读取 config.yaml 中 ``hermes_lark_streaming.theme`` 覆盖段（缺省/异常 → 空）."""
    try:
        from ..config import Config
        overlay = Config()._plugin_sec().get("theme")
        return overlay if isinstance(overlay, dict) else {}
    except Exception:
        return {}


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """两段合并: overlay 的 dict 值与 base 同 key dict 做浅合并，其余直接覆盖."""
    out = copy.deepcopy(base)
    for key, val in overlay.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = {**out[key], **val}
        else:
            out[key] = val
    return out


def get_theme() -> dict[str, Any]:
    """返回生效主题 = 泡波默认 + 配置覆盖。每次调用实时合并（体量小，不做缓存）."""
    overlay = _config_theme_overlay()
    if not overlay:
        return copy.deepcopy(BUBBLE_WAVE)
    return _deep_merge(BUBBLE_WAVE, overlay)
