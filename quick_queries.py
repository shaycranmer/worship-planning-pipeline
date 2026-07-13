#!/usr/bin/env python3
"""
Quick queries for the worship database.
Simple examples of how to use the database for worship planning.
"""

from worship_database import WorshipDatabase
from datetime import date, timedelta

def show_menu():
    """Display menu of available queries."""
    print("\n" + "="*60)
    print("WORSHIP DATABASE - QUICK QUERIES")
    print("="*60)
    print("\n1. Find songs not used recently (good for variety)")
    print("2. Find most used songs (check for overuse)")
    print("3. Search songs by keyword")
    print("4. View recent services")
    print("5. Get all songs (browse full list)")
    print("6. Add a new song")
    print("7. Record today's service")
    print("8. Exit")
    print("\nEnter your choice (1-8): ", end="")

def find_fresh_songs(db):
    """Find songs not used in a while."""
    print("\nHow many days back should I look?")
    days = int(input("Days (e.g., 60, 90, 120): "))

    songs = db.find_songs_not_used_in_days(days)

    print(f"\n✓ Found {len(songs)} songs not used in {days} days:")
    print("\nCONTEMPORARY:")
    contemp = [s for s in songs if s['type'] == 'contemporary']
    for song in contemp[:20]:  # Show first 20
        last_used = song['last_used_date'] or "Never"
        print(f"  • {song['title']} - {song['artist_source']} (Last: {last_used})")

    print("\nTRADITIONAL:")
    trad = [s for s in songs if s['type'] == 'traditional']
    for song in trad[:20]:  # Show first 20
        last_used = song['last_used_date'] or "Never"
        print(f"  • {song['title']} ({song['hymnal_number']}) (Last: {last_used})")

    if len(songs) > 40:
        print(f"\n... and {len(songs) - 40} more")

def show_most_used(db):
    """Show most frequently used songs."""
    print("\nHow many top songs to show?")
    limit = int(input("Number (e.g., 10, 20): "))

    songs = db.get_most_used_songs(limit=limit)

    print(f"\n✓ Top {limit} most used songs:")
    for i, song in enumerate(songs, 1):
        print(f"\n{i}. {song['title']}")
        print(f"   Type: {song['type']}")
        if song['artist_source']:
            print(f"   Artist: {song['artist_source']}")
        print(f"   Times used: {song['times_used']}")
        print(f"   Last used: {song['last_used_date'] or 'Never'}")

def search_songs(db):
    """Search for songs by keyword."""
    print("\nEnter search term (searches title, artist, tags, notes):")
    keyword = input("Search: ")

    songs = db.find_songs_by_theme(keyword)

    print(f"\n✓ Found {len(songs)} songs matching '{keyword}':")
    for song in songs:
        if song['type'] == 'contemporary':
            print(f"  • {song['title']} - {song['artist_source']}")
        else:
            print(f"  • {song['title']} ({song['hymnal_number']})")

def view_recent_services(db):
    """View recent worship services."""
    print("\nHow many recent services to show?")
    limit = int(input("Number (e.g., 5, 10): "))

    services = db.get_recent_services(limit=limit)

    print(f"\n✓ Last {limit} services:\n")
    for service in services:
        print(f"📅 {service['date']}")
        if service['theme']:
            print(f"   Theme: {service['theme']}")
        if service['season']:
            print(f"   Season: {service['season']}")

        # Get songs for this service
        songs = db.get_service_songs(service['id'])
        print(f"   Songs ({len(songs)}):")
        for song in songs:
            order = song.get('order_in_service', '?')
            print(f"     {order}. {song['title']}")
        print()

def browse_all_songs(db):
    """Browse all songs in database."""
    print("\nWhich type?")
    print("1. Contemporary")
    print("2. Traditional")
    print("3. Both")
    choice = input("Choice (1-3): ")

    if choice == "1":
        song_type = "contemporary"
    elif choice == "2":
        song_type = "traditional"
    else:
        song_type = None

    # Get all songs
    cursor = db.conn.cursor()
    if song_type:
        cursor.execute("SELECT * FROM songs WHERE type = ? ORDER BY title", (song_type,))
    else:
        cursor.execute("SELECT * FROM songs ORDER BY type, title")

    songs = cursor.fetchall()

    print(f"\n✓ Found {len(songs)} songs:\n")
    current_type = None
    for song in songs:
        if song[2] != current_type:  # type is column 2
            current_type = song[2]
            print(f"\n{current_type.upper()}:")

        title = song[1]
        artist_source = song[3]
        times_used = song[8]
        last_used = song[7] or "Never used"

        if current_type == "contemporary":
            print(f"  • {title} - {artist_source} (Used {times_used}x, Last: {last_used})")
        else:
            hymnal = song[4]
            print(f"  • {title} ({hymnal}) (Used {times_used}x, Last: {last_used})")

