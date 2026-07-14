#!/usr/bin/env python3
"""
add_resources.py - Link music files (PDFs etc.) to songs in the database.

Usage: python3 add_resources.py
"""

import sqlite3
import os
import glob

DB_PATH = os.path.join(os.path.dirname(__file__), 'worship.db')

# Auto-detect Google Drive base path
def find_google_drive_path():
    cloud_storage = os.path.expanduser('~/Library/CloudStorage')
    if os.path.exists(cloud_storage):
        drives = glob.glob(os.path.join(cloud_storage, 'GoogleDrive-*', 'My Drive'))
        if drives:
            return drives[0]
    # Fallback: check old-style Google Drive path
    old_path = os.path.expanduser('~/Google Drive/My Drive')
    if os.path.exists(old_path):
        return old_path
    return None

GOOGLE_DRIVE_BASE = find_google_drive_path()
MUSIC_LIBRARY = os.path.join(GOOGLE_DRIVE_BASE, "Trinity Music Library") if GOOGLE_DRIVE_BASE else None

RESOURCE_TYPES = {
    '1': ('piano', 'Piano sheet (full accompaniment)'),
    '2': ('chords', 'Chord chart'),
    '3': ('vocal', 'Vocal part'),
    '4': ('master', 'MuseScore master file'),
    '5': ('other', 'Other'),
}

def get_db():
    return sqlite3.connect(DB_PATH)

def search_songs(query):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, artist_source, hymnal_number
        FROM songs
        WHERE title LIKE ? OR artist_source LIKE ?
        ORDER BY title
        LIMIT 20
    ''', (f'%{query}%', f'%{query}%'))
    results = cursor.fetchall()
    conn.close()
    return results

def get_song_resources(song_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, resource_type, key_signature, file_path, notes
        FROM resources
        WHERE song_id = ?
        ORDER BY resource_type
    ''', (song_id,))
    results = cursor.fetchall()
    conn.close()
    return results

def show_resources(song_id, song_title):
    resources = get_song_resources(song_id)
    if not resources:
        print(f'  No resources linked yet for "{song_title}"')
    else:
        print(f'  Resources for "{song_title}":')
        for r in resources:
            key_str = f' [{r[2]}]' if r[2] else ''
            notes_str = f'; {r[4]}' if r[4] else ''
            exists = '✅' if os.path.exists(r[3]) else '❌ FILE MISSING'
            print(f'    ID {r[0]}: {r[1]}{key_str}{notes_str}')
            print(f'      {exists} {r[3]}')

def pick_song():
    """Search for and select a song. Returns (song_id, song_title) or None."""
    query = input('\nSearch for song (title or artist): ').strip()
    if not query:
        return None

    results = search_songs(query)
    if not results:
        print('  No songs found.')
        return None

    print()
    for i, (sid, title, artist, hymnal) in enumerate(results, 1):
        hymnal_str = f' [{hymnal}]' if hymnal else ''
        artist_str = f'; {artist}' if artist else ''
        print(f'  {i}. ID {sid:3d}: {title}{artist_str}{hymnal_str}')

    choice = input('\nEnter number (or Enter to cancel): ').strip()
    if not choice:
        return None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(results):
            return results[idx][0], results[idx][1]
    except ValueError:
        pass
    print('  Invalid choice.')
    return None

