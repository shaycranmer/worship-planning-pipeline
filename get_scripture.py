#!/usr/bin/env python3
"""
get_scripture.py; scripture retrieval for the demo pipeline.

DESIGN NOTE, and it matters: this public demonstration ships with scripture
as local fixture text (scripture_fixtures.json) in the World English Bible,
a public-domain translation. The production system retrieves its licensed
translation through channels permitted by that publisher's terms, and that
implementation stays private. Two rules hold in both worlds:

  1. Scripture text is never generated, re-typed, or paraphrased by a
     language model. It is fetched from an authoritative source and placed
     programmatically. (The retired API version of this pipeline broke that
     rule and produced a recurring text-corruption bug; see the README.)
  2. Text rights are respected. A demo that scraped a licensed translation
     would be a data-handling failure in a repository that exists to
     demonstrate careful data handling.

Usage:
    python3 get_scripture.py "Isaiah 55:10-13"     # look up a fixture passage
    (or imported by build_worship_plan.py via fetch_readings)

To add passages to the demo, append them to scripture_fixtures.json with a
lowercase "book chapter:verses" key and public-domain text.
"""

import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(BASE_DIR, "scripture_fixtures.json")


def _normalize(ref: str) -> str:
    """'Isaiah 55:10-13, As the rain waters...' -> 'isaiah 55:10-13'"""
    ref = re.split(r"\s*(?:;|,\s(?=[A-Z]))", ref, maxsplit=1)[0]
    return re.sub(r"\s+", " ", ref).strip().lower()


def _load_fixtures() -> dict:
    with open(FIXTURES) as f:
        return json.load(f)


def fetch_passage(ref: str):
    """Return (display_reference, passage_text) from the local fixture file."""
    fixtures = _load_fixtures()
    key = _normalize(ref)
    if key not in fixtures:
        available = ", ".join(sorted(fixtures))
        raise KeyError(
            f"'{key}' is not in scripture_fixtures.json (demo has: {available}). "
            f"Add the passage from a public-domain translation, or supply text manually.")
    entry = fixtures[key]
    return f"{entry['reference']} ({entry['translation']})", entry["text"]


def fetch_readings(readings: dict) -> dict:
    """
    Fetch scripture text for all readings in a worship_input readings dict.
    Keys: first_reading, psalm, second_reading, gospel
    Returns same dict with full text added, or citation-only on error.
    """
    result = {}
    for slot, ref in readings.items():
        if not ref:
            result[slot] = ref
            continue
        try:
            display_ref, text = fetch_passage(ref)
            result[slot] = f"{display_ref}\n\n{text}"
            print(f"  ✅ {slot}: {display_ref}")
        except Exception as e:
            result[slot] = ref
            print(f"  ⚠️  {slot}: fixture not found; citation kept as-is ({e})")
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        ref, text = fetch_passage(" ".join(sys.argv[1:]))
        print(ref + "\n")
        print(text)
    else:
        print(__doc__)
