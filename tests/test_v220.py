"""v2.2.0 泡波样式锁定测试 — 猴哥拍板的 emoji/文本决策（决策表①②③）+ 结构定制守卫.

两类断言:
1. 泡波决策锁定: 每个替换后的 emoji/文本逐字断言，防止回归改回旧样式
2. 结构守卫: 嘟嘟五大定制（无header / 无reaction拦截 / answer在panel之上 /
   panel默认收起纯统计 / 无footer）结构不变，只换皮
"""

from __future__ import annotations

from pathlib import Path

from hermes_lark_streaming.cardkit import (
    ANSWER_ELEMENT_ID,
    UNIFIED_PANEL_ELEMENT_ID,
    build_streaming_card_v2,
    build_unified_panel,
)
from hermes_lark_streaming.cardkit.elements import (
    _LOADING_ELEMENT_ID,
    _build_reasoning_round_title,
    _build_tool_step_title,
    _render_footer_field,
    build_panel_children,
    build_panel_header,
)
from hermes_lark_streaming.cardkit.i18n import _T
from hermes_lark_streaming.cardkit.theme import BUBBLE_WAVE, get_theme, is_emoji_icon
from hermes_lark_streaming.config import Config
from hermes_lark_streaming.state.linear import ReasoningRound
from hermes_lark_streaming.state.tooluse import ToolUseTracker

_REPO_ROOT = Path(__file__).resolve().parent.parent


# ── 决策表①: 工具图标 ────────────────────────────────────────────────


class TestToolIcons:
    """13 个工具图标 + 渲染分支（emoji 走文本，token 走 standard_icon）."""

    EXPECTED = {
        "skill": "🤹🏻‍♀️",
        "read": "👩🏻‍🏫",
        "write": "👩🏻‍🎨",
        "web_search": "🕵🏻‍♀️",
        "web_fetch": "👩🏻‍🚀",
        "grep": "👩🏻‍🔬",
        "glob": "👮🏻‍♀️",
        "exec": "👩🏻‍💻",
        "browser": "🥷🏻",
        "agent": "👷🏻‍♀️",
        "check": "👩🏻‍⚖️",
        "analyze": "👩🏻‍🎓",
        "fallback": "👩🏻‍🔧",
    }

    def test_theme_tool_icons_match_decisions(self) -> None:
        assert get_theme()["tool_icons"] == self.EXPECTED

    def test_tracker_emits_theme_emoji_per_tool(self) -> None:
        tracker = ToolUseTracker()
        for name in ("read_file", "write_file", "exec_command", "web_search",
                     "grep_search", "glob_files", "browser_navigate",
                     "delegate_task", "check_result", "analyze_data", "skill_load"):
            tracker.record_start(name)
        steps = tracker.build_display_steps()
        assert len(steps) == 11
        assert steps[0]["icon"] == "👩🏻‍🏫"    # read_file
        assert steps[1]["icon"] == "👩🏻‍🎨"    # write_file
        assert steps[2]["icon"] == "👩🏻‍💻"    # exec_command
        assert steps[3]["icon"] == "🕵🏻‍♀️"   # web_search
        assert steps[4]["icon"] == "👩🏻‍🔬"    # grep_search
        assert steps[5]["icon"] == "👮🏻‍♀️"    # glob_files
        assert steps[6]["icon"] == "🥷🏻"       # browser_navigate
        assert steps[7]["icon"] == "👷🏻‍♀️"    # delegate_task (决策表① #25)
        assert steps[8]["icon"] == "👩🏻‍⚖️"    # check_result
        assert steps[9]["icon"] == "👩🏻‍🎓"    # analyze_data
        assert steps[10]["icon"] == "🤹🏻‍♀️"   # skill_load

    def test_unknown_tool_gets_fallback_emoji(self) -> None:
        tracker = ToolUseTracker()
        tracker.record_start("some_mystery_tool")
        steps = tracker.build_display_steps()
        assert steps[0]["icon"] == "👩🏻‍🔧"

    def test_dudu_real_tool_names_hit_correct_emoji(self) -> None:
        """嘟嘟 Hermes 0.20 实际工具名（agent.log 实测）必须命中对应描述符，
        不许掉 fallback。防 terminal→👩🏻‍🔧 这类漏配回归。"""
        cases = {
            "terminal": "👩🏻‍💻",        # exec 别名漏配会掉 fallback（2026-08-16 猴哥亲诊）
            "execute_code": "👩🏻‍💻",
            "read_file": "👩🏻‍🏫",
            "write_file": "👩🏻‍🎨",
            "patch": "👩🏻‍🎨",         # 写操作归 Edit
            "search_files": "👮🏻‍♀️",
            "web_search": "🕵🏻‍♀️",
            "web_extract": "👩🏻‍🚀",
            "browser_exec": "🥷🏻",
            "delegate_task": "👷🏻‍♀️",
            "vision_analyze": "👩🏻‍🎓",
            "skill_view": "🤹🏻‍♀️",
            "skill_manage": "🤹🏻‍♀️",
            "skills_list": "🤹🏻‍♀️",
        }
        for name, expected in cases.items():
            tracker = ToolUseTracker()
            tracker.record_start(name)
            steps = tracker.build_display_steps()
            assert steps[0]["icon"] == expected, (
                f"工具名 {name!r} 应出 {expected}，实际出 {steps[0]['icon']!r}"
                "——别名漏配，检查 _TOOL_DESCRIPTORS"
            )

    def test_emoji_step_renders_in_text_without_icon_key(self) -> None:
        el = _build_tool_step_title({"title": "Read", "status": "success", "icon": "👩🏻‍🏫"})
        assert "icon" not in el  # emoji 不进 standard_icon（渲染空白）
        assert el["text"]["content"].startswith("👩🏻‍🏫 ")
        assert "**Read**" in el["text"]["content"]

    def test_token_step_keeps_standard_icon(self) -> None:
        el = _build_tool_step_title({"title": "Read", "status": "success", "icon": "file-link-text_outlined"})
        assert el["icon"]["tag"] == "standard_icon"
        assert el["icon"]["token"] == "file-link-text_outlined"
        assert not el["text"]["content"].startswith("file-link-text")

    def test_is_emoji_icon_classifier(self) -> None:
        assert is_emoji_icon("👩🏻‍🏫")
        assert is_emoji_icon("🥷🏻")
        assert not is_emoji_icon("tool_02")
        assert not is_emoji_icon("edit_outlined")
        assert not is_emoji_icon("down-small-ccm_outlined")
        assert not is_emoji_icon("")
        assert not is_emoji_icon(None)


