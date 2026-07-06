from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from core.logger import get_logger

from .interfaces import PluginContext, PluginResult

logger = get_logger(__name__)


@dataclass
class TestResult:
    name: str
    passed: bool
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "error": self.error,
            "metadata": self.metadata,
        }


class MockPluginContext(PluginContext):
    def __init__(self, **overrides: Any) -> None:
        mock_kernel = _Stub(name="mock_kernel", **overrides.pop("kernel_overrides", {}))
        mock_cm = _Stub(name="mock_capability_manager")
        mock_ke = _Stub(name="mock_knowledge_engine")
        mock_eb = _Stub(name="mock_event_bus")
        super().__init__(
            kernel=overrides.pop("kernel", mock_kernel),
            capability_manager=overrides.pop("capability_manager", mock_cm),
            knowledge_engine=overrides.pop("knowledge_engine", mock_ke),
            event_bus=overrides.pop("event_bus", mock_eb),
            logger=overrides.pop("logger", get_logger("mock_plugin_context")),
            metadata=overrides.pop("metadata", {}),
        )
        self.granted_permissions = set(overrides.pop("granted_permissions", set()))
        if overrides:
            self.__dict__.update(overrides)


class _Stub:
    def __init__(self, name: str = "stub", **attrs: Any) -> None:
        self._name = name
        self.__dict__.update(attrs)

    def __getattr__(self, item: str) -> Callable[..., Any]:
        def _no_op(*args: Any, **kwargs: Any) -> None:
            logger.debug("%s stub no-op: %s", self._name, item)

        return _no_op

    def __repr__(self) -> str:
        return f"<mock {self._name}>"


class PluginTestHarness:
    def __init__(self, context: PluginContext | None = None) -> None:
        self.context = context or MockPluginContext()
        self._plugin: Any = None
        self._plugin_id: str | None = None

    def load_plugin(self, plugin_class: type, plugin_id: str | None = None) -> Any:
        self._plugin = plugin_class()
        self._plugin.context = self.context
        self._plugin_id = plugin_id or getattr(self._plugin.manifest, "name", plugin_class.__name__)
        logger.info("Loaded plugin %s into harness", self._plugin_id)
        return self._plugin

    def execute(self, capability: str, payload: dict[str, Any] | None = None) -> PluginResult:
        if self._plugin is None:
            raise RuntimeError("No plugin loaded. Call load_plugin() first.")
        method = getattr(self._plugin, capability, None)
        if method is None or not callable(method):
            return PluginResult.fail(f"No such capability: {capability}")
        try:
            data = method(**(payload or {}))
        except Exception as exc:
            logger.exception("Capability %s raised", capability)
            return PluginResult.fail(str(exc))
        if isinstance(data, PluginResult):
            return data
        return PluginResult.ok(data)

    def assert_success(self, result: PluginResult) -> None:
        if not result.success:
            raise AssertionError(f"Expected success but got error: {result.error}")

    def assert_error(self, result: PluginResult) -> None:
        if result.success:
            raise AssertionError(f"Expected error but succeeded with data: {result.data!r}")

    def assert_contains(self, result: PluginResult, key: str) -> None:
        if not result.success:
            raise AssertionError(f"Cannot assert contents on failed result: {result.error}")
        data = result.data
        if not isinstance(data, dict):
            raise AssertionError(f"Result data is not a dict: {data!r}")
        if key not in data:
            raise AssertionError(f"Expected key '{key}' in result data; got {list(data)}")


class PluginTestSuite:
    def __init__(self, harness: PluginTestHarness | None = None) -> None:
        self._harness = harness or PluginTestHarness()
        self._tests: list[tuple[str, Callable[[PluginTestHarness], None]]] = []

    def add_test(self, name: str, func: Callable[[PluginTestHarness], None]) -> None:
        self._tests.append((name, func))

    def run(self) -> list[TestResult]:
        results: list[TestResult] = []
        for name, func in self._tests:
            try:
                func(self._harness)
                results.append(TestResult(name=name, passed=True))
                logger.info("Test passed: %s", name)
            except Exception as exc:
                results.append(TestResult(name=name, passed=False, error=str(exc)))
                logger.warning("Test failed: %s (%s)", name, exc)
        return results
