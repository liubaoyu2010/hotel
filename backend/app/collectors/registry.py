from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.collectors.base import BaseCollector

_CACHE: list[type[BaseCollector]] | None = None


def _discover_collectors() -> list[type[BaseCollector]]:
    """Auto-discover collector classes in this package."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    import app.collectors as pkg

    result: list[type[BaseCollector]] = []
    for _importer, modname, _ispkg in pkgutil.iter_modules(pkg.__path__):
        if modname in ("base", "registry", "__init__"):
            continue
        try:
            mod = importlib.import_module(f"app.collectors.{modname}")
        except ImportError:
            continue
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, importlib.import_module("app.collectors.base").BaseCollector)
                and attr is not importlib.import_module("app.collectors.base").BaseCollector
            ):
                result.append(attr)

    _CACHE = result
    return result


def get_all_collectors() -> list[BaseCollector]:
    """Return instantiated collectors sorted by priority."""
    from app.collectors.base import BaseCollector

    classes = _discover_collectors()
    instances = [cls() for cls in classes if cls.enabled_by_default]
    instances.sort(key=lambda c: c.priority)
    return instances


def get_collector(name: str) -> BaseCollector | None:
    """Return a collector instance by name, or None."""
    from app.collectors.base import BaseCollector

    classes = _discover_collectors()
    for cls in classes:
        if cls.name == name:
            return cls()
    return None


def list_available_collectors() -> list[dict]:
    """Return metadata for all discovered collectors."""
    classes = _discover_collectors()
    return [
        {
            "name": cls.name,
            "display_name": cls.display_name,
            "priority": cls.priority,
            "enabled_by_default": cls.enabled_by_default,
        }
        for cls in classes
    ]
