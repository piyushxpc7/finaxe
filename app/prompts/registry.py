"""Versioned prompt registry — loads YAML prompt files by name + version."""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Optional

import yaml
from langchain_core.prompts import ChatPromptTemplate

# Root of the prompts/ directory (two levels up from this file)
_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"


class PromptSpec:
    """Parsed prompt specification from a YAML file."""

    def __init__(self, data: dict, path: Path):
        self.name: str = data["name"]
        self.version: str = data["version"]
        self.model: str = data.get("model", "")
        self.date: str = str(data.get("date", ""))
        self.changelog: str = data.get("changelog", "")
        self.system: str = data["system"].strip()
        self.user: str = data["user"].strip()
        self._path = path

    def to_langchain_template(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", self.system),
            ("user", self.user),
        ])

    def __repr__(self) -> str:
        return f"PromptSpec(name={self.name!r}, version={self.version!r})"


@functools.lru_cache(maxsize=64)
def load_prompt(name: str, version: str) -> PromptSpec:
    """
    Load a prompt by name and version from the prompts/ registry.

    Raises FileNotFoundError (with available versions listed) if the
    requested version does not exist. Cached after first load.
    """
    prompt_dir = _PROMPTS_ROOT / name
    target = prompt_dir / f"{version}.yaml"

    if not target.exists():
        available = _available_versions(prompt_dir)
        avail_str = ", ".join(available) if available else "none"
        raise FileNotFoundError(
            f"Prompt '{name}' version '{version}' not found at {target}. "
            f"Available: {avail_str}"
        )

    with target.open() as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError(
            f"Prompt file {target} is empty. "
            "Add system and user fields before using this version."
        )

    return PromptSpec(data, target)


def list_versions(name: str) -> list[str]:
    """Return all available versions for a prompt name, sorted."""
    prompt_dir = _PROMPTS_ROOT / name
    return _available_versions(prompt_dir)


def invalidate_cache() -> None:
    """Clear the prompt cache (useful in tests)."""
    load_prompt.cache_clear()


def _available_versions(prompt_dir: Path) -> list[str]:
    if not prompt_dir.is_dir():
        return []
    return sorted(
        p.stem for p in prompt_dir.glob("*.yaml") if p.stat().st_size > 0
    )
