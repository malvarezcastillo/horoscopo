# horoscopo — The Cosmic Noise Diviner

Scrapes horoscopes from 20 sources in 20 languages, adds procedural noise (Perlin-mapped emojis, tarot, I Ching, moon phase, numerology), feeds it all to Claude as a mystical diviner, and publishes daily horoscopes to a Telegram channel.

## Quick Start

```bash
cd ~/scrapers/horoscopo && source .venv/bin/activate
pip install -r requirements.txt
python sources.py                # test-scrape all sources
python noise.py                  # preview noise generation
python diviner.py                # generate horoscopes via Claude
python telegram_publish.py       # publish to Telegram channel
./run_cron.sh                    # full pipeline
```

## Pipeline

1. **`sources.py`** — Scrapes horoscopes from 20 web sources in 20 different languages. Each source returns raw text per zodiac sign. Stores results in SQLite.

2. **`noise.py`** — Generates interpretable randomness per sign:
   - Perlin noise → emoji sequences (2D: time axis × sign index)
   - Tarot card draws (seeded by date + sign)
   - I Ching hexagram
   - Actual moon phase
   - Numerology from current date
   - Random element/color associations
   - Biorhythm sine waves

3. **`diviner.py`** — Sends all scraped horoscopes + noise artifacts to Claude CLI as "The Oracle of Infinite Tongues". Claude synthesizes a single horoscope per sign in Spanish, channeling the cosmic chaos.

4. **`telegram_publish.py`** — Posts the 12 horoscopes to a Telegram channel via Telethon. Each sign gets its own message with emoji header.

**Cron:** `run_cron.sh` → `run_cron.py`: scrape → noise → divine → publish. `report.py` writes `report.json`.

## Data and state

- DB: `db/horoscopo.db` (SQLite WAL). Tables: `raw_horoscopes`, `noise_artifacts`, `generated_horoscopes`, `publish_state`.
- Schema in `db.py`.

## Environment

**Required:** `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE`, `TELEGRAM_CHANNEL` (channel to publish to).
**Optional:** `CLAUDE_MODEL` (default: claude-sonnet-4-6), `HOROSCOPE_LANG` (output language, default: es).

## Notes

- Claude CLI (`~/.local/bin/claude`) is a runtime dependency.
- Sources are best-effort: if some fail, the diviner works with whatever it gets.
- The noise is deterministic per day+sign (seeded), so re-runs produce the same horoscope.