def add_song_interactive(db):
    """Add a new song interactively."""
    print("\n--- ADD NEW SONG ---")

    title = input("Song title: ")

    print("Type: 1=Contemporary, 2=Traditional")
    type_choice = input("Type (1 or 2): ")
    song_type = "contemporary" if type_choice == "1" else "traditional"

    artist_source = input("Artist/Source: ")

    hymnal_number = ""
    if song_type == "traditional":
        hymnal_number = input("Hymnal number (e.g., ELW 123): ")

    tags = input("Tags (comma-separated, e.g., christmas,joy,advent): ")

    key_sig = input("Key signature (e.g., G Major, optional): ")

    song_id = db.add_song(
        title=title,
        song_type=song_type,
        artist_source=artist_source,
        hymnal_number=hymnal_number if hymnal_number else None,
        tags=tags,
        key_signature=key_sig if key_sig else None
    )

    print(f"\n✓ Added song: {title} (ID: {song_id})")

def record_service_interactive(db):
    """Record a service interactively."""
    print("\n--- RECORD SERVICE ---")

    date_str = input("Date (YYYY-MM-DD) or press Enter for today: ")
    if date_str:
        service_date = date.fromisoformat(date_str)
    else:
        service_date = date.today()

    season = input("Season (e.g., Advent, Lent, Easter, optional): ")
    theme = input("Theme (optional): ")
    verses = input("Liturgical verses (optional): ")

    print("\nEnter song titles one at a time. Press Enter with no text when done.")
    song_titles = []
    while True:
        title = input(f"Song #{len(song_titles)+1} (or Enter to finish): ")
        if not title:
            break
        song_titles.append(title)

    # Find song IDs
    song_ids = []
    not_found = []
    for title in song_titles:
        songs = db.find_songs_by_theme(title)
        # Try exact match first
        exact_match = [s for s in songs if s['title'].lower() == title.lower()]
        if exact_match:
            song_ids.append(exact_match[0]['id'])
        elif songs:
            # Show options if multiple matches
            if len(songs) > 1:
                print(f"\nMultiple matches for '{title}':")
                for i, s in enumerate(songs, 1):
                    print(f"  {i}. {s['title']} ({s['type']})")
                choice = int(input("Which one? "))
                song_ids.append(songs[choice-1]['id'])
            else:
                song_ids.append(songs[0]['id'])
        else:
            not_found.append(title)

    if not_found:
        print(f"\n⚠ Could not find these songs: {', '.join(not_found)}")
        print("Add them first, then record this service.")
        return

    # Record service
    service_id = db.record_complete_service(
        service_date=service_date,
        song_ids=song_ids,
        season=season if season else None,
        theme=theme if theme else None,
        liturgical_verses=verses if verses else None
    )

    print(f"\n✓ Recorded service on {service_date} with {len(song_ids)} songs (ID: {service_id})")

def main():
    """Main interactive loop."""
    db = WorshipDatabase("worship.db")

    try:
        while True:
            show_menu()
            choice = input().strip()

            if choice == "1":
                find_fresh_songs(db)
            elif choice == "2":
                show_most_used(db)
            elif choice == "3":
                search_songs(db)
            elif choice == "4":
                view_recent_services(db)
            elif choice == "5":
                browse_all_songs(db)
            elif choice == "6":
                add_song_interactive(db)
            elif choice == "7":
                record_service_interactive(db)
            elif choice == "8":
                print("\n👋 Goodbye!")
                break
            else:
                print("\n❌ Invalid choice. Try again.")

            input("\nPress Enter to continue...")

    finally:
        db.close()

if __name__ == "__main__":
    main()
