#!/usr/bin/env python3
"""Generate interpretable noise artifacts for each zodiac sign.

All noise is deterministic per (date, sign) — seeded by day ordinal + sign index.
This ensures re-runs on the same day produce identical results.
"""
import hashlib
import json
import math
import random
from datetime import date, datetime

import ephem
from noise import pnoise2

from db import SIGNS, get_db, store_noise

# ---------------------------------------------------------------------------
# Emoji pools by "cosmic category"
# ---------------------------------------------------------------------------

EMOJI_POOLS = {
    "celestial": list("🌙🌞⭐💫✨🌟☄️🪐🌍🌕🌑🌓🌗🔭🛸"),
    "nature": list("🌊🔥🌬️🌿🍃🌸🌺🌻🌵🌴🍄🦋🐉🦅🐍🕊️"),
    "mystical": list("🔮🪬🧿🕯️📿🗝️⚗️🪄✝️☯️☮️🕉️♾️"),
    "emotion": list("💀👁️🫀🧠💜🖤❤️‍🔥💔💝🥀😈👻🤡"),
    "abstract": list("♠️♣️♥️♦️🎭🎪🎰🃏🀄🎴⚡🌀🫧💠🔷"),
    "food": list("🍷🍵☕🧉🫖🍯🧂🌶️🍄🫒🥚🍳"),
    "cosmic_junk": list("🛒🧻🪣🧲📎🗿🪨🧊🫠🤌🦷👀🦴🧬"),
}

# Tarot Major Arcana
TAROT_MAJOR = [
    "The Fool", "The Magician", "The High Priestess", "The Empress", "The Emperor",
    "The Hierophant", "The Lovers", "The Chariot", "Strength", "The Hermit",
    "Wheel of Fortune", "Justice", "The Hanged Man", "Death", "Temperance",
    "The Devil", "The Tower", "The Star", "The Moon", "The Sun",
    "Judgement", "The World",
]

TAROT_EMOJIS = {
    "The Fool": "🃏", "The Magician": "🪄", "The High Priestess": "🌙",
    "The Empress": "👑", "The Emperor": "⚔️", "The Hierophant": "📿",
    "The Lovers": "💕", "The Chariot": "🏇", "Strength": "🦁",
    "The Hermit": "🏔️", "Wheel of Fortune": "🎡", "Justice": "⚖️",
    "The Hanged Man": "🙃", "Death": "💀", "Temperance": "🏺",
    "The Devil": "😈", "The Tower": "🗼", "The Star": "⭐",
    "The Moon": "🌕", "The Sun": "🌞", "Judgement": "📯", "The World": "🌍",
}

# I Ching trigrams
TRIGRAMS = ["☰", "☱", "☲", "☳", "☴", "☵", "☶", "☷"]
TRIGRAM_NAMES = {
    "☰": "Heaven (Qian)", "☱": "Lake (Dui)", "☲": "Fire (Li)", "☳": "Thunder (Zhen)",
    "☴": "Wind (Xun)", "☵": "Water (Kan)", "☶": "Mountain (Gen)", "☷": "Earth (Kun)",
}

ELEMENTS = ["🔥 Fire", "🌊 Water", "🌍 Earth", "🌬️ Air", "⚡ Aether"]
COLORS = [
    "🔴 Crimson", "🟠 Amber", "🟡 Gold", "🟢 Emerald", "🔵 Sapphire",
    "🟣 Violet", "⚫ Obsidian", "⚪ Pearl", "🟤 Bronze", "🩷 Rose",
]

