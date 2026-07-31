"""flush.py 测试 — FlushController 节流、刷新、完成逻辑."""

from __future__ import annotations

import asyncio
import threading
import time

import pytest

from hermes_lark_streaming.flush import (
    BATCH_AFTER_GAP_MS,
    LONG_GAP_MS,
    FlushController,
)


def _make_async(**kwargs: object) -> FlushController:
    """必须在 async 测试内调用，以捕获正确的事件循环."""
    return FlushController(**kwargs)  # type: ignore[arg-type]


class TestScheduleUpdate:
    @pytest.mark.asyncio
    async def test_first_call_schedules_delayed_flush(self) -> None:
        ctrl = _make_async(throttle_ms=0.100)  # 使用显式 100ms 节流，不依赖默认值
        ctrl.set_card_message_ready(True)
        flushed = asyncio.Event()

        async def do_flush() -> None:
            flushed.set()

        # 第一次调用: elapsed ≈ 0 < throttle_ms → 延迟路径
        ctrl.schedule_update(do_flush)
        await asyncio.sleep(0.05)
        assert not flushed.is_set()  # 还没触发
        await asyncio.sleep(0.10)
        assert flushed.is_set()  # 节流窗口过后触发

    @pytest.mark.asyncio
    async def test_immediate_path_taken_after_elapsed(self) -> None:
        ctrl = _make_async(throttle_ms=0.05)  # 50ms
        ctrl.set_card_message_ready(True)
        count = 0

        async def do_flush() -> None:
            nonlocal count
            count += 1

        # 等待节流窗口过去
        await asyncio.sleep(0.08)
        ctrl.schedule_update(do_flush)
        # 无 pending timer 说明走了立即路径（via call_soon）
        assert ctrl._pending_timer is None
        # call_soon → create_task 管道需要时间传播
        await asyncio.sleep(0.2)
        assert count == 1

    @pytest.mark.asyncio
    async def test_no_flush_when_not_ready(self) -> None:
        ctrl = _make_async()
        # card_message_ready 为 False
        count = 0

        async def do_flush() -> None:
            nonlocal count
            count += 1

        ctrl.schedule_update(do_flush)
        await asyncio.sleep(0.05)
        assert count == 0

    @pytest.mark.asyncio
    async def test_no_flush_after_completed(self) -> None:
        ctrl = _make_async()
        ctrl.set_card_message_ready(True)
        ctrl.mark_completed()
        count = 0

        async def do_flush() -> None:
            nonlocal count
            count += 1

        ctrl.schedule_update(do_flush)
        await asyncio.sleep(0.05)
        assert count == 0

    @pytest.mark.asyncio
    async def test_long_gap_schedules_delayed_batch(self) -> None:
        ctrl = _make_async()
        ctrl.set_card_message_ready(True)
        count = 0

        async def do_flush() -> None:
            nonlocal count
            count += 1

        # 模拟长时间空闲
        ctrl._last_update_time = time.monotonic() - LONG_GAP_MS - 1.0
        ctrl.schedule_update(do_flush)
        # 不应立即刷新
        await asyncio.sleep(0.01)
        assert count == 0
        # 延迟批量刷新后触发
        await asyncio.sleep(BATCH_AFTER_GAP_MS + 0.05)
        assert count == 1


class TestFlushNow:
    @pytest.mark.asyncio
    async def test_flush_now_executes_immediately(self) -> None:
        ctrl = _make_async()
        ctrl.set_card_message_ready(True)
        count = 0

        async def do_flush() -> None:
            nonlocal count
            count += 1

        await ctrl.flush_now(do_flush)
        assert count == 1

    @pytest.mark.asyncio
    async def test_flush_now_skips_when_completed(self) -> None:
        ctrl = _make_async()
        ctrl.set_card_message_ready(True)
        ctrl.mark_completed()
        count = 0

        async def do_flush() -> None:
            nonlocal count
            count += 1

        await ctrl.flush_now(do_flush)
        assert count == 0

    @pytest.mark.asyncio
    async def test_flush_now_skips_when_not_ready(self) -> None:
        ctrl = _make_async()
        count = 0

        async def do_flush() -> None:
            nonlocal count
            count += 1

        await ctrl.flush_now(do_flush)
        assert count == 0

    @pytest.mark.asyncio
    async def test_flush_now_cancels_pending_timer(self) -> None:
        ctrl = _make_async(throttle_ms=500.0)
        ctrl.set_card_message_ready(True)
        count = 0

        async def do_flush() -> None:
            nonlocal count
            count += 1

        # 构造一个 pending timer 的场景
        # schedule_update 现在通过 call_soon_threadsafe 调度，
        # 需要让事件循环处理回调后 _pending_timer 才会被设置
        ctrl._last_update_time = time.monotonic() - 0.05
        ctrl.schedule_update(do_flush)
        await asyncio.sleep(0.01)  # 让事件循环处理 call_soon_threadsafe 回调
        assert ctrl._pending_timer is not None
        await ctrl.flush_now(do_flush)
        assert ctrl._pending_timer is None


