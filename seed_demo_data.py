#!/usr/bin/env python3
"""
seed_demo_data.py — Build the demonstration database for Trinity Community Church,
a fictional congregation.

Every song, artist, service, and note below is invented for demonstration.
No production data, and no information about any real congregation or person,
appears anywhere in this repository — that exclusion is a design decision,
documented in the README's data-handling section.

Run:  python3 seed_demo_data.py     (creates worship.db in this folder)
"""

import os
from datetime import date, timedelta
from worship_database import WorshipDatabase

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "worship.db")

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("Removed old demo database.")

db = WorshipDatabase(DB_PATH)

# ── Fictional song library ─────────────────────────────────────────────────────
# Invented titles, invented artists, fictional "TCH" hymnal numbers.
SONGS = [
    # (title, type, artist_source, hymnal#, tags, key, complexity, familiarity, notes, lyrics, typical_leader)
    ("Morning by the Water",     "contemporary", "River & Reed",              None,  "creation,gathering,morning",   "G",  "easy",      "well-known", "Band note: sits best in G for our vocal range.",
        "Morning by the water, mercy on the tide, / everything that slept awakes, everything's alive. / Gather at the edges, sing the day begun, / love has met us early, warm as morning sun.", "band"),
    ("Come, Bright Dawn",        "contemporary", "The Meadowlark Collective", None,  "hope,resurrection,light",      "D",  "moderate",  "familiar",   "Capo 2 on guitar; keys lead the intro.",
        "Come, bright dawn, over the hills of our waiting, / come, bright dawn, gentle and gold on our grief. / Night was long but never once was it winning, / morning writes mercy on every leaf.", "cantor"),
    ("Deep Calls to Deep",       "contemporary", "Harbor Lane",               None,  "lament,trust,water",           "Em", "moderate",  "learning",   "New this season; teach pre-service twice before using.",
        "Deep calls to deep in the roar of the waters, / all of your waves have washed over me. / Still I will trust when the current is pulling, / you are the shore I cannot yet see.", "cantor"),
    ("Every Table Widens",       "contemporary", "River & Reed",              None,  "communion,welcome,justice",    "C",  "easy",      "familiar",   "Communion favorite; verse 3 optional when time is short.",
        "Every table widens when the stranger takes a seat, / every loaf is larger broken than complete. / Come and find your hunger answered here with room to spare, / grace is not divided, grace is everywhere.", "band"),
    ("Wind Over the Fields",     "contemporary", "Cass & Corridor",           None,  "pentecost,spirit,renewal",     "A",  "difficult", "new",        "Syncopated bridge; drummer should count the band in.",
        "Wind over the fields, fire on our tongues, / breath of the beginning, sing us into one. / Shake the settled rafters, wake the weary throng, / Spirit, reign within us, teach us all your song.", "band"),
    ("Light the Long Night",     "contemporary", "The Meadowlark Collective", None,  "advent,waiting,hope",          "Bm", "moderate",  "familiar",   "Advent staple; candles verse works a cappella.",
        "Light the long night, one candle at a time, / hope is a small flame learning how to climb. / We who walk in darkness carry what we know: / every promised morning starts this small, this slow.", "cantor"),
    ("Garden at First Light",    "contemporary", "Harbor Lane",               None,  "easter,surprise,tenderness",   "G",  "easy",      "learning",   "Pairs well with resurrection narratives.",
        "In the garden at first light, someone says her name, / all the world is otherwise, nothing is the same. / Tender as the morning, quiet as the dew, / everything she buried walks the path with her anew.", "cantor"),
    ("O Rising Sun of Justice",  "traditional",  "TCH Hymnal",                "214", "justice,morning,discipleship", "F",  "easy",      "well-known", "Congregation sings all four verses from memory.",
        "O rising sun of justice, dispel our idle sleep, / and warm the frozen places where mercy waits to leap. / Make plain the crooked highway, make soft the hardened will, / till all your hungry children have eaten and are filled.", "organ"),
    ("Gather at the Shoreline",  "traditional",  "TCH Hymnal",                "89",  "gathering,baptism,water",      "Bb", "easy",      "well-known", "Processional favorite for baptism Sundays.",
        "Gather at the shoreline, people of the flood, / remember in the water you were claimed and called beloved. / The river runs before us older than our fear; / gather at the shoreline, God has brought us here.", "organ"),
    ("Bread for the Wandering",  "traditional",  "TCH Hymnal",                "377", "communion,pilgrimage,comfort", "Eb", "moderate",  "familiar",   "Organ introduction; band tacet first verse.",
        "Bread for the wandering, wine for the worn, / table of welcome spread since the morn. / Long is the journey, short is the rest; / here at your table the weary are blessed.", "organ"),
    ("Sing, You Sleeping Bones", "traditional",  "TCH Hymnal",                "402", "resurrection,lent,dry-bones",  "Dm", "moderate",  "learning",   "Ezekiel imagery; strong Lent 5 pairing.",
        "Sing, you sleeping bones, the breath is coming near, / valley of the scattered, the wind is at your ear. / Sinew, flesh, and spirit, knitted by the Word: / nothing is too broken to be summoned and be heard.", "choir"),
    ("Canticle of the Deep",     "traditional",  "TCH Hymnal",                "156", "creation,water,praise",        "D",  "moderate",  "familiar",   "Descant on final verse if sopranos are present.",
        "All you deeps and dwellings of the waters wide, / bless the One who made you, in whom the tides abide. / Great lakes and small rivers, rain and hidden spring, / join the ancient chorus every creature sings.", "choir"),
    ("Now the Quiet Descends",   "traditional",  "TCH Hymnal",                "521", "evening,peace,sending",        "C",  "easy",      "well-known", "Benediction standard; unaccompanied final verse.",
        "Now the quiet descends like the dusk on the field, / all our labor is gathered, our gladness is sealed. / Go in gentleness, go in the keeping of grace; / God goes on before us to light every place.", "organ"),
    ("Alleluia round the Table", "liturgical",   "TCH Hymnal",                "301", "acclamation,gospel,joy",       "G",  "easy",      "well-known", "Default gospel acclamation in ordinary time.",
        "Alleluia, alleluia, round the table of the Word; / open now our hearts to listen, let the gospel here be heard.", "cantor"),
]