# Elder Futhark Runes (Norse)
RUNES = [
    ("ᚠ", "Fehu", "Wealth, abundance, cattle — the primal fire of ownership"),
    ("ᚢ", "Uruz", "Strength, wild ox — untamed power and health"),
    ("ᚦ", "Thurisaz", "Thorn, giant — reactive force, chaos that protects"),
    ("ᚨ", "Ansuz", "Odin's rune — divine breath, prophecy, the word"),
    ("ᚱ", "Raidho", "Journey, wagon — cosmic order in motion"),
    ("ᚲ", "Kenaz", "Torch, ulcer — illumination through pain"),
    ("ᚷ", "Gebo", "Gift — sacred exchange, the bond that cannot be broken"),
    ("ᚹ", "Wunjo", "Joy — harmony achieved, the clan-fire that warms"),
    ("ᚺ", "Hagalaz", "Hail — uncontrollable destruction that clears the way"),
    ("ᚾ", "Nauthiz", "Need-fire — constraint that teaches, resistance that strengthens"),
    ("ᛁ", "Isa", "Ice — standstill, the frozen moment before the thaw"),
    ("ᛃ", "Jera", "Year, harvest — patience rewarded, the wheel turns"),
    ("ᛇ", "Eihwaz", "Yew — the world-tree axis, death and endurance"),
    ("ᛈ", "Perthro", "Dice cup, fate — the unknowable, wyrd's laughter"),
    ("ᛉ", "Algiz", "Elk-sedge — protection, the hand reaching upward"),
    ("ᛊ", "Sowilo", "Sun — victory, wholeness, the lightning bolt of clarity"),
    ("ᛏ", "Tiwaz", "Tyr — sacrifice, justice, the one-handed god's oath"),
    ("ᛒ", "Berkano", "Birch — rebirth, the mother, secrets kept in earth"),
    ("ᛖ", "Ehwaz", "Horse — partnership, trust, the bond between rider and steed"),
    ("ᛗ", "Mannaz", "Human — the self, intelligence, what makes us mortal"),
    ("ᛚ", "Laguz", "Water, lake — the unconscious, flow, what lies beneath"),
    ("ᛜ", "Ingwaz", "Ing — gestation, internal growth, the seed in darkness"),
    ("ᛞ", "Dagaz", "Day — breakthrough, dawn, the moment everything changes"),
    ("ᛟ", "Othala", "Heritage — ancestral land, what was left for you"),
]

# Vedic Nakshatras (27 lunar mansions)
NAKSHATRAS = [
    ("Ashwini", "अश्विनी", "The Horse Riders — swift healing, new beginnings"),
    ("Bharani", "भरणी", "The Bearer — transformation through intensity"),
    ("Krittika", "कृत्तिका", "The Razor — purification by fire, cutting away"),
    ("Rohini", "रोहिणी", "The Red One — fertility, growth, desire fulfilled"),
    ("Mrigashira", "मृगशिरा", "The Deer's Head — searching, wandering, gentle curiosity"),
    ("Ardra", "आर्द्रा", "The Moist One — storms that clear, tears that cleanse"),
    ("Punarvasu", "पुनर्वसु", "Return of the Light — renewal, the arrow that comes back"),
    ("Pushya", "पुष्य", "The Nourisher — most auspicious, spiritual milk"),
    ("Ashlesha", "आश्लेषा", "The Serpent — coiled wisdom, hypnotic embrace"),
    ("Magha", "मघा", "The Mighty — ancestors speak, throne of lineage"),
    ("Purva Phalguni", "पूर्वफाल्गुनी", "The Former Red One — pleasure, creation, the wedding bed"),
    ("Uttara Phalguni", "उत्तरफाल्गुनी", "The Latter Red One — patronage, contracts, the morning after"),
    ("Hasta", "हस्त", "The Hand — skill, craft, what the fingers know"),
    ("Chitra", "चित्रा", "The Brilliant — jewel of the sky, cosmic architecture"),
    ("Swati", "स्वाती", "The Sword — independence, the wind that bends but doesn't break"),
    ("Vishakha", "विशाखा", "The Forked Branch — determination, the archer's focus"),
    ("Anuradha", "अनुराधा", "Following Radha — devotion, friendship, the lotus in mud"),
    ("Jyeshtha", "ज्येष्ठा", "The Eldest — protective power, the chief's burden"),
    ("Mula", "मूला", "The Root — uprooting, getting to the bottom, Kali's laughter"),
    ("Purva Ashadha", "पूर्वाषाढ़ा", "The Former Invincible — purification, early victory"),
    ("Uttara Ashadha", "उत्तराषाढ़ा", "The Latter Invincible — final victory, universal"),
    ("Shravana", "श्रवण", "The Ear — listening, learning, what the cosmos whispers"),
    ("Dhanishta", "धनिष्ठा", "The Drum — rhythm, wealth, music of the spheres"),
    ("Shatabhisha", "शतभिषा", "Hundred Healers — the veiling star, oceanic medicine"),
    ("Purva Bhadrapada", "पूर्वभाद्रपदा", "The Former Lucky Feet — scorching intensity, funeral pyre"),
    ("Uttara Bhadrapada", "उत्तरभाद्रपदा", "The Latter Lucky Feet — deep waters, kundalini depths"),
    ("Revati", "रेवती", "The Wealthy — safe journey, the final nakshatra, cosmic completion"),
]

