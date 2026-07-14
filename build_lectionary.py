#!/usr/bin/env python3
"""
Build lectionary table in worship.db (demo: Year A 2025-2026)
Year A 2025-2026; verified against yeara_25_26_all.pdf
"""
import sqlite3
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

conn = sqlite3.connect("worship.db")
cur = conn.cursor()

# Create table
cur.executescript("""
CREATE TABLE IF NOT EXISTS lectionary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_date DATE NOT NULL UNIQUE,
    season TEXT,
    lectionary_year TEXT,
    sunday_title TEXT,
    first_reading TEXT,
    psalm TEXT,
    second_reading TEXT,
    gospel TEXT,
    notes TEXT,
    verified INTEGER DEFAULT 0
);
""")

# Year A 2025-2026 Sundays; extracted from yeara_25_26_all.pdf
# verified = 1 means confirmed against the ELCA PDF
rows = [
    # LENT (remaining)
    ("2026-03-22", "Lent", "A", "Lent 5",
     "Ezekiel 37:1-14", "Psalm 130", "Romans 8:6-11", "John 11:1-45",
     "Lazarus; dry bones. Spring Equinox; Trinity does a Celebration of Seasons service", 1),

    ("2026-03-29", "Lent/Holy Week", "A", "Palm Sunday",
     "Isaiah 50:4-9a", "Psalm 31:9-16", "Philippians 2:5-11", "Matthew 26:14-27:66 or 27:11-54",
     "Procession gospel: Matthew 21:1-11. Trinity uses the procession reading only (not the passion). "
     "OT may substitute Ezekiel 37:1-14. Color: Scarlet/Purple", 1),

    # HOLY WEEK
    ("2026-04-02", "Holy Week", "A", "Maundy Thursday",
     "Exodus 12:1-4, 11-14", "Psalm 116:1-2, 12-19", "1 Corinthians 11:23-26", "John 13:1-17, 31b-35",
     "Color: Scarlet/White", 1),

    ("2026-04-03", "Holy Week", "A", "Good Friday",
     "Isaiah 52:13-53:12", "Psalm 22", "Hebrews 10:16-25 or Hebrews 4:14-16; 5:7-9",
     "John 18:1-19:42", "Color: None", 1),

    # EASTER
    ("2026-04-05", "Easter", "A", "Easter Sunday",
     "Acts 10:34-43 or Jeremiah 31:1-6", "Psalm 118:1-2, 14-24",
     "Colossians 3:1-4 or Acts 10:34-43", "Matthew 28:1-10 or John 20:1-18",
     "Color: White/Gold", 1),

    ("2026-04-12", "Easter", "A", "Easter 2",
     "Acts 2:14a, 22-32", "Psalm 16",
     "1 Peter 1:3-9", "John 20:19-31",
     "Thomas Sunday. Color: White", 1),

    ("2026-04-19", "Easter", "A", "Easter 3",
     "Acts 2:14a, 36-41", "Psalm 116:1-4, 12-19",
     "1 Peter 1:17-23", "Luke 24:13-35",
     "Road to Emmaus. Color: White", 1),

    ("2026-04-26", "Easter", "A", "Easter 4",
     "Acts 2:42-47", "Psalm 23",
     "1 Peter 2:19-25", "John 10:1-10",
     "Good Shepherd Sunday. Color: White", 1),

    ("2026-05-03", "Easter", "A", "Easter 5",
     "Acts 7:55-60", "Psalm 31:1-5, 15-16",
     "1 Peter 2:2-10", "John 14:1-14",
     "I am the Way, the Truth, the Life. Color: White", 1),

    ("2026-05-10", "Easter", "A", "Easter 6",
     "Acts 17:22-31", "Psalm 66:8-20",
     "1 Peter 3:13-22", "John 14:15-21",
     "Color: White", 1),

    ("2026-05-14", "Easter", "A", "Ascension of Our Lord",
     "Acts 1:1-11", "Psalm 47 or Psalm 93",
     "Ephesians 1:15-23", "Luke 24:44-53",
     "Thursday. Color: White", 1),

    ("2026-05-17", "Easter", "A", "Easter 7",
     "Acts 1:6-14", "Psalm 68:1-10, 32-35",
     "1 Peter 4:12-14; 5:6-11", "John 17:1-11",
     "Sunday after Ascension. Color: White", 1),

    ("2026-05-24", "Easter", "A", "Day of Pentecost",
     "Acts 2:1-21 or Numbers 11:24-30", "Psalm 104:24-34, 35b",
     "1 Corinthians 12:3b-13 or Acts 2:1-21", "John 20:19-23 or John 7:37-39",
     "Color: Red", 1),

    # TIME AFTER PENTECOST
    ("2026-05-31", "Ordinary", "A", "Holy Trinity Sunday",
     "Genesis 1:1-2:4a", "Psalm 8",
     "2 Corinthians 13:11-13", "Matthew 28:16-20",
     "First Sunday after Pentecost. Color: White", 1),

    ("2026-06-07", "Ordinary", "A", "Lectionary 10",
     "Hosea 5:15-6:6", "Psalm 50:7-15",
     "Romans 4:13-25", "Matthew 9:9-13, 18-26",
     "Color: Green", 1),

    ("2026-06-14", "Ordinary", "A", "Lectionary 11",
     "Exodus 19:2-8a", "Psalm 100",
     "Romans 5:1-8", "Matthew 9:35-10:8 [9-23]",
     "Color: Green", 1),

    ("2026-06-21", "Ordinary", "A", "Lectionary 12",
     "Jeremiah 20:7-13", "Psalm 69:7-10 [11-15] 16-18",
     "Romans 6:1b-11", "Matthew 10:24-39",
     "Color: Green", 1),

    ("2026-06-28", "Ordinary", "A", "Lectionary 13",
     "Jeremiah 28:5-9", "Psalm 89:1-4, 15-18",
     "Romans 6:12-23", "Matthew 10:40-42",
     "Color: Green", 1),

    ("2026-07-05", "Ordinary", "A", "Lectionary 14",
     "Zechariah 9:9-12", "Psalm 145:8-14",
     "Romans 7:15-25a", "Matthew 11:16-19, 25-30",
     "Color: Green", 1),

    ("2026-07-12", "Ordinary", "A", "Lectionary 15",
     "Isaiah 55:10-13", "Psalm 65:[1-8] 9-13",
     "Romans 8:1-11", "Matthew 13:1-9, 18-23",
     "Parable of the Sower. Color: Green", 1),

    ("2026-07-19", "Ordinary", "A", "Lectionary 16",
     "Isaiah 44:6-8 or Wisdom of Solomon 12:13, 16-19", "Psalm 86:11-17",
     "Romans 8:12-25", "Matthew 13:24-30, 36-43",
     "Parable of the Weeds. Color: Green", 1),

    ("2026-07-26", "Ordinary", "A", "Lectionary 17",
     "1 Kings 3:5-12", "Psalm 119:129-136",
     "Romans 8:26-39", "Matthew 13:31-33, 44-52",
     "Color: Green", 1),

    ("2026-08-02", "Ordinary", "A", "Lectionary 18",
     "Isaiah 55:1-5", "Psalm 145:8-9, 14-21",
     "Romans 9:1-5", "Matthew 14:13-21",
     "Feeding of the 5000. Color: Green", 1),

    ("2026-08-09", "Ordinary", "A", "Lectionary 19",
     "1 Kings 19:9-18", "Psalm 85:8-13",
     "Romans 10:5-15", "Matthew 14:22-33",
     "Jesus walks on water. Color: Green", 1),

    ("2026-08-16", "Ordinary", "A", "Lectionary 20",
     "Isaiah 56:1, 6-8", "Psalm 67",
     "Romans 11:1-2a, 29-32", "Matthew 15:[10-20] 21-28",
     "Canaanite woman. Color: Green", 1),

    ("2026-08-23", "Ordinary", "A", "Lectionary 21",
     "Isaiah 51:1-6", "Psalm 138",
     "Romans 12:1-8", "Matthew 16:13-20",
     "Peter's confession. Color: Green", 1),

    ("2026-08-30", "Ordinary", "A", "Lectionary 22",
     "Jeremiah 15:15-21", "Psalm 26:1-8",
     "Romans 12:9-21", "Matthew 16:21-28",
     "Take up your cross. Color: Green", 1),

    ("2026-09-06", "Ordinary", "A", "Lectionary 23",
     "Ezekiel 33:7-11", "Psalm 119:33-40",
     "Romans 13:8-14", "Matthew 18:15-20",
     "Church discipline; where two or three gather. Color: Green", 1),

    ("2026-09-13", "Ordinary", "A", "Lectionary 24",
     "Genesis 50:15-21", "Psalm 103:[1-7] 8-13",
     "Romans 14:1-12", "Matthew 18:21-35",
     "Forgiveness; parable of unforgiving servant. Color: Green", 1),

    ("2026-09-20", "Ordinary", "A", "Lectionary 25",
     "Jonah 3:10-4:11", "Psalm 145:1-8",
     "Philippians 1:21-30", "Matthew 20:1-16",
     "Workers in the vineyard. Color: Green", 1),

    ("2026-09-27", "Ordinary", "A", "Lectionary 26",
     "Ezekiel 18:1-4, 25-32", "Psalm 25:1-9",
     "Philippians 2:1-13", "Matthew 21:23-32",
     "Two sons parable. Color: Green", 1),

    ("2026-10-04", "Ordinary", "A", "Lectionary 27",
     "Isaiah 5:1-7", "Psalm 80:7-15",
     "Philippians 3:4b-14", "Matthew 21:33-46",
     "Parable of wicked tenants. Color: Green", 1),

    ("2026-10-11", "Ordinary", "A", "Lectionary 28",
     "Isaiah 25:1-9", "Psalm 23",
     "Philippians 4:1-9", "Matthew 22:1-14",
     "Wedding banquet parable. Color: Green", 1),

    ("2026-10-18", "Ordinary", "A", "Lectionary 29",
     "Isaiah 45:1-7", "Psalm 96:1-9 [10-13]",
     "1 Thessalonians 1:1-10", "Matthew 22:15-22",
     "Render to Caesar. Color: Green", 1),

    ("2026-10-25", "Ordinary", "A", "Lectionary 30 / Reformation Sunday",
     "Leviticus 19:1-2, 15-18", "Psalm 1",
     "1 Thessalonians 2:1-8", "Matthew 22:34-46",
     "Greatest commandment. OR Reformation: Jeremiah 31:31-34, Psalm 46, Romans 3:19-28, John 8:31-36. Color: Green/Scarlet", 1),

    ("2026-11-01", "Ordinary", "A", "All Saints Sunday",
     "Revelation 7:9-17", "Psalm 34:1-10, 22",
     "1 John 3:1-3", "Matthew 5:1-12",
     "Beatitudes. Color: White", 1),

    ("2026-11-08", "Ordinary", "A", "Lectionary 32",
     "Amos 5:18-24 or Wisdom of Solomon 6:12-16", "Psalm 70",
     "1 Thessalonians 4:13-18", "Matthew 25:1-13",
     "Ten bridesmaids parable. Color: Green", 1),

    ("2026-11-15", "Ordinary", "A", "Lectionary 33",
     "Zephaniah 1:7, 12-18", "Psalm 90:1-8 [9-11] 12",
     "1 Thessalonians 5:1-11", "Matthew 25:14-30",
     "Parable of talents. Color: Green", 1),

    ("2026-11-22", "Ordinary", "A", "Christ the King Sunday",
     "Ezekiel 34:11-16, 20-24", "Psalm 95:1-7a",
     "Ephesians 1:15-23", "Matthew 25:31-46",
     "Sheep and goats. Last Sunday of church year. Color: White/Green", 1),
]

inserted = 0
skipped = 0
for row in rows:
    try:
        cur.execute("""
            INSERT OR IGNORE INTO lectionary
            (service_date, season, lectionary_year, sunday_title,
             first_reading, psalm, second_reading, gospel, notes, verified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, row)
        if cur.rowcount > 0:
            inserted += 1
        else:
            skipped += 1
    except Exception as e:
        print(f"Error on {row[0]}: {e}")

conn.commit()
conn.close()
print(f"✅ Lectionary table built: {inserted} rows inserted, {skipped} already existed")
print(f"   Covers {len(rows)} Sundays/festivals, Year A 2025-2026")
print(f"   Verified against: yeara_25_26_all.pdf")