class TestWaitForFlush:
    @pytest.mark.asyncio
    async def test_returns_immediately_when_idle(self) -> None:
        ctrl = _make_async()
        ctrl.set_card_message_ready(True)
        await ctrl.wait_for_flush()  # 不应挂起

    @pytest.mark.asyncio
    async def test_waits_for_flush_to_complete(self) -> None:
        ctrl = _make_async()
        ctrl.set_card_message_ready(True)
        flush_event = asyncio.Event()
        count = 0

        async def slow_flush() -> None:
            nonlocal count
            count += 1
            await flush_event.wait()

        # 启动一个阻塞的 flush
        _task = asyncio.create_task(ctrl._do_flush(slow_flush))
        await asyncio.sleep(0.02)
        assert ctrl._flush_in_progress

        # wait_for_flush 应阻塞
        waiter = asyncio.create_task(ctrl.wait_for_flush())
        await asyncio.sleep(0.02)
        assert not waiter.done()

        # 释放 flush
        flush_event.set()
        await asyncio.sleep(0.02)
        assert waiter.done()


class TestMarkCompleted:
    @pytest.mark.asyncio
    async def test_prevents_future_flushes(self) -> None:
        ctrl = _make_async()
        ctrl.set_card_message_ready(True)
        ctrl.mark_completed()
        count = 0

        async def do_flush() -> None:
            nonlocal count
            count += 1

        await ctrl.flush_now(do_flush)
        assert count == 0

    @pytest.mark.asyncio
    async def test_resolves_waiters(self) -> None:
        ctrl = _make_async()
        ctrl.set_card_message_ready(True)
        flush_event = asyncio.Event()

        async def blocking_flush() -> None:
            await flush_event.wait()

        _task = asyncio.create_task(ctrl._do_flush(blocking_flush))
        await asyncio.sleep(0.02)

        waiter = asyncio.create_task(ctrl.wait_for_flush())
        await asyncio.sleep(0.02)
        assert not waiter.done()

        ctrl.mark_completed()
        await asyncio.sleep(0.02)
        assert waiter.done()


class TestReflush:
    @pytest.mark.asyncio
    async def test_needs_reflush_during_active_flush(self) -> None:
        ctrl = _make_async()
        ctrl.set_card_message_ready(True)
        flush_event = asyncio.Event()
        count = 0

        async def slow_flush() -> None:
            nonlocal count
            count += 1
            if count == 1:
                await flush_event.wait()

        # 启动一个慢 flush
        task = asyncio.create_task(ctrl._do_flush(slow_flush))
        await asyncio.sleep(0.02)
        assert ctrl._flush_in_progress

        # 再次尝试 flush → 应设置 reflush 标志
        asyncio.create_task(ctrl._do_flush(slow_flush))
        await asyncio.sleep(0.02)
        assert ctrl._needs_reflush

        # 释放第一个 flush
        flush_event.set()
        await task
        await asyncio.sleep(0.02)
        # reflush 应自动触发
        assert count >= 2


class TestSetCardMessageReady:
    @pytest.mark.asyncio
    async def test_enables_flushing(self) -> None:
        ctrl = _make_async(throttle_ms=0.100)  # 使用显式 100ms 节流
        count = 0

        async def do_flush() -> None:
            nonlocal count
            count += 1

        ctrl.schedule_update(do_flush)
        await asyncio.sleep(0.05)
        assert count == 0

        ctrl.set_card_message_ready(True)
        # 等待节流窗口过去
        await asyncio.sleep(0.15)
        ctrl.schedule_update(do_flush)
        await asyncio.sleep(0.05)
        assert count == 1

    @pytest.mark.asyncio
    async def test_initializes_timestamp(self) -> None:
        ctrl = _make_async()
        assert ctrl.last_update_time == 0.0
        ctrl.set_card_message_ready(True)
        assert ctrl.last_update_time > 0.0


