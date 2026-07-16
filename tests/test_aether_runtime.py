"""P3 Aether AI Runtime — routing, tool dispatch, context persistence."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import core.database as cd
from aether.runtime import AetherRuntime, Router, ToolDispatcher, Provider
from aether.models import AetherToolCall


@pytest.fixture
def session(tmp_path, monkeypatch):
    db_path = tmp_path / "p3.db"
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(cd, "engine", engine)
    monkeypatch.setattr(cd, "SessionLocal", factory)
    cd.init_db()
    with factory() as s:
        yield s
    engine.dispose()


def test_router_prefers_cheap_within_budget():
    router = Router(
        providers=[
            Provider("openai", "gpt-4o-mini", 0.15, 2.0),
            Provider("ollama", "local-model", 0.0, 1.0),
            Provider("anthropic", "claude-haiku", 0.25, 2.5),
        ],
        budget_cap=1.0,
    )
    sel = router.route()
    assert sel.name == "ollama"


def test_router_falls_back_when_over_budget():
    router = Router(
        providers=[
            Provider("openai", "gpt-4o-mini", 0.15, 2.0),
            Provider("ollama", "local-model", 0.0, 1.0),
        ],
        budget_cap=0.0,  # nothing fits budget -> lowest latency among available
    )
    sel = router.route()
    assert sel.name == "ollama"


def test_router_fallback_chain_excludes_preferred():
    router = Router(budget_cap=1.0)
    preferred = router.route()
    chain = router.fallback_chain(preferred)
    assert preferred.name not in [p.name for p in chain]


def test_tool_dispatch_isolated_on_failure():
    d = ToolDispatcher()
    d.register("ok", lambda args: {"echo": args.get("x")})
    d.register("boom", lambda args: (_ for _ in ()).throw(RuntimeError("boom")))

    good = d.dispatch("ok", {"x": 1})
    assert good.status == "success"
    bad = d.dispatch("boom", {})
    assert bad.status == "error"
    assert "boom" in bad.error
    unknown = d.dispatch("nope", {})
    assert unknown.status == "error"


def test_runtime_persists_context_and_tool_calls(session):
    rt = AetherRuntime()
    rt.dispatcher.register("ping", lambda args: {"pong": args.get("n", 0)})

    ctx_id = rt.save_context(session, "sess-1", {"memory": "short", "tokens": 10})
    assert ctx_id
    loaded = rt.load_context(session, "sess-1")
    assert loaded == {"memory": "short", "tokens": 10}

    res = rt.run_tool(session, "sess-1", "ping", {"n": 3})
    assert res.status == "success"
    assert res.result == {"pong": 3}

    calls = session.query(AetherToolCall).all()
    assert len(calls) == 1
    assert calls[0].status == "success"
    assert calls[0].tool == "ping"


def test_runtime_select_provider_shape():
    rt = AetherRuntime()
    sel = rt.select_provider(budget=1.0)
    assert "provider" in sel and "model" in sel and "fallback" in sel
    assert sel["provider"] in ("ollama", "openai", "anthropic")
