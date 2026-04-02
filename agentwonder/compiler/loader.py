"""YAML loader — reads configuration files and returns raw dicts.

This is the only place raw YAML touches the system. Everything downstream
receives either raw dicts (for validation) or typed Pydantic models.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class YAMLLoadError(Exception):
    """Raised when a YAML file cannot be read or parsed."""


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a single YAML file and return its contents as a dict.

    Args:
        path: Absolute or relative path to a YAML file.

    Returns:
        Parsed YAML content as a dictionary.

    Raises:
        YAMLLoadError: If the file does not exist, is not valid YAML,
            or does not contain a mapping at the top level.
    """
    path = Path(path)
    if not path.exists():
        raise YAMLLoadError(f"YAML file not found: {path}")
    if not path.is_file():
        raise YAMLLoadError(f"Path is not a file: {path}")

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise YAMLLoadError(f"Cannot read {path}: {exc}") from exc

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise YAMLLoadError(f"Invalid YAML in {path}: {exc}") from exc

    if data is None:
        raise YAMLLoadError(f"YAML file is empty: {path}")
    if not isinstance(data, dict):
        raise YAMLLoadError(
            f"Expected a YAML mapping at top level in {path}, got {type(data).__name__}"
        )

    logger.debug("Loaded YAML: %s (%d keys)", path, len(data))
    return data


def load_all_yaml(directory: Path) -> list[dict[str, Any]]:
    """Load all YAML files from a directory (non-recursive).

    Scans for files ending in ``.yaml`` or ``.yml``, loads each one,
    and returns the list of parsed dicts.  Files that fail to load are
    logged as warnings and skipped.

    Args:
        directory: Path to a directory containing YAML files.

    Returns:
        List of parsed YAML dicts, one per file.

    Raises:
        YAMLLoadError: If the directory does not exist.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise YAMLLoadError(f"Directory not found: {directory}")

    results: list[dict[str, Any]] = []
    yaml_files = sorted(
        p for p in directory.iterdir()
        if p.is_file() and p.suffix in (".yaml", ".yml")
    )

    if not yaml_files:
        logger.warning("No YAML files found in %s", directory)
        return results

    for path in yaml_files:
        try:
            results.append(load_yaml(path))
        except YAMLLoadError as exc:
            logger.warning("Skipping %s: %s", path, exc)

    logger.info("Loaded %d YAML files from %s", len(results), directory)
    return results
