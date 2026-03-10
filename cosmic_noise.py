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

# Arcanos Mayores del Tarot
TAROT_MAJOR = [
    "El Loco", "El Mago", "La Sacerdotisa", "La Emperatriz", "El Emperador",
    "El Sumo Sacerdote", "Los Enamorados", "El Carro", "La Fuerza", "El Ermitaño",
    "La Rueda de la Fortuna", "La Justicia", "El Colgado", "La Muerte", "La Templanza",
    "El Diablo", "La Torre", "La Estrella", "La Luna", "El Sol",
    "El Juicio", "El Mundo",
]

TAROT_EMOJIS = {
    "El Loco": "🃏", "El Mago": "🪄", "La Sacerdotisa": "🌙",
    "La Emperatriz": "👑", "El Emperador": "⚔️", "El Sumo Sacerdote": "📿",
    "Los Enamorados": "💕", "El Carro": "🏇", "La Fuerza": "🦁",
    "El Ermitaño": "🏔️", "La Rueda de la Fortuna": "🎡", "La Justicia": "⚖️",
    "El Colgado": "🙃", "La Muerte": "💀", "La Templanza": "🏺",
    "El Diablo": "😈", "La Torre": "🗼", "La Estrella": "⭐",
    "La Luna": "🌕", "El Sol": "🌞", "El Juicio": "📯", "El Mundo": "🌍",
}

# Trigramas del I Ching
TRIGRAMS = ["☰", "☱", "☲", "☳", "☴", "☵", "☶", "☷"]
TRIGRAM_NAMES = {
    "☰": "Cielo (Qián)", "☱": "Lago (Duì)", "☲": "Fuego (Lí)", "☳": "Trueno (Zhèn)",
    "☴": "Viento (Xùn)", "☵": "Agua (Kǎn)", "☶": "Montaña (Gèn)", "☷": "Tierra (Kūn)",
}

ELEMENTS = ["🔥 Fuego", "🌊 Agua", "🌍 Tierra", "🌬️ Aire", "⚡ Éter"]
COLORS = [
    "🔴 Carmesí", "🟠 Ámbar", "🟡 Oro", "🟢 Esmeralda", "🔵 Zafiro",
    "🟣 Violeta", "⚫ Obsidiana", "⚪ Perla", "🟤 Bronce", "🩷 Rosa",
]

# Runas Elder Futhark (nórdicas)
RUNES = [
    ("ᚠ", "Fehu", "Riqueza, abundancia, ganado — el fuego primordial de la posesión"),
    ("ᚢ", "Uruz", "Fuerza, uro salvaje — poder indómito y salud"),
    ("ᚦ", "Thurisaz", "Espina, gigante — fuerza reactiva, caos que protege"),
    ("ᚨ", "Ansuz", "Runa de Odín — aliento divino, profecía, la palabra"),
    ("ᚱ", "Raidho", "Viaje, carro — orden cósmico en movimiento"),
    ("ᚲ", "Kenaz", "Antorcha, llaga — iluminación a través del dolor"),
    ("ᚷ", "Gebo", "Regalo — intercambio sagrado, el vínculo inquebrantable"),
    ("ᚹ", "Wunjo", "Alegría — armonía alcanzada, el fuego del clan que calienta"),
    ("ᚺ", "Hagalaz", "Granizo — destrucción incontrolable que despeja el camino"),
    ("ᚾ", "Nauthiz", "Fuego de necesidad — restricción que enseña, resistencia que fortalece"),
    ("ᛁ", "Isa", "Hielo — quietud, el momento congelado antes del deshielo"),
    ("ᛃ", "Jera", "Año, cosecha — paciencia recompensada, la rueda gira"),
    ("ᛇ", "Eihwaz", "Tejo — el eje del árbol-mundo, muerte y resistencia"),
    ("ᛈ", "Perthro", "Cubilete del dado, destino — lo incognoscible, la risa del wyrd"),
    ("ᛉ", "Algiz", "Juncia de alce — protección, la mano que se alza"),
    ("ᛊ", "Sowilo", "Sol — victoria, plenitud, el rayo de claridad"),
    ("ᛏ", "Tiwaz", "Tyr — sacrificio, justicia, el juramento del dios manco"),
    ("ᛒ", "Berkano", "Abedul — renacimiento, la madre, secretos guardados en tierra"),
    ("ᛖ", "Ehwaz", "Caballo — compañerismo, confianza, el vínculo entre jinete y corcel"),
    ("ᛗ", "Mannaz", "Humano — el yo, inteligencia, lo que nos hace mortales"),
    ("ᛚ", "Laguz", "Agua, lago — el inconsciente, fluir, lo que yace debajo"),
    ("ᛜ", "Ingwaz", "Ing — gestación, crecimiento interno, la semilla en la oscuridad"),
    ("ᛞ", "Dagaz", "Día — ruptura, amanecer, el momento en que todo cambia"),
    ("ᛟ", "Othala", "Herencia — tierra ancestral, lo que te fue legado"),
]

