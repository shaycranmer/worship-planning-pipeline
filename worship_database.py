#!/usr/bin/env python3
"""
Worship Leader Database Management System
==========================================

A comprehensive SQLite database system for managing worship songs, resources,
and service planning. This script demonstrates key digital humanities concepts:
- Structured data management for cultural/religious content
- Relational database design for interconnected information
- Temporal tracking of usage patterns
- Metadata schemas for liturgical resources

Author: Digital Humanities Project
Purpose: Educational example of database-driven worship planning
"""

import sqlite3
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
import os


class WorshipDatabase:
    """
    Main database class for worship management.

    This class encapsulates all database operations, following the principle
    of separation of concerns - keeping database logic isolated from application
    logic. This is a common pattern in digital humanities projects.
    """

    def __init__(self, db_path: str = "worship_data.db"):
        """
        Initialize the database connection.

        Args:
            db_path: Path to the SQLite database file. If it doesn't exist,
                    it will be created automatically.
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        # Enable foreign key constraints (not enabled by default in SQLite)
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Return rows as dictionaries instead of tuples for easier access
        self.conn.row_factory = sqlite3.Row

        # Create all tables if they don't exist
        self._create_schema()

    def _create_schema(self):
        """
        Create the complete database schema.

        This method demonstrates normalization principles:
        - Separate tables for distinct entities (songs, resources, services)
        - Foreign keys to maintain referential integrity
        - Nullable fields where data might be optional
        - Default values for tracking fields (times_used)
        """
        cursor = self.conn.cursor()

        # SONGS TABLE
        # Core table for all worship music, whether contemporary or traditional
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('contemporary', 'traditional', 'liturgical')),
                artist_source TEXT NOT NULL,
                hymnal_number TEXT,
                tags TEXT,  -- Stored as comma-separated values for simplicity
                key_signature TEXT,
                last_used_date DATE,
                times_used INTEGER DEFAULT 0,
                teaching_complexity TEXT CHECK(teaching_complexity IN ('easy', 'moderate', 'difficult', NULL)),
                congregational_familiarity TEXT CHECK(congregational_familiarity IN ('new', 'learning', 'familiar', 'well-known', NULL)),
                notes TEXT,
                lyrics TEXT,                     -- full text, used by the register/flag pass
                lyrics_verified INTEGER DEFAULT 0,  -- human confirmed lyrics against the source
                files_verified INTEGER DEFAULT 0,   -- human confirmed sheet music exists in the right key
                typical_leader TEXT,             -- who usually leads it (role, e.g. 'cantor', 'band')
                tune_name TEXT,
                alt_tunes TEXT,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # RESOURCES TABLE
        # Links to external files (sheet music, chord charts, etc.)
        # Demonstrates one-to-many relationship: one song can have many resources
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                song_id INTEGER NOT NULL,
                resource_type TEXT NOT NULL CHECK(resource_type IN (
                    'guitar chart',
                    'SATB',
                    'piano accompaniment',
                    'MuseScore',
                    'unison vocal part',
                    'text for bulletin'
                )),
                file_path TEXT NOT NULL,
                created_date DATE DEFAULT CURRENT_DATE,
                notes TEXT,
                FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
            )
        """)

        # SERVICE_HISTORY TABLE
        # Records each worship service with its liturgical context
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS service_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL UNIQUE,
                season TEXT,  -- e.g., Advent, Lent, Easter, Ordinary Time
                theme TEXT,
                liturgical_verses TEXT,  -- Scripture references for the day
                notes TEXT,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # SERVICE_SONGS TABLE
        # Junction table creating many-to-many relationship between services and songs
        # This allows tracking which songs were used in which services
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS service_songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id INTEGER NOT NULL,
                song_id INTEGER NOT NULL,
                order_in_service INTEGER,  -- Track sequence: opening, offertory, closing, etc.
                slot TEXT,   -- liturgical slot: gathering, hymn_of_day, offering, communion, sending…
                notes TEXT,  -- per-use notes: 'cut verse 3', 'key felt high'; the lived memory
                FOREIGN KEY (service_id) REFERENCES service_history(id) ON DELETE CASCADE,
                FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
            )
        """)

        # LITURGICAL_ELEMENTS TABLE
        # Stores reusable liturgical texts (prayers, creeds, blessings)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS liturgical_elements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                element_type TEXT NOT NULL CHECK(element_type IN (
                    'creed',
                    'prayer',
                    'blessing',
                    'intercession'
                )),
                text TEXT NOT NULL,
                tags TEXT,
                source TEXT,  -- Attribution for where the text comes from
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for common query patterns to improve performance
        # Indexes are like book indexes - they help find data quickly
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_type ON songs(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_last_used ON songs(last_used_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_resources_song ON resources(song_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_service_date ON service_history(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_service_songs_service ON service_songs(service_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_service_songs_song ON service_songs(song_id)")

        self.conn.commit()

    # ==================================================================
    # SONG MANAGEMENT FUNCTIONS
    # ==================================================================

    def add_song(self, title: str, song_type: str, artist_source: str,
                 hymnal_number: Optional[str] = None, tags: Optional[str] = None,
                 key_signature: Optional[str] = None, teaching_complexity: Optional[str] = None,
                 congregational_familiarity: Optional[str] = None,
                 notes: Optional[str] = None, lyrics: Optional[str] = None,
                 typical_leader: Optional[str] = None, tune_name: Optional[str] = None) -> int:
        """
        Add a new song to the database.

        Args:
            title: Song title
            song_type: Either 'contemporary' or 'traditional'
            artist_source: Artist name or hymnal source
            hymnal_number: Hymn number if from a hymnal (optional)
            tags: Comma-separated tags (e.g., "thanksgiving,joy,praise")
            key_signature: Musical key (e.g., "G Major", "D")
            teaching_complexity: How difficult to teach ('easy', 'moderate', 'difficult')
            congregational_familiarity: How well-known ('new', 'learning', 'familiar', 'well-known')
            notes: Any additional notes

        Returns:
            The ID of the newly created song

        Example:
            song_id = db.add_song(
                title="Amazing Grace",
                song_type="traditional",
                artist_source="John Newton",
                hymnal_number="341",
                tags="grace,redemption,classic",
                key_signature="G Major",
                congregational_familiarity="well-known"
            )
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO songs (
                title, type, artist_source, hymnal_number, tags,
                key_signature, teaching_complexity, congregational_familiarity, notes,
                lyrics, typical_leader, tune_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, song_type, artist_source, hymnal_number, tags,
              key_signature, teaching_complexity, congregational_familiarity, notes,
              lyrics, typical_leader, tune_name))

        self.conn.commit()
        return cursor.lastrowid

    def find_songs_by_tags(self, search_tags: List[str], match_all: bool = False) -> List[Dict]:
        """
        Find songs that match given tags.

        This demonstrates text searching in databases - a common challenge in
        digital humanities when dealing with categorized cultural materials.

        Args:
            search_tags: List of tags to search for
            match_all: If True, song must have ALL tags. If False, ANY tag matches.

        Returns:
            List of song dictionaries matching the criteria

        Example:
            # Find songs tagged with "christmas" OR "joy"
            songs = db.find_songs_by_tags(["christmas", "joy"])

            # Find songs tagged with BOTH "lent" AND "reflection"
            songs = db.find_songs_by_tags(["lent", "reflection"], match_all=True)
        """
        cursor = self.conn.cursor()

        if match_all:
            # All tags must be present - use AND logic
            conditions = " AND ".join(["tags LIKE ?" for _ in search_tags])
            params = [f"%{tag}%" for tag in search_tags]
        else:
            # Any tag can match - use OR logic
            conditions = " OR ".join(["tags LIKE ?" for _ in search_tags])
            params = [f"%{tag}%" for tag in search_tags]

        query = f"SELECT * FROM songs WHERE {conditions} ORDER BY title"
        cursor.execute(query, params)

        return [dict(row) for row in cursor.fetchall()]

    def find_songs_by_theme(self, theme: str) -> List[Dict]:
        """
        Find songs matching a theme by searching title, tags, and notes.

        This performs a full-text search across multiple fields, useful for
        finding songs when you remember a concept but not exact tags.

        Args:
            theme: Search term to look for

        Returns:
            List of matching songs

        Example:
            # Find all songs related to "peace"
            peace_songs = db.find_songs_by_theme("peace")
        """
        cursor = self.conn.cursor()
        search_term = f"%{theme}%"

        cursor.execute("""
            SELECT * FROM songs
            WHERE title LIKE ?
               OR tags LIKE ?
               OR notes LIKE ?
            ORDER BY title
        """, (search_term, search_term, search_term))

        return [dict(row) for row in cursor.fetchall()]

    def find_songs_not_used_in_days(self, days: int) -> List[Dict]:
        """
        Find songs that haven't been used recently.

        This is useful for ensuring variety in worship planning and avoiding
        over-reliance on the same songs. Demonstrates date arithmetic in SQL.

        Args:
            days: Number of days to look back

        Returns:
            List of songs not used within the specified time period

        Example:
            # Find songs not used in the last 90 days
            unused_songs = db.find_songs_not_used_in_days(90)
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM songs
            WHERE last_used_date IS NULL
               OR last_used_date < date('now', '-' || ? || ' days')
            ORDER BY last_used_date ASC NULLS FIRST, title
        """, (days,))

        return [dict(row) for row in cursor.fetchall()]

    def get_song_by_id(self, song_id: int) -> Optional[Dict]:
        """
        Retrieve a single song by its ID.

        Args:
            song_id: The song's database ID

        Returns:
            Song dictionary or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM songs WHERE id = ?", (song_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_song_usage(self, song_id: int, usage_date: Optional[date] = None):
        """
        Update the usage statistics for a song.

        This should be called whenever a song is used in a service to maintain
        accurate tracking of usage patterns.

        Args:
            song_id: The song's database ID
            usage_date: Date the song was used (defaults to today)
        """
        if usage_date is None:
            usage_date = date.today()

        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE songs
            SET last_used_date = ?,
                times_used = times_used + 1
            WHERE id = ?
        """, (usage_date, song_id))

        self.conn.commit()

    # ==================================================================
    # RESOURCE MANAGEMENT FUNCTIONS
    # ==================================================================

    def add_resource(self, song_id: int, resource_type: str, file_path: str,
                    notes: Optional[str] = None) -> int:
        """
        Add a resource file for a song.

        Resources are external files like PDFs, MuseScore files, etc.
        This demonstrates how databases can reference external digital assets.

        Args:
            song_id: ID of the song this resource belongs to
            resource_type: Type of resource (guitar chart, SATB, etc.)
            file_path: Path to the file (can be relative or absolute)
            notes: Optional notes about this resource

        Returns:
            The ID of the newly created resource

        Example:
            resource_id = db.add_resource(
                song_id=1,
                resource_type="guitar chart",
                file_path="charts/amazing_grace_G.pdf",
                notes="Capo 2 for easier voicing"
            )
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO resources (song_id, resource_type, file_path, notes)
            VALUES (?, ?, ?, ?)
        """, (song_id, resource_type, file_path, notes))

        self.conn.commit()
        return cursor.lastrowid

    def get_song_resources(self, song_id: int) -> List[Dict]:
        """
        Get all resources for a specific song.

        Args:
            song_id: The song's database ID

        Returns:
            List of resource dictionaries

        Example:
            resources = db.get_song_resources(1)
            for resource in resources:
                print(f"{resource['resource_type']}: {resource['file_path']}")
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM resources
            WHERE song_id = ?
            ORDER BY resource_type
        """, (song_id,))

        return [dict(row) for row in cursor.fetchall()]

    def get_resources_by_type(self, resource_type: str) -> List[Dict]:
        """
        Get all resources of a specific type across all songs.

        Useful for finding all guitar charts, all SATB arrangements, etc.

        Args:
            resource_type: The type of resource to find

        Returns:
            List of resources with associated song information
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT r.*, s.title as song_title, s.artist_source
            FROM resources r
            JOIN songs s ON r.song_id = s.id
            WHERE r.resource_type = ?
            ORDER BY s.title
        """, (resource_type,))

        return [dict(row) for row in cursor.fetchall()]

    # ==================================================================
    # SERVICE PLANNING FUNCTIONS
    # ==================================================================

    def create_service(self, service_date: date, season: Optional[str] = None,
                      theme: Optional[str] = None, liturgical_verses: Optional[str] = None,
                      notes: Optional[str] = None) -> int:
        """
        Create a new service record.

        This creates the basic service information. Songs are added separately
        using add_song_to_service().

        Args:
            service_date: Date of the service
            season: Liturgical season (Advent, Lent, Easter, etc.)
            theme: Theme or focus of the service
            liturgical_verses: Scripture readings for the day
            notes: Any additional notes

        Returns:
            The ID of the newly created service

        Example:
            service_id = db.create_service(
                service_date=date(2026, 12, 25),
                season="Christmas",
                theme="The Incarnation",
                liturgical_verses="Isaiah 9:2-7, Luke 2:1-20",
                notes="Christmas Day morning service"
            )
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO service_history (date, season, theme, liturgical_verses, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (service_date, season, theme, liturgical_verses, notes))

        self.conn.commit()
        return cursor.lastrowid

    def add_song_to_service(self, service_id: int, song_id: int,
                           order_in_service: Optional[int] = None,
                           slot: Optional[str] = None, notes: Optional[str] = None):
        """
        Add a song to a service.

        This links a song to a service and updates the song's usage statistics.

        Args:
            service_id: ID of the service
            song_id: ID of the song
            order_in_service: Position in the service order (1=opening, 2=second song, etc.)

        Example:
            # Add opening song
            db.add_song_to_service(service_id=1, song_id=5, order_in_service=1)
            # Add closing song
            db.add_song_to_service(service_id=1, song_id=12, order_in_service=4)
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO service_songs (service_id, song_id, order_in_service, slot, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (service_id, song_id, order_in_service, slot, notes))

        # Update song usage statistics
        service = self.get_service_by_id(service_id)
        if service:
            self.update_song_usage(song_id, service['date'])

        self.conn.commit()

    def record_complete_service(self, service_date: date, song_ids: List[int],
                               season: Optional[str] = None, theme: Optional[str] = None,
                               liturgical_verses: Optional[str] = None,
                               notes: Optional[str] = None,
                               slots: Optional[List[str]] = None) -> int:
        """
        Create a complete service record with all songs in one operation.

        This is a convenience function that combines create_service() and
        multiple add_song_to_service() calls.

        Args:
            service_date: Date of the service
            song_ids: List of song IDs in order of service
            season: Liturgical season
            theme: Service theme
            liturgical_verses: Scripture readings
            notes: Additional notes

        Returns:
            The ID of the newly created service

        Example:
            service_id = db.record_complete_service(
                service_date=date(2026, 2, 15),
                song_ids=[1, 5, 8, 12],  # Order: opening to closing
                season="Epiphany",
                theme="Light of the World",
                liturgical_verses="Matthew 5:14-16"
            )
        """
        # Create the service record
        service_id = self.create_service(service_date, season, theme,
                                        liturgical_verses, notes)

        # Add all songs with their order (and liturgical slot, if provided)
        for order, song_id in enumerate(song_ids, start=1):
            slot = slots[order-1] if slots and order-1 < len(slots) else None
            self.add_song_to_service(service_id, song_id, order, slot=slot)

        return service_id

    def get_service_by_id(self, service_id: int) -> Optional[Dict]:
        """
        Retrieve a service by its ID.

        Args:
            service_id: The service's database ID

        Returns:
            Service dictionary or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM service_history WHERE id = ?", (service_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_service_by_date(self, service_date: date) -> Optional[Dict]:
        """
        Retrieve a service by its date.

        Args:
            service_date: The date of the service

        Returns:
            Service dictionary or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM service_history WHERE date = ?", (service_date,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_service_songs(self, service_id: int) -> List[Dict]:
        """
        Get all songs for a service in order.

        Args:
            service_id: The service's database ID

        Returns:
            List of songs with service order information

        Example:
            songs = db.get_service_songs(1)
            for song in songs:
                print(f"{song['order_in_service']}. {song['title']}")
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.*, ss.order_in_service
            FROM songs s
            JOIN service_songs ss ON s.id = ss.song_id
            WHERE ss.service_id = ?
            ORDER BY ss.order_in_service NULLS LAST, s.title
        """, (service_id,))

        return [dict(row) for row in cursor.fetchall()]

    def get_recent_services(self, limit: int = 10) -> List[Dict]:
        """
        Get the most recent services.

        Args:
            limit: Maximum number of services to return

        Returns:
            List of recent services, newest first
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM service_history
            ORDER BY date DESC
            LIMIT ?
        """, (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def get_services_by_season(self, season: str) -> List[Dict]:
        """
        Get all services for a specific liturgical season.

        Args:
            season: The liturgical season to search for

        Returns:
            List of services in that season

        Example:
            lent_services = db.get_services_by_season("Lent")
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM service_history
            WHERE season LIKE ?
            ORDER BY date DESC
        """, (f"%{season}%",))

        return [dict(row) for row in cursor.fetchall()]

    # ==================================================================
    # LITURGICAL ELEMENTS FUNCTIONS
    # ==================================================================

    def add_liturgical_element(self, element_type: str, text: str,
                              tags: Optional[str] = None,
                              source: Optional[str] = None) -> int:
        """
        Add a liturgical element (prayer, creed, blessing, etc.).

        Args:
            element_type: Type of element (creed, prayer, blessing, intercession)
            text: The actual text of the element
            tags: Comma-separated tags
            source: Attribution or source information

        Returns:
            The ID of the newly created element

        Example:
            element_id = db.add_liturgical_element(
                element_type="blessing",
                text="May the Lord bless you and keep you...",
                tags="benediction,numbers",
                source="Numbers 6:24-26"
            )
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO liturgical_elements (element_type, text, tags, source)
            VALUES (?, ?, ?, ?)
        """, (element_type, text, tags, source))

        self.conn.commit()
        return cursor.lastrowid

    def get_liturgical_elements_by_type(self, element_type: str) -> List[Dict]:
        """
        Get all liturgical elements of a specific type.

        Args:
            element_type: The type to search for

        Returns:
            List of matching liturgical elements
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM liturgical_elements
            WHERE element_type = ?
            ORDER BY source, id
        """, (element_type,))

        return [dict(row) for row in cursor.fetchall()]

    # ==================================================================
    # REPORTING AND ANALYSIS FUNCTIONS
    # ==================================================================

    def get_most_used_songs(self, limit: int = 10) -> List[Dict]:
        """
        Get the most frequently used songs.

        This helps identify which songs are congregation favorites.

        Args:
            limit: Number of songs to return

        Returns:
            List of songs ordered by usage frequency
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM songs
            WHERE times_used > 0
            ORDER BY times_used DESC, title
            LIMIT ?
        """, (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def get_song_usage_stats(self) -> Dict:
        """
        Get overall statistics about song usage.

        Returns:
            Dictionary with various statistics

        Example:
            stats = db.get_song_usage_stats()
            print(f"Total songs: {stats['total_songs']}")
            print(f"Average uses per song: {stats['avg_uses']:.1f}")
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_songs,
                SUM(times_used) as total_uses,
                AVG(times_used) as avg_uses,
                MAX(times_used) as max_uses,
                COUNT(CASE WHEN times_used = 0 THEN 1 END) as never_used
            FROM songs
        """)

        return dict(cursor.fetchone())

    def search_songs_full_text(self, search_term: str) -> List[Dict]:
        """
        Perform a comprehensive search across all song fields.

        Args:
            search_term: Term to search for

        Returns:
            List of matching songs
        """
        cursor = self.conn.cursor()
        pattern = f"%{search_term}%"

        cursor.execute("""
            SELECT * FROM songs
            WHERE title LIKE ?
               OR artist_source LIKE ?
               OR tags LIKE ?
               OR notes LIKE ?
               OR hymnal_number LIKE ?
            ORDER BY
                CASE
                    WHEN title LIKE ? THEN 1
                    WHEN tags LIKE ? THEN 2
                    ELSE 3
                END,
                title
        """, (pattern, pattern, pattern, pattern, pattern, pattern, pattern))

        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures connection is closed."""
        self.close()


# ==================================================================
# DEMONSTRATION AND TESTING CODE
# ==================================================================

def demonstrate_database():
    """
    Demonstration function showing how to use the database system.

    This serves as both documentation and a test suite, showing practical
    usage patterns for digital humanities students.
    """
    print("=" * 70)
    print("WORSHIP DATABASE MANAGEMENT SYSTEM - DEMONSTRATION")
    print("=" * 70)
    print()

    # Create database instance (using context manager for automatic cleanup)
    with WorshipDatabase("demo_worship.db") as db:

        # ==========================================
        # SECTION 1: Adding Songs
        # ==========================================
        print("SECTION 1: Adding Songs to Database")
        print("-" * 70)

        song1 = db.add_song(
            title="Amazing Grace",
            song_type="traditional",
            artist_source="John Newton",
            hymnal_number="341",
            tags="grace,redemption,assurance,classic",
            key_signature="G Major",
            teaching_complexity="easy",
            congregational_familiarity="well-known",
            notes="One of the most beloved hymns, known worldwide"
        )
        print(f"✓ Added: Amazing Grace (ID: {song1})")

        song2 = db.add_song(
            title="10,000 Reasons (Bless the Lord)",
            song_type="contemporary",
            artist_source="Matt Redman",
            tags="praise,thanksgiving,morning,evening",
            key_signature="G Major",
            teaching_complexity="easy",
            congregational_familiarity="familiar"
        )
        print(f"✓ Added: 10,000 Reasons (ID: {song2})")

        song3 = db.add_song(
            title="O Come, O Come Emmanuel",
            song_type="traditional",
            artist_source="Latin Hymn",
            hymnal_number="88",
            tags="advent,christmas,anticipation,longing",
            key_signature="E Minor",
            congregational_familiarity="familiar",
            notes="Traditional Advent hymn, plainsong melody"
        )
        print(f"✓ Added: O Come, O Come Emmanuel (ID: {song3})")

        song4 = db.add_song(
            title="Cornerstone",
            song_type="contemporary",
            artist_source="Hillsong Worship",
            tags="christ,foundation,hope,assurance",
            key_signature="C Major",
            teaching_complexity="moderate",
            congregational_familiarity="familiar"
        )
        print(f"✓ Added: Cornerstone (ID: {song4})")

        song5 = db.add_song(
            title="Great Is Thy Faithfulness",
            song_type="traditional",
            artist_source="Thomas Chisholm",
            hymnal_number="276",
            tags="faithfulness,morning,provision,thanksgiving",
            key_signature="D Major",
            congregational_familiarity="well-known"
        )
        print(f"✓ Added: Great Is Thy Faithfulness (ID: {song5})")

        print()

        # ==========================================
        # SECTION 2: Adding Resources
        # ==========================================
        print("SECTION 2: Adding Resources for Songs")
        print("-" * 70)

        db.add_resource(
            song_id=song1,
            resource_type="guitar chart",
            file_path="charts/amazing_grace_G.pdf",
            notes="Standard fingering, capo on 2 for easier voicing"
        )
        print(f"✓ Added guitar chart for Amazing Grace")

        db.add_resource(
            song_id=song1,
            resource_type="SATB",
            file_path="sheet_music/amazing_grace_satb.pdf"
        )
        print(f"✓ Added SATB arrangement for Amazing Grace")

        db.add_resource(
            song_id=song2,
            resource_type="guitar chart",
            file_path="charts/10000_reasons_G.pdf"
        )
        print(f"✓ Added guitar chart for 10,000 Reasons")

        db.add_resource(
            song_id=song3,
            resource_type="piano accompaniment",
            file_path="piano/emmanuel_piano.pdf",
            notes="Includes descant for final verse"
        )
        print(f"✓ Added piano accompaniment for O Come, O Come Emmanuel")

        print()

        # ==========================================
        # SECTION 3: Recording Services
        # ==========================================
        print("SECTION 3: Recording Worship Services")
        print("-" * 70)

        service1 = db.record_complete_service(
            service_date=date(2026, 1, 4),
            song_ids=[song5, song4, song1],  # Opening, middle, closing
            season="Epiphany",
            theme="Light of the World",
            liturgical_verses="Isaiah 60:1-6, Matthew 2:1-12",
            notes="Epiphany Sunday - focus on Christ revealed to the nations"
        )
        print(f"✓ Recorded service on 2026-01-04 (ID: {service1})")
        print(f"  Season: Epiphany | Songs used: 3")

        service2 = db.record_complete_service(
            service_date=date(2025, 12, 21),
            song_ids=[song3, song2],
            season="Advent",
            theme="Waiting and Hope",
            liturgical_verses="Luke 1:26-38",
            notes="Fourth Sunday of Advent"
        )
        print(f"✓ Recorded service on 2025-12-21 (ID: {service2})")
        print(f"  Season: Advent | Songs used: 2")

        print()

        # ==========================================
        # SECTION 4: Adding Liturgical Elements
        # ==========================================
        print("SECTION 4: Adding Liturgical Elements")
        print("-" * 70)

        db.add_liturgical_element(
            element_type="blessing",
            text="The Lord bless you and keep you; the Lord make his face shine on you "
                 "and be gracious to you; the Lord turn his face toward you and give you peace.",
            tags="benediction,peace,blessing",
            source="Numbers 6:24-26"
        )
        print("✓ Added Aaronic Blessing")

        db.add_liturgical_element(
            element_type="creed",
            text="I believe in God, the Father almighty, creator of heaven and earth...",
            tags="apostles,creed,faith",
            source="Apostles' Creed"
        )
        print("✓ Added Apostles' Creed")

        print()

        # ==========================================
        # SECTION 5: Searching and Querying
        # ==========================================
        print("SECTION 5: Searching and Querying")
        print("-" * 70)

        print("\n5a. Search by tags (songs with 'grace' or 'faithfulness'):")
        grace_songs = db.find_songs_by_tags(["grace", "faithfulness"])
        for song in grace_songs:
            print(f"   • {song['title']} - Tags: {song['tags']}")

        print("\n5b. Search by theme (songs mentioning 'hope'):")
        hope_songs = db.find_songs_by_theme("hope")
        for song in hope_songs:
            print(f"   • {song['title']} - {song['artist_source']}")

        print("\n5c. Find songs not used in 30 days:")
        unused = db.find_songs_not_used_in_days(30)
        for song in unused:
            last_used = song['last_used_date'] or 'Never'
            print(f"   • {song['title']} - Last used: {last_used}")

        print("\n5d. Get resources for Amazing Grace:")
        resources = db.get_song_resources(song1)
        for resource in resources:
            print(f"   • {resource['resource_type']}: {resource['file_path']}")

        print("\n5e. View recent services:")
        recent = db.get_recent_services(limit=5)
        for service in recent:
            print(f"   • {service['date']} - {service['season']}: {service['theme']}")

        print("\n5f. Songs from a specific service:")
        service_songs = db.get_service_songs(service1)
        print(f"   Service on {recent[0]['date']}:")
        for song in service_songs:
            print(f"   {song['order_in_service']}. {song['title']}")

        print()

        # ==========================================
        # SECTION 6: Statistics and Analysis
        # ==========================================
        print("SECTION 6: Statistics and Analysis")
        print("-" * 70)

        stats = db.get_song_usage_stats()
        print(f"Total songs in database: {stats['total_songs']}")
        print(f"Total times songs used: {stats['total_uses']}")
        print(f"Average uses per song: {stats['avg_uses']:.2f}")
        print(f"Most used song used: {stats['max_uses']} times")
        print(f"Songs never used: {stats['never_used']}")

        print("\nMost frequently used songs:")
        most_used = db.get_most_used_songs(limit=5)
        for i, song in enumerate(most_used, 1):
            print(f"   {i}. {song['title']} - Used {song['times_used']} time(s)")

        print()

        # ==========================================
        # Summary
        # ==========================================
        print("=" * 70)
        print("DEMONSTRATION COMPLETE")
        print("=" * 70)
        print(f"\nDatabase created: demo_worship.db")
        print(f"Total songs: {stats['total_songs']}")
        print(f"Total services: {len(recent)}")
        print(f"Total resources: {len(db.get_resources_by_type('guitar chart')) + len(db.get_resources_by_type('SATB')) + len(db.get_resources_by_type('piano accompaniment'))}")
        print("\nYou can now open this database with any SQLite browser")
        print("or continue adding data using the WorshipDatabase class.")
        print()


# ==================================================================
# COMMAND-LINE INTERFACE
# ==================================================================

if __name__ == "__main__":
    """
    Main entry point for the script.

    Run this script directly to see a demonstration of all features:
        python worship_database.py

    Or import it as a module to use in your own code:
        from worship_database import WorshipDatabase
        db = WorshipDatabase("my_church.db")
    """
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("""
Worship Leader Database Management System
==========================================

USAGE:
    python worship_database.py              Run demonstration
    python worship_database.py --help       Show this help message

PROGRAMMATIC USAGE:
    from worship_database import WorshipDatabase

    # Create/open database
    db = WorshipDatabase("my_church.db")

    # Add a song
    song_id = db.add_song(
        title="Amazing Grace",
        song_type="traditional",
        artist_source="John Newton",
        tags="grace,redemption"
    )

    # Search for songs
    songs = db.find_songs_by_tags(["christmas"])

    # Record a service
    service_id = db.record_complete_service(
        service_date=date(2026, 2, 15),
        song_ids=[1, 5, 8],
        season="Epiphany"
    )

    # Always close when done
    db.close()

For more information, see the docstrings in the code.
        """)
    else:
        demonstrate_database()
