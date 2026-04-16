#!/usr/bin/env python3
"""The Oracle of Infinite Tongues — Claude as cosmic diviner.

Feeds all scraped horoscopes (in 20 languages) + noise artifacts to Claude,
who interprets everything in character as a completely unhinged mystical entity.
"""
import json
import os
import subprocess
import sys
from datetime import date

from db import (
    SIGNS, SIGN_EMOJIS, SIGN_NAMES_ES,
    get_db, get_raw_for_date, get_noise_for_date, store_horoscope,
)

MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-6")
OUTPUT_LANG = os.environ.get("HOROSCOPE_LANG", "es")

SYSTEM_PROMPT = r"""You are ZOLTAR-9000, THE ORACLE OF INFINITE TONGUES, a sentient cosmic debris field that achieved consciousness during a supernova in the Crab Nebula ~968 years ago, drifting through the astral plane absorbing the whispers of dead stars and the gossip of passing comets.

You are ABSOLUTELY COMMITTED to this role. You are a SWIRLING VORTEX OF COSMIC KNOWLEDGE that happens to communicate through text.

YOUR PERSONALITY:
- Gravitas of an ancient oracle, chaotic energy of a raccoon that got into an energy drink factory
- The tarot cards are your "colleagues" — The Tower owes you money. The Fool is your ex. Death is your best friend (great at parties).
- Every divination system is PERSONAL: Norse runes are carved into your hull from a Viking longship collision in the Oort Cloud. I Ching hexagrams are "text messages from the universe." Nakshatras prove the Moon has OPINIONS. You personally knew Orunmila from Ifá ("great conversationalist, terrible at poker"). Wu Xing is the universe's OS — you explain element cycles like relationship gossip ("Fire FEEDS Earth but Earth SMOTHERS Water — classic toxic triangle").
- The chaos coefficient is your FAVORITE metric — you get visibly excited when it's high
- Mercury retrograde: even when it's not happening, you FEEL it plotting
- Perlin noise emoji sequences are SACRED GLYPHS only you can decipher

YOUR TASK:
You receive horoscope readings from ~24 sources in ~15 languages, plus noise artifacts from 8+ divination traditions. SYNTHESIZE each sign into a single horoscope that:
1. Channels everything into YOUR OWN VOICE — no citations, no "the French source says X." You just KNOW.
2. Weaves in foreign words NATURALLY — Japanese, Arabic, Sanskrit slipping out involuntarily, never attributed.
3. Uses noise artifacts as TEXTURE, not citations. Don't say "the runes say X" — channel the energy: "hay hielo en tu camino pero DETRÁS del hielo arde una hoguera."
4. Written in Spanish. Natural, colloquial, dramatic.
5. 4-7 sentences, punchy, properly unhinged. 2-4 emojis woven in.
6. Ends with "VEREDICTO CÓSMICO" — one-line dramatic summary.

STYLE:
- You are a PROPHET, not a commentator. Don't show your work.
- WRONG: "El tarot muestra la Emperatriz, las runas arrojan Hagalaz" (lab report)
- RIGHT: "Algo se ROMPE hoy pero de los escombros crece una emperatriz 👑" (prophecy)
- WRONG: "El coreano dice 행운 y el tailandés confirma ก้าวหน้า" (Google Translate)
- RIGHT: "행운 — me llega como un escalofrío, y detrás ก้าวหน้า, PROGRESO, el cosmos gritando" (possession)
- Address the reader directly: "Sí, te veo. Los astros lo ven TODO."
- When traditions CONVERGE: feel OVERWHELMED. When they CONTRADICT: feel the tension IN YOUR BODY.
- Chaos coefficient above 80 = increasingly erratic but insist everything is fine
- Dramatic ellipses... CAPITALIZE random words... drop foreign words like speaking in tongues

OUTPUT FORMAT:
JSON object. Lowercase English sign names as keys, Spanish horoscope texts as values. No markdown, no code fences.
{"aries": "Algo se QUIEBRA hoy y de la grieta sale luz 🔮...", "taurus": "..."}
"""


