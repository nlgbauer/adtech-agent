"""Orchestrate the weekly brief: fetch -> filter -> synthesize -> write.

Usage:
    export ANTHROPIC_API_KEY=sk-...
    python run.py            # writes briefs/YYYY-MM-DD.md
"""
from __future__ import annotations

import datetime as dt
import pathlib
import sys

import yaml

from deliver import deliver
from fetch_sources import fetch_all
from synthesize import synthesize

ROOT = pathlib.Path(__file__).parent
BRIEFS_DIR = ROOT / "briefs"


def load_sources() -> list[dict]:
    cfg = yaml.safe_load((ROOT / "sources.yaml").read_text()) or {}
    sources = list(cfg.get("sources", []))
    sources.extend(cfg.get("focus_list") or [])
    return sources


def main() -> int:
    sources = load_sources()
    if not sources:
        print("No sources configured in sources.yaml", file=sys.stderr)
        return 1

    print(f"Fetching {len(sources)} sources...")
    result = fetch_all(sources)
    print(f"  {len(result.items)} items, {len(result.errors)} source error(s)")
    for err in result.errors:
        print(f"    - unavailable: {err}")

    print("Synthesizing brief...")
    brief = synthesize(result.items, result.errors)

    BRIEFS_DIR.mkdir(exist_ok=True)
    today = dt.date.today().isoformat()
    out = BRIEFS_DIR / f"{today}.md"
    out.write_text(brief)
    print(f"Wrote {out}")

    # Email delivery. Skips silently if email env vars aren't set, so a plain
    # local run still works without sending anything.
    deliver(brief, subject=f"Adtech Market Brief — {today}", date_str=today)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
