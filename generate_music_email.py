#!/usr/bin/env python3
"""
generate_music_email.py
-----------------------
Generates the weekly music resource email for the congregation's band.

Usage (from natural language input; the planning assistant handles the parsing):
  python3 generate_music_email.py

Or import and call directly:
  from generate_music_email import build_email
  result = build_email(
      service_date="2026-05-03",
      roster=["Arielle", "Dave", "Sophia", "Victoriya"],
      new_musicians=["Arielle"],
      special_notes="Thanks for a great Easter season. Lydia's Table this week.",
      include_liturgical=False   # set True if new musician on roster
  )
"""

import sqlite3
import os
import re
import json
from datetime import date, datetime

# ── Config ──────────────────────────────────────────────────────────────────
DB_PATH      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "worship.db")
MUSIC_LIB    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music_library")
INPUT_JSON   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "worship_input.json")
SPOTIFY_LINK = "https://open.spotify.com/playlist/2v2gaVMVAzlbq4fwfVhhfU"
VOCAL_PARTS_LINK = "https://drive.google.com/drive/folders/1biYoqEyX4_tNX4O6606UgBfPKYkeLYTV?usp=drive_link"

# These are liturgical by function even if not in DB as type='liturgical'
LITURGICAL_TITLES = ['kyrie', 'lamb of god', 'agnus dei']

# Keywords in service notes that warrant a review flag
FLAG_KEYWORDS = [
    "don't assign", "do not assign", "revisit", "check", "ensure",
    "struggled", "difficult", "wrong", "caution", "note:", "needs real",
    "next time", "double check"
]

# ── File finder ─────────────────────────────────────────────────────────────
def find_pdfs(song_title):
    """
    Search Music PDF Library for files matching a song title.
    Returns dict: {'voice': [...], 'piano': [...], 'chords': [...], 'choir': [...], 'other': [...]}

    Disambiguation logic:
    - If the title has a parenthetical (e.g. "Come As You Are (Shane and Shane)"),
      first try to match files that include that disambiguator.
    - If no files match with the disambiguator, fall back to the base title.
    - This prevents "Come As You Are (The Many)" from appearing when the plan
      calls for "Come As You Are (Shane and Shane)".
    """
    disambiguator = re.search(r'\(([^)]+)\)', song_title)
    base = re.sub(r'\s*\([^)]+\)', '', song_title).strip().lower()
    # Normalize punctuation for matching — handles titles like "Halle, Halle, Hallelujah"
    # where files may be named without commas
    base_match = re.sub(r'[,;]', '', base).strip()
    result = {'voice': [], 'piano': [], 'chords': [], 'choir': [], 'other': []}

    try:
        all_files = sorted(os.listdir(MUSIC_LIB))

        def fname_match(f, term):
            """Match term against filename, normalizing punctuation on both sides."""
            return re.sub(r'[,;]', '', f.lower()).find(re.sub(r'[,;]', '', term.lower())) != -1

        # If there's a disambiguator, try to match files that include it first
        if disambiguator:
            disambig_lower = disambiguator.group(1).lower()
            specific_files = [f for f in all_files
                              if f.lower().endswith('.pdf')
                              and fname_match(f, base)
                              and disambig_lower in f.lower()]
            if specific_files:
                # Only use files that match the specific version
                all_files = specific_files
            else:
                # Fall back to base title only (no disambiguated version exists yet)
                all_files = [f for f in all_files
                             if f.lower().endswith('.pdf') and fname_match(f, base)]
        else:
            all_files = [f for f in all_files
                         if f.lower().endswith('.pdf') and fname_match(f, base)]

        for fname in all_files:
            if not fname_match(fname, base):
                continue
            f = fname.lower()
            if 'choral' in f or 'choir' in f or 'accompaniment' in f:
                result['choir'].append(fname)
            elif 'voice' in f or 'vocal' in f:
                result['voice'].append(fname)
            elif 'piano' in f:
                result['piano'].append(fname)
            elif 'chord' in f:
                result['chords'].append(fname)
            else:
                result['other'].append(fname)
    except FileNotFoundError:
        pass

    return result


