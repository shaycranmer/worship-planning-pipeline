#!/usr/bin/env python3
"""
get_scripture.py — Fetch NRSV scripture text from Bible Gateway.

Usage:
    python get_scripture.py                          # interactive mode
    python get_scripture.py "Matthew 28:1-10"        # direct lookup
    python get_scripture.py "Acts 10:34-43"          # any reference

No API key needed. Uses Bible Gateway NRSV directly.
"""

import sys
import re
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.biblegateway.com/passage/"
VERSION = "NRSV"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_passage(reference: str) -> tuple:
    """
    Fetch NRSV passage text from Bible Gateway.
    Returns (display_ref, clean_text) tuple.
    Raises ValueError on failure.
    """
    # Strip description after " — " or " - "
    display_ref = reference.strip()
    for sep in [' \u2014 ', ' \u2013 ', ' - ']:
        if sep in display_ref:
            display_ref = display_ref.split(sep)[0].strip()

    params = {"search": display_ref, "version": VERSION}
    resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)

    if resp.status_code != 200:
        raise ValueError(f"Bible Gateway returned {resp.status_code} for '{display_ref}'")

    soup = BeautifulSoup(resp.text, "html.parser")

    # Find all text containers — non-contiguous ranges (e.g. "Psalm 118:1-2, 14-24")
    # produce multiple result-text-style-normal divs; collect all of them.
    passage_wraps = soup.find_all("div", class_=re.compile(r"result-text-style-normal"))

    if not passage_wraps:
        # Fallback: try passage-content
        fallback = soup.find("div", class_="passage-content")
        if fallback:
            passage_wraps = [fallback]

    if not passage_wraps:
        raise ValueError(
            f"Could not find passage text for '{display_ref}'. "
            "Check the reference format, e.g. 'Matthew 28:1-10'."
        )

    segments = []
    for passage_wrap in passage_wraps:
        # Remove footnotes, crossrefs, verse numbers, chapter numbers, and headings
        for tag in list(passage_wrap.find_all(["sup", "h1", "h2", "h3", "h4"])):
            classes = " ".join(tag.get("class", []))
            # Remove noise elements with known classes
            if any(x in classes for x in ["footnote", "crossref", "chapternum", "versenum"]):
                tag.decompose()
            # Remove section headings and footnote/crossref headers (no class = editorial heading)
            elif not classes and tag.name in ("h3", "h4"):
                tag.decompose()
            # Remove chapter number headings (e.g. "Psalm 118" displayed as h3.chapter)
            elif "chapter" in classes and tag.name in ("h3", "h4"):
                tag.decompose()

        for tag in list(passage_wrap.find_all("span")):
            classes = " ".join(tag.get("class", []))
            if any(x in classes for x in ["chapternum", "versenum"]):
                tag.decompose()

        for tag in list(passage_wrap.find_all("div", class_=re.compile(r"footnotes|crossrefs"))):
            tag.decompose()

        raw = passage_wrap.get_text(separator=" ")
        # Normalize non-breaking / unicode spaces first — Bible Gateway uses &nbsp;
        # ( ) for poetic-line indentation, which otherwise survives as funky
        # multi-space gaps mid-line in poetry (e.g. Zechariah 9, the Psalms).
        raw = raw.replace(" ", " ").replace(" ", " ").replace(" ", " ")
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        segment = re.sub(r"\s+", " ", " ".join(lines)).strip()
        # Remove trailing "Read full chapter" link text
        segment = re.sub(r"\s*Read full chapter\s*$", "", segment).strip()
        if segment:
            segments.append(segment)

    text = " … ".join(segments)
    # Fix spacing artifacts from link tags (e.g. "the Lord ," → "the Lord,")
    text = re.sub(r" ([,;:.!?''])", r"\1", text)
    # Fix possessives with space (e.g. "Lord 's" → "Lord's") — handles curly apostrophes
    text = re.sub(r" (\u2019s|\u2018s|'s)\b", r"\1", text)

    if not text:
        raise ValueError(f"No text extracted for '{display_ref}'")

    return display_ref, text


def format_passage(ref: str, text: str) -> str:
    """Format for display."""
    bar = "\u2500" * 52
    return f"\n{bar}\n  {ref}  (NRSV)\n{bar}\n{text}\n{bar}\n"


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
            print(f"  \u2705 {slot}: {display_ref}")
        except Exception as e:
            result[slot] = ref
            print(f"  \u26a0\ufe0f  {slot}: could not fetch — {e}")
    return result


def interactive_mode():
    print("\n\U0001f4d6  Scripture Fetcher (NRSV via Bible Gateway)")
    print("    Type a reference or 'q' to quit.")
    print("    Examples: 'Matthew 28:1-10'  |  'Acts 10:34-43'  |  'Psalm 118:1-2, 14-24'")
    print()

    while True:
        try:
            ref = input("Reference: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not ref or ref.lower() in ("q", "quit", "exit"):
            print("Goodbye!")
            break

        try:
            display_ref, text = fetch_passage(ref)
            print(format_passage(display_ref, text))
        except ValueError as e:
            print(f"\n\u274c  {e}\n")
        except Exception as e:
            print(f"\n\u274c  Network error: {e}\n")


def main():
    if len(sys.argv) > 1:
        ref_string = " ".join(sys.argv[1:])
        try:
            display_ref, text = fetch_passage(ref_string)
            print(format_passage(display_ref, text))
        except ValueError as e:
            print(f"\n\u274c  {e}\n")
            sys.exit(1)
        except Exception as e:
            print(f"\n\u274c  Network error: {e}\n")
            sys.exit(1)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
