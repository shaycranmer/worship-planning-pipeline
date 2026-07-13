#!/usr/bin/env python3
"""
build_worship_plan.py — deterministic worship plan builder (post-mini pipeline).

The current pipeline. No mini-personas, no API calls, no LLM in the loop. The liturgist
real one) writes liturgy into the shared handoff folder; this script reads it,
fetches scripture in plain Python, runs the flag pass against the database, and
generates the .docx directly through the generator. Scripture never passes through
a model, so the encoding bug that plagued the retired mini-builder cannot happen here.

Inputs:
  - worship_input.json (this folder)           — structured service params (builder writes)
  - <handoff>/<date>/liturgist_blocks.txt      — liturgy, labeled plain text (liturgist writes)

Outputs:
  - Worship Plans/worship_plan_<date>_<TITLE>.docx
  - <handoff>/<date>/builder_flags.md  +  builder_BUILT marker

Usage:
  python3 build_worship_plan.py                 # build the date in worship_input.json
  python3 build_worship_plan.py 2026-06-28      # override the date
  python3 build_worship_plan.py --force         # build even if liturgist_READY is missing
"""

import os
import re
import sys
import json
import sqlite3
from datetime import date, datetime, timedelta

from worship_plan_generator import WorshipPlanGenerator
from get_scripture import fetch_readings

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DB_PATH     = os.path.join(BASE_DIR, "worship.db")
INPUT_FILE  = os.path.join(BASE_DIR, "worship_input.json")
HANDOFF_DIR = os.path.join(BASE_DIR, "handoff")

# The liturgist's UPPER_SNAKE labels → the generator's custom_chunks keys.
# Everything lowercases cleanly except PRAYERS_OF_INTERCESSION → prayers.
LABEL_TO_KEY = {
    "THANKSGIVING_FOR_BAPTISM": "thanksgiving_baptism",
    "CONFESSION":               "confession",
    "PRAYER_OF_DAY":            "prayer_of_day",
    "PRAYERS_OF_INTERCESSION":  "prayers",
    "OFFERING_PRAYER":          "offering_prayer",
    "PRAYER_AFTER_COMMUNION":   "prayer_after_communion",
    "BLESSING":                 "blessing",
    "DISMISSAL":                "dismissal",
}

# Main song slots that count toward the weekly traditional/contemporary split.
MAIN_SLOTS = ["gathering", "hymn_of_day", "offering", "communion", "sending"]

# Cumulative-weight register scan. One song with this language is fine; a set that
# leans heavy on it pulls the room toward triumphalism faster than prayers can correct.
TRIUMPHALIST = [
    "dominion", "victory", "victorious", "conquer", "conquering", "conqueror",
    "enemies", "enemy", "stronghold", "strongholds", "hell", "throne", "thrones",
    "reign", "reigns", "prison", "chains", "war", "battle", "army", "sword",
    "crush", "defeat", "mighty fortress", "shake the earth", "king of kings",
]


# ── The liturgist's blocks ───────────────────────────────────────────────────────────────
def parse_liturgist_blocks(text):
    """Parse labeled plain text into {generator_key: text}. Unknown labels are ignored."""
    chunks = {}
    current = None
    buf = []
    for line in text.splitlines():
        m = re.match(r"^([A-Z_]+):\s*(.*)$", line.strip())
        if m and m.group(1) in LABEL_TO_KEY:
            if current:
                chunks[LABEL_TO_KEY[current]] = "\n".join(buf).strip()
            current = m.group(1)
            buf = [m.group(2)] if m.group(2) else []
        elif current is not None:
            buf.append(line)
    if current:
        chunks[LABEL_TO_KEY[current]] = "\n".join(buf).strip()
    # Drop empty / placeholder blocks so the generator falls back to standard text
    return {k: v for k, v in chunks.items() if v and not v.lstrip().startswith("[")}


def load_liturgist_blocks(service_dir, force):
    blocks_path = os.path.join(service_dir, "liturgist_blocks.txt")
    ready_path  = os.path.join(service_dir, "liturgist_READY")
    if not os.path.exists(blocks_path):
        print(f"❌ No liturgist_blocks.txt in {service_dir}")
        print("   The liturgist hasn't written this week's liturgy yet.")
        sys.exit(1)
    if not os.path.exists(ready_path) and not force:
        print(f"⚠️  liturgist_READY marker is missing; the liturgist may still be writing.")
        print(f"   Re-run with --force to build anyway.")
        sys.exit(1)
    with open(blocks_path) as f:
        return parse_liturgist_blocks(f.read())