# ── 决策表②: i18n 文本（5 改 28 留，英文不动）─────────────────────────


class TestI18nDecisions:

    def test_processing_prefix_zh_changed_en_kept(self) -> None:
        en, zh = _T["processing_prefix"]
        assert zh == "⚕Hermesing…"
        assert en == "💭 Processing..."  # 英文不动

    def test_agent_process_zh_bubble(self) -> None:
        en, zh = _T["agent_process"]
        assert zh == "🫧"
        assert en == "💭"  # 英文不动

    def test_rounds_zh_bubble(self) -> None:
        en, zh = _T["rounds"]
        assert zh == "🫧{}"
        assert en == "💭{}"

    def test_tools_count_zh_sparkle(self) -> None:
        en, zh = _T["tools_count"]
        assert zh == "✨{}"
        assert en == "🛠️{}"

    def test_round_n_zh_wave(self) -> None:
        en, zh = _T["round_n"]
        assert zh == "第 {} 波"
        assert en == "Round {}"

    def test_untouched_keys_stay(self) -> None:
        # 铁律#1: 未填写的保持原状（抽查关键键）
        assert _T["processing"] == ("⚕Hermesing…", "⚕Hermesing…")
        assert _T["elapsed"] == ("Elapsed {}", "耗时 {}")
        assert _T["context"] == ("Context {}", "上下文 {}")
        assert _T["cache"] == ("Cache {}", "缓存 {}")
        assert _T["status_completed"] == ("Completed", "已完成")


# ── 决策表③: panel header / 折叠提示 / footer / reaction ─────────────


