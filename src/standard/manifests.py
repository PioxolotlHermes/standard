"""Reading dependencies from pyproject.toml and package.json."""

import json
import re
import tomllib
from dataclasses import dataclass

NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*([^;]*)")
NPM_EXACT = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
PY_EXACT = re.compile(r"^==\s*[0-9A-Za-z.+!_-]+$")


@dataclass(frozen=True)
class Dep:
    name: str
    spec: str
    runtime: bool  # False = development tool

    @property
    def pinned(self) -> bool:
        return bool(NPM_EXACT.match(self.spec) if self.spec[:1].isdigit() else PY_EXACT.match(self.spec.strip()))


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _python(items: object, runtime: bool) -> list[Dep]:
    deps = []
    for item in items if isinstance(items, list) else []:
        match = NAME.match(item) if isinstance(item, str) else None
        if match:
            deps.append(Dep(normalize(match.group(1)), match.group(2).strip(), runtime))
    return deps


def python_deps(text: str) -> list[Dep]:
    """`[project].dependencies` (+ optional extras) as runtime, every `[dependency-groups]` list as dev."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return []
    project = data.get("project", {})
    deps = _python(project.get("dependencies"), True)
    for extra in project.get("optional-dependencies", {}).values():
        deps += _python(extra, True)
    for group in data.get("dependency-groups", {}).values():
        deps += _python(group, False)
    return deps


def npm_deps(text: str) -> list[Dep]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    deps = []
    for section, runtime in (("dependencies", True), ("devDependencies", False)):
        entries = data.get(section, {}) if isinstance(data, dict) else {}
        deps += [Dep(name, str(spec), runtime) for name, spec in entries.items()]
    return deps