# Nakshatras védicos (27 mansiones lunares)
NAKSHATRAS = [
    ("Ashwini", "अश्विनी", "Los Jinetes — sanación veloz, nuevos comienzos"),
    ("Bharani", "भरणी", "La Portadora — transformación a través de la intensidad"),
    ("Krittika", "कृत्तिका", "La Navaja — purificación por fuego, cortar lo que sobra"),
    ("Rohini", "रोहिणी", "La Roja — fertilidad, crecimiento, deseo cumplido"),
    ("Mrigashira", "मृगशिरा", "Cabeza de Ciervo — búsqueda, errancia, curiosidad suave"),
    ("Ardra", "आर्द्रा", "La Húmeda — tormentas que despejan, lágrimas que limpian"),
    ("Punarvasu", "पुनर्वसु", "Retorno de la Luz — renovación, la flecha que regresa"),
    ("Pushya", "पुष्य", "La Nodriza — lo más auspicioso, leche espiritual"),
    ("Ashlesha", "आश्लेषा", "La Serpiente — sabiduría enroscada, abrazo hipnótico"),
    ("Magha", "मघा", "La Poderosa — los ancestros hablan, trono del linaje"),
    ("Purva Phalguni", "पूर्वफाल्गुनी", "La Primera Roja — placer, creación, el lecho nupcial"),
    ("Uttara Phalguni", "उत्तरफाल्गुनी", "La Segunda Roja — mecenazgo, contratos, la mañana siguiente"),
    ("Hasta", "हस्त", "La Mano — habilidad, artesanía, lo que los dedos saben"),
    ("Chitra", "चित्रा", "La Brillante — joya del cielo, arquitectura cósmica"),
    ("Swati", "स्वाती", "La Espada — independencia, el viento que dobla sin romper"),
    ("Vishakha", "विशाखा", "La Rama Bifurcada — determinación, la mira del arquero"),
    ("Anuradha", "अनुराधा", "Siguiendo a Radha — devoción, amistad, el loto en el barro"),
    ("Jyeshtha", "ज्येष्ठा", "La Mayor — poder protector, la carga del jefe"),
    ("Mula", "मूला", "La Raíz — arrancar de raíz, llegar al fondo, la risa de Kali"),
    ("Purva Ashadha", "पूर्वाषाढ़ा", "La Primera Invencible — purificación, victoria temprana"),
    ("Uttara Ashadha", "उत्तराषाढ़ा", "La Segunda Invencible — victoria final, universal"),
    ("Shravana", "श्रवण", "El Oído — escuchar, aprender, lo que el cosmos susurra"),
    ("Dhanishta", "धनिष्ठा", "El Tambor — ritmo, riqueza, música de las esferas"),
    ("Shatabhisha", "शतभिषा", "Cien Sanadores — la estrella que vela, medicina oceánica"),
    ("Purva Bhadrapada", "पूर्वभाद्रपदा", "Los Primeros Pies Afortunados — intensidad abrasadora, pira funeraria"),
    ("Uttara Bhadrapada", "उत्तरभाद्रपदा", "Los Segundos Pies Afortunados — aguas profundas, abismos de kundalini"),
    ("Revati", "रेवती", "La Próspera — viaje seguro, el último nakshatra, culminación cósmica"),
]