class TestPanelHeaderDecisions:

    def test_stats_row_bubble_wave(self) -> None:
        header = build_panel_header(
            reasoning_rounds=[ReasoningRound(index=1, text="x")],
            tool_steps=[{"title": "t", "status": "success"}],
            tool_elapsed_ms=12345,
            model="anthropic/claude-opus-5",
        )
        stats = header["title"]["content"]
        # ⚕model · 🫧N · ✨N · 🎶elapsed（⚕/· 保持，💭→🫧 🛠️→✨ ⏱→🎶）
        assert stats == "👸🏻claude-opus-5 · 🌊1 · 🫧1 · ✨12.3s"

    def test_stats_row_no_model(self) -> None:
        header = build_panel_header(
            reasoning_rounds=[], tool_steps=[], tool_elapsed_ms=0, model=None,
        )
        assert header["title"]["content"] == "🌊0 · 🫧0 · ✨0.0s"

    def test_header_chevron_icon_kept(self) -> None:
        # 结构守卫: header 图标仍是官方 chevron token（不是 emoji）
        header = build_panel_header(
            reasoning_rounds=[], tool_steps=[], tool_elapsed_ms=0,
        )
        assert header["icon"]["tag"] == "standard_icon"
        assert header["icon"]["token"] == "down-small-ccm_outlined"
        assert header["icon_position"] == "right"


class TestRoundTitleDecisions:

    def test_round_title_wave_icon_and_wave_label(self) -> None:
        el = _build_reasoning_round_title(3, 2500, finalized=True)
        assert "icon" not in el  # 🌊 走文本渲染
        content = el["text"]["content"]
        assert content.startswith("🌊 ")
        assert "第 3 波" in content  # 决策表② round_n 联动
        assert "2.5s" in content

    def test_theme_round_icon_default(self) -> None:
        assert get_theme()["round_icon"] == "🌊"


class TestCollapseHintDecisions:

    def test_collapse_hint_droplet(self) -> None:
        rounds = [ReasoningRound(index=i + 1, text=f"r{i}") for i in range(5)]
        children = build_panel_children(
            reasoning_rounds=rounds, tool_steps=[],
            max_reasoning_rounds=2, max_tool_steps=20,
        )
        assert children[0]["content"] == "💦 还有 3 轮早期推理已折叠"

    def test_theme_collapse_icon_default(self) -> None:
        assert get_theme()["collapse_icon"] == "💦"


class TestFooterDecisions:

    def test_footer_model_prefix_kept(self) -> None:
        en, zh = _render_footer_field("model", {"model": "anthropic/claude-opus-5"}, False, False, False)
        assert en == "⚕claude-opus-5"  # ⚕ 保持（决策表③）
        assert zh == en

    def test_footer_tokens_arrows_kept_reasoning_bubble(self) -> None:
        en, zh = _render_footer_field(
            "tokens",
            {"input_tokens": 2100, "output_tokens": 850, "reasoning_tokens": 3200},
            False, False, False,
        )
        # ↑↓ 保持，推理 token 💭→🫧
        assert en == "↑ 2.1K ↓ 850 🫧 3.2K"

    def test_footer_tokens_without_reasoning(self) -> None:
        en, zh = _render_footer_field(
            "tokens", {"input_tokens": 100, "output_tokens": 50}, False, False, False,
        )
        assert en == "↑ 100 ↓ 50"
        assert "🫧" not in en


class TestReactionDecisions:

    EXPECTED = {
        "👩🏻‍🏫": "Reading",
        "🙆🏻‍♀️": "Done",
        "🧏🏻‍♀️": "Thinking",
        "💆🏻‍♀️": "Processing",
        "🙋🏻‍♀️": "Completed",
        "🙅🏻‍♀️": "Refreshing",
        "💁🏻‍♀️": "Composing",
    }

    def test_theme_reactions_match_decisions(self) -> None:
        assert get_theme()["reactions"] == self.EXPECTED

    def test_adapter_map_matches_theme(self) -> None:
        from hermes_lark_streaming.patching import _REACTION_STATUS_MAP
        assert _REACTION_STATUS_MAP == self.EXPECTED

    def test_old_reaction_emojis_gone(self) -> None:
        from hermes_lark_streaming.patching import _REACTION_STATUS_MAP
        for old in ("👀", "👍", "🤔", "⏳", "✅", "🔄", "📝"):
            assert old not in _REACTION_STATUS_MAP