# ── Database helpers ─────────────────────────────────────────────────────────────
def lookup_song(cur, title):
    """Find a song by fuzzy title match (ignores parenthetical version tags)."""
    needle = f"%{title.split('(')[0].strip()}%"
    cur.execute("""
        SELECT id, title, type, last_used_date, times_used, notes, lyrics
        FROM songs WHERE title LIKE ? LIMIT 1
    """, (needle,))
    return cur.fetchone()


def previous_service_split(cur, service_date_str):
    """Traditional/contemporary count of the main slots in the most recent prior service."""
    cur.execute("""
        SELECT s.type, ss.slot
        FROM service_history sh
        JOIN service_songs ss ON sh.id = ss.service_id
        JOIN songs s ON ss.song_id = s.id
        WHERE sh.date < ? AND sh.date = (
            SELECT MAX(date) FROM service_history WHERE date < ?
        )
    """, (service_date_str, service_date_str))
    trad = contemp = 0
    prev_date = None
    cur.execute("SELECT MAX(date) FROM service_history WHERE date < ?", (service_date_str,))
    row = cur.fetchone()
    prev_date = row[0] if row else None
    cur.execute("""
        SELECT s.type, ss.slot
        FROM service_history sh
        JOIN service_songs ss ON sh.id = ss.service_id
        JOIN songs s ON ss.song_id = s.id
        WHERE sh.date = ?
    """, (prev_date,))
    for stype, slot in cur.fetchall():
        if slot not in MAIN_SLOTS:
            continue
        if stype == "traditional":
            trad += 1
        elif stype == "contemporary":
            contemp += 1
    return prev_date, trad, contemp


def song_use_notes(cur, song_id, service_date_str, weeks=16):
    """Per-use notes from recent services — the lived memory ('cut verse 3', 'key too high')."""
    since = (datetime.strptime(service_date_str, "%Y-%m-%d").date()
             - timedelta(weeks=weeks)).isoformat()
    cur.execute("""
        SELECT sh.date, ss.slot, ss.notes
        FROM service_songs ss
        JOIN service_history sh ON ss.service_id = sh.id
        WHERE ss.song_id = ? AND sh.date >= ? AND ss.notes IS NOT NULL AND ss.notes != ''
        ORDER BY sh.date DESC
    """, (song_id, since))
    return cur.fetchall()


# ── The flag pass (this is the part the retired mini-builder did badly) ────────────────────────
def flag_pass(ctx, conn):
    flags = []
    cur = conn.cursor()
    service_date_str = ctx["date"]
    service_date = datetime.strptime(service_date_str, "%Y-%m-%d").date()
    songs = ctx.get("songs", {})

    week_types = {}  # slot -> type, for the split

    for slot, title in songs.items():
        if not title:
            continue
        row = lookup_song(cur, title)
        if not row:
            flags.append(f"⚠️  '{title}' [{slot}] not found in the database — "
                         f"can't check history or pull lyrics. Verify the title.")
            continue
        sid, dbtitle, stype, last_used, times_used, notes, lyrics = row
        week_types[slot] = stype

        # Persistent song note; the worship leader put it there for a reason
        if notes:
            flags.append(f"📝 Song note — {dbtitle}: {notes}")

        # Repetition inside 4 weeks — the congregation notices.
        # Liturgical items (gospel acclamation, sanctus) are intentionally repeated
        # within a season, so they never count as a streak.
        if last_used and stype != "liturgical":
            try:
                lu = datetime.strptime(last_used, "%Y-%m-%d").date()
                if (service_date - lu).days <= 28:
                    flags.append(f"🔁 Repetition — {dbtitle} [{slot}] was used "
                                 f"{lu.isoformat()} ({(service_date - lu).days} days ago). "
                                 f"Consider an alternative.")
            except ValueError:
                pass

        # Lived memory — per-use notes from recent services
        for d, prev_slot, note in song_use_notes(cur, sid, service_date_str):
            flags.append(f"🧠 Last time — {dbtitle} on {d} [{prev_slot}]: {note}")

    # Weekly traditional/contemporary split vs. the previous Sunday
    trad = sum(1 for s in MAIN_SLOTS if week_types.get(s) == "traditional")
    contemp = sum(1 for s in MAIN_SLOTS if week_types.get(s) == "contemporary")
    prev_date, ptrad, pcontemp = previous_service_split(cur, service_date_str)
    if trad or contemp:
        line = (f"⚖️  Split this week: {trad} traditional / {contemp} contemporary "
                f"(main slots).")
        if prev_date:
            line += f" Previous Sunday {prev_date}: {ptrad} trad / {pcontemp} contemp."
            if (trad > contemp) == (ptrad > pcontemp) and (ptrad != pcontemp):
                line += " Same lean two weeks running — consider inverting."
        flags.append(line)

    # Triumphalist register — cumulative weight across the set
    heavy = []
    for slot, title in songs.items():
        if not title:
            continue
        row = lookup_song(cur, title)
        if not row or not row[6]:
            continue
        lyrics = row[6].lower()
        hits = sorted({kw for kw in TRIUMPHALIST
                       if re.search(r"\b" + re.escape(kw) + r"\b", lyrics)})
        if len(hits) >= 2:
            heavy.append((row[1], hits))
    if len(heavy) >= 3:
        detail = "; ".join(f"{t} ({', '.join(h)})" for t, h in heavy)
        flags.append(f"⚔️  Triumphalist register — {len(heavy)} songs lean heavy on "
                     f"conquest/dominion language: {detail}. Consider softening one slot "
                     f"toward vulnerability or lament if the theme calls for it.")

    return flags


