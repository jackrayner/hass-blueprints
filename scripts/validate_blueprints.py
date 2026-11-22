#!/usr/bin/env python3
"""Static checks for Home Assistant blueprints (no Home Assistant install needed).

Errors (exit 1): YAML that doesn't parse, missing blueprint keys, `!input`
references to undeclared inputs, declared inputs that are never used, a
`source_url` that doesn't match the file's path on main.
Warnings: parameters removed from light.turn_on in Home Assistant 2026.3.

Usage: validate_blueprints.py [--strict] [FILE ...]   (default: every blueprint)
--strict turns warnings into errors.
"""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCE_PREFIX = "https://github.com/jackrayner/hass-blueprints/blob/main/"
REQUIRED = ("name", "domain", "input")
REMOVED_LIGHT_KEYS = {"color_temp", "kelvin", "min_mireds", "max_mireds"}
SKIP_DIRS = {".git", ".github", "scripts", "node_modules"}


class Input(str):
    """A `!input name` reference."""


class Loader(yaml.SafeLoader):
    pass


Loader.add_constructor("!input", lambda loader, node: Input(loader.construct_scalar(node)))


def declared_inputs(inputs):
    """Flatten `section:` groups into {name: definition}."""
    found = {}
    for key, value in (inputs or {}).items():
        if isinstance(value, dict) and "input" in value and "selector" not in value:
            found.update(declared_inputs(value["input"]))
        else:
            found[key] = value or {}
    return found


def walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def used_inputs(node):
    if isinstance(node, Input):
        yield str(node)
    elif isinstance(node, dict):
        for value in node.values():
            yield from used_inputs(value)
    elif isinstance(node, list):
        for value in node:
            yield from used_inputs(value)


def check(path):
    errors, warnings = [], []
    rel = path.relative_to(ROOT).as_posix()
    try:
        doc = yaml.load(path.read_text(), Loader)
    except yaml.YAMLError as exc:
        return [f"invalid YAML: {exc}"], []
    if not isinstance(doc, dict) or not isinstance(doc.get("blueprint"), dict):
        return ["missing top-level `blueprint:` mapping"], []

    bp = doc["blueprint"]
    for key in REQUIRED:
        if key not in bp:
            errors.append(f"blueprint.{key} is missing")
    if "source_url" in bp and bp["source_url"] != SOURCE_PREFIX + rel:
        errors.append(f"source_url should be {SOURCE_PREFIX + rel}")

    declared = declared_inputs(bp.get("input"))
    body = {k: v for k, v in doc.items() if k != "blueprint"}
    used = set(used_inputs(body))
    for name in sorted(used - declared.keys()):
        errors.append(f"`!input {name}` is not declared under blueprint.input")
    for name in sorted(declared.keys() - used):
        errors.append(f"input `{name}` is declared but never used")
    for name, definition in declared.items():
        if "name" not in definition:
            errors.append(f"input `{name}` has no name")

    for node in walk(body):
        for key in REMOVED_LIGHT_KEYS & node.keys():
            if key == "color_temp" and not isinstance(node[key], (Input, int, float)):
                continue
            warnings.append(f"`{key}:` was removed from light.turn_on in HA 2026.3; use color_temp_kelvin")
    for name, definition in declared.items():
        selector = definition.get("selector") or {}
        if "color_temp" in selector and (selector["color_temp"] or {}).get("unit") != "kelvin":
            warnings.append(f"input `{name}` uses a mired color_temp selector; set `unit: kelvin`")
    return errors, warnings


def find_blueprints():
    return sorted(
        p for p in ROOT.rglob("*.yaml")
        if not SKIP_DIRS & set(p.relative_to(ROOT).parts)
    )


def main(argv):
    strict = "--strict" in argv
    files = [Path(a).resolve() for a in argv if not a.startswith("--")] or find_blueprints()
    failed = False
    for path in files:
        errors, warnings = check(path)
        rel = path.relative_to(ROOT).as_posix()
        for msg in errors:
            print(f"::error file={rel}::{msg}")
        for msg in warnings:
            print(f"::{'error' if strict else 'warning'} file={rel}::{msg}")
        failed |= bool(errors) or (strict and bool(warnings))
        print(f"{'FAIL' if errors else 'ok  '} {rel} ({len(errors)} errors, {len(warnings)} warnings)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