def add_resource():
    """Add a resource file link for a song."""
    result = pick_song()
    if not result:
        return
    song_id, song_title = result

    # Show existing resources first
    print()
    show_resources(song_id, song_title)
    print()

    # Pick resource type
    print('Resource type:')
    for key, (rtype, desc) in RESOURCE_TYPES.items():
        print(f'  {key}. {rtype}; {desc}')
    type_choice = input('Enter number: ').strip()
    if type_choice not in RESOURCE_TYPES:
        print('  Invalid choice.')
        return
    resource_type = RESOURCE_TYPES[type_choice][0]

    # Key signature
    key_sig = input('Key signature (e.g. Bb, G, D; or Enter to skip): ').strip() or None

    # File path
    print()
    if MUSIC_LIBRARY:
        print(f'  Google Drive Music Library: {MUSIC_LIBRARY}')
        print('  Tip: drag a file from Finder into Terminal to paste its path')
    file_path = input('Full file path to PDF: ').strip().strip("'\"")

    if not file_path:
        print('  No path entered, cancelled.')
        return

    # Validate path exists
    if not os.path.exists(file_path):
        print(f'  ⚠️  Warning: file not found at that path: {file_path}')
        confirm = input('  Save anyway? (y/N): ').strip().lower()
        if confirm != 'y':
            print('  Cancelled.')
            return

    # Notes
    notes = input('Notes (e.g. "SATB", "no chords", "2-part"; or Enter to skip): ').strip() or None

    # Save to DB
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO resources (song_id, resource_type, file_path, key_signature, notes)
        VALUES (?, ?, ?, ?, ?)
    ''', (song_id, resource_type, file_path, key_sig, notes))
    conn.commit()
    resource_id = cursor.lastrowid
    conn.close()

    key_str = f' in {key_sig}' if key_sig else ''
    print(f'\n✅ Saved! Resource ID {resource_id}: {resource_type}{key_str} for "{song_title}"')

def view_resources():
    """View all resources for a song."""
    result = pick_song()
    if not result:
        return
    song_id, song_title = result
    print()
    show_resources(song_id, song_title)

def list_songs_with_resources():
    """List songs that have at least one resource."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.id, s.title, COUNT(r.id) as resource_count
        FROM songs s
        JOIN resources r ON s.id = r.song_id
        GROUP BY s.id
        ORDER BY s.title
    ''')
    results = cursor.fetchall()
    conn.close()

    if not results:
        print('  No songs have resources yet.')
        return

    print(f'\n  {len(results)} songs with resources:')
    for sid, title, count in results:
        print(f'    ID {sid:3d}: {title} ({count} file{"s" if count != 1 else ""})')

def list_songs_without_resources():
    """List songs with no resources linked."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.id, s.title
        FROM songs s
        WHERE s.id NOT IN (SELECT DISTINCT song_id FROM resources)
        ORDER BY s.title
    ''')
    results = cursor.fetchall()
    conn.close()

    print(f'\n  {len(results)} songs with no resources:')
    for sid, title in results:
        print(f'    ID {sid:3d}: {title}')

def delete_resource():
    """Remove a resource entry."""
    result = pick_song()
    if not result:
        return
    song_id, song_title = result

    resources = get_song_resources(song_id)
    if not resources:
        print(f'  No resources to delete for "{song_title}"')
        return

    print()
    show_resources(song_id, song_title)
    res_id = input('\nEnter resource ID to delete (or Enter to cancel): ').strip()
    if not res_id:
        return

    try:
        res_id = int(res_id)
    except ValueError:
        print('  Invalid ID.')
        return

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM resources WHERE id = ? AND song_id = ?', (res_id, song_id))
    if cursor.rowcount:
        conn.commit()
        print(f'  🗑️  Deleted resource ID {res_id}.')
    else:
        print(f'  Resource ID {res_id} not found for this song.')
    conn.close()

def main():
    print('='*60)
    print('  RESOURCE MANAGER; Trinity Worship Database')
    print('='*60)

    if MUSIC_LIBRARY:
        exists = '✅' if os.path.exists(MUSIC_LIBRARY) else '⚠️  (folder not created yet)'
        print(f'\n  Google Drive Music Library: {exists}')
        print(f'  {MUSIC_LIBRARY}')
    else:
        print('\n  ⚠️  Google Drive desktop app not detected.')
        print('  Install from: https://www.google.com/drive/download/')
        print('  Once installed, this tool will auto-detect your Music Library path.')

    while True:
        print('\n' + '-'*40)
        print('  1. Add resource for a song')
        print('  2. View resources for a song')
        print('  3. List songs WITH resources')
        print('  4. List songs WITHOUT resources')
        print('  5. Delete a resource entry')
        print('  Q. Quit')
        print('-'*40)

        choice = input('Choice: ').strip().upper()

        if choice == '1':
            add_resource()
        elif choice == '2':
            view_resources()
        elif choice == '3':
            list_songs_with_resources()
        elif choice == '4':
            list_songs_without_resources()
        elif choice == '5':
            delete_resource()
        elif choice == 'Q':
            print('\nBye! 🎵')
            break
        else:
            print('  Invalid choice, try again.')

if __name__ == '__main__':
    main()
