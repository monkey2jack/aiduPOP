"""callback 拦截测试 — 验证 _maybe_wrap_callbacks 的核心行为.

覆盖场景:
  1. answer_wrapper: 卡片消费文字时不调原始回调 → 避免重复
  2. thinking_wrapper: 卡片消费文字时不调原始回调 → 修复重复消息 bug
  3. thinking_wrapper: 文字已被 stream_delta 消费时 dedup 跳过
  4. 卡片未消费(禁用/非飞书/异常)时正常调原始回调
  5. 无 event_message_id 时不包装回调
  6. 防止重复包装
  7. 完整管道模拟: 验证卡片活跃时纯文本管道不被触发
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hermes_lark_streaming.patching import (
    _msg_ctx,
    _maybe_wrap_callbacks,
    _thread_local_ctx,
)


# ── Helpers ──


class FakeAgent:
    """Real object with plain-Python callback functions (not MagicMock).

    MagicMock attributes interfere with _maybe_wrap_callbacks:
    setattr(mock_fn, "_hls_wrapper", True) creates a sub-mock, and
    getattr(mock_fn, "_hls_wrapper", False) returns a MagicMock instead
    of True/False, breaking the guard logic.
    """

    def __init__(self):
        self.stream_calls = []
        self.interim_calls = []

        def _stream_cb(text, *args, **kwargs):
            self.stream_calls.append({"text": text, "args": args, "kwargs": kwargs})

        def _interim_cb(text, *args, **kwargs):
            self.interim_calls.append({"text": text, "args": args, "kwargs": kwargs})

        self.stream_delta_callback = _stream_cb
        self.interim_assistant_callback = _interim_cb
        self.tool_progress_callback = lambda *a, **k: None
        self.reasoning_callback = None
        self.background_review_callback = None


def _make_mock_ctrl(*, enabled: bool = True) -> MagicMock:
    """Create a mock controller that makes on_answer/on_thinking work."""
    ctrl = MagicMock()
    ctrl.enabled = enabled
    ctrl.on_answer = MagicMock(return_value=None)
    ctrl.on_thinking = MagicMock(return_value=None)
    return ctrl


def _set_msg_ctx(eid: str = "test_eid_123456789") -> None:
    """Set up message context with a valid event_message_id."""
    _msg_ctx.set({
        "message_id": "msg_test",
        "chat_id": "chat_test",
        "anchor_id": "anchor_test",
        "event_message_id": eid,
        "card_sent": False,
    })
    _thread_local_ctx.data = dict(_msg_ctx.get())


def _clear_msg_ctx() -> None:
    """Clear message context."""
    _msg_ctx.set(None)
    _thread_local_ctx.data = None


# ── answer_wrapper tests ──


class TestAnswerWrapper:
    """stream_delta_callback 拦截行为: 卡片消费文字时不调原始回调."""

    def setup_method(self):
        _clear_msg_ctx()

    def teardown_method(self):
        _clear_msg_ctx()

    def test_card_consumes_text_skips_original_callback(self):
        """当卡片消费了文字, 不调原始 stream_delta_callback → 避免重复消息."""
        mock_ctrl = _make_mock_ctrl()
        with patch("hermes_lark_streaming.patching.hooks.get_controller", return_value=mock_ctrl):
            _set_msg_ctx()
            agent = FakeAgent()

            _maybe_wrap_callbacks(agent)
            agent.stream_delta_callback("Hello world")

            # on_answer 被调了 (卡片消费)
            assert mock_ctrl.on_answer.call_count == 1
            # 原始回调不应被调
            assert len(agent.stream_calls) == 0

    def test_card_does_not_consume_text_calls_original(self):
        """当卡片没消费文字, 正常调原始回调."""
        mock_ctrl = MagicMock()
        mock_ctrl.enabled = False  # disabled → on_answer_delta returns False
        with patch("hermes_lark_streaming.patching.hooks.get_controller", return_value=mock_ctrl):
            _set_msg_ctx()
            agent = FakeAgent()

            _maybe_wrap_callbacks(agent)
            agent.stream_delta_callback("Hello world")

            # 原始回调应被调
            assert len(agent.stream_calls) == 1
            assert agent.stream_calls[0]["text"] == "Hello world"

    def test_empty_text_not_consumed(self):
        """空文字不触发卡片消费, 直接调原始回调."""
        mock_ctrl = _make_mock_ctrl()
        with patch("hermes_lark_streaming.patching.hooks.get_controller", return_value=mock_ctrl):
            _set_msg_ctx()
            agent = FakeAgent()

            _maybe_wrap_callbacks(agent)
            agent.stream_delta_callback("")

            # 空文字不调 on_answer
            assert mock_ctrl.on_answer.call_count == 0
            # 原始回调应被调
            assert len(agent.stream_calls) == 1

    def test_exception_falls_through_to_original(self):
        """on_answer_delta 抛异常时, 降级调原始回调."""
        mock_ctrl = MagicMock()
        mock_ctrl.enabled = True
        mock_ctrl.on_answer = MagicMock(side_effect=RuntimeError("boom"))
        with patch("hermes_lark_streaming.patching.hooks.get_controller", return_value=mock_ctrl):
            _set_msg_ctx()
            agent = FakeAgent()

            _maybe_wrap_callbacks(agent)
            agent.stream_delta_callback("Hello world")

            # 异常后仍调原始回调
            assert len(agent.stream_calls) == 1


# ── thinking_wrapper tests ──


class TestThinkingWrapper:
    """interim_assistant_callback 拦截行为: 修复重复消息 bug 的核心测试."""

    def setup_method(self):
        _clear_msg_ctx()

    def teardown_method(self):
        _clear_msg_ctx()

    def test_card_consumes_text_skips_original_callback(self):
        """[BUG FIX] 卡片消费了文字 → 不调原始 interim_assistant_callback → 不重复."""
        mock_ctrl = _make_mock_ctrl()
        with patch("hermes_lark_streaming.patching.hooks.get_controller", return_value=mock_ctrl):
            _set_msg_ctx()
            agent = FakeAgent()

            _maybe_wrap_callbacks(agent)
            agent.interim_assistant_callback("Let me search for that")

            # on_thinking 被调了 (卡片消费)
            assert mock_ctrl.on_thinking.call_count == 1
            # 关键断言: 原始回调不应被调 (之前会调 → 重复消息)
            assert len(agent.interim_calls) == 0

    def test_card_disabled_calls_original_callback(self):
        """卡片禁用时, 正常调原始回调 → 降级为纯文本."""
        mock_ctrl = MagicMock()
        mock_ctrl.enabled = False
        with patch("hermes_lark_streaming.patching.hooks.get_controller", return_value=mock_ctrl):
            _set_msg_ctx()
            agent = FakeAgent()

            _maybe_wrap_callbacks(agent)
            agent.interim_assistant_callback("Let me search for that")

            # 卡片没消费, 原始回调应被调
            assert len(agent.interim_calls) == 1
            assert agent.interim_calls[0]["text"] == "Let me search for that"

    def test_exception_falls_through_to_original(self):
        """on_thinking_delta 抛异常时, 降级调原始回调."""
        mock_ctrl = MagicMock()
        mock_ctrl.enabled = True
        mock_ctrl.on_thinking = MagicMock(side_effect=RuntimeError("boom"))
        with patch("hermes_lark_streaming.patching.hooks.get_controller", return_value=mock_ctrl):
            _set_msg_ctx()
            agent = FakeAgent()

            _maybe_wrap_callbacks(agent)
            agent.interim_assistant_callback("Let me search for that")

            # 异常后仍调原始回调
            assert len(agent.interim_calls) == 1

    def test_empty_text_skips_card_not_original(self):
        """空文字不触发卡片消费, 但调原始回调."""
        mock_ctrl = _make_mock_ctrl()
        with patch("hermes_lark_streaming.patching.hooks.get_controller", return_value=mock_ctrl):
            _set_msg_ctx()
            agent = FakeAgent()

            _maybe_wrap_callbacks(agent)
            agent.interim_assistant_callback("")

            # 空文字不调 on_thinking
            assert mock_ctrl.on_thinking.call_count == 0
            # 原始回调应被调
            assert len(agent.interim_calls) == 1

    def test_already_streamed_kwarg_accepted_when_card_consumes(self):
        """already_streamed=True 时, 跳过卡片 on_thinking 但仍调原始回调.

        When Hermes sets already_streamed=True, it means the text was already
        delivered via stream_delta_callback.  We must NOT add it to the card
        (would cause duplication), but we MUST call the original callback so
        Hermes's _stream_consumer.on_segment_break() fires correctly.
        """
        mock_ctrl = _make_mock_ctrl()
        with patch("hermes_lark_streaming.patching.hooks.get_controller", return_value=mock_ctrl):
            _set_msg_ctx()
            agent = FakeAgent()

            _maybe_wrap_callbacks(agent)
            agent.interim_assistant_callback("text", already_streamed=True)

            # on_thinking 不应被调(文字已被 stream 消费, already_streamed=True)
            assert mock_ctrl.on_thinking.call_count == 0
            # 原始回调应被调(Hermes 需要 on_segment_break)
            assert len(agent.interim_calls) == 1
            assert agent.interim_calls[0]["kwargs"].get("already_streamed") is True

    def test_already_streamed_kwarg_passed_through_when_card_not_consumed(self):
        """卡片没消费时, already_streamed 应正确传递给原始回调."""
        mock_ctrl = MagicMock()
        mock_ctrl.enabled = False
        with patch("hermes_lark_streaming.patching.hooks.get_controller", return_value=mock_ctrl):
            _set_msg_ctx()
            agent = FakeAgent()

            _maybe_wrap_callbacks(agent)
            agent.interim_assistant_callback("text", already_streamed=True)

            # 卡片没消费, 原始回调应被调, 且 already_streamed=True 传递过去
            assert len(agent.interim_calls) == 1
            assert agent.interim_calls[0]["kwargs"].get("already_streamed") is True


class TestThinkingWrapperDedup:
    """thinking_wrapper 与 stream_delta 的 dedup 逻辑."""

    def setup_method(self):
        _clear_msg_ctx()

    def teardown_method(self):
        _clear_msg_ctx()

    def test_text_already_consumed_by_stream_delta_skips_card_but_passes_through(self):
        """当文字已被 stream_delta_callback 消费(卡片已展示),
        thinking_wrapper 应跳过 on_thinking_delta 但调原始回调.

        Length-based dedup: if the total text consumed by stream_delta_callback
        is >= the interim text length, the text was fully streamed already.
        We skip on_thinking_delta (prevent card duplication) but call
        _orig_interim (Hermes needs on_segment_break for state management).
        """
        mock_ctrl = _make_mock_ctrl()
        with patch("hermes_lark_streaming.patching.hooks.get_controller", return_value=mock_ctrl):
            _set_msg_ctx()
            agent = FakeAgent()

            _maybe_wrap_callbacks(agent)

            # 先通过 stream_delta 消费文字
            agent.stream_delta_callback("I'll search for that")

            # 然后同样的文字通过 interim_assistant_callback 传来
            agent.interim_assistant_callback("I'll search for that")

            # on_thinking 不应被调(文字已被 stream 消费, dedup)
            assert mock_ctrl.on_thinking.call_count == 0
            # 原始回调应被调(Hermes 需要 on_segment_break)
            assert len(agent.interim_calls) == 1
            # stream 也不应被调(卡片消费了)
            assert len(agent.stream_calls) == 0

    def test_different_text_from_stream_delta_goes_to_card(self):
        """当 interim 文字和 stream_delta 不同时, 应发到卡片."""
        mock_ctrl = _make_mock_ctrl()
        with patch("hermes_lark_streaming.patching.hooks.get_controller", return_value=mock_ctrl):
            _set_msg_ctx()
            agent = FakeAgent()

            _maybe_wrap_callbacks(agent)

            # stream_delta 发了文字 A
            agent.stream_delta_callback("searching...")

            # interim 发了文字 B(不同)
            agent.interim_assistant_callback("Let me search for that")

            # on_thinking 应被调(文字不同, 不是 dedup)
            assert mock_ctrl.on_thinking.call_count == 1
            # 卡片消费了, 原始回调不应被调
            assert len(agent.interim_calls) == 0
            # stream 也不应被调
            assert len(agent.stream_calls) == 0


# ── No Feishu context tests ──


class TestNoFeishuContext:
    """非飞书环境不应包装回调."""

    def setup_method(self):
        _clear_msg_ctx()

    def teardown_method(self):
        _clear_msg_ctx()

    def test_no_event_message_id_skips_wrapping(self):
        """无 event_message_id 时, 回调不应被包装."""
        agent = FakeAgent()
        orig_stream = agent.stream_delta_callback
        orig_interim = agent.interim_assistant_callback

        _maybe_wrap_callbacks(agent)

        # 回调应保持原样(没被包装)
        assert agent.stream_delta_callback is orig_stream
        assert agent.interim_assistant_callback is orig_interim


# ── Double-wrap guard tests ──


class TestDoubleWrapGuard:
    """防止回调被重复包装."""

    def setup_method(self):
        _clear_msg_ctx()

    def teardown_method(self):
        _clear_msg_ctx()

    def test_second_wrap_is_noop(self):
        """已经包装过的回调不应被二次包装."""
        mock_ctrl = _make_mock_ctrl()
        with patch("hermes_lark_streaming.patching.hooks.get_controller", return_value=mock_ctrl):
            _set_msg_ctx()
            agent = FakeAgent()

            _maybe_wrap_callbacks(agent)
            first_wrapper = agent.stream_delta_callback

            # 第二次调用应跳过
            _maybe_wrap_callbacks(agent)
            second_wrapper = agent.stream_delta_callback

            # 应该是同一个包装函数(没被重新包装)
            assert first_wrapper is second_wrapper


# ── Full pipeline simulation test ──


class TestFullPipelineSimulation:
    """模拟完整的 Hermes Agent + 插件 + _stream_consumer 链路.

    这是之前 567 个测试完全没覆盖的场景 — 验证当卡片消费文字时,
    原始回调(通往 _stream_consumer → adapter.send 的纯文本管道)不会被触发.
    """

    def setup_method(self):
        _clear_msg_ctx()

    def teardown_method(self):
        _clear_msg_ctx()

    def test_no_duplicate_message_when_card_active(self):
        """[核心场景] 卡片活跃时, 文字不应同时走卡片和纯文本两条管道.

        模拟:
          1. stream_delta_callback 收到 "搜索中" → 卡片消费 → 原始回调不调
          2. interim_assistant_callback 收到 "我来搜索一下" → 卡片消费 → 原始回调不调
          3. 更多流式输出

        期望: 原始回调(通往 _stream_consumer → adapter.send 的管道)不应被调.
        """
        mock_ctrl = _make_mock_ctrl()
        with patch("hermes_lark_streaming.patching.hooks.get_controller", return_value=mock_ctrl):
            _set_msg_ctx()
            agent = FakeAgent()

            _maybe_wrap_callbacks(agent)

            # Step 1: AI 逐字输出 → stream_delta
            agent.stream_delta_callback("搜索中")
            assert len(agent.stream_calls) == 0  # 卡片消费, 不走纯文本管道

            # Step 2: AI 中间状态消息 → interim_assistant
            agent.interim_assistant_callback("我来搜索一下")
            assert len(agent.interim_calls) == 0  # 卡片消费, 不走纯文本管道

            # Step 3: 更多流式输出
            agent.stream_delta_callback("这是搜索结果")
            assert len(agent.stream_calls) == 0

    def test_fallback_to_plain_text_when_card_disabled(self):
        """[降级场景] 卡片禁用时, 文字应走原始管道(纯文本)."""
        mock_ctrl = MagicMock()
        mock_ctrl.enabled = False
        with patch("hermes_lark_streaming.patching.hooks.get_controller", return_value=mock_ctrl):
            _set_msg_ctx()
            agent = FakeAgent()

            _maybe_wrap_callbacks(agent)

            # 卡片禁用 → 返回 False → 走原始管道
            agent.stream_delta_callback("搜索中")
            assert len(agent.stream_calls) == 1

            agent.interim_assistant_callback("我来搜索一下")
            assert len(agent.interim_calls) == 1

    def test_interim_with_already_streamed_true_card_active(self):
        """[already_streamed 场景] 卡片活跃 + already_streamed=True 时,
        on_thinking 被跳过, 原始回调被调以触发 on_segment_break.

        When already_streamed=True, Hermes tells us the text was already
        delivered via stream_delta_callback.  We must NOT add it to the card
        (would duplicate), but we MUST call the original callback so
        _stream_consumer.on_segment_break() fires correctly.
        """
        mock_ctrl = _make_mock_ctrl()
        with patch("hermes_lark_streaming.patching.hooks.get_controller", return_value=mock_ctrl):
            _set_msg_ctx()
            agent = FakeAgent()

            _maybe_wrap_callbacks(agent)

            # 模拟: stream_delta 先输出了 "搜索中"
            agent.stream_delta_callback("搜索中")

            # 然后 interim_assistant_callback 被调, same text + already_streamed=True
            agent.interim_assistant_callback("搜索中", already_streamed=True)

            # on_thinking 不应被调(文字已被 stream 消费, already_streamed=True)
            assert mock_ctrl.on_thinking.call_count == 0
            # 原始回调应被调(Hermes 需要 on_segment_break)
            assert len(agent.interim_calls) == 1
            assert agent.interim_calls[0]["kwargs"].get("already_streamed") is True