# Signos del Tzolkin maya (20 signos diarios)
TZOLKIN_SIGNS = [
    ("Imix", "🐊", "Cocodrilo — aguas primordiales, la espalda de la Madre Tierra"),
    ("Ik", "💨", "Viento — aliento de vida, espíritu, comunicación con lo divino"),
    ("Akbal", "🌑", "Noche — el vacío, la casa del sueño, oscuridad interior"),
    ("Kan", "🌽", "Semilla — potencial, la red de abundancia, medicina de lagarto"),
    ("Chicchan", "🐍", "Serpiente — kundalini, fuerza vital, sabiduría emplumada"),
    ("Cimi", "💀", "Muerte — transformación, el consejo del búho, ancestros"),
    ("Manik", "🦌", "Ciervo — mano sanadora, la cacería, herramientas de creación"),
    ("Lamat", "⭐", "Estrella — Venus, armonía, la multiplicación del conejo"),
    ("Muluc", "💧", "Agua — ofrenda, el tirón de la luna, mareas emocionales"),
    ("Oc", "🐕", "Perro — lealtad, guía al inframundo, corazón fiel"),
    ("Chuen", "🐒", "Mono — artesano, embaucador, el hilandero del tiempo"),
    ("Eb", "🌿", "Hierba — camino, viaje humano, la senda de muchos pasos"),
    ("Ben", "🌾", "Caña — autoridad, caminante del cielo, el hueso hueco que canaliza"),
    ("Ix", "🐆", "Jaguar — hechicero nocturno, magia terrestre, visión chamánica"),
    ("Men", "🦅", "Águila — visión desde lo alto, la mente que vuela"),
    ("Cib", "🕯️", "Buitre — sabiduría ancestral, limpieza kármica, alma vieja"),
    ("Caban", "🌍", "Tierra — sincronicidad, terremotos de comprensión"),
    ("Etznab", "🔪", "Pedernal — verdad que corta, espejo de obsidiana, sacrificio"),
    ("Cauac", "⛈️", "Tormenta — seres del trueno, purificación, furia cósmica"),
    ("Ahau", "☀️", "Sol — iluminación, el señor, flores de consciencia"),
]

# Odù del Ifá Yoruba (16 figuras principales)
IFA_ODU = [
    ("Ogbe", "𐌉𐌉𐌉𐌉", "El rey de la luz — bendición pura, caminos abiertos, el cielo desciende"),
    ("Oyeku", "𐌗𐌗𐌗𐌗", "El rey de la oscuridad — finales, ancestros, lo que se oculta para proteger"),
    ("Iwori", "𐌉𐌗𐌗𐌉", "El camaleón — adaptabilidad, inversión, visión interior"),
    ("Odi", "𐌗𐌉𐌉𐌗", "La puerta cerrada — límites, gestación, el vientre"),
    ("Irosun", "𐌉𐌉𐌗𐌗", "La sangre del sacrificio — linaje, memoria del ADN, deuda ancestral"),
    ("Owonrin", "𐌗𐌗𐌉𐌉", "La risa del embaucador — magia del caos, la encrucijada de Eshu"),
    ("Obara", "𐌉𐌗𐌗𐌗", "El que se arrodilla — la humildad abre lo que la fuerza no puede"),
    ("Okanran", "𐌗𐌗𐌗𐌉", "La boca única — verdad dicha a precio, el fuego del corazón"),
    ("Ogunda", "𐌉𐌉𐌉𐌗", "El camino despejado con hierro — la ruta de Ogún, guerra que crea"),
    ("Osa", "𐌗𐌉𐌉𐌉", "El recado del viento — el tornado de Oyá, cambio repentino"),
    ("Ika", "𐌗𐌗𐌉𐌗", "El que muerde — astucia, medicina que pica para sanar"),
    ("Oturupon", "𐌗𐌉𐌗𐌗", "El volcado — la enfermedad como maestra, la tierra reclama"),
    ("Otura", "𐌉𐌗𐌉𐌗", "El místico — la voz propia del Ifá, adivinación al cuadrado"),
    ("Irete", "𐌗𐌉𐌗𐌉", "El que presiona — persistencia, la victoria de la tortuga"),
    ("Ose", "𐌉𐌗𐌉𐌉", "El hechicero — la miel de Oshún, dulzura con poder"),
    ("Ofun", "𐌉𐌉𐌗𐌉", "El paño blanco — pureza original, retorno a la fuente"),
]

