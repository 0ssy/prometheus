import pytest
from core.container import ServiceContainer


class TestServiceContainer:
    def test_register_and_get(self):
        container = ServiceContainer()
        container.register("foo", {"bar": 1})
        assert container.get("foo") == {"bar": 1}

    def test_get_missing_raises(self):
        container = ServiceContainer()
        with pytest.raises(KeyError, match="not found"):
            container.get("missing")

    def test_list_services(self):
        container = ServiceContainer()
        container.register("a", 1)
        container.register("b", 2)
        assert sorted(container.list_services()) == ["a", "b"]

    def test_overwrite_service(self):
        container = ServiceContainer()
        container.register("foo", 1)
        container.register("foo", 2)
        assert container.get("foo") == 2

    def test_resolve_type(self):
        container = ServiceContainer()
        container.register("foo", {"bar": 1})
        resolved = container.resolve("foo", dict)
        assert resolved == {"bar": 1}

    def test_resolve_wrong_type_raises(self):
        container = ServiceContainer()
        container.register("foo", {"bar": 1})
        with pytest.raises(TypeError, match="expected int"):
            container.resolve("foo", int)