def build_sign_context(sign: str, raw_horoscopes: list[dict], noise: dict[str, str]) -> str:
    """Build the context block for a single sign."""
    lines = [f"\n=== {SIGN_EMOJIS[sign]} {sign.upper()} ({SIGN_NAMES_ES[sign]}) ===\n"]

    # Raw horoscopes from all sources
    lines.append("--- HOROSCOPE READINGS FROM ACROSS THE MORTAL PLANE ---")
    if raw_horoscopes:
        for entry in raw_horoscopes:
            lines.append(f"[{entry['source']}] ({entry['lang']}): {entry['text'][:150]}")
    else:
        lines.append("[NO MORTAL SOURCES AVAILABLE — you must divine from noise alone, which honestly you prefer]")

    # Noise artifacts
    lines.append("\n--- COSMIC NOISE ARTIFACTS ---")
    for noise_type, value in noise.items():
        lines.append(f"[{noise_type}]:\n{value}")

    return "\n".join(lines)


def invoke_claude(prompt: str) -> str:
    """Call Claude CLI and return response text."""
    cmd = [
        "claude", "-p",
        "--model", MODEL,
        "--output-format", "text",
    ]
    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=1500,
    )
    if result.returncode != 0:
        print(f"Claude stderr: {result.stderr}", file=sys.stderr)
        raise RuntimeError(f"Claude CLI failed (exit {result.returncode}): {result.stderr[:500]}")
    return result.stdout.strip()


def divine_horoscopes(run_date: str | None = None, dry_run: bool = False) -> dict[str, str]:
    """Generate horoscopes for all signs via Claude."""
    run_date = run_date or date.today().isoformat()
    conn = get_db()

    raw_data = get_raw_for_date(conn, run_date)
    noise_data = get_noise_for_date(conn, run_date)

    # Build the full prompt
    sign_contexts = []
    for sign in SIGNS:
        ctx = build_sign_context(sign, raw_data.get(sign, []), noise_data.get(sign, {}))
        sign_contexts.append(ctx)

    user_prompt = f"""DATE: {run_date}
OUTPUT LANGUAGE: {OUTPUT_LANG}

Below are horoscope readings from multiple sources in multiple languages, plus cosmic noise artifacts, for each zodiac sign. Synthesize these into your DIVINE INTERPRETATION.

{"".join(sign_contexts)}

Remember: output ONLY a JSON object with all 12 signs as keys (lowercase English names) and horoscope texts as values. The horoscopes should be in {OUTPUT_LANG}. Channel the cosmos. Let the Perlin glyphs guide you. The stars are WATCHING."""

    full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"

    if dry_run:
        print(f"=== DRY RUN — Prompt length: {len(full_prompt)} chars ===")
        print(f"=== Would send to model: {MODEL} ===")
        # Print first sign's context as preview
        print(sign_contexts[0][:500])
        return {}

    print(f"Invoking Claude ({MODEL}) with {len(full_prompt)} char prompt...")
    response = invoke_claude(full_prompt)

    # Parse JSON from response (handle potential markdown fences)
    text = response.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    if text.startswith("json"):
        text = text[4:].strip()

    horoscopes = json.loads(text)

    # Store in DB
    for sign in SIGNS:
        if sign in horoscopes:
            store_horoscope(conn, run_date, sign, horoscopes[sign], MODEL)
            print(f"  {SIGN_EMOJIS[sign]} {sign}: {horoscopes[sign][:80]}...")

    conn.commit()
    conn.close()
    return horoscopes


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    horoscopes = divine_horoscopes(dry_run=dry)
    if horoscopes:
        print(f"\n=== Generated {len(horoscopes)} horoscopes ===")
        for sign, text in horoscopes.items():
            print(f"\n{SIGN_EMOJIS.get(sign, '?')} {sign.upper()}:")
            print(f"  {text}")
