"""
P3 Aether AI Runtime — provider adapters, routing, tool dispatch.

Deterministic, local-first routing with a configurable fallback chain
and a safety budget cap. Tool dispatch executes capability calls via a
pluggable handler registry (the real runtime wires this to
``PlatformService``). When the Rust ``ai-runtime`` crate is available it
is used; otherwise a Python fallback keeps behavior testable.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from core.logger import get_logger
from sqlalchemy.orm import Session

from aether.models import AetherContext, AetherToolCall

logger = get_logger(__name__)


@dataclass
class Provider:
    name: str
    model: str
    cost_per_1k: float  # relative cost unit
    latency_score: float  # lower is faster
    available: bool = True


# Default provider catalog (local-first). Override per deployment.
DEFAULT_PROVIDERS: list[Provider] = [
    Provider("ollama", "local-model", cost_per_1k=0.0, latency_score=1.0),
    Provider("openai", "gpt-4o-mini", cost_per_1k=0.15, latency_score=2.0),
    Provider("anthropic", "claude-haiku", cost_per_1k=0.25, latency_score=2.5),
]


class Router:
    """Local-first, cost/perf-aware router with a fallback chain."""

    def __init__(self, providers: list[Provider] | None = None, budget_cap: float = 1.0):
        self._providers = providers or list(DEFAULT_PROVIDERS)
        self._budget_cap = budget_cap
        self._rust = None
        try:
            import aether_runtime as _ar
            self._rust = _ar
        except ImportError:
            pass

    def route(self, budget: float | None = None) -> Provider:
        if self._rust is not None:
            import json
            providers_json = json.dumps([
                {"name": p.name, "model": p.model, "cost_per_1k": p.cost_per_1k, "latency_score": p.latency_score, "available": p.available}
                for p in self._providers
            ])
            selected_json = self._rust.route_py(providers_json, budget)
            selected = json.loads(selected_json)
            return Provider(**selected)
        cap = self._budget_cap if budget is None else budget
        available = [p for p in self._providers if p.available]
        if not available:
            raise RuntimeError("No providers available")
        within = [p for p in available if p.cost_per_1k <= cap]
        pool = within if within else available
        pool.sort(key=lambda p: (p.cost_per_1k, p.latency_score))
        return pool[0]

    def fallback_chain(self, preferred: Provider) -> list[Provider]:
        if self._rust is not None:
            import json
            providers_json = json.dumps([
                {"name": p.name, "model": p.model, "cost_per_1k": p.cost_per_1k, "latency_score": p.latency_score, "available": p.available}
                for p in self._providers
            ])
            chain = self._rust.fallback_chain_py(providers_json, preferred.name)
            return [Provider(**c) for c in chain]
        others = [p for p in self._providers if p.available and p.name != preferred.name]
        others.sort(key=lambda p: (p.cost_per_1k, p.latency_score))
        return others


@dataclass
class ToolResult:
    tool: str
    status: str
    result: Any = None
    error: str | None = None


class ToolDispatcher:
    """Executes capability calls via a registered handler registry."""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}

    def register(self, tool: str, handler: Callable[[dict[str, Any]], Any]) -> None:
        self._handlers[tool] = handler

    def dispatch(self, tool: str, args: dict[str, Any]) -> ToolResult:
        handler = self._handlers.get(tool)
        if handler is None:
            return ToolResult(tool=tool, status="error", error=f"unknown tool: {tool}")
        try:
            result = handler(args)
            return ToolResult(tool=tool, status="success", result=result)
        except Exception as exc:  # isolation: one tool failure can't crash the run
            logger.exception("Tool '%s' failed", tool)
            return ToolResult(tool=tool, status="error", error=str(exc))


class AetherRuntime:
    def __init__(self, providers: list[Provider] | None = None, budget_cap: float = 1.0):
        self.router = Router(providers, budget_cap)
        self.dispatcher = ToolDispatcher()

    # --- context persistence ---
    def save_context(self, db: Session, session_id: str, window_state: dict[str, Any]) -> str:
        ctx = AetherContext(
            id=str(uuid.uuid4()),
            session_id=session_id,
            window_state=json.dumps(window_state, default=str),
            created_at=datetime.now(timezone.utc),
        )
        db.add(ctx)
        db.commit()
        return ctx.id

    def load_context(self, db: Session, session_id: str) -> dict[str, Any] | None:
        row = (
            db.query(AetherContext)
            .filter(AetherContext.session_id == session_id)
            .order_by(AetherContext.created_at.desc())
            .first()
        )
        return json.loads(row.window_state) if row else None

    # --- tool execution with audit trail ---
    def run_tool(self, db: Session, session_id: str, tool: str, args: dict[str, Any]) -> ToolResult:
        result = self.dispatcher.dispatch(tool, args)
        call = AetherToolCall(
            id=str(uuid.uuid4()),
            session_id=session_id,
            tool=tool,
            args_json=json.dumps(args, default=str),
            result_json=json.dumps(result.result, default=str) if result.result is not None else "{}",
            status=result.status,
            created_at=datetime.now(timezone.utc),
        )
        db.add(call)
        db.commit()
        return result

    # --- provider selection (with fallback SLA) ---
    def select_provider(self, budget: float | None = None) -> dict[str, Any]:
        preferred = self.router.route(budget)
        chain = self.router.fallback_chain(preferred)
        return {
            "provider": preferred.name,
            "model": preferred.model,
            "fallback": [p.name for p in chain],
        }
