"""SQLite schema and helpers for horoscopo."""
import json
import os
import sqlite3
from datetime import date

DB_PATH = os.path.join(os.path.dirname(__file__), "db", "horoscopo.db")

SIGNS = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
]

SIGN_EMOJIS = {
    "aries": "\u2648", "taurus": "\u2649", "gemini": "\u264a", "cancer": "\u264b",
    "leo": "\u264c", "virgo": "\u264d", "libra": "\u264e", "scorpio": "\u264f",
    "sagittarius": "\u2650", "capricorn": "\u2651", "aquarius": "\u2652", "pisces": "\u2653",
}

SIGN_NAMES_ES = {
    "aries": "Aries", "taurus": "Tauro", "gemini": "G\u00e9minis", "cancer": "C\u00e1ncer",
    "leo": "Leo", "virgo": "Virgo", "libra": "Libra", "scorpio": "Escorpio",
    "sagittarius": "Sagitario", "capricorn": "Capricornio", "aquarius": "Acuario", "pisces": "Piscis",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_horoscopes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_lang TEXT NOT NULL,
    sign TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    scraped_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(run_date, source_name, sign)
);

CREATE TABLE IF NOT EXISTS noise_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    sign TEXT NOT NULL,
    noise_type TEXT NOT NULL,
    value TEXT NOT NULL,
    UNIQUE(run_date, sign, noise_type)
);

CREATE TABLE IF NOT EXISTS generated_horoscopes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    sign TEXT NOT NULL,
    horoscope_text TEXT NOT NULL,
    model TEXT,
    generated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(run_date, sign)
);

CREATE TABLE IF NOT EXISTS publish_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    sign TEXT NOT NULL,
    message_id INTEGER,
    published_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(run_date, sign)
);
"""


def get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def store_raw(conn: sqlite3.Connection, run_date: str, source_name: str,
              source_lang: str, sign: str, text: str):
    conn.execute(
        "INSERT OR REPLACE INTO raw_horoscopes (run_date, source_name, source_lang, sign, raw_text) "
        "VALUES (?, ?, ?, ?, ?)",
        (run_date, source_name, source_lang, sign, text),
    )


def store_noise(conn: sqlite3.Connection, run_date: str, sign: str,
                noise_type: str, value: str):
    conn.execute(
        "INSERT OR REPLACE INTO noise_artifacts (run_date, sign, noise_type, value) "
        "VALUES (?, ?, ?, ?)",
        (run_date, sign, noise_type, value),
    )


def store_horoscope(conn: sqlite3.Connection, run_date: str, sign: str,
                    text: str, model: str):
    conn.execute(
        "INSERT OR REPLACE INTO generated_horoscopes (run_date, sign, horoscope_text, model) "
        "VALUES (?, ?, ?, ?)",
        (run_date, sign, text, model),
    )


def get_raw_for_date(conn: sqlite3.Connection, run_date: str) -> dict[str, list[dict]]:
    """Returns {sign: [{source_name, source_lang, raw_text}, ...]}."""
    rows = conn.execute(
        "SELECT sign, source_name, source_lang, raw_text FROM raw_horoscopes WHERE run_date = ?",
        (run_date,),
    ).fetchall()
    result: dict[str, list[dict]] = {s: [] for s in SIGNS}
    for r in rows:
        result[r["sign"]].append({
            "source": r["source_name"],
            "lang": r["source_lang"],
            "text": r["raw_text"],
        })
    return result


def get_noise_for_date(conn: sqlite3.Connection, run_date: str) -> dict[str, dict[str, str]]:
    """Returns {sign: {noise_type: value}}."""
    rows = conn.execute(
        "SELECT sign, noise_type, value FROM noise_artifacts WHERE run_date = ?",
        (run_date,),
    ).fetchall()
    result: dict[str, dict[str, str]] = {s: {} for s in SIGNS}
    for r in rows:
        result[r["sign"]][r["noise_type"]] = r["value"]
    return result


def get_horoscopes_for_date(conn: sqlite3.Connection, run_date: str) -> dict[str, str]:
    """Returns {sign: horoscope_text}."""
    rows = conn.execute(
        "SELECT sign, horoscope_text FROM generated_horoscopes WHERE run_date = ?",
        (run_date,),
    ).fetchall()
    return {r["sign"]: r["horoscope_text"] for r in rows}


def get_published_signs(conn: sqlite3.Connection, run_date: str) -> set[str]:
    rows = conn.execute(
        "SELECT sign FROM publish_state WHERE run_date = ?",
        (run_date,),
    ).fetchall()
    return {r["sign"] for r in rows}


def mark_published(conn: sqlite3.Connection, run_date: str, sign: str, message_id: int):
    conn.execute(
        "INSERT OR REPLACE INTO publish_state (run_date, sign, message_id) VALUES (?, ?, ?)",
        (run_date, sign, message_id),
    )