# Mayan Tzolkin day signs (20 day signs)
TZOLKIN_SIGNS = [
    ("Imix", "🐊", "Crocodile — primordial waters, the Earth Mother's back"),
    ("Ik", "💨", "Wind — breath of life, spirit, communication with the divine"),
    ("Akbal", "🌑", "Night — the void, the dreaming house, inner darkness"),
    ("Kan", "🌽", "Seed — potential, the net of abundance, lizard medicine"),
    ("Chicchan", "🐍", "Serpent — kundalini, life force, feathered wisdom"),
    ("Cimi", "💀", "Death — transformation, the owl's counsel, ancestors"),
    ("Manik", "🦌", "Deer — healing hand, the hunt, tools of creation"),
    ("Lamat", "⭐", "Star — Venus, harmony, the rabbit's multiplication"),
    ("Muluc", "💧", "Water — offering, the moon's pull, emotional tides"),
    ("Oc", "🐕", "Dog — loyalty, guides to the underworld, faithful heart"),
    ("Chuen", "🐒", "Monkey — artisan, trickster, the thread-spinner of time"),
    ("Eb", "🌿", "Grass — road, human journey, the path of many steps"),
    ("Ben", "🌾", "Reed — authority, skywalker, the hollow bone that channels"),
    ("Ix", "🐆", "Jaguar — night sorcerer, earth magic, shamanic vision"),
    ("Men", "🦅", "Eagle — vision from above, the mind that soars"),
    ("Cib", "🕯️", "Vulture — ancestral wisdom, karmic cleansing, old soul"),
    ("Caban", "🌍", "Earth — synchronicity, earthquakes of understanding"),
    ("Etznab", "🔪", "Flint — truth that cuts, mirror of obsidian, sacrifice"),
    ("Cauac", "⛈️", "Storm — thunder beings, purification, cosmic rage"),
    ("Ahau", "☀️", "Sun — enlightenment, the lord, flowers of consciousness"),
]

# Yoruba Ifá Odù (16 principal figures)
IFA_ODU = [
    ("Ogbe", "𐌉𐌉𐌉𐌉", "The king of light — pure blessing, open roads, heaven descends"),
    ("Oyeku", "𐌗𐌗𐌗𐌗", "The king of darkness — endings, ancestors, what hides to protect"),
    ("Iwori", "𐌉𐌗𐌗𐌉", "The chameleon — adaptability, reversal, inner vision"),
    ("Odi", "𐌗𐌉𐌉𐌗", "The closed door — boundaries, gestation, the womb"),
    ("Irosun", "𐌉𐌉𐌗𐌗", "The blood of sacrifice — lineage, DNA memory, ancestral debt"),
    ("Owonrin", "𐌗𐌗𐌉𐌉", "The trickster's laugh — chaos magic, Eshu's crossroads"),
    ("Obara", "𐌉𐌗𐌗𐌗", "The kneeling one — humility opens what force cannot"),
    ("Okanran", "𐌗𐌗𐌗𐌉", "The one mouth — truth spoken at cost, the heart's fire"),
    ("Ogunda", "𐌉𐌉𐌉𐌗", "The path cleared by iron — Ogun's road, war that creates"),
    ("Osa", "𐌗𐌉𐌉𐌉", "The wind's errand — Oya's tornado, sudden change"),
    ("Ika", "𐌗𐌗𐌉𐌗", "The biting one — cunning, medicine that stings to heal"),
    ("Oturupon", "𐌗𐌉𐌗𐌗", "The overturned — illness as teacher, the earth reclaims"),
    ("Otura", "𐌉𐌗𐌉𐌗", "The mystic — Ifa's own voice, divination squared"),
    ("Irete", "𐌗𐌉𐌗𐌉", "The presser — persistence, the tortoise's victory"),
    ("Ose", "𐌉𐌗𐌉𐌉", "The sorcerer — Oshun's honey, sweetness with power"),
    ("Ofun", "𐌉𐌉𐌗𐌉", "The white cloth — original purity, return to source"),
]