# Ogham celta (alfabeto arbóreo de adivinación)
OGHAM = [
    ("ᚁ", "Beith", "Abedul — nuevos comienzos, purificación, la primera marca"),
    ("ᚂ", "Luis", "Serbal — protección contra el encantamiento, visión clara"),
    ("ᚃ", "Fearn", "Aliso — poder oracular, el puente entre mundos"),
    ("ᚄ", "Saille", "Sauce — árbol lunar, intuición, la memoria del agua"),
    ("ᚅ", "Nion", "Fresno — primo de Yggdrasil, conexión, la telaraña cósmica"),
    ("ᚆ", "Huath", "Espino — portal, paciencia, el espino de las hadas"),
    ("ᚇ", "Duir", "Roble — umbral, fuerza, el árbol de los druidas"),
    ("ᚈ", "Tinne", "Acebo — desafío, energía guerrera, la lanza que prueba"),
    ("ᚉ", "Coll", "Avellano — sabiduría, la poza del salmón, nueve nueces del saber"),
    ("ᚊ", "Quert", "Manzano — belleza, inmortalidad, el don de Avalón"),
    ("ᚋ", "Muin", "Vid — cosecha, profecía, verdad dionisíaca"),
    ("ᚌ", "Gort", "Hiedra — tenacidad, el laberinto, crecimiento en espiral"),
    ("ᚍ", "Ngetal", "Caña — acción directa, techo de la casa-espíritu"),
    ("ᚎ", "Straif", "Endrino — sin elección, destino, la disciplina de la madre oscura"),
    ("ᚏ", "Ruis", "Saúco — finales, la anciana, muerte que alimenta nueva vida"),
]

# Geomancia árabe (Raml) — 16 figuras
GEOMANCY = [
    ("⚊⚊\n⚊⚊\n⚊⚊\n⚊⚊", "Vía", "El Camino — movimiento puro, el sendero mismo es la respuesta"),
    ("⚋⚋\n⚋⚋\n⚋⚋\n⚋⚋", "Populus", "El Pueblo — colectivo, disolución, la multitud decide"),
    ("⚊⚊\n⚋⚋\n⚋⚋\n⚊⚊", "Carcer", "La Prisión — restricción que revela, confinamiento necesario"),
    ("⚋⚋\n⚊⚊\n⚊⚊\n⚋⚋", "Conjunctio", "El Encuentro — unión de opuestos, encrucijada"),
    ("⚊⚊\n⚊⚊\n⚋⚋\n⚋⚋", "Fortuna Major", "Gran Fortuna — éxito abrumador, el sol asciende"),
    ("⚋⚋\n⚋⚋\n⚊⚊\n⚊⚊", "Fortuna Minor", "Pequeña Fortuna — suerte fugaz, agárrala YA"),
    ("⚊⚊\n⚋⚋\n⚊⚊\n⚋⚋", "Acquisitio", "La Ganancia — acumulación, lo que entra no sale"),
    ("⚋⚋\n⚊⚊\n⚋⚋\n⚊⚊", "Amissio", "La Pérdida — soltar, lo que se va nunca fue verdaderamente tuyo"),
    ("⚊⚊\n⚊⚊\n⚊⚊\n⚋⚋", "Laetitia", "Alegría — ascenso, la fuente, risa de la tierra"),
    ("⚋⚋\n⚊⚊\n⚊⚊\n⚊⚊", "Tristitia", "Tristeza — descenso, el pozo, pena que profundiza"),
    ("⚊⚊\n⚋⚋\n⚋⚋\n⚋⚋", "Caput Draconis", "Cabeza del Dragón — comienzos, el portal se abre hacia arriba"),
    ("⚋⚋\n⚋⚋\n⚋⚋\n⚊⚊", "Cauda Draconis", "Cola del Dragón — finales, el portal drena hacia abajo"),
    ("⚊⚊\n⚊⚊\n⚋⚋\n⚊⚊", "Puella", "La Doncella — belleza, receptividad, Venus sonríe"),
    ("⚋⚋\n⚊⚊\n⚊⚊\n⚋⚋", "Puer", "El Muchacho — agresión, impulso, Marte carga"),
    ("⚊⚊\n⚋⚋\n⚊⚊\n⚊⚊", "Rubeus", "El Rojo — pasión, peligro, sangre en la arena"),
    ("⚋⚋\n⚊⚊\n⚋⚋\n⚋⚋", "Albus", "El Blanco — sabiduría, claridad, el sabio habla"),
]