ids = {}
for title, stype, artist, hymnal, tags, key, complexity, fam, notes, lyrics, leader in SONGS:
    ids[title] = db.add_song(
        title=title, song_type=stype, artist_source=artist, hymnal_number=hymnal,
        tags=tags, key_signature=key, teaching_complexity=complexity,
        congregational_familiarity=fam, notes=notes, lyrics=lyrics, typical_leader=leader)
print(f"Seeded {len(SONGS)} fictional songs.")

# ── Fictional liturgical elements ──────────────────────────────────────────────
db.add_liturgical_element("prayer",
    "God of every shoreline, you gather the scattered and steady the unsure. "
    "Meet us in word and song, that what we hear together we may live apart, "
    "in courage and in kindness. **Amen.**",
    tags="ordinary-time,gathering", source="Demo text, written for this sample repository.")
db.add_liturgical_element("blessing",
    "May the road hold you, the water keep you, and the light go on ahead of you, "
    "this day and always. **Amen.**",
    tags="sending", source="Demo text, written for this sample repository.")
print("Seeded liturgical elements.")

# ── Fictional service history (drives the usage-frequency logic) ───────────────
today = date(2026, 7, 12)
HISTORY = [
    (today - timedelta(days=7),  "Ordinary Time", "Rooted and Reaching",
        ["Morning by the Water", "Alleluia round the Table", "Every Table Widens", "Now the Quiet Descends"]),
    (today - timedelta(days=14), "Ordinary Time", "The Mustard Seed Economy",
        ["Gather at the Shoreline", "Alleluia round the Table", "Bread for the Wandering", "O Rising Sun of Justice"]),
    (today - timedelta(days=21), "Ordinary Time", "Storm and Stillness",
        ["Deep Calls to Deep", "Alleluia round the Table", "Canticle of the Deep", "Now the Quiet Descends"]),
    (today - timedelta(days=35), "Pentecost", "Wind and Fire, Gift and Task",
        ["Wind Over the Fields", "Alleluia round the Table", "Every Table Widens", "O Rising Sun of Justice"]),
    (today - timedelta(days=63), "Easter", "Something Has Changed",
        ["Garden at First Light", "Alleluia round the Table", "Bread for the Wandering", "Come, Bright Dawn"]),
    (today - timedelta(days=140), "Advent", "Keeping Watch",
        ["Light the Long Night", "Gather at the Shoreline", "Bread for the Wandering", "Now the Quiet Descends"]),
]
SLOTS = ["gathering", "gospel_acclamation", "hymn_of_day", "sending"]
for sdate, season, theme, titles in HISTORY:
    db.record_complete_service(service_date=sdate, song_ids=[ids[t] for t in titles],
                               season=season, theme=theme, slots=SLOTS)

# One per-use note: the "lived memory" the flag pass surfaces before repeat use
import sqlite3
conn = sqlite3.connect(DB_PATH)
conn.execute("""UPDATE service_songs SET notes='Cut verse 3 for time; keep an eye on length.'
    WHERE song_id=? AND service_id=(SELECT id FROM service_history ORDER BY date DESC LIMIT 1)""",
    (ids["Every Table Widens"],))
conn.commit(); conn.close()
print("Seeded one per-use service note (lived memory demo).")
print(f"Seeded {len(HISTORY)} fictional services of history.")

# ── Fictional sheet-music resources ────────────────────────────────────────────
for title, rtype, path in [
    ("Morning by the Water", "guitar chart", "music_library/morning_by_the_water_G.pdf"),
    ("Every Table Widens",   "guitar chart", "music_library/every_table_widens_C.pdf"),
    ("O Rising Sun of Justice", "piano accompaniment", "music_library/tch214_o_rising_sun.pdf"),
]:
    db.add_resource(song_id=ids[title], resource_type=rtype, file_path=path,
                    notes=f"Demo resource entry for {title}")
print("Seeded resource links.")

db.close()
print(f"\nDemo database ready: {DB_PATH}")
print("Fictional congregation: Trinity Community Church. No real data anywhere.")