# Celtic Ogham (tree alphabet divination)
OGHAM = [
    ("ᚁ", "Beith", "Birch — new beginnings, purification, the first mark"),
    ("ᚂ", "Luis", "Rowan — protection against enchantment, clear vision"),
    ("ᚃ", "Fearn", "Alder — oracular power, the bridge between worlds"),
    ("ᚄ", "Saille", "Willow — moon tree, intuition, the water's memory"),
    ("ᚅ", "Nion", "Ash — Yggdrasil's cousin, connection, the cosmic web"),
    ("ᚆ", "Huath", "Hawthorn — gateway, patience, the fairy thorn"),
    ("ᚇ", "Duir", "Oak — doorway, strength, the druids' own tree"),
    ("ᚈ", "Tinne", "Holly — challenge, warrior energy, the spear that tests"),
    ("ᚉ", "Coll", "Hazel — wisdom, the salmon's pool, nine nuts of knowledge"),
    ("ᚊ", "Quert", "Apple — beauty, immortality, Avalon's gift"),
    ("ᚋ", "Muin", "Vine — harvest, prophecy, Dionysian truth"),
    ("ᚌ", "Gort", "Ivy — tenacity, the labyrinth, spiral growth"),
    ("ᚍ", "Ngetal", "Reed — direct action, thatch of the spirit-house"),
    ("ᚎ", "Straif", "Blackthorn — no choice, fate, the dark mother's discipline"),
    ("ᚏ", "Ruis", "Elder — endings, the crone, death that feeds new life"),
]

# Arabic Geomancy (Raml) — 16 figures
GEOMANCY = [
    ("⚊⚊\n⚊⚊\n⚊⚊\n⚊⚊", "Via", "The Way — pure movement, the path itself is the answer"),
    ("⚋⚋\n⚋⚋\n⚋⚋\n⚋⚋", "Populus", "The People — collective, dissolution, the crowd decides"),
    ("⚊⚊\n⚋⚋\n⚋⚋\n⚊⚊", "Carcer", "The Prison — restriction that reveals, necessary confinement"),
    ("⚋⚋\n⚊⚊\n⚊⚊\n⚋⚋", "Conjunctio", "The Meeting — union of opposites, crossroads"),
    ("⚊⚊\n⚊⚊\n⚋⚋\n⚋⚋", "Fortuna Major", "Great Fortune — overwhelming success, the sun ascends"),
    ("⚋⚋\n⚋⚋\n⚊⚊\n⚊⚊", "Fortuna Minor", "Lesser Fortune — fleeting luck, grab it NOW"),
    ("⚊⚊\n⚋⚋\n⚊⚊\n⚋⚋", "Acquisitio", "The Gain — accumulation, what enters does not leave"),
    ("⚋⚋\n⚊⚊\n⚋⚋\n⚊⚊", "Amissio", "The Loss — release, what leaves was never truly yours"),
    ("⚊⚊\n⚊⚊\n⚊⚊\n⚋⚋", "Laetitia", "Joy — upward, the fountain, laughter of the earth"),
    ("⚋⚋\n⚊⚊\n⚊⚊\n⚊⚊", "Tristitia", "Sorrow — downward, the well, grief that deepens"),
    ("⚊⚊\n⚋⚋\n⚋⚋\n⚋⚋", "Caput Draconis", "Dragon's Head — beginnings, the portal opens upward"),
    ("⚋⚋\n⚋⚋\n⚋⚋\n⚊⚊", "Cauda Draconis", "Dragon's Tail — endings, the portal drains downward"),
    ("⚊⚊\n⚊⚊\n⚋⚋\n⚊⚊", "Puella", "The Girl — beauty, receptivity, Venus smiles"),
    ("⚋⚋\n⚊⚊\n⚊⚊\n⚋⚋", "Puer", "The Boy — aggression, impulse, Mars charges"),
    ("⚊⚊\n⚋⚋\n⚊⚊\n⚊⚊", "Rubeus", "The Red — passion, danger, blood on the sand"),
    ("⚋⚋\n⚊⚊\n⚋⚋\n⚋⚋", "Albus", "The White — wisdom, clarity, the sage speaks"),
]