# Wu Xing chino (五行) — Cinco Fases con ciclos productivo/destructivo
WU_XING = [
    ("木 Mù", "Madera", "🌳", "Crecimiento, flexibilidad, el bambú que se dobla", "alimenta al Fuego", "domina la Tierra"),
    ("火 Huǒ", "Fuego", "🔥", "Pasión, brillo, la fragua de la creación", "alimenta la Tierra", "domina el Metal"),
    ("土 Tǔ", "Tierra", "🏔️", "Estabilidad, nutrición, la madre de diez mil cosas", "alimenta el Metal", "domina el Agua"),
    ("金 Jīn", "Metal", "⚔️", "Precisión, duelo, la hoja que discierne", "alimenta el Agua", "domina la Madera"),
    ("水 Shuǐ", "Agua", "🌊", "Sabiduría, miedo, el abismo que refleja", "alimenta la Madera", "domina el Fuego"),
]

# Chakras hindúes
CHAKRAS = [
    ("Muladhara", "मूलाधार", "🔴", "Raíz — supervivencia, tierra, YO SOY"),
    ("Svadhisthana", "स्वाधिष्ठान", "🟠", "Sacro — placer, agua, YO SIENTO"),
    ("Manipura", "मणिपूर", "🟡", "Plexo solar — poder, fuego, YO ACTÚO"),
    ("Anahata", "अनाहत", "🟢", "Corazón — amor, aire, YO AMO"),
    ("Vishuddha", "विशुद्ध", "🔵", "Garganta — verdad, éter, YO HABLO"),
    ("Ajna", "आज्ञा", "🟣", "Tercer ojo — intuición, luz, YO VEO"),
    ("Sahasrara", "सहस्रार", "⚪", "Corona — consciencia, pensamiento, YO COMPRENDO"),
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
    for label, card in zip(["Pasado", "Presente", "Futuro"], cards):
        emoji = TAROT_EMOJIS.get(card, "🎴")
        lines.append(f"{label}: {emoji} {card}")
    return "\n".join(lines)


def generate_iching(run_date: str, sign: str) -> str:
    """Generate an I Ching hexagram (two trigrams)."""
    rng = random.Random(_seed(run_date, sign) + 42)
    upper = rng.choice(TRIGRAMS)
    lower = rng.choice(TRIGRAMS)
    return f"{upper}{lower} — {TRIGRAM_NAMES[upper]} sobre {TRIGRAM_NAMES[lower]}"


def calculate_moon_phase(run_date: str) -> str:
    """Calculate actual moon phase for the date."""
    d = ephem.Date(run_date)
    moon = ephem.Moon(d)
    phase_pct = moon.phase

    if phase_pct < 2:
        name, emoji = "Luna Nueva", "🌑"
    elif phase_pct < 25:
        name, emoji = "Creciente", "🌒"
    elif phase_pct < 48:
        name, emoji = "Cuarto Creciente", "🌓"
    elif phase_pct < 75:
        name, emoji = "Gibosa Creciente", "🌔"
    elif phase_pct < 98:
        name, emoji = "Luna Llena", "🌕"
    elif phase_pct < 100:
        name, emoji = "Gibosa Menguante", "🌖"
    else:
        name, emoji = "Luna Llena", "🌕"

    # Refine waning
    # ephem.phase goes 0 (new) -> 100 (full) -> 0 (new)
    # We need to check if moon is waxing or waning
    prev_day = ephem.Date(d - 1)
    prev_moon = ephem.Moon(prev_day)
    if prev_moon.phase > phase_pct and phase_pct > 50:
        if phase_pct > 75:
            name, emoji = "Gibosa Menguante", "🌖"
        elif phase_pct > 48:
            name, emoji = "Cuarto Menguante", "🌗"
        else:
            name, emoji = "Menguante", "🌘"

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
        1: "🔱 Nuevos comienzos, independencia, fuerza bruta",
        2: "☯️ Dualidad, alianza, equilibrio oculto",
        3: "🔺 Creación, expresión, comedia cósmica",
        4: "🧱 Estructura, cimientos, tierra obstinada",
        5: "🌀 Cambio, libertad, caos hermoso",
        6: "💝 Armonía, responsabilidad, la carga del amante",
        7: "👁️ Misterio, introspección, el abismo devuelve la mirada",
        8: "♾️ Poder, infinito, bucles kármicos",
        9: "🔮 Culminación, sabiduría, el final que es un principio",
        11: "⚡ Iluminación Maestra — el camino del rayo",
        22: "🏗️ Constructor Maestro — arquitecto de sueños imposibles",
        33: "🌟 Maestro de Maestros — el profesor cósmico está en clase",
    }
    return f"Vibración {total}: {meanings.get(total, '🎲 Resonancia desconocida')}"


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
        f"Físico:      [{bar(physical)}] {physical:+.2f}\n"
        f"Emocional:   [{bar(emotional)}] {emotional:+.2f}\n"
        f"Intelectual: [{bar(intellectual)}] {intellectual:+.2f}"
    )


