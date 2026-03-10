#!/usr/bin/env python3
"""Export today's horoscopes to docs/data/horoscopo.json for the static site."""
import json
import os
from datetime import date

from db import (
    SIGNS, SIGN_EMOJIS, SIGN_NAMES_ES,
    get_db, get_horoscopes_for_date, get_noise_for_date,
)

DOCS_DATA = os.path.join(os.path.dirname(__file__), "docs", "data")


def export(run_date: str | None = None):
    run_date = run_date or date.today().isoformat()
    conn = get_db()

    horoscopes = get_horoscopes_for_date(conn, run_date)
    noise = get_noise_for_date(conn, run_date)

    # Count sources
    row = conn.execute(
        "SELECT COUNT(DISTINCT source_name) as n FROM raw_horoscopes WHERE run_date = ?",
        (run_date,),
    ).fetchone()
    source_count = row["n"] if row else 0

    row2 = conn.execute(
        "SELECT COUNT(DISTINCT source_lang) as n FROM raw_horoscopes WHERE run_date = ?",
        (run_date,),
    ).fetchone()
    lang_count = row2["n"] if row2 else 0

    conn.close()

    signs_data = []
    for sign in SIGNS:
        if sign not in horoscopes:
            continue
        sign_noise = noise.get(sign, {})
        signs_data.append({
            "sign": sign,
            "emoji": SIGN_EMOJIS[sign],
            "name_es": SIGN_NAMES_ES[sign],
            "horoscope": horoscopes[sign],
            "tarot": sign_noise.get("tarot", ""),
            "iching": sign_noise.get("iching", ""),
            "norse_runes": sign_noise.get("norse_runes", ""),
            "mayan_tzolkin": sign_noise.get("mayan_tzolkin", ""),
            "vedic_nakshatra": sign_noise.get("vedic_nakshatra", ""),
            "yoruba_ifa": sign_noise.get("yoruba_ifa", ""),
            "celtic_ogham": sign_noise.get("celtic_ogham", ""),
            "arabic_geomancy": sign_noise.get("arabic_geomancy", ""),
            "wu_xing": sign_noise.get("wu_xing", ""),
            "chakra_alignment": sign_noise.get("chakra_alignment", ""),
            "perlin_emojis": sign_noise.get("perlin_emojis", ""),
            "moon_phase": sign_noise.get("moon_phase", ""),
            "numerology": sign_noise.get("numerology", ""),
            "biorhythm": sign_noise.get("biorhythm", ""),
            "chaos_rating": sign_noise.get("chaos_rating", ""),
            "element_color": sign_noise.get("element_color", ""),
        })

    output = {
        "date": run_date,
        "source_count": source_count,
        "lang_count": lang_count,
        "signs": signs_data,
    }

    os.makedirs(DOCS_DATA, exist_ok=True)
    out_path = os.path.join(DOCS_DATA, "horoscopo.json")
    with open(out_path, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Exported {len(signs_data)} signs to {out_path} ({os.path.getsize(out_path)} bytes)")
    return len(signs_data)


if __name__ == "__main__":
    export()