# Chinese Wu Xing (五行) — Five Phases with productive/destructive cycles
WU_XING = [
    ("木 Mù", "Wood", "🌳", "Growth, flexibility, the bamboo that bends", "feeds Fire", "overcomes Earth"),
    ("火 Huǒ", "Fire", "🔥", "Passion, brilliance, the forge of creation", "feeds Earth", "overcomes Metal"),
    ("土 Tǔ", "Earth", "🏔️", "Stability, nourishment, the mother of ten thousand", "feeds Metal", "overcomes Water"),
    ("金 Jīn", "Metal", "⚔️", "Precision, grief, the blade that discerns", "feeds Water", "overcomes Wood"),
    ("水 Shuǐ", "Water", "🌊", "Wisdom, fear, the abyss that reflects", "feeds Wood", "overcomes Fire"),
]

# Hindu Chakras
CHAKRAS = [
    ("Muladhara", "मूलाधार", "🔴", "Root — survival, earth, I AM"),
    ("Svadhisthana", "स्वाधिष्ठान", "🟠", "Sacral — pleasure, water, I FEEL"),
    ("Manipura", "मणिपूर", "🟡", "Solar Plexus — power, fire, I DO"),
    ("Anahata", "अनाहत", "🟢", "Heart — love, air, I LOVE"),
    ("Vishuddha", "विशुद्ध", "🔵", "Throat — truth, ether, I SPEAK"),
    ("Ajna", "आज्ञा", "🟣", "Third Eye — intuition, light, I SEE"),
    ("Sahasrara", "सहस्रार", "⚪", "Crown — consciousness, thought, I UNDERSTAND"),
]


def _seed(run_date: str, sign: str) -> int:
    """Deterministic seed from date + sign."""
    h = hashlib.sha256(f"{run_date}:{sign}".encode()).hexdigest()
    return int(h[:8], 16)


def generate_perlin_emojis(run_date: str, sign: str) -> str:
    """Map 2D Perlin noise to emoji sequences.

    X axis = time (day of year), Y axis = sign index.
    The noise value selects both the emoji category and the specific emoji.
    """
    sign_idx = SIGNS.index(sign)
    day_of_year = date.fromisoformat(run_date).timetuple().tm_yday

    categories = list(EMOJI_POOLS.keys())
    emojis = []

    for offset in range(12):
        # Use wider spacing and prime multipliers to break Perlin correlation
        x = (day_of_year * 7.31 + offset * 13.7) * 0.037
        y = (sign_idx * 11.3 + offset * 5.9) * 0.041

        val = pnoise2(x, y, octaves=4, persistence=0.65, lacunarity=2.3,
                       repeatx=1024, repeaty=1024, base=day_of_year % 256)
        # Normalize from [-1, 1] to [0, 1]
        norm = (val + 1) / 2

        # Select category — use a second noise sample to decorrelate
        cat_val = pnoise2(x + 500, y + 500, octaves=2, base=(day_of_year + 37) % 256)
        cat_idx = int(((cat_val + 1) / 2) * len(categories)) % len(categories)
        cat = categories[cat_idx]
        pool = EMOJI_POOLS[cat]

        # Second noise sample for emoji within category
        val2 = pnoise2(x + 100, y + 100, octaves=2)
        emoji_idx = int(((val2 + 1) / 2) * len(pool)) % len(pool)
        emojis.append(pool[emoji_idx])

    return "".join(emojis)


