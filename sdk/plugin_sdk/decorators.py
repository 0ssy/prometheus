from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

from core.logger import get_logger

from .interfaces import BasePlugin, PluginManifest

logger = get_logger(__name__)

_PLUGIN_MANIFEST_ATTR = "__plugin_manifest__"
_PLUGIN_CAPABILITIES_ATTR = "__plugin_capabilities__"
_PLUGIN_HOOKS_ATTR = "__plugin_hooks__"
_PLUGIN_PERMISSIONS_ATTR = "__plugin_permissions__"


def _extract_manifest(cls: type) -> PluginManifest:
    kwargs: dict[str, Any] = {}
    for field_name in PluginManifest.__dataclass_fields__:
        if hasattr(cls, field_name) and not callable(getattr(cls, field_name)):
            kwargs[field_name] = getattr(cls, field_name)
    missing = {"name", "version"} - set(kwargs)
    if missing:
        raise ValueError(f"Plugin {cls.__name__} is missing required manifest field(s): {sorted(missing)}")
    return PluginManifest(**kwargs)


def _scan_members(cls: type) -> None:
    capabilities: dict[str, dict[str, Any]] = {}
    hooks: dict[str, str] = {}
    for name, member in vars(cls).items():
        if not callable(member):
            continue
        cap = getattr(member, _PLUGIN_CAPABILITIES_ATTR, None)
        if cap is not None:
            capabilities[name] = cap
        hook_map = getattr(member, _PLUGIN_HOOKS_ATTR, None)
        if hook_map is not None:
            hooks.update(hook_map)
    setattr(cls, _PLUGIN_CAPABILITIES_ATTR, capabilities)
    setattr(cls, _PLUGIN_HOOKS_ATTR, hooks)


def plugin(cls: type) -> type:
    if not issubclass(cls, BasePlugin):
        cls = type(cls.__name__, (cls, BasePlugin), dict(cls.__dict__))
    if not hasattr(cls, "manifest") or getattr(cls, _PLUGIN_MANIFEST_ATTR, False) is False:
        cls.manifest = _extract_manifest(cls)
        setattr(cls, _PLUGIN_MANIFEST_ATTR, True)
    if not hasattr(cls, _PLUGIN_CAPABILITIES_ATTR):
        setattr(cls, _PLUGIN_CAPABILITIES_ATTR, {})
    if not hasattr(cls, _PLUGIN_HOOKS_ATTR):
        setattr(cls, _PLUGIN_HOOKS_ATTR, {})
    _scan_members(cls)
    cls.manifest.capabilities = sorted(set(cls.manifest.capabilities) | set(getattr(cls, _PLUGIN_CAPABILITIES_ATTR)))
    logger.debug("Registered plugin class: %s", cls.__name__)
    return cls


def capability(func: Callable[..., Any]) -> Callable[..., Any]:
    setattr(
        func,
        _PLUGIN_CAPABILITIES_ATTR,
        {
            "description": (func.__doc__ or "").strip(),
            "permissions": getattr(func, _PLUGIN_PERMISSIONS_ATTR, set()),
        },
    )
    return func


def requires_permission(*perms: str) -> Callable[..., Any]:
    required = set(perms)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        existing = getattr(func, _PLUGIN_PERMISSIONS_ATTR, set())
        setattr(func, _PLUGIN_PERMISSIONS_ATTR, existing | required)

        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            granted = set()
            context = getattr(self, "context", None)
            if context is not None:
                granted = set(getattr(context, "granted_permissions", set()) or set())
            missing = required - granted
            if missing:
                raise PermissionError(
                    f"Capability '{func.__name__}' requires permissions {sorted(missing)} "
                    f"but only {sorted(granted)} were granted"
                )
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def plugin_hook(hook_name: str) -> Callable[..., Any]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        hooks = getattr(func, _PLUGIN_HOOKS_ATTR, None)
        if hooks is None:
            hooks = {}
            setattr(func, _PLUGIN_HOOKS_ATTR, hooks)
        hooks[hook_name] = func.__name__
        return func

    return decorator
