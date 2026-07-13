#!/usr/bin/env python3
"""
Quick song search tool - find song IDs by title
"""

import sys
from worship_database import WorshipDatabase

if len(sys.argv) < 2:
    print("Usage: python3 search_songs.py <search term>")
    print("Example: python3 search_songs.py 'Amazing Grace'")
    sys.exit(1)

search_term = ' '.join(sys.argv[1:])

db = WorshipDatabase('worship.db')
songs = db.find_songs_by_theme(search_term)

if songs:
    print(f'\nFound {len(songs)} song(s) matching "{search_term}":')
    print('-' * 70)
    for song in songs:
        if song['type'] == 'traditional' and song.get('hymnal_number'):
            print(f"  ID {song['id']:3d}: {song['title']} ({song['hymnal_number']})")
        elif song['type'] == 'traditional':
            print(f"  ID {song['id']:3d}: {song['title']} (traditional)")
        else:
            print(f"  ID {song['id']:3d}: {song['title']} - {song['artist_source']}")
else:
    print(f'\nNo songs found matching "{search_term}"')
    print("You may need to add it to the database first!")

db.close()
