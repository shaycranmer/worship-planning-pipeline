#!/usr/bin/env python3
"""
STEP 1: Get song suggestions from database.
Swap in the week's theme keywords and slots below, then run:
    python3 get_suggestions.py
Bring the results back to the liturgist to pick songs!
"""

import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from worship_plan_generator import WorshipPlanGenerator

gen = WorshipPlanGenerator("worship.db")

# ============================================================
# SWAP THESE OUT EACH WEEK WITH THE WEEK'S KEYWORDS AND SLOTS
# ============================================================

keywords = ['seen', 'known', 'loved', 'beloved', 'call', 'promise', 'blessing', 'trust', 'new_beginnings', 'spirit', 'night', 'assurance', 'rest']

slots = ['gathering', 'hymn_of_day', 'offering', 'communion', 'sending']

# ============================================================

suggestions = gen.suggest_songs(keywords, slots)

print("\n" + "=" * 70)
print("SONG SUGGESTIONS FROM DATABASE")
print("=" * 70)

for slot, song_list in suggestions.items():
    print(f"\n{slot.upper().replace('_', ' ')}:")
    print("-" * 40)
    if song_list:
        for i, song in enumerate(song_list, 1):
            has_lyrics = "✓ lyrics" if song.get('lyrics') else "  no lyrics"
            times = song.get('times_used', 0)
            last = song.get('last_used_date', 'never') or 'never'
            if song['type'] == 'traditional' and song.get('hymnal_number'):
                print(f"  {i}. {song['title']} ({song['hymnal_number']}) [{has_lyrics}] - used {times}x, last: {last}")
            else:
                print(f"  {i}. {song['title']} - {song['artist_source']} [{has_lyrics}] - used {times}x, last: {last}")
    else:
        print("  (no matches found - try different keywords)")

print("\n" + "=" * 70)
print("Copy these suggestions and bring them back to the liturgist to pick songs!")
print("=" * 70 + "\n")

gen.close()