def generate_tarot(run_date: str, sign: str) -> str:
    """Draw 3 tarot cards (past, present, future)."""
    rng = random.Random(_seed(run_date, sign))
    cards = rng.sample(TAROT_MAJOR, 3)
    lines = []
    for label, card in zip(["Past", "Present", "Future"], cards):
        emoji = TAROT_EMOJIS.get(card, "🎴")
        lines.append(f"{label}: {emoji} {card}")
    return "\n".join(lines)


def generate_iching(run_date: str, sign: str) -> str:
    """Generate an I Ching hexagram (two trigrams)."""
    rng = random.Random(_seed(run_date, sign) + 42)
    upper = rng.choice(TRIGRAMS)
    lower = rng.choice(TRIGRAMS)
    return f"{upper}{lower} — {TRIGRAM_NAMES[upper]} over {TRIGRAM_NAMES[lower]}"


def calculate_moon_phase(run_date: str) -> str:
    """Calculate actual moon phase for the date."""
    d = ephem.Date(run_date)
    moon = ephem.Moon(d)
    phase_pct = moon.phase

    if phase_pct < 2:
        name, emoji = "New Moon", "🌑"
    elif phase_pct < 25:
        name, emoji = "Waxing Crescent", "🌒"
    elif phase_pct < 48:
        name, emoji = "First Quarter", "🌓"
    elif phase_pct < 75:
        name, emoji = "Waxing Gibbous", "🌔"
    elif phase_pct < 98:
        name, emoji = "Full Moon", "🌕"
    elif phase_pct < 100:
        name, emoji = "Waning Gibbous", "🌖"
    else:
        name, emoji = "Full Moon", "🌕"

    # Refine waning
    # ephem.phase goes 0 (new) -> 100 (full) -> 0 (new)
    # We need to check if moon is waxing or waning
    prev_day = ephem.Date(d - 1)
    prev_moon = ephem.Moon(prev_day)
    if prev_moon.phase > phase_pct and phase_pct > 50:
        if phase_pct > 75:
            name, emoji = "Waning Gibbous", "🌖"
        elif phase_pct > 48:
            name, emoji = "Last Quarter", "🌗"
        else:
            name, emoji = "Waning Crescent", "🌘"

    return f"{emoji} {name} ({phase_pct:.1f}%)"


def generate_numerology(run_date: str, sign: str) -> str:
    """Calculate numerological vibration for the day+sign."""
    digits = [int(c) for c in run_date.replace("-", "") if c.isdigit()]
    sign_val = SIGNS.index(sign) + 1

    # Reduce to single digit
    total = sum(digits) + sign_val
    while total > 9 and total not in (11, 22, 33):  # Master numbers
        total = sum(int(d) for d in str(total))

    meanings = {
        1: "🔱 New beginnings, independence, raw force",
        2: "☯️ Duality, partnership, hidden balance",
        3: "🔺 Creation, expression, cosmic comedy",
        4: "🧱 Structure, foundation, stubborn earth",
        5: "🌀 Change, freedom, beautiful chaos",
        6: "💝 Harmony, responsibility, the lover's burden",
        7: "👁️ Mystery, introspection, the void stares back",
        8: "♾️ Power, infinity, karmic loops",
        9: "🔮 Completion, wisdom, the end that is a beginning",
        11: "⚡ Master Illumination — the lightning path",
        22: "🏗️ Master Builder — architect of impossible dreams",
        33: "🌟 Master Teacher — the cosmic professor is in",
    }
    return f"Vibration {total}: {meanings.get(total, '🎲 Unknown resonance')}"


def generate_biorhythm(run_date: str, sign: str) -> str:
    """Pseudo-biorhythm based on sine waves with different periods."""
    seed = _seed(run_date, sign)
    day = date.fromisoformat(run_date).toordinal()

    physical = math.sin(2 * math.pi * (day + seed % 23) / 23)
    emotional = math.sin(2 * math.pi * (day + seed % 28) / 28)
    intellectual = math.sin(2 * math.pi * (day + seed % 33) / 33)

    def bar(val):
        filled = int((val + 1) / 2 * 10)
        return "█" * filled + "░" * (10 - filled)

    return (
        f"Physical:     [{bar(physical)}] {physical:+.2f}\n"
        f"Emotional:    [{bar(emotional)}] {emotional:+.2f}\n"
        f"Intellectual: [{bar(intellectual)}] {intellectual:+.2f}"
    )


