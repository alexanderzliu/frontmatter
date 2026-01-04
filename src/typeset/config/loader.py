"""Configuration file loading."""

from pathlib import Path
from typing import Any

import yaml

from typeset.config.models import TypesetConfig


def load_config(config_path: Path) -> TypesetConfig:
    """Load configuration from a YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        data = yaml.safe_load(f) or {}

    return TypesetConfig(**data)


def find_config_file(start_dir: Path) -> Path | None:
    """Search for configuration file in directory and parents."""
    config_names = ["typeset.yaml", "typeset.yml", ".typeset.yaml", ".typeset.yml"]

    current = start_dir.resolve()
    while current != current.parent:
        for name in config_names:
            config_path = current / name
            if config_path.exists():
                return config_path
        current = current.parent

    return None


def merge_configs(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two configuration dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result