class TestFlushException:
    @pytest.mark.asyncio
    async def test_exception_does_not_break_controller(self) -> None:
        ctrl = _make_async()
        ctrl.set_card_message_ready(True)
        count = 0

        async def failing_flush() -> None:
            nonlocal count
            count += 1
            if count == 1:
                raise RuntimeError("test error")

        await ctrl._do_flush(failing_flush)
        assert count == 1
        assert not ctrl._flush_in_progress

    @pytest.mark.asyncio
    async def test_exception_still_updates_timestamp(self) -> None:
        ctrl = _make_async()
        ctrl.set_card_message_ready(True)
        before = ctrl.last_update_time

        async def failing_flush() -> None:
            raise RuntimeError("test")

        await ctrl._do_flush(failing_flush)
        assert ctrl.last_update_time >= before


class TestSetThrottle:
    @pytest.mark.asyncio
    async def test_updates_throttle(self) -> None:
        ctrl = _make_async()
        ctrl.set_throttle(500.0)
        assert ctrl.throttle_ms == 500.0


class TestThreadSafeScheduleUpdate:
    """Tests for call_soon_threadsafe fix — schedule_update from worker threads.

    v0.10.1 fix: schedule_update now uses call_soon_threadsafe to ensure
    the event loop is woken up when called from a worker thread.
    This was the root cause of the "marquee with no text" bug.
    """

    @pytest.mark.asyncio
    async def test_schedule_update_from_worker_thread(self) -> None:
        """schedule_update called from a worker thread should trigger flush on the event loop."""
        ctrl = _make_async(throttle_ms=0.05)
        ctrl.set_card_message_ready(True)
        flushed = asyncio.Event()

        async def do_flush() -> None:
            flushed.set()

        # Call schedule_update from a worker thread (simulates LLM streaming callback)
        def worker_call():
            time.sleep(0.01)  # small delay to ensure we're truly in a worker thread
            ctrl.schedule_update(do_flush)

        t = threading.Thread(target=worker_call, daemon=True)
        t.start()

        # The event loop should be woken up and the flush should execute
        await asyncio.sleep(0.3)
        assert flushed.is_set(), "Flush should have been triggered from worker thread via call_soon_threadsafe"
        t.join(timeout=1.0)

    @pytest.mark.asyncio
    async def test_multiple_worker_thread_calls(self) -> None:
        """Multiple schedule_update calls from worker threads should not lose updates."""
        ctrl = _make_async(throttle_ms=0.05)
        ctrl.set_card_message_ready(True)
        count = 0

        async def do_flush() -> None:
            nonlocal count
            count += 1

        # Simulate rapid LLM streaming callbacks from worker threads
        barrier = threading.Barrier(3, timeout=5.0)

        def worker_call():
            barrier.wait()
            ctrl.schedule_update(do_flush)

        threads = [threading.Thread(target=worker_call, daemon=True) for _ in range(3)]
        for t in threads:
            t.start()

        # Wait for all threads to fire and at least one flush to complete
        await asyncio.sleep(0.5)
        # At least one flush should have been triggered (throttle may coalesce)
        assert count >= 1, "At least one flush should have been triggered from worker threads"
        for t in threads:
            t.join(timeout=1.0)

    @pytest.mark.asyncio
    async def test_closed_loop_does_not_crash(self) -> None:
        """schedule_update should not crash when event loop is closed."""
        ctrl = _make_async(throttle_ms=0.05)
        ctrl.set_card_message_ready(True)

        async def do_flush() -> None:
            pass

        # This should not raise even if the loop is in a weird state
        # The call_soon_threadsafe wrapper catches RuntimeError
        ctrl.schedule_update(do_flush)
        await asyncio.sleep(0.05)

    @pytest.mark.asyncio
    async def test_schedule_update_from_event_loop_thread_still_works(self) -> None:
        """schedule_update called from the event loop thread should still work correctly."""
        ctrl = _make_async(throttle_ms=0.05)
        ctrl.set_card_message_ready(True)
        flushed = asyncio.Event()

        async def do_flush() -> None:
            flushed.set()

        # Wait for throttle window to pass
        await asyncio.sleep(0.08)
        # Call from the event loop thread directly
        ctrl.schedule_update(do_flush)
        # Should trigger immediately since elapsed > throttle_ms
        await asyncio.sleep(0.3)
        assert flushed.is_set(), "Flush should have been triggered from event loop thread"
