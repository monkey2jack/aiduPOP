"""Hermes compatibility adapter — isolates all Hermes internal interface access."""

from __future__ import annotations
import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any, Optional

_logger = logging.getLogger("hermes_lark_streaming")

class HermesCompat:
    """Encapsulates all Hermes internal module access."""
    
    def __init__(self):
        self._detect_version()
        self._resolve_modules()
    
    def _detect_version(self) -> None:
        """Detect Hermes version from various sources."""
        self.hermes_version: str = "unknown"
        
        # Try importlib.metadata
        try:
            from importlib.metadata import version
            self.hermes_version = version("hermes-agent")
        except Exception:
            _logger.debug("HLS: importlib.metadata version lookup failed", exc_info=True)
        
        # Try __version__ attribute
        if self.hermes_version == "unknown":
            try:
                import hermes_cli
                self.hermes_version = getattr(hermes_cli, "__version__", "unknown")
            except Exception:
                _logger.debug("HLS: hermes_cli version lookup failed", exc_info=True)
        
        _logger.info("HLS: Hermes version detected: %s", self.hermes_version)
    
    def _resolve_modules(self) -> None:
        """Resolve all Hermes internal modules, recording what's available."""
        self.gateway_runner_class: Any | None = None
        self.aiagent_class: Any | None = None
        self.feishu_adapter_class: Any | None = None
        self.cron_scheduler_module: Any | None = None
        self.conversation_loop_module: Any | None = None
        self.conversation_loop_func: Any | None = None
        self.run_agent_module: Any | None = None

        # GatewayRunner — resolve from sys.modules and known aliases (deadlock-safe)
        for _name, _mod in list(sys.modules.items()):
            if _mod is None:
                continue
            if _name in ("gateway.run", "gateway.run_inbound", "gateway.run_turn") or _name.endswith(".gateway.run"):
                _cls = getattr(_mod, "GatewayRunner", None)
                if _cls is not None:
                    self.gateway_runner_class = _cls
                    break
        if self.gateway_runner_class is None:
            _logger.debug("HLS: GatewayRunner not available yet (gateway.run not in sys.modules)")

        # AIAgent — resolve from sys.modules and known aliases (deadlock-safe)
        for _name, _mod in list(sys.modules.items()):
            if _mod is None:
                continue
            if _name == "run_agent" or _name.endswith(".run_agent"):
                _cls = getattr(_mod, "AIAgent", None)
                if _cls is not None:
                    self.run_agent_module = _mod
                    self.aiagent_class = _cls
                    break
        if self.aiagent_class is None:
            _logger.debug("HLS: AIAgent not available yet (run_agent not in sys.modules)")
        
        # FeishuAdapter — 抽取到 _resolve_feishu_adapter()，
        # 便于 resolve_feishu_adapter_class_fresh() 复用（v1.4.0: fix deferred loading patch miss）
        self.feishu_adapter_class = self._resolve_feishu_adapter()
        
        # Cron scheduler
        for mod_name in ("cron.scheduler", "gateway.cron.scheduler"):
            try:
                mod = importlib.import_module(mod_name)
                if hasattr(mod, "_deliver_result"):
                    self.cron_scheduler_module = mod
                    break
            except ImportError:
                continue
        
        # Conversation loop (with namespace collision workaround)
        self._resolve_conversation_loop()
    
    def _resolve_feishu_adapter(self) -> Any | None:
        """Resolve FeishuAdapter class through the gateway's namespace."""
        # 顺序很关键：真身（hermes_plugins.feishu_platform.adapter）优先，确保
        # 如果 deferred loader 已触发，我们能拿到 gateway 实际使用的 class object。
        _feishu_import_paths = [
            "hermes_plugins.feishu_platform.adapter",  # Hermes v0.17+ (gateway runtime 真身)
            "plugins.platforms.feishu.adapter",        # Source path (替身，always available)
            "gateway.platforms.feishu",                # Legacy path (Hermes < v0.17)
        ]
        for _mod_path in _feishu_import_paths:
            try:
                mod = importlib.import_module(_mod_path)
                if hasattr(mod, "FeishuAdapter"):
                    cls = getattr(mod, "FeishuAdapter")
                    _logger.debug("HLS: FeishuAdapter resolved via %s", _mod_path)
                    return cls
            except (ImportError, AttributeError):
                if _mod_path == "hermes_plugins.feishu_platform.adapter":
                    pass
                continue
        _logger.debug("HLS: FeishuAdapter not available via any import path")
        return None
    
    def resolve_feishu_adapter_class_fresh(self) -> Any | None:
        """Re-resolve FeishuAdapter class without reusing cached state."""
        return self._resolve_feishu_adapter()
    
    def _resolve_conversation_loop(self) -> None:
        """Resolve agent.conversation_loop, handling Apple Silicon namespace collision."""
        # Strategy 1: sys.modules cache
        cl_mod = sys.modules.get("agent.conversation_loop")
        if cl_mod is not None:
            func = getattr(cl_mod, "run_conversation", None)
            if func is not None:
                self.conversation_loop_module = cl_mod
                self.conversation_loop_func = func
                _logger.debug("HLS: conversation_loop resolved via sys.modules")
                return
        
        # Strategy 2: Anchor-based discovery
        # sys.modules ONLY (2026-08-17 deadlock fix): importing gateway.run or
        # run_agent here would re-create the same cross-thread import deadlock
        # as in _resolve_modules().  If neither anchor is loaded yet, fall
        # through to Strategy 3 (agent.conversation_loop is lightweight and
        # safe to import directly).
        for anchor_name in ("gateway.run", "run_agent"):
            anchor = sys.modules.get(anchor_name)
            if anchor is None:
                continue
            anchor_file = getattr(anchor, "__file__", None)
            if not anchor_file:
                continue
            repo_root = Path(anchor_file).resolve().parent
            if anchor_name == "gateway.run":
                repo_root = repo_root.parent
            cl_file = repo_root / "agent" / "conversation_loop.py"
            if not cl_file.is_file():
                continue
            spec = importlib.util.spec_from_file_location("agent.conversation_loop", str(cl_file))
            if spec is None or spec.loader is None:
                continue
            try:
                mod = importlib.util.module_from_spec(spec)
                sys.modules["agent.conversation_loop"] = mod
                spec.loader.exec_module(mod)
                func = getattr(mod, "run_conversation", None)
                if func is not None:
                    self.conversation_loop_module = mod
                    self.conversation_loop_func = func
                    _logger.debug("HLS: conversation_loop resolved via anchor %s", anchor_name)
                    return
            except Exception as e:
                _logger.debug("HLS: anchor-based load failed: %s", e)
        
        # Strategy 3: Standard import
        try:
            from agent.conversation_loop import run_conversation as _func
            import agent.conversation_loop as _mod
            self.conversation_loop_module = _mod
            self.conversation_loop_func = _func
        except (ImportError, AttributeError):
            pass
    
    @property
    def has_gateway_runner(self) -> bool:
        return self.gateway_runner_class is not None
    
    @property
    def has_aiagent(self) -> bool:
        return self.aiagent_class is not None
    
    @property
    def has_feishu_adapter(self) -> bool:
        return self.feishu_adapter_class is not None
    
    @property
    def has_cron_scheduler(self) -> bool:
        return self.cron_scheduler_module is not None
    
    @property
    def has_conversation_loop(self) -> bool:
        return self.conversation_loop_func is not None
    
    def get_layout_report(self) -> dict[str, bool]:
        """Return a dict of what's available — for doctor command and logging."""
        return {
            "has_gateway_runner": self.has_gateway_runner,
            "has_aiagent": self.has_aiagent,
            "has_feishu_adapter": self.has_feishu_adapter,
            "has_cron_scheduler": self.has_cron_scheduler,
            "has_conversation_loop": self.has_conversation_loop,
            "hermes_version": self.hermes_version,
        }


def patch_finish_reason_guard() -> bool:
    """
    Auto-patch Hermes chat_completion_helpers to properly handle Responses API /
    relayed models (like muse-spark) that end stream with terminal usage instead of finish_reason.
    """
    try:
        import agent.chat_completion_helpers as cch
        # Check if file has patch
        import inspect
        src_file = inspect.getfile(cch)
        with open(src_file, "r", encoding="utf-8") as f:
            code = f.read()
        if "_saw_terminal_usage" not in code:
            import subprocess
            subprocess.run(["/root/.hermes/scripts/fix_muse_finish_reason.py"], check=False)
            return True
        return True
    except Exception:
        return False