# ── DB helpers ───────────────────────────────────────────────────────────────
def get_song_db(cur, title):
    """Look up a song by title (fuzzy). Returns row dict or None."""
    cur.execute(
        "SELECT id, title, type, typical_leader, key_signature, files_verified, notes "
        "FROM songs WHERE title = ? COLLATE NOCASE",
        (title,)
    )
    row = cur.fetchone()
    if not row:
        # Try contains match
        cur.execute(
            "SELECT id, title, type, typical_leader, key_signature, files_verified, notes "
            "FROM songs WHERE title LIKE ? COLLATE NOCASE LIMIT 1",
            (f"%{title}%",)
        )
        row = cur.fetchone()
    if row:
        return dict(zip(['id','title','type','typical_leader','key_signature','files_verified','notes'], row))
    return None


def get_last_performance_note(cur, song_id):
    """Pull the most recent service note for a song. Returns (date_str, slot, note) or None."""
    cur.execute("""
        SELECT sh.date, ss.slot, ss.notes
        FROM service_songs ss
        JOIN service_history sh ON ss.service_id = sh.id
        WHERE ss.song_id = ? AND ss.notes IS NOT NULL AND ss.notes != ''
        ORDER BY sh.date DESC LIMIT 1
    """, (song_id,))
    return cur.fetchone()


def get_musician(cur, name):
    """Look up a musician by first name (case-insensitive). Returns row dict or None."""
    cur.execute(
        "SELECT id, name, email, instrument, music_preference FROM musicians "
        "WHERE name LIKE ? AND is_active = 1",
        (f"%{name}%",)
    )
    row = cur.fetchone()
    if row:
        return dict(zip(['id','name','email','instrument','music_preference'], row))
    return None


def get_all_musicians(cur):
    """Return all active musicians as list of dicts."""
    cur.execute(
        "SELECT id, name, email, instrument, music_preference FROM musicians WHERE is_active = 1"
    )
    cols = ['id','name','email','instrument','music_preference']
    return [dict(zip(cols, row)) for row in cur.fetchall()]


# ── Song slot label formatter ────────────────────────────────────────────────
SLOT_LABELS = {
    'gathering':          'Gathering',
    'gospel_acclamation': 'Gospel Acclamation',
    'hymn_of_day':        'Hymn of the Day',
    'offering':           'Offering',
    'communion':          'Communion',
    'sending':            'Sending',
    'entrance':           'Entrance',
}

def slot_label(slot):
    return SLOT_LABELS.get(slot, slot.replace('_', ' ').title())


def is_liturgical(song_title, song_type):
    """Return True if this song should be skipped unless onboarding."""
    if song_type in ('liturgical',):
        return True
    if any(t in song_title.lower() for t in LITURGICAL_TITLES):
        return True
    return False


