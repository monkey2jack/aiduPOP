"""Dynamic version provider — reads from plugin.yaml (single source of truth)."""

from pathlib import Path

from setuptools import setup

_plugin_yaml = Path(__file__).resolve().parent / "plugin.yaml"

if not _plugin_yaml.exists():
    raise FileNotFoundError(f"plugin.yaml not found at {_plugin_yaml}")

_version = None
for _line in _plugin_yaml.read_text(encoding="utf-8").splitlines():
    if _line.startswith("version:"):
        _version = _line.split(":", 1)[1].strip().strip('"').strip("'")
        break

if not _version:
    raise ValueError(f"No 'version:' field found in {_plugin_yaml}")

setup(version=_version)
