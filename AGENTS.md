# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## What this is

A collection of [Home Assistant blueprints](https://www.home-assistant.io/docs/blueprint/), one YAML file per device, grouped by manufacturer:

- `Philips/remotes/RWL022.yaml`: ZHA Philips Hue Dimmer Switch.
- `IKEA/remotes/five_button.yaml`: IKEA five-button remote.

## Conventions

- Blueprints use the `!input` YAML tag, which plain YAML loaders reject. To validate, register a constructor for `!input` (for example in PyYAML, `SafeLoader.add_constructor('!input', ...)`).
- Each blueprint's `source_url` points at its file on `main`; keep it correct if a file moves.
- Changing or removing an input name breaks existing automations built from the blueprint. Call this out in the commit and PR as a breaking change.
- Grouped (collapsible) inputs via `section:` need Home Assistant 2024.6 or later.

## Workflow

- `main` is protected: open a PR rather than pushing. The owner is exempt as a repository admin.
- CI (`.github/workflows/ci.yml`) runs `validate`, `yamllint` and `markdownlint`. Run `pip install -r scripts/requirements.txt && python scripts/validate_blueprints.py` locally before pushing; add `--strict` to treat warnings (removed `light.turn_on` parameters) as errors.
- Home Assistant 2026.3 removed the mired `color_temp` parameter from `light.turn_on`; use `color_temp_kelvin`.