def generate_element_color(run_date: str, sign: str) -> str:
    """Random element and color assignment."""
    rng = random.Random(_seed(run_date, sign) + 777)
    element = rng.choice(ELEMENTS)
    color = rng.choice(COLORS)
    return f"Element: {element} | Color: {color}"


def generate_chaos_rating(run_date: str, sign: str) -> str:
    """A totally meaningless chaos coefficient."""
    rng = random.Random(_seed(run_date, sign) + 1337)
    chaos = rng.gauss(50, 20)
    chaos = max(0, min(100, chaos))

    if chaos > 90:
        desc = "MAXIMUM ENTROPY 🌪️💥"
    elif chaos > 70:
        desc = "Turbulent waters ahead 🌊"
    elif chaos > 50:
        desc = "Moderate cosmic interference 🌀"
    elif chaos > 30:
        desc = "Relative calm in the void 🕊️"
    else:
        desc = "Suspiciously peaceful... 😐"

    return f"Chaos coefficient: {chaos:.1f}% — {desc}"


def generate_rune_cast(run_date: str, sign: str) -> str:
    """Cast 3 Elder Futhark runes (situation, challenge, outcome)."""
    rng = random.Random(_seed(run_date, sign) + 2718)
    drawn = rng.sample(RUNES, 3)
    labels = ["Situation", "Challenge", "Outcome"]
    lines = []
    for label, (glyph, name, meaning) in zip(labels, drawn):
        # 20% chance of reversed (merkstave)
        reversed_str = " ᛭REVERSED᛭" if rng.random() < 0.2 else ""
        lines.append(f"{label}: {glyph} {name}{reversed_str} — {meaning}")
    return "\n".join(lines)


def generate_nakshatra(run_date: str, sign: str) -> str:
    """Select the ruling Vedic nakshatra (lunar mansion) for today."""
    rng = random.Random(_seed(run_date, sign) + 108)
    name, sanskrit, meaning = rng.choice(NAKSHATRAS)
    pada = rng.randint(1, 4)  # Each nakshatra has 4 padas (quarters)
    return f"🕉️ {name} ({sanskrit}) — Pada {pada}\n{meaning}"


def generate_tzolkin(run_date: str, sign: str) -> str:
    """Calculate Mayan Tzolkin day sign + number (1-13)."""
    d = date.fromisoformat(run_date)
    # Tzolkin is a 260-day cycle (20 signs × 13 numbers)
    # Using a reference point: 4 Ahau = Dec 21, 2012 (13.0.0.0.0)
    ref = date(2012, 12, 21)
    days_since = (d - ref).days + _seed(run_date, sign) % 20  # Offset per sign
    sign_idx = days_since % 20
    number = (days_since % 13) + 1
    name, emoji, meaning = TZOLKIN_SIGNS[sign_idx]
    return f"{emoji} {number} {name} — {meaning}"


def generate_ifa(run_date: str, sign: str) -> str:
    """Cast an Ifá Odù (Yoruba divination)."""
    rng = random.Random(_seed(run_date, sign) + 256)
    primary = rng.choice(IFA_ODU)
    secondary = rng.choice(IFA_ODU)
    name1, marks1, meaning1 = primary
    name2, marks2, meaning2 = secondary
    return (
        f"Primary Odù: {name1} — {meaning1}\n"
        f"Witness Odù: {name2} — {meaning2}"
    )


def generate_ogham(run_date: str, sign: str) -> str:
    """Draw an Ogham few (Celtic tree oracle)."""
    rng = random.Random(_seed(run_date, sign) + 3141)
    drawn = rng.sample(OGHAM, 2)
    glyph1, name1, meaning1 = drawn[0]
    glyph2, name2, meaning2 = drawn[1]
    return (
        f"Foundation: {glyph1} {name1} — {meaning1}\n"
        f"Growth:     {glyph2} {name2} — {meaning2}"
    )