# ── theme 层机制 ─────────────────────────────────────────────────────


class TestThemeLayer:

    def test_bubble_wave_is_factory_default(self) -> None:
        # 开源原则: 出厂默认 = 泡波样式
        assert get_theme() == BUBBLE_WAVE

    def test_get_theme_returns_copy(self) -> None:
        t = get_theme()
        t["tool_icons"]["read"] = "MUTATED"
        assert get_theme()["tool_icons"]["read"] == "👩🏻‍🏫"
        assert BUBBLE_WAVE["tool_icons"]["read"] == "👩🏻‍🏫"

    def test_config_theme_property_defaults_empty(self) -> None:
        assert Config().theme == {}


# ── 结构守卫: 嘟嘟五大定制（只换皮，不改结构）──────────────────────────


class TestStructuralGuards:

    def test_card_no_header(self) -> None:
        card = build_streaming_card_v2()
        assert "header" not in card  # 定制①: 无 header
        assert set(card.keys()) == {"schema", "config", "body"}

    def test_answer_above_panel_order(self) -> None:
        card = build_streaming_card_v2()
        ids = [e.get("element_id") for e in card["body"]["elements"]]
        assert ANSWER_ELEMENT_ID in ids
        assert UNIFIED_PANEL_ELEMENT_ID in ids
        assert ids.index(ANSWER_ELEMENT_ID) < ids.index(UNIFIED_PANEL_ELEMENT_ID)  # 定制③

    def test_panel_placeholder_collapsed_by_default(self) -> None:
        # 定制④: panel 自动收起（config 默认 False）
        assert Config().panel_expanded is False
        assert Config().streaming_panel_expanded is False

    def test_no_footer_by_default(self) -> None:
        # 定制⑤: footer 取消（默认字段列表为空）
        assert Config().footer_fields == []

    def test_reaction_interception_stays_disabled(self) -> None:
        # 定制②: reaction 拦截保持注释禁用（泡波 reaction 数据为休眠配置）
        src = (_REPO_ROOT / "patching" / "__init__.py").read_text(encoding="utf-8")
        assert "Reaction interception disabled (嘟嘟定制)" in src
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert "_wrap_feishu_adapter_add_reaction(" not in stripped
            assert "_wrap_feishu_adapter_delete_reaction(" not in stripped

    def test_panel_default_expanded_false_in_builder(self) -> None:
        panel = build_unified_panel(
            reasoning_rounds=[], tool_steps=[], tool_elapsed_ms=0,
        )
        assert panel["tag"] == "collapsible_panel"
        assert panel["expanded"] is False
        assert panel["element_id"] == UNIFIED_PANEL_ELEMENT_ID

    def test_loading_spinner_still_present(self) -> None:
        # 结构守卫: loading spinner 元素仍在（定制未涉及，不许误删）
        card = build_streaming_card_v2()
        ids = [e.get("element_id") for e in card["body"]["elements"]]
        assert _LOADING_ELEMENT_ID in ids


# ── 版本号 ───────────────────────────────────────────────────────────


class TestVersion:

    def test_plugin_yaml_has_version(self) -> None:
        # v2.4.1：不再锁死具体版本号（坑13 根治）——升版时此测试无需同步改。
        # 版本值的正确性由 plugin.yaml 单一真相源 + test_version.py 保证。
        yaml_text = (_REPO_ROOT / "plugin.yaml").read_text(encoding="utf-8")
        assert any(l.startswith("version:") for l in yaml_text.splitlines())

    def test_package_version_matches_yaml(self) -> None:
        import hermes_lark_streaming
        for line in (_REPO_ROOT / "plugin.yaml").read_text(encoding="utf-8").splitlines():
            if line.startswith("version:"):
                expected = line.split(":", 1)[1].strip().strip('"').strip("'")
                break
        else:
            raise AssertionError("plugin.yaml 无 version: 字段")
        assert hermes_lark_streaming.__version__ == expected
