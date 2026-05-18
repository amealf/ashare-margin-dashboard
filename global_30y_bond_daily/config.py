from __future__ import annotations

from pathlib import Path

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.yaml")


def load_config(config_path: str | Path | None = None) -> dict:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    with path.open("r", encoding="utf-8") as fp:
        config = yaml.safe_load(fp)
    config["_config_dir"] = str(path.resolve().parent)
    return config


def resolve_config_path(config: dict, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return Path(config["_config_dir"]).joinpath(path).resolve()
