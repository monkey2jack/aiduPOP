"""End-to-end test framework for hermes-lark-streaming.

v1.1.0 (Task 3.4): Full e2e test framework with mock Feishu API server
and mock Hermes components. Tests verify the complete message → card JSON
pipeline without needing a real Feishu account or Hermes installation.

Architecture:
  - MockFeishuServer: Simulates Feishu CardKit + IM API endpoints
  - MockFeishuClient: Drop-in replacement for FeishuClient that uses the mock server
  - MockHermesAgent: Simulates AIAgent callback invocation (answer/reasoning/tool)
  - E2ETestRunner: Orchestrates the full flow: create session → feed deltas → verify card

Usage:
  from tests.e2e.framework import E2ETestRunner, MockFeishuServer

  async def test_simple_answer():
      runner = E2ETestRunner()
      await runner.setup()
      try:
          session = await runner.start_message("hello")
          await runner.feed_answer_delta(session, "Hello ")
          await runner.feed_answer_delta(session, "world!")
          await runner.complete_message(session)
          card = runner.get_final_card(session)
          assert "Hello world!" in card["answer_text"]
      finally:
          await runner.teardown()
"""
