#!/usr/bin/env python3
"""
Build registry.json from each recipe's info.json + pipeline's info.json.

Also reports drift between the three places a version lives:
    1. <kind>/<name>/<file>.yaml's top-level `version:`  ← actual runtime
    2. <kind>/<name>/info.json's `version`               ← display metadata
    3. registry.json's <kind>[].version                  ← marketplace listing

This script ONLY writes registry.json (built from each info.json).
yaml ↔ info.json drift is reported as a warning — fix manually, since
either side might be the correct one (yaml is what Forge actually runs,
info.json is what the marketplace shows).

Usage:
    python3 tools/build_registry.py            # rebuild registry.json
    python3 tools/build_registry.py --check    # exit 1 on any drift (CI gate)

Why this exists: bumping pipeline.yaml/info.json without bumping
registry.json silently breaks the Forge marketplace sync UI (it sees
"no update available" forever).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "registry.json"


def parse_yaml_version(path: Path) -> str | None:
    """
    Extract a top-level `version:` from a yaml file without depending
    on PyYAML. Some pipeline scripts embed non-printable chars that
    yaml.safe_load chokes on, so a small regex is sufficient here.
    """
    if not path.exists():
        return None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            # Indented = nested; not the top-level version.
            if line and line[0] in (" ", "\t"):
                continue
            m = re.match(r'^version:\s*(.+?)\s*$', line)
            if not m:
                continue
            raw = m.group(1).strip()
            if raw.startswith('"') and raw.endswith('"'):
                raw = raw[1:-1]
            elif raw.startswith("'") and raw.endswith("'"):
                raw = raw[1:-1]
            return raw or None
    return None


def collect(kind: str, existing_order: list[str] | None = None) -> tuple[list[dict], list[str]]:
    """
    kind: 'recipes' or 'pipelines'.
    Returns (entries, change_log). Preserves the existing registry's
    order for entries that already exist; new entries get appended.
    """
    dir_ = ROOT / kind
    yaml_filename = "recipe.yaml" if kind == "recipes" else "pipeline.yaml"
    changes: list[str] = []
    entries: list[dict] = []
    if not dir_.is_dir():
        return entries, changes

    by_name: dict[str, dict] = {}
    for child in sorted(dir_.iterdir()):
        if not child.is_dir():
            continue
        info_path = child / "info.json"
        if not info_path.exists():
            continue
        try:
            info = json.loads(info_path.read_text())
        except json.JSONDecodeError as e:
            print(f"warning: {info_path} not valid JSON: {e}", file=sys.stderr)
            continue
        yaml_version = parse_yaml_version(child / yaml_filename)
        if yaml_version and info.get("version") != yaml_version:
            changes.append(
                f"{kind}/{child.name}: {yaml_filename} version {yaml_version!r} "
                f"≠ info.json version {info.get('version')!r} — fix manually"
            )
        entry = {"name": info.get("name") or child.name}
        for field in ("display_name", "description", "version", "author", "tags", "score", "rating"):
            if field in info:
                entry[field] = info[field]
        by_name[entry["name"]] = entry

    # Preserve the existing registry's order; new entries get appended
    # in alphabetical order (minimizes diff churn when the script first
    # runs on an existing registry).
    ordered_names = []
    seen = set()
    for name in (existing_order or []):
        if name in by_name and name not in seen:
            ordered_names.append(name)
            seen.add(name)
    for name in sorted(by_name.keys()):
        if name not in seen:
            ordered_names.append(name)
            seen.add(name)
    return [by_name[n] for n in ordered_names], changes


def build() -> tuple[dict, list[str]]:
    existing = {}
    if REGISTRY_PATH.exists():
        try:
            existing = json.loads(REGISTRY_PATH.read_text())
        except json.JSONDecodeError:
            pass

    recipe_order = [r.get("name") for r in (existing.get("recipes") or []) if r.get("name")]
    pipeline_order = [p.get("name") for p in (existing.get("pipelines") or []) if p.get("name")]
    recipes, rc = collect("recipes", recipe_order)
    pipelines, pc = collect("pipelines", pipeline_order)
    changes = rc + pc

    new = {
        "version": existing.get("version", 1),
        "updated_at": existing.get("updated_at", ""),
        "recipes": recipes,
        "pipelines": pipelines,
    }
    return new, changes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="Exit non-zero if anything would change.")
    args = ap.parse_args()

    new, changes = build()
    new_text = json.dumps(new, indent=2) + "\n"
    current = REGISTRY_PATH.read_text() if REGISTRY_PATH.exists() else ""

    # yaml ↔ info.json drift is a warning the script can't auto-resolve.
    # registry.json drift is a hard failure in --check mode (always
    # derivable from info.json).
    for c in changes:
        print(f"warning: {c}", file=sys.stderr)

    if args.check:
        if new_text != current:
            print("registry.json is out of sync with info.json files.", file=sys.stderr)
            print("Run `python3 tools/build_registry.py` and commit.", file=sys.stderr)
            return 1
        if changes:
            return 1  # yaml/info drift — non-fatal for build, but block CI
        print("registry.json is up to date.")
        return 0

    if new_text == current:
        print("registry.json already in sync — no changes.")
        return 0
    REGISTRY_PATH.write_text(new_text)
    print(f"wrote registry.json: {len(new['recipes'])} recipes + {len(new['pipelines'])} pipelines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