# ── Main ─────────────────────────────────────────────────────────────────────────
def main():
    args = [a for a in sys.argv[1:]]
    force = "--force" in args
    args = [a for a in args if not a.startswith("--")]

    with open(INPUT_FILE) as f:
        ctx = json.load(f)
    if args:
        ctx["date"] = args[0]

    service_date_str = ctx["date"]
    service_dir = os.path.join(HANDOFF_DIR, service_date_str)
    print(f"\n🎵 Building worship plan for {service_date_str} — "
          f"{ctx.get('liturgical_day', ctx.get('season',''))}")
    print(f"   Theme: {ctx.get('theme','')}")
    print(f"   Template: {ctx.get('template','?')}\n")

    # 1. The liturgist's blocks
    print("📜 Reading the liturgist's blocks...")
    custom_chunks = load_liturgist_blocks(service_dir, force)
    print(f"   Got: {', '.join(custom_chunks.keys()) or '(none)'}\n")

    # 2. Scripture — deterministic, never through an LLM
    print("📖 Fetching scripture...")
    readings = fetch_readings(ctx.get("readings", {}))
    print()

    # 3. Flag pass
    print("🔍 Running the flag pass...")
    conn = sqlite3.connect(DB_PATH)
    flags = flag_pass(ctx, conn)
    conn.close()
    print(f"   {len(flags)} flag(s).\n")

    # 4. Generate the docx
    print("🔧 Generating the document...")
    y, m, d = (int(x) for x in service_date_str.split("-"))
    day = ctx.get("liturgical_day", ctx.get("season", "SERVICE")).upper()
    slug = re.sub(r"[^A-Z0-9]", "", day.replace(" ", ""))[:14]
    filename = f"worship_plan_{service_date_str.replace('-', '_')}_{slug}.docx"
    gen = WorshipPlanGenerator(DB_PATH)
    out = gen.generate_docx(
        template=ctx.get("template", "A"),
        service_date=date(y, m, d),
        season=ctx.get("season", ""),
        theme=ctx.get("theme", ""),
        readings=readings,
        songs=ctx.get("songs", {}),
        custom_chunks=custom_chunks,
        filename=filename,
    )
    gen.close()
    print(f"✅ Saved: {out}\n")

    # 5. Write flags back to the DMZ
    os.makedirs(service_dir, exist_ok=True)
    flags_path = os.path.join(service_dir, "builder_flags.md")
    with open(flags_path, "w") as f:
        f.write(f"# Builder flags: {service_date_str}\n\n")
        f.write(f"Theme: {ctx.get('theme','')}  |  Template: {ctx.get('template','?')}\n\n")
        if flags:
            for fl in flags:
                f.write(f"- {fl}\n")
        else:
            f.write("No flags — everything looks good.\n")
        f.write(f"\nPlan generated: `{os.path.basename(out)}`\n")
    open(os.path.join(service_dir, "builder_BUILT"), "w").close()

    # 6. Surface flags in the terminal too
    if flags:
        print("⚑  FLAGS (also written to builder_flags.md):")
        for fl in flags:
            print(f"   {fl}")
    else:
        print("   No flags — everything looks good.")
    print(f"\nDone. Plan in Worship Plans/, flags in {os.path.relpath(flags_path, BASE_DIR)}")


if __name__ == "__main__":
    main()