def generate_element_color(run_date: str, sign: str) -> str:
    """Random element and color assignment."""
    rng = random.Random(_seed(run_date, sign) + 777)
    element = rng.choice(ELEMENTS)
    color = rng.choice(COLORS)
    return f"Elemento: {element} | Color: {color}"


def generate_chaos_rating(run_date: str, sign: str) -> str:
    """A totally meaningless chaos coefficient."""
    rng = random.Random(_seed(run_date, sign) + 1337)
    chaos = rng.gauss(50, 20)
    chaos = max(0, min(100, chaos))

    if chaos > 90:
        desc = "ENTROPÍA MÁXIMA 🌪️💥"
    elif chaos > 70:
        desc = "Aguas turbulentas por delante 🌊"
    elif chaos > 50:
        desc = "Interferencia cósmica moderada 🌀"
    elif chaos > 30:
        desc = "Calma relativa en el vacío 🕊️"
    else:
        desc = "Sospechosamente pacífico... 😐"

    return f"Coeficiente de caos: {chaos:.1f}% — {desc}"


def generate_rune_cast(run_date: str, sign: str) -> str:
    """Cast 3 Elder Futhark runes (situation, challenge, outcome)."""
    rng = random.Random(_seed(run_date, sign) + 2718)
    drawn = rng.sample(RUNES, 3)
    labels = ["Situación", "Desafío", "Resultado"]
    lines = []
    for label, (glyph, name, meaning) in zip(labels, drawn):
        # 20% chance of reversed (merkstave)
        reversed_str = " ᛭INVERTIDA᛭" if rng.random() < 0.2 else ""
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
        f"Odù principal: {name1} — {meaning1}\n"
        f"Odù testigo: {name2} — {meaning2}"
    )


def generate_ogham(run_date: str, sign: str) -> str:
    """Draw an Ogham few (Celtic tree oracle)."""
    rng = random.Random(_seed(run_date, sign) + 3141)
    drawn = rng.sample(OGHAM, 2)
    glyph1, name1, meaning1 = drawn[0]
    glyph2, name2, meaning2 = drawn[1]
    return (
        f"Cimiento:    {glyph1} {name1} — {meaning1}\n"
        f"Crecimiento: {glyph2} {name2} — {meaning2}"
    )


def generate_geomancy(run_date: str, sign: str) -> str:
    """Cast an Arabic geomantic figure (Raml / Ilm al-Raml)."""
    rng = random.Random(_seed(run_date, sign) + 1001)
    figure, name, meaning = rng.choice(GEOMANCY)
    house = rng.randint(1, 12)  # Geomantic house (like astrological houses)
    house_meanings = {
        1: "Yo", 2: "Riqueza", 3: "Hermanos", 4: "Hogar",
        5: "Placer", 6: "Salud", 7: "Pareja", 8: "Muerte/Renacimiento",
        9: "Viajes", 10: "Carrera", 11: "Esperanzas", 12: "Enemigos ocultos",
    }
    return f"🏜️ {name} en Casa {house} ({house_meanings[house]})\n{meaning}"


def generate_wu_xing(run_date: str, sign: str) -> str:
    """Determine the dominant Wu Xing (五行) phase and its cycle position."""
    rng = random.Random(_seed(run_date, sign) + 5555)
    chinese, spanish, emoji, meaning, feeds, overcomes = rng.choice(WU_XING)
    intensity = rng.choice(["creciente", "cénit", "menguante", "latente"])
    return (
        f"{emoji} {chinese} ({spanish}) — {intensity}\n"
        f"{meaning}\n"
        f"Ciclo productivo: {feeds} | Ciclo destructivo: {overcomes}"
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
    lines.append(f"\nDominante: {dominant[2]} {dominant[0]} — {dominant[3]}")
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
    print("=== Generando ruido cósmico ===\n")
    all_noise = generate_all_noise()
    for sign, noise in all_noise.items():
        print(f"\n{'='*60}")
        print(f"  {sign.upper()}")
        print(f"{'='*60}")
        for noise_type, value in noise.items():
            print(f"\n  [{noise_type}]")
            for line in value.split("\n"):
                print(f"    {line}")
