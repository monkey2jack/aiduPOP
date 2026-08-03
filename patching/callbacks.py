"""Callback wrapping for AIAgent streaming callbacks."""

from __future__ import annotations

import time
from typing import Any

from . import (
    _msg_ctx,
    _thread_local_ctx,
    _logger,
    _get_event_message_id,
    _model_cache,
)

def _resolve_eid(fallback_eid: str | None) -> str | None:
    """Re-resolve the current event_message_id from _msg_ctx at call time."""
    _eid = _get_event_message_id()
    return _eid if _eid else fallback_eid

def _maybe_wrap_callbacks(agent) -> None:
    """Replace streaming callbacks on *agent* with wrappers that also fire
    Feishu CardKit updates.  Skips silently when outside a Feishu message
    context (i.e. no event_message_id in context)."""
    _logger.debug("HLS: _maybe_wrap_callbacks invoked, has_stream=%s, eid_lookup=%s", bool(getattr(agent, "stream_delta_callback", None)), bool(_get_event_message_id()))

    # ── 【嘟嘟定制 v22.2 根治】模块级全局缓存 ──
    # _model_cache 是普通 Python dict，不依赖 contextvar/thread-local/asyncio task 边界。
    # 同一进程内 any 线程/task 都能读到。升级时 grep 此标记找回所有定制点。
    #
    # 【嘟嘟定制 v22.4 修复】辅助 agent 禁止污染 _model_cache。
    # 症状：后台复盘 fork（auxiliary.background_review 走 aux 模型）在独立线程里
    # 调 _maybe_wrap_callbacks，拿不到 event_message_id，只写了 _model_cache["current"]。
    # 主卡片封版渲染 panel 时若 eid 未命中，fallback 读 "current"，
    # 就把 aux 模型名（如 Grok-4.5）印到大叔的卡片上。
    # 判定依据：background_review.py 给 fork 打了 _memory_write_origin /
    # _persist_disabled 标记；正常主 agent 不带这些。
    ctx = _msg_ctx.get()
    model_val = getattr(agent, "model", None)
    _is_aux_fork = (
        getattr(agent, "_memory_write_origin", None) == "background_review"
        or getattr(agent, "_memory_write_context", None) == "background_review"
        or getattr(agent, "_persist_disabled", False) is True
    )
    if model_val and not _is_aux_fork:
        _model_cache["current"] = model_val
        eid = (ctx.get("event_message_id") if ctx else None) or _get_event_message_id()
        if eid:
            if len(_model_cache) > 500:
                for k in list(_model_cache.keys()):
                    if k != "current":
                        del _model_cache[k]
            _model_cache[eid] = model_val
    elif _is_aux_fork:
        _logger.debug(
            "HLS: skip _model_cache write for aux fork model=%s", model_val
        )
    if ctx is not None and not _is_aux_fork:
        ctx["_agent_ref"] = agent
        ctx["_agent_model"] = model_val or ""
        _thread_local_ctx.data = dict(ctx)

    eid = _get_event_message_id()
    if not eid:
        _logger.debug("HLS: skip — no event_message_id in ctx")
        return  # Not in a hermes-lark-streaming context — skip

    # ── 【嘟嘟定制：细粒度回调包装】 ──
    # 不再因为 "任何一个已被包装" 就整体跳过，而是每个 callback 独立按需包装，
    # 彻底解决切换模型后部分 callback 被重置导致未能包装的 Bug。

    # 共享流式去重状态
    _stream_consumed_len: dict[str, int] = {}

    def _cleanup_consumed_len(_eid: str) -> None:
        """Remove consumed-length tracking for a completed message."""
        _stream_consumed_len.pop(_eid, None)

    # 1. 包装 stream_delta_callback
    _current_stream = getattr(agent, "stream_delta_callback", None)
    if _current_stream and not getattr(_current_stream, "_hls_wrapper", False):
        _orig_stream = _current_stream

        def _answer_wrapper(text, *args, **kwargs):
            _eid = _resolve_eid(eid)
            if not _eid:
                return _orig_stream(text, *args, **kwargs)
            try:
                from .hooks import on_answer_delta

                if text and on_answer_delta(message_id=_eid, text=text):
                    # Record total consumed length for dedup with interim_assistant_callback
                    _stream_consumed_len[_eid] = _stream_consumed_len.get(_eid, 0) + len(text)
                    return
            except Exception:
                _logger.debug("HLS: answer_wrapper exception", exc_info=True)
            return _orig_stream(text, *args, **kwargs)

        agent.stream_delta_callback = _answer_wrapper
        setattr(agent.stream_delta_callback, "_hls_wrapper", True)
        _logger.debug("HLS: _maybe_wrap_callbacks stream_delta_callback wrapped")
    elif not _current_stream:
        # Fix: Create our own stream_delta_callback that routes answer tokens to
        def _answer_wrapper_synthetic(text, *args, **kwargs):
            if text is None:
                return
            _eid = _resolve_eid(eid)
            if not _eid:
                return
            try:
                from .hooks import on_answer_delta

                if text and on_answer_delta(message_id=_eid, text=text):
                    _stream_consumed_len[_eid] = _stream_consumed_len.get(_eid, 0) + len(text)
                    return
            except Exception:
                _logger.debug("HLS: answer_wrapper_synthetic exception", exc_info=True)

        agent.stream_delta_callback = _answer_wrapper_synthetic
        setattr(agent.stream_delta_callback, "_hls_wrapper", True)

    # 2. 包装 interim_assistant_callback
    _current_interim = getattr(agent, "interim_assistant_callback", None)
    if not _current_interim or not getattr(_current_interim, "_hls_wrapper", False):
        _orig_interim = _current_interim if _current_interim else None

        def _thinking_wrapper(text, *args, **kwargs):
            _eid = _resolve_eid(eid)
            if not _eid:
                if _orig_interim:
                    return _orig_interim(text, *args, **kwargs)
                return
            try:
                already_streamed = kwargs.get("already_streamed", False)
                if already_streamed:
                    _cleanup_consumed_len(_eid)
                    if _orig_interim:
                        return _orig_interim(text, *args, **kwargs)
                    return

                consumed_len = _stream_consumed_len.get(_eid, 0)
                if text and consumed_len > 0 and len(text) <= consumed_len:
                    _cleanup_consumed_len(_eid)
                    if _orig_interim:
                        return _orig_interim(text, *args, **kwargs)
                    return

                if text:
                    from .hooks import on_thinking_delta
                    consumed = on_thinking_delta(message_id=_eid, text=text)
                    if consumed:
                        return
            except Exception:
                _logger.debug("HLS: thinking_wrapper exception", exc_info=True)
            if _orig_interim:
                return _orig_interim(text, *args, **kwargs)

        agent.interim_assistant_callback = _thinking_wrapper
        setattr(agent.interim_assistant_callback, "_hls_wrapper", True)
        _logger.debug("HLS: _maybe_wrap_callbacks interim_assistant_callback wrapped")

    # 3. 包装 tool_progress_callback
    _current_tool = getattr(agent, "tool_progress_callback", None)
    if not _current_tool or not getattr(_current_tool, "_hls_wrapper", False):
        _orig_tool = _current_tool if _current_tool else None

        def _tool_wrapper(event_type, tool_name=None, preview=None, *args, **kwargs):
            _eid = _resolve_eid(eid)
            if not _eid:
                if _orig_tool:
                    return _orig_tool(event_type, tool_name, preview, *args, **kwargs)
                return
            try:
                from .hooks import on_tool_updated

                if event_type in ("tool.started", "tool.completed"):
                    if on_tool_updated(
                        message_id=_eid,
                        tool_name=tool_name or "",
                        status="started" if event_type == "tool.started" else "completed",
                        detail=preview or "",
                    ):
                        return
            except Exception:
                _logger.debug("HLS: tool_wrapper exception", exc_info=True)
            if _orig_tool:
                return _orig_tool(event_type, tool_name, preview, *args, **kwargs)

        agent.tool_progress_callback = _tool_wrapper
        setattr(agent.tool_progress_callback, "_hls_wrapper", True)

    # 4. 包装 reasoning_callback
    _current_reasoning = getattr(agent, "reasoning_callback", None)
    if not _current_reasoning or not getattr(_current_reasoning, "_hls_wrapper", False):
        _orig_reasoning = _current_reasoning if _current_reasoning else None

        def _reasoning_wrapper(text, *args, **kwargs):
            _eid = _resolve_eid(eid)
            if not _eid:
                if _orig_reasoning and not getattr(_orig_reasoning, "_hls_wrapper", False):
                    return _orig_reasoning(text, *args, **kwargs)
                return
            try:
                from .hooks import on_reasoning_delta

                if text:
                    on_reasoning_delta(message_id=_eid, text=text)
            except Exception:
                _logger.debug("HLS: reasoning_wrapper exception", exc_info=True)
            if _orig_reasoning and not getattr(_orig_reasoning, "_hls_wrapper", False):
                return _orig_reasoning(text, *args, **kwargs)

        agent.reasoning_callback = _reasoning_wrapper
        setattr(agent.reasoning_callback, "_hls_wrapper", True)

    # 5. 包装 background_review_callback
    _current_bg = getattr(agent, "background_review_callback", None)
    if not _current_bg or not getattr(_current_bg, "_hls_wrapper", False):
        _orig_bg = _current_bg if _current_bg else None

        def _bg_wrapper(message, *args, **kwargs):
            _eid = _resolve_eid(eid)
            if not _eid:
                if _orig_bg:
                    return _orig_bg(message, *args, **kwargs)
                return
            try:
                from .hooks import on_background_review_message

                deferred = on_background_review_message(
                    message_id=_eid,
                    text=message,
                    sender=_orig_bg,
                )
                if deferred:
                    return
            except Exception:
                _logger.debug("HLS: bg_wrapper exception", exc_info=True)
            if _orig_bg:
                return _orig_bg(message, *args, **kwargs)

        agent.background_review_callback = _bg_wrapper
        setattr(agent.background_review_callback, "_hls_wrapper", True)
