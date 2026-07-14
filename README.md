# Worship Planning Pipeline

**A ten-stage, human-verified production system for planning weekly worship services, built by a working worship leader in collaboration with AI, and run in real production every week.**

This repository is the public, demonstration version of that system. It runs end-to-end on a completely fictional congregation ("Trinity Community Church") with invented songs, invented artists, and invented service history. See [Data handling](#data-handling-what-is-not-here) for why that's a feature, not a limitation.

## The problem it solves

A worship leader assembling a Sunday service is running a small weekly production company: theme and scripture selection, song programming against congregational memory ("didn't we just sing this?"), liturgy writing, document production for band and clergy, sheet-music logistics in the right keys, and communications to volunteer musicians; every single week, forever, usually alongside another job. The knowledge that makes it work (what the congregation knows, what the band can carry, what happened last time) traditionally lives in one person's head.

This pipeline turns that knowledge into structured data, automates the mechanical steps, and then does the design's most important thing: it **flags rather than decides**. Every judgment call is surfaced to the human, with the evidence attached.

## The ten stages

| # | Stage | Where it lives |
|---|-------|----------------|
| 1 | **Lectionary grounding**: the liturgical calendar loaded as data, verified by hand against the published lectionary | `build_lectionary.py` |
| 2 | **Theme and scripture selection**: the human decision, captured as structured input | `worship_input.json` |
| 3 | **Scripture retrieval**: passage text placed programmatically at build time, never re-typed and never generated. The public demo uses local fixtures in a public-domain translation; the production system fetches its licensed translation under that publisher's terms, privately | `get_scripture.py` + `scripture_fixtures.json` |
| 4 | **Song discovery**: search by theme, tag, or title across the library | `search_songs.py` |
| 5 | **Usage-frequency and familiarity checks**: which songs have rested, what the congregation can carry, what needs teaching | `get_suggestions.py` + database fields |
| 6 | **Liturgy writing**: an AI liturgist collaborator writes prayers to the week's theme, delivered as labeled plain text through a file-based handoff | `handoff/<date>/liturgist_blocks.txt` |
| 7 | **The flag pass**: repetition detection, per-use "lived memory" notes, traditional/contemporary balance across consecutive weeks, and a cumulative register scan across the whole song set | `build_worship_plan.py` |
| 8 | **Document assembly**: the full service plan generated as a formatted `.docx` from liturgical templates | `worship_plan_generator.py` |
| 9 | **Sheet-music verification**: resources linked per song and key, with an explicit human-verified flag | `add_resources.py`, `files_verified` |
| 10 | **Staged communications**: the weekly band email generated from the plan, with review flags surfaced before anything is sent | `generate_music_email.py` |

## The verification-gates philosophy

Nothing in this pipeline sends, publishes, or finalizes anything on its own. Instead it raises **flags**, and the flags carry evidence. From this repository's demo build, on fictional data:

```
📝 Song note; Deep Calls to Deep: New this season; teach pre-service twice before using.
🔁 Repetition; Deep Calls to Deep [hymn_of_day] was used 2026-06-21 (28 days ago). Consider an alternative.
🧠 Last time; Every Table Widens on 2026-07-05 [hymn_of_day]: Cut verse 3 for time; keep an eye on length.
⚖️  Split this week: 2 traditional / 3 contemporary (main slots). Previous Sunday: 1 trad / 2 contemp.
    Same lean two weeks running; consider inverting.
```

The register scan is the same idea applied to theology: it reads the lyrics of the whole week's set and warns when the *cumulative* weight of the songs pulls against the service's stated tone: one triumphant song is a choice, four is an accident. The human reads the flags and decides. That division of labor is the product.

## What we learned: the retired API version

The first version of stage 6–8 was more impressive and worse. Two "mini" AI personas (one for liturgy, one for assembly) were orchestrated over API calls each week. It worked, mostly. But evaluation in real production found a recurring failure: the assembly persona *re-typed scripture from its own context* each week, which introduced a recurring text-corruption bug in the one part of the document where errors are least acceptable.

So it was retired, deliberately, for the current design: a deterministic Python builder, a file-based handoff between collaborators with explicit `READY`/`BUILT` markers, and a hard rule that **scripture text never passes through a language model**: it is placed programmatically from an authoritative source. Less impressive to describe. Correct every week since.

That arc (build the clever version, measure it honestly, choose the boring one) is the most transferable thing in this repository.

## Data handling (what is *not* here)

The production system this demonstrates serves a real congregation, and its database holds information about real people: who leads which songs, what keys suit which voices, notes about real services. **None of that is in this repository, by design.** No production database, no congregation members' names, no real service history, no real correspondence. Scripture ships as public-domain fixture text rather than a scraped licensed translation, because text rights are data handling too. The git history of this repository was started fresh for publication and has never contained any of it.

Everything here is generated by `seed_demo_data.py`: fictional songs with invented lyrics, role-based leader labels ("cantor", "band"), and a fictional service history built to exercise every check the pipeline performs. Careful handling of a community's data is part of the craft this repository exists to demonstrate.

## Quickstart

```bash
pip install python-docx
python3 seed_demo_data.py        # builds worship.db, the fictional congregation
python3 build_worship_plan.py    # builds the 2026-07-19 demo service end-to-end
```

The build reads `worship_input.json`, ingests the liturgist's blocks from `handoff/2026-07-19/`, loads the scripture fixtures, runs the flag pass, and writes a formatted service plan to `Worship Plans/` plus a `builder_flags.md` beside the handoff. Everything runs locally; no network needed.

A pre-built sample of the output document and flags file ships in the repository, so you can read the results without running anything.

## File map

```
worship_database.py        the data layer: songs, services, resources, liturgical texts (SQLite)
seed_demo_data.py          builds the fictional demo database
build_lectionary.py        loads the liturgical calendar as data
get_scripture.py           scripture from public-domain fixtures; never touches a model
search_songs.py            title/tag search
get_suggestions.py         usage-frequency song suggestions per liturgical slot
build_worship_plan.py      the deterministic builder: handoff ingest → flag pass → document
worship_plan_generator.py  liturgical templates (ELW-pattern orders A and B) and .docx assembly
add_resources.py           sheet-music linking with human-verified flags
generate_music_email.py    the weekly band email, with review flags
quick_queries.py           worked examples against the database
handoff/                   the file-based collaboration handoff (demo week included)
Worship Plans/             generated service plans (demo output included)
```

## License

Code: MIT. Demo content (invented songs, lyrics, liturgy): CC BY 4.0.

Built in production use for a working congregation; published as a portfolio demonstration of AI-human collaboration under real-world constraints, where the constraint that matters most is trust.
