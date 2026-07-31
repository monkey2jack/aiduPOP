"""End-to-end tests — full message → card pipeline.

v1.1.1: 群聊为主，私聊覆盖核心流程。
- 核心流程（TestCoreFlow）：群聊 + 私聊各跑一遍
- 其他测试：只跑群聊（和聊天场景无关，不需要重复私聊）
- 卡片结构：mock 专属

测试间自动加 2 秒延迟（真飞书模式）避免触发飞书 API 限流。
"""

from __future__ import annotations

import asyncio
import pytest

# v1.1.1: 只有核心流程参数化群聊+私聊
_CHAT_MODES = [
    pytest.param(False, id="群聊"),
    pytest.param(True, id="私聊"),
]


class TestCoreFlow:
    """核心流程测试——群聊 + 私聊各跑一遍."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("use_open_id", _CHAT_MODES)
    async def test_basic_answer(self, runner, use_open_id):
        """基本答案：发消息 → AI 回复 → 卡片显示答案 → 封卡."""
        session = await runner.start_message("hello", use_open_id=use_open_id)
        await runner.feed_answer(session, "Hello! How can I help you?")
        await runner.complete(session, answer="Hello! How can I help you?")

        runner.assert_card_created(session)
        await runner.assert_card_sealed(session)
        answer = runner.get_answer_text(session)
        assert "Hello! How can I help you?" in answer, f"答案未显示在卡片中: {answer!r}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("use_open_id", _CHAT_MODES)
    async def test_reasoning_and_tools(self, runner, use_open_id):
        """推理 + 工具：AI 回复含推理过程和工具调用."""
        session = await runner.start_message("search and explain", use_open_id=use_open_id)
        await runner.feed_reasoning(session, "Let me search for that.")
        await runner.feed_tool_update(session, tool_name="web_search", status="success", detail="query=test")
        await runner.feed_answer(session, "Here is the result.")
        await runner.complete(session, answer="Here is the result.")

        runner.assert_card_created(session)
        await runner.assert_card_sealed(session)
        panel = runner.get_panel_elements(session)
        assert len(panel) > 0, "面板应包含推理和工具元素"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("use_open_id", _CHAT_MODES)
    async def test_multiple_answer_deltas(self, runner, use_open_id):
        """多段答案拼接：多个 delta 应拼接成完整答案."""
        session = await runner.start_message("tell me a story", use_open_id=use_open_id)
        for chunk in ["Once upon a time, ", "there was a plugin ", "that rendered cards."]:
            await runner.feed_answer(session, chunk)
        await runner.complete(session, answer="Once upon a time, there was a plugin that rendered cards.")

        runner.assert_card_created(session)
        await runner.assert_card_sealed(session)
        answer = runner.get_answer_text(session)
        assert "Once upon a time" in answer, "答案缺少开头部分"
        assert "rendered cards" in answer, "答案缺少结尾部分"


class TestBugFixes:
    """v1.1.1 Bug 修复验证——只跑群聊（和聊天场景无关）."""

    @pytest.mark.asyncio
    async def test_drain_300309_fallback(self, runner):
        """drain 遇 300309 改用 batch_update 写入答案."""
        from hermes_lark_streaming.feishu import FeishuAPIError, CARDKIT_STREAMING_CLOSED
        from unittest.mock import AsyncMock

        session = await runner.start_message("test 300309")
        await runner.feed_answer(session, "answer after streaming closed")

        original = runner.controller._client.cardkit_stream_element
        runner.controller._client.cardkit_stream_element = AsyncMock(
            side_effect=FeishuAPIError("test", code=CARDKIT_STREAMING_CLOSED)
        )
        await runner.complete(session, answer="answer after streaming closed")
        runner.controller._client.cardkit_stream_element = original

        runner.assert_card_created(session)
        await runner.assert_card_sealed(session)
        answer = runner.get_answer_text(session)
        assert "streaming closed" in answer, "300309 fallback 后答案未写入"

    @pytest.mark.asyncio
    async def test_drain_300313_fallback_no_tag(self, runner):
        """drain 遇 300313 fallback 不带 tag."""
        from hermes_lark_streaming.feishu import FeishuAPIError, CARDKIT_ELEMENT_NOT_FOUND
        from unittest.mock import AsyncMock

        session = await runner.start_message("test 300313")
        await runner.feed_answer(session, "answer for 313 test")

        original = runner.controller._client.cardkit_stream_element
        runner.controller._client.cardkit_stream_element = AsyncMock(
            side_effect=FeishuAPIError("test", code=CARDKIT_ELEMENT_NOT_FOUND)
        )
        await runner.complete(session, answer="answer for 313 test")
        runner.controller._client.cardkit_stream_element = original

        runner.assert_card_created(session)
        await runner.assert_card_sealed(session)
        answer = runner.get_answer_text(session)
        assert "313 test" in answer, "300313 fallback 后答案未写入"


class TestSessionManagement:
    """session 管理测试——只跑群聊（和聊天场景无关）."""

    @pytest.mark.asyncio
    async def test_prune_skips_streaming_session(self, runner):
        """STREAMING 状态的 session 超 TTL 不被清理."""
        session = await runner.start_message("long running task")
        await runner.feed_answer(session, "partial answer")

        assert runner.simulate_session_age(session.message_id, 700) is True
        session2 = await runner.start_message("new message after TTL")

        assert session.message_id in runner.controller._sessions, "活跃 session 不应被清理"
        assert session2.message_id in runner.controller._sessions, "新 session 应存在"

    @pytest.mark.asyncio
    async def test_prune_cleans_completed_session(self, runner):
        """COMPLETED 状态的 session 超 TTL 正常清理."""
        session = await runner.start_message("completed task")
        await runner.feed_answer(session, "done")
        await runner.complete(session, answer="done")

        from hermes_lark_streaming.state.phase import CardPhase
        for _ in range(20):
            if runner.controller._sessions[session.message_id].state == CardPhase.COMPLETED:
                break
            await asyncio.sleep(0.5)
        assert runner.controller._sessions[session.message_id].state == CardPhase.COMPLETED, \
            "session 应为 COMPLETED 状态"

        assert runner.simulate_session_age(session.message_id, 700) is True
        session2 = await runner.start_message("new message")

        assert session.message_id not in runner.controller._sessions, "终态 session 超时应被清理"
        assert session2.message_id in runner.controller._sessions, "新 session 应存在"

    @pytest.mark.asyncio
    async def test_release_session_data_after_seal(self, runner):
        """封卡后重数据被释放."""
        session = await runner.start_message("test release data")
        await runner.feed_answer(session, "answer to be released")
        await runner.complete(session, answer="answer to be released")

        if runner.is_real_mode:
            for _ in range(20):
                if runner.controller._sessions[session.message_id].unified_state is None:
                    break
                await asyncio.sleep(0.5)

        assert runner.controller._sessions[session.message_id].unified_state is None, \
            "封卡后 unified_state 应被释放"


class TestCardLifecycle:
    """卡片生命周期测试——只跑群聊（和聊天场景无关）."""

    @pytest.mark.asyncio
    async def test_error_recovery(self, runner):
        """错误恢复：AI 报错 → 卡片仍能封卡."""
        session = await runner.start_message("trigger error")
        await runner.feed_answer(session, "partial")
        await runner.complete(session, answer="partial", error_message="AI encountered an error")

        runner.assert_card_created(session)
        await runner.assert_card_sealed(session)

    @pytest.mark.asyncio
    async def test_interrupted_by_new_message(self, runner):
        """中断恢复：新消息中断旧消息 → 旧卡 seal."""
        session1 = await runner.start_message("first message")
        await runner.feed_answer(session1, "first answer")

        runner.controller.on_interrupted(
            old_message_id=session1.message_id,
            new_message_id=f"{session1.message_id}_new",
            chat_id=session1.chat_id,
            anchor_id=session1.anchor_id or session1.message_id,
        )

        if runner.is_real_mode:
            for _ in range(20):
                await asyncio.sleep(0.5)
                if session1.is_terminal_phase:
                    break
        else:
            await asyncio.sleep(1.0)

        assert session1.state in ("aborted", "terminated", "completed"), \
            f"旧 session 应为终态，实际: {session1.state}"

    @pytest.mark.asyncio
    async def test_long_answer(self, runner):
        """长答案：20 段 delta 拼接 + 封卡完整."""
        session = await runner.start_message("long answer test")
        chunks = [f"Chunk {i}. " for i in range(20)]
        full_answer = "".join(chunks)
        for chunk in chunks:
            await runner.feed_answer(session, chunk)
        await runner.complete(session, answer=full_answer)

        runner.assert_card_created(session)
        await runner.assert_card_sealed(session)
        answer = runner.get_answer_text(session)
        assert "Chunk 0" in answer, "长答案缺少开头"
        assert "Chunk 19" in answer, "长答案缺少结尾"


class TestCardStructure:
    """卡片结构测试——mock 专属（真飞书无法查元素）."""

    @pytest.mark.asyncio
    async def test_card_structure(self, runner):
        """卡片元素结构：loading hint → answer element → 移除 hint."""
        if runner.is_real_mode:
            pytest.skip("卡片结构检查仅在 mock 模式下可用（真飞书无法查询卡片元素）")

        from hermes_lark_streaming.cardkit.elements import (
            _LOADING_HINT_ELEMENT_ID,
            ANSWER_ELEMENT_ID,
        )

        session = await runner.start_message("test")
        card = runner.get_card(session)
        assert card is not None, "卡片未创建"
        assert _LOADING_HINT_ELEMENT_ID not in card.elements, "定制初始卡片不应显示加载提示"

        await runner.feed_answer(session, "Answer text")
        await asyncio.sleep(0.2)

        card = runner.get_card(session)
        assert card is not None, "卡片未创建"
        assert _LOADING_HINT_ELEMENT_ID not in card.elements, "加载提示应被移除"
        assert ANSWER_ELEMENT_ID in card.elements, "答案元素应存在"