# ── Core builder ─────────────────────────────────────────────────────────────
def build_email(
    service_date=None,
    roster=None,
    new_musicians=None,
    special_notes=None,
    include_liturgical=False,
    from_json=True
):
    """
    Build the weekly music email.

    Returns a dict:
      {
        'email_body': str,           # the full email text
        'attachments': [str],        # list of PDF filenames to attach
        'attachment_paths': [str],   # full paths for each attachment
        'flags': [str],              # warnings for the worship leader to review
        'missing_files': [str],      # songs where no PDF was found
        'unverified_songs': [str],   # songs where files_verified = 0
      }
    """
    roster        = roster or []
    new_musicians = new_musicians or []
    flags         = []
    attachments   = []
    attachment_paths = []
    missing_files = []
    unverified    = []

    # ── Load service plan ────────────────────────────────────────────────────
    songs_in_service = []   # list of (slot, title)

    if from_json:
        with open(INPUT_JSON) as f:
            plan = json.load(f)
        if service_date is None:
            service_date = plan.get('date', '')
        for slot, title in plan.get('songs', {}).items():
            songs_in_service.append((slot, title))
    else:
        # Pull from service_history if the service is already logged
        conn_check = sqlite3.connect(DB_PATH)
        c = conn_check.cursor()
        c.execute("""
            SELECT ss.slot, s.title
            FROM service_songs ss
            JOIN songs s ON ss.song_id = s.id
            JOIN service_history sh ON ss.service_id = sh.id
            WHERE sh.date = ?
            ORDER BY ss.order_in_service
        """, (service_date,))
        songs_in_service = [(row[0], row[1]) for row in c.fetchall()]
        conn_check.close()

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # ── Choir special flag ───────────────────────────────────────────────────
    # Check if offering slot is a choir special. If so, Victoriya takes the
    # choir downstairs for sound check at 9:00am, cutting into band rehearsal.
    # This gets stressful with new singers or heavy contemporary weeks.
    offering_song = next((t for s, t in songs_in_service if s == 'offering'), None)
    if offering_song:
        offering_db = get_song_db(cur, offering_song)
        is_choir_special = offering_db and offering_db.get('type') == 'choir'
        has_new_musicians = bool(new_musicians)

        # Also flag if it's a contemporary-heavy week (more than 2 contemporary songs)
        contemporary_count = 0
        for slot, title in songs_in_service:
            song = get_song_db(cur, title)
            if song and song.get('type') == 'contemporary':
                contemporary_count += 1
        heavy_contemporary = contemporary_count >= 3

        if is_choir_special and (has_new_musicians or heavy_contemporary):
            flags.append(
                f"⚑ REHEARSAL TIME: Choir special this week — Victoriya takes choir to "
                f"sound check at 9:00am. This cuts into band rehearsal time. "
                f"{'New musicians on roster (' + ', '.join(new_musicians) + '). ' if has_new_musicians else ''}"
                f"{'Heavy contemporary week (' + str(contemporary_count) + ' contemporary songs). ' if heavy_contemporary else ''}"
                f"Plan rehearsal order explicitly or confirm timing is workable."
            )
        elif is_choir_special:
            flags.append(
                "⚑ REHEARSAL NOTE: Choir special this week — Victoriya takes choir to "
                "sound check at 9:00am. Confirm band rehearsal time is workable."
            )

    # ── Build song block + attachments ──────────────────────────────────────
    song_lines   = []
    per_song_flags = []

    for slot, title in songs_in_service:
        db_song = get_song_db(cur, title)
        stype   = db_song['type'] if db_song else 'traditional'

        # Skip liturgical unless we're onboarding
        if is_liturgical(title, stype) and not include_liturgical:
            # Still list it in the song block, just don't attach music
            hymnal = ''
            if db_song and db_song.get('notes') and 'ELW' in str(db_song.get('notes', '')):
                pass  # could pull hymnal number
            song_lines.append(f"{slot_label(slot)}: {title}")
            continue

        # Build the display line
        line = f"{slot_label(slot)}: {title}"

        # Surface typical leader if they're on the roster this week
        leader_note = ''
        if db_song and db_song.get('typical_leader'):
            leader = db_song['typical_leader']
            if any(leader.lower() in r.lower() for r in roster):
                line += f" ({leader} leads)"
                leader_note = leader

        # Pull last performance note
        if db_song:
            last = get_last_performance_note(cur, db_song['id'])
            if last:
                last_date, last_slot, last_note = last
                # Flag if note contains action keywords
                note_lower = last_note.lower()
                if any(kw in note_lower for kw in FLAG_KEYWORDS):
                    per_song_flags.append(
                        f"⚑ {title} (last {last_date}): {last_note[:120]}{'...' if len(last_note) > 120 else ''}"
                    )

        song_lines.append(line)

        # Find and collect PDFs
        if db_song and not db_song['files_verified']:
            unverified.append(title)

        pdfs = find_pdfs(title)
        all_found = pdfs['voice'] + pdfs['piano'] + pdfs['chords'] + pdfs['choir'] + pdfs['other']

        if not all_found:
            missing_files.append(title)
        else:
            for cat in ('voice', 'piano', 'chords', 'choir', 'other'):
                for fname in pdfs[cat]:
                    if fname not in attachments:
                        attachments.append(fname)
                        attachment_paths.append(os.path.join(MUSIC_LIB, fname))

    conn.close()

    # ── Build musician roster info ──────────────────────────────────────────
    # (Used for tone of the intro — not rendered in email body by default)
    # The worship leader writes the personal intro; we surface the bones they need.

    # ── Compose email body ──────────────────────────────────────────────────
    lines = []

    # Greeting
    lines.append("Hey team!")
    lines.append("")

    # Special notes block (the leader's personal message)
    if special_notes:
        lines.append(special_notes)
        lines.append("")

    # New musician onboarding note (if applicable)
    if new_musicians:
        for nm in new_musicians:
            lines.append(
                f"{nm}, I usually send out a fairly extensive pile of sheet music. "
                "Not ALL of it will be necessary — much of it is to give you choices. "
                "For each song, decide what type of music you'd prefer to work from "
                "(full piano sheet, chords and lyrics, or vocal part) and print just that one."
            )
        lines.append("")

    # Song list
    lines.append("Here's the music for the upcoming week:")
    lines.append("")
    for line in song_lines:
        lines.append(line)
    lines.append("")

    # Spotify
    lines.append(f"Playlist of Recordings: {SPOTIFY_LINK}")
    lines.append("")

    # Vocal parts (Google Drive, searchable by song)
    lines.append(f"Vocal Parts for the week (searchable by song): {VOCAL_PARTS_LINK}")
    lines.append("")

    # Attachment note
    if attachments:
        lines.append("Sheet Music: (attached below)")
    elif missing_files:
        lines.append("Sheet Music: [⚑ Some files could not be located — see flags]")
    lines.append("")

    # Sign off
    lines.append("See you Sunday,")
    lines.append("The Worship Team")

    email_body = "\n".join(lines)

    # ── Compile flags ────────────────────────────────────────────────────────
    if unverified:
        flags.append(f"⚑ Unverified file library for: {', '.join(unverified)} — confirm PDFs before sending.")
    if missing_files:
        flags.append(f"⚑ No PDFs found for: {', '.join(missing_files)} — attach manually.")
    flags.extend(per_song_flags)

    return {
        'email_body':      email_body,
        'attachments':     attachments,
        'attachment_paths': attachment_paths,
        'flags':           flags,
        'missing_files':   missing_files,
        'unverified_songs': unverified,
        'service_date':    service_date,
    }


# ── CLI runner ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("📧 Music email generator\n")
    print("Reading from worship_input.json...\n")

    result = build_email(
        roster=["Dave", "Sophia", "Arielle", "Victoriya"],
        special_notes="Thanks for a beautiful Easter season — you all have been incredible. Here's the music for this Sunday.",
        new_musicians=[],
        include_liturgical=False
    )

    print("=" * 60)
    print("EMAIL DRAFT")
    print("=" * 60)
    print(result['email_body'])

    print("\n" + "=" * 60)
    print("ATTACHMENTS")
    print("=" * 60)
    for f in result['attachments']:
        print(f"  📎 {f}")

    if result['flags']:
        print("\n" + "=" * 60)
        print("FLAGS FOR REVIEW")
        print("=" * 60)
        for flag in result['flags']:
            print(f"  {flag}")

    if result['missing_files']:
        print("\n⚑ MISSING FILES (attach manually):")
        for m in result['missing_files']:
            print(f"  - {m}")

    if result['unverified_songs']:
        print("\n⚑ UNVERIFIED IN LIBRARY (double-check before sending):")
        for u in result['unverified_songs']:
            print(f"  - {u}")