def generate_geomancy(run_date: str, sign: str) -> str:
    """Cast an Arabic geomantic figure (Raml / Ilm al-Raml)."""
    rng = random.Random(_seed(run_date, sign) + 1001)
    figure, name, meaning = rng.choice(GEOMANCY)
    house = rng.randint(1, 12)  # Geomantic house (like astrological houses)
    house_meanings = {
        1: "Self", 2: "Wealth", 3: "Siblings", 4: "Home",
        5: "Pleasure", 6: "Health", 7: "Partnership", 8: "Death/Rebirth",
        9: "Journeys", 10: "Career", 11: "Hopes", 12: "Hidden enemies",
    }
    return f"🏜️ {name} in House {house} ({house_meanings[house]})\n{meaning}"


def generate_wu_xing(run_date: str, sign: str) -> str:
    """Determine the dominant Wu Xing (五行) phase and its cycle position."""
    rng = random.Random(_seed(run_date, sign) + 5555)
    chinese, english, emoji, meaning, feeds, overcomes = rng.choice(WU_XING)
    intensity = rng.choice(["waxing", "peak", "waning", "dormant"])
    return (
        f"{emoji} {chinese} ({english}) — {intensity}\n"
        f"{meaning}\n"
        f"Productive cycle: {feeds} | Destructive cycle: {overcomes}"
    )


def generate_chakra_alignment(run_date: str, sign: str) -> str:
    """Generate chakra activation levels using noise."""
    rng = random.Random(_seed(run_date, sign) + 7777)
    lines = []
    dominant_idx = -1
    dominant_val = -1
    for i, (name, sanskrit, color, desc) in enumerate(CHAKRAS):
        activation = rng.gauss(50, 25)
        activation = max(0, min(100, activation))
        if activation > dominant_val:
            dominant_val = activation
            dominant_idx = i
        bar_len = int(activation / 10)
        bar = "▓" * bar_len + "░" * (10 - bar_len)
        lines.append(f"{color} [{bar}] {name} ({sanskrit}) {activation:.0f}%")

    dominant = CHAKRAS[dominant_idx]
    lines.append(f"\nDominant: {dominant[2]} {dominant[0]} — {dominant[3]}")
    return "\n".join(lines)


def generate_all_noise(run_date: str | None = None) -> dict[str, dict[str, str]]:
    """Generate all noise artifacts for all signs. Returns {sign: {type: value}}."""
    run_date = run_date or date.today().isoformat()
    conn = get_db()
    moon = calculate_moon_phase(run_date)

    result: dict[str, dict[str, str]] = {}

    for sign in SIGNS:
        noise = {
            "perlin_emojis": generate_perlin_emojis(run_date, sign),
            "tarot": generate_tarot(run_date, sign),
            "iching": generate_iching(run_date, sign),
            "moon_phase": moon,
            "numerology": generate_numerology(run_date, sign),
            "biorhythm": generate_biorhythm(run_date, sign),
            "element_color": generate_element_color(run_date, sign),
            "chaos_rating": generate_chaos_rating(run_date, sign),
            # Multicultural divination systems
            "norse_runes": generate_rune_cast(run_date, sign),
            "vedic_nakshatra": generate_nakshatra(run_date, sign),
            "mayan_tzolkin": generate_tzolkin(run_date, sign),
            "yoruba_ifa": generate_ifa(run_date, sign),
            "celtic_ogham": generate_ogham(run_date, sign),
            "arabic_geomancy": generate_geomancy(run_date, sign),
            "wu_xing": generate_wu_xing(run_date, sign),
            "chakra_alignment": generate_chakra_alignment(run_date, sign),
        }

        for noise_type, value in noise.items():
            store_noise(conn, run_date, sign, noise_type, value)

        result[sign] = noise

    conn.commit()
    conn.close()
    return result


if __name__ == "__main__":
    print("=== Generating cosmic noise ===\n")
    all_noise = generate_all_noise()
    for sign, noise in all_noise.items():
        print(f"\n{'='*60}")
        print(f"  {sign.upper()}")
        print(f"{'='*60}")
        for noise_type, value in noise.items():
            print(f"\n  [{noise_type}]")
            for line in value.split("\n"):
                print(f"    {line}")
