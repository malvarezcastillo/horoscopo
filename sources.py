#!/usr/bin/env python3
"""Scrape horoscopes from 13 sources in multiple languages.

Each source is a function that returns {sign: text} or raises on failure.
Sources are best-effort — failures are logged and skipped.
"""
import asyncio
import sys
from datetime import date

import httpx
from bs4 import BeautifulSoup

from db import SIGNS, get_db, store_raw

# Sign mappings per source (some sites use different names/IDs)
SIGN_IDS_EN = {
    "aries": 1, "taurus": 2, "gemini": 3, "cancer": 4, "leo": 5, "virgo": 6,
    "libra": 7, "scorpio": 8, "sagittarius": 9, "capricorn": 10, "aquarius": 11, "pisces": 12,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
}


# ---------------------------------------------------------------------------
# Source definitions
# ---------------------------------------------------------------------------

async def horoscope_com(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """English — horoscope.com"""
    results = {}
    for sign, sid in SIGN_IDS_EN.items():
        r = await client.get(f"https://www.horoscope.com/us/horoscopes/general/horoscope-general-daily-today.aspx?sign={sid}")
        soup = BeautifulSoup(r.text, "lxml")
        p = soup.select_one("div.main-horoscope p")
        if p:
            # Remove the <strong> date tag
            for strong in p.find_all("strong"):
                strong.decompose()
            results[sign] = p.get_text(strip=True)
    return "horoscope.com", "en", results


async def astrosage_com(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """Hindi/English — astrosage.com"""
    results = {}
    for sign in SIGNS:
        r = await client.get(f"https://www.astrosage.com/horoscope/daily-{sign}-horoscope.asp")
        soup = BeautifulSoup(r.text, "lxml")
        div = soup.select_one("div.ui-large-content.text-justify")
        if div:
            results[sign] = div.get_text(strip=True)
    return "astrosage.com", "en-in", results


async def elle_horoscope_fr(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """French — elle.fr"""
    sign_map = {
        "aries": "belier", "taurus": "taureau", "gemini": "gemeaux", "cancer": "cancer",
        "leo": "lion", "virgo": "vierge", "libra": "balance", "scorpio": "scorpion",
        "sagittarius": "sagittaire", "capricorn": "capricorne", "aquarius": "verseau", "pisces": "poissons",
    }
    results = {}
    for sign, fr_name in sign_map.items():
        r = await client.get(f"https://www.elle.fr/Astro/Horoscope/Quotidien/{fr_name}")
        soup = BeautifulSoup(r.text, "lxml")
        zone = soup.select_one("div.zone-resultat")
        if zone:
            paragraphs = zone.select("p")
            texts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
            if texts:
                results[sign] = " ".join(texts)
    return "elle.fr", "fr", results


async def sunsigns_com(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """English — sunsigns.com"""
    results = {}
    for sign in SIGNS:
        r = await client.get(f"https://www.sunsigns.com/horoscopes/daily/{sign}")
        soup = BeautifulSoup(r.text, "lxml")
        content = soup.select_one("div.horoscope-content > p")
        if content:
            results[sign] = content.get_text(strip=True)
    return "sunsigns.com", "en", results


async def oroscopo_it(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """Italian — oroscopo.it"""
    sign_map = {
        "aries": "ariete", "taurus": "toro", "gemini": "gemelli", "cancer": "cancro",
        "leo": "leone", "virgo": "vergine", "libra": "bilancia", "scorpio": "scorpione",
        "sagittarius": "sagittario", "capricorn": "capricorno", "aquarius": "acquario", "pisces": "pesci",
    }
    results = {}
    for sign, it_name in sign_map.items():
        r = await client.get(f"https://www.oroscopo.it/oroscopo-del-giorno/{it_name}/")
        soup = BeautifulSoup(r.text, "lxml")
        content = soup.select_one("div.entry-content p") or soup.select_one("article p")
        if content:
            results[sign] = content.get_text(strip=True)
    return "oroscopo.it", "it", results


async def horoscopo_negro_com(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """Spanish (snarky) — horoscoponegro.com (blog listing, grabs latest post)"""
    sign_map = {
        "aries": "aries", "taurus": "tauro", "gemini": "geminis", "cancer": "cancer",
        "leo": "leo", "virgo": "virgo", "libra": "libra", "scorpio": "escorpio",
        "sagittarius": "sagitario", "capricorn": "capricornio", "aquarius": "acuario", "pisces": "piscis",
    }
    results = {}
    for sign, es_name in sign_map.items():
        r = await client.get(f"https://www.horoscoponegro.com/{es_name}/")
        soup = BeautifulSoup(r.text, "lxml")
        content = soup.select_one(".et_pb_blog_0_tb_body article .post-content")
        if content:
            results[sign] = content.get_text(strip=True)
    return "horoscoponegro.com", "es-dark", results


async def zodiacsign_com(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """English — zodiacsign.com (formerly astrology-zodiac-signs.com)"""
    results = {}
    for sign in SIGNS:
        r = await client.get(f"https://www.zodiacsign.com/horoscope/{sign}/daily/")
        soup = BeautifulSoup(r.text, "lxml")
        div = soup.select_one("div.horo_des_d")
        if div:
            paragraphs = div.select("p")
            texts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
            if texts:
                results[sign] = " ".join(texts)
    return "zodiacsign.com", "en", results


async def ganeshaspeaks_com(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """English (India) — ganeshaspeaks.com"""
    results = {}
    for sign in SIGNS:
        r = await client.get(f"https://www.ganeshaspeaks.com/horoscopes/daily-horoscope/{sign}/")
        soup = BeautifulSoup(r.text, "lxml")
        div = soup.select_one("div.horoscope-content")
        if div:
            for p in div.find_all("p"):
                txt = p.get_text(strip=True)
                if len(txt) > 50 and "horoscope-strip" not in (p.get("class") or []):
                    results[sign] = txt
                    break
    return "ganeshaspeaks.com", "en-in", results


async def astrostyle_com(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """English — astrostyle.com"""
    results = {}
    for sign in SIGNS:
        r = await client.get(f"https://astrostyle.com/horoscopes/daily/{sign}/")
        soup = BeautifulSoup(r.text, "lxml")
        div = soup.select_one("div.horoscope-content")
        if div:
            # Text is in first direct div child with substantial content
            for child in div.find_all("div", recursive=False):
                txt = child.get_text(strip=True)
                if len(txt) > 80:
                    results[sign] = txt
                    break
    return "astrostyle.com", "en", results


async def personare_br(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """Brazilian Portuguese — personare.com.br"""
    sign_map = {
        "aries": "aries", "taurus": "touro", "gemini": "gemeos", "cancer": "cancer",
        "leo": "leao", "virgo": "virgem", "libra": "libra", "scorpio": "escorpiao",
        "sagittarius": "sagitario", "capricorn": "capricornio", "aquarius": "aquario", "pisces": "peixes",
    }
    results = {}
    for sign, br_name in sign_map.items():
        r = await client.get(f"https://www.personare.com.br/horoscopo-do-dia/{br_name}")
        soup = BeautifulSoup(r.text, "lxml")
        paragraphs = soup.select("p.font-claude-response-body")
        texts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
        if texts:
            results[sign] = " ".join(texts)
    return "personare.com.br", "pt-br", results


async def astroyogi_com(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """English (India) — astroyogi.com"""
    results = {}
    for sign in SIGNS:
        r = await client.get(f"https://www.astroyogi.com/horoscopes/daily/{sign}-free-horoscope.aspx")
        soup = BeautifulSoup(r.text, "lxml")
        content = soup.select_one("div.content-page > p")
        if content:
            results[sign] = content.get_text(strip=True)
    return "astroyogi.com", "en-in", results


async def horo_mail_ru(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """Russian — horo.mail.ru"""
    results = {}
    for sign in SIGNS:
        r = await client.get(f"https://horo.mail.ru/prediction/{sign}/today/")
        soup = BeautifulSoup(r.text, "lxml")
        section = soup.select_one("section.js-media-stat-article")
        if section:
            p = section.select_one("p")
            if p:
                results[sign] = p.get_text(strip=True)
    return "horo.mail.ru", "ru", results


async def huffpost_horoscopes(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """English — huffpost.com"""
    results = {}
    for sign in SIGNS:
        r = await client.get(f"https://www.huffpost.com/horoscopes/{sign}")
        soup = BeautifulSoup(r.text, "lxml")
        content = soup.select_one("div.sign-day__text")
        if content:
            results[sign] = content.get_text(strip=True)
    return "huffpost.com", "en", results


# ---------------------------------------------------------------------------
# Non-Western sources
# ---------------------------------------------------------------------------

async def elabraj_ar(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """Arabic — elabraj.net (ابراج اليوم)"""
    results = {}
    for sign, sid in SIGN_IDS_EN.items():
        r = await client.get(f"https://www.elabraj.net/ar/horoscope/daily/{sid}")
        soup = BeautifulSoup(r.text, "lxml")
        content = soup.select_one("div.horoscope-daily-text")
        if content:
            results[sign] = content.get_text(strip=True)[:500]
    return "elabraj.net", "ar", results


async def arabhaz_ar(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """Arabic — arabhaz.com"""
    results = {}
    for sign in SIGNS:
        r = await client.get(f"https://arabhaz.com/wp/zodiac/{sign}/")
        soup = BeautifulSoup(r.text, "lxml")
        p = soup.select_one("div.card-body p")
        if p:
            results[sign] = p.get_text(strip=True)
    return "arabhaz.com", "ar", results


async def hurriyet_tr(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """Turkish — hurriyet.com.tr"""
    sign_map = {
        "aries": "koc", "taurus": "boga", "gemini": "ikizler", "cancer": "yengec",
        "leo": "aslan", "virgo": "basak", "libra": "terazi", "scorpio": "akrep",
        "sagittarius": "yay", "capricorn": "oglak", "aquarius": "kova", "pisces": "balik",
    }
    results = {}
    for sign, tr_name in sign_map.items():
        r = await client.get(f"https://www.hurriyet.com.tr/mahmure/astroloji/{tr_name}-burcu/")
        soup = BeautifulSoup(r.text, "lxml")
        content = soup.select_one("div.horoscope-detail-tab-content p")
        if content:
            # Skip first p if it's just author name
            ps = soup.select("div.horoscope-detail-tab-content p")
            for p in ps:
                txt = p.get_text(strip=True)
                if len(txt) > 50:
                    results[sign] = txt
                    break
    return "hurriyet.com.tr", "tr", results


async def xzw_cn(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """Chinese — xzw.com (星座屋)"""
    results = {}
    for sign in SIGNS:
        r = await client.get(f"https://www.xzw.com/fortune/{sign}/")
        soup = BeautifulSoup(r.text, "lxml")
        ps = soup.select(".c_cont p")
        texts = [p.get_text(strip=True) for p in ps if p.get_text(strip=True)]
        if texts:
            results[sign] = " ".join(texts)[:500]
    return "xzw.com", "zh", results


async def cainer_jp(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """Japanese — cainer.jp"""
    results = {}
    for sign in SIGNS:
        r = await client.get(f"https://www.cainer.jp/daily/{sign}/")
        soup = BeautifulSoup(r.text, "lxml")
        content = soup.select_one("div.constellation-result__box-content-body")
        if content:
            results[sign] = content.get_text(strip=True)[:500]
    return "cainer.jp", "ja", results


async def naver_ko(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """Korean — Naver search (운세)"""
    sign_map = {
        "aries": "양자리", "taurus": "황소자리", "gemini": "쌍둥이자리", "cancer": "게자리",
        "leo": "사자자리", "virgo": "처녀자리", "libra": "천칭자리", "scorpio": "전갈자리",
        "sagittarius": "사수자리", "capricorn": "염소자리", "aquarius": "물병자리", "pisces": "물고기자리",
    }
    results = {}
    for sign, ko_name in sign_map.items():
        import urllib.parse
        query = urllib.parse.quote(f"{ko_name} 오늘 운세")
        r = await client.get(f"https://search.naver.com/search.naver?where=nexearch&query={query}")
        soup = BeautifulSoup(r.text, "lxml")
        content = soup.select_one("p.text._cs_fortune_text")
        if content:
            results[sign] = content.get_text(strip=True)[:500]
    return "naver.com", "ko", results


async def thairath_th(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """Thai — thairath.co.th (ดวงรายสัปดาห์)"""
    results = {}
    for sign in SIGNS:
        r = await client.get(f"https://www.thairath.co.th/horoscope/weekly_zodiac/{sign}")
        soup = BeautifulSoup(r.text, "lxml")
        ps = soup.select("div.__TROL_horo_subzodiac_highlight_detail p")
        texts = [p.get_text(strip=True) for p in ps if p.get_text(strip=True)]
        if texts:
            results[sign] = " ".join(texts)[:500]
    return "thairath.co.th", "th", results


async def ngaydep_vi(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """Vietnamese — ngaydep.com (tử vi hôm nay)"""
    sign_map = {
        "aries": "bach-duong", "taurus": "kim-nguu", "gemini": "song-tu", "cancer": "cu-giai",
        "leo": "su-tu", "virgo": "xu-nu", "libra": "thien-binh", "scorpio": "bo-cap",
        "sagittarius": "nhan-ma", "capricorn": "ma-ket", "aquarius": "bao-binh", "pisces": "song-ngu",
    }
    results = {}
    for sign, vi_name in sign_map.items():
        r = await client.get(f"https://ngaydep.com/tu-vi-hom-nay-va-ngay-mai-cung-{vi_name}.html")
        soup = BeautifulSoup(r.text, "lxml")
        div = soup.select_one("div._bdtuvi")
        if div:
            p = div.select_one("p")
            if p:
                results[sign] = p.get_text(strip=True)[:500]
    return "ngaydep.com", "vi", results


async def livehindustan_hi(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """Hindi — livehindustan.com (राशिफल)"""
    import json as _json
    rashi_keys = {
        "aries": "rashiAries", "taurus": "rashiTaurus", "gemini": "rashiGemini",
        "cancer": "rashiCancer", "leo": "rashiLeo", "virgo": "rashiVirgo",
        "libra": "rashiLibra", "scorpio": "rashiScorpio", "sagittarius": "rashiSagittarius",
        "capricorn": "rashiCapricorn", "aquarius": "rashiAquarius", "pisces": "rashiPisces",
    }
    results = {}
    # All signs are in a single page response
    r = await client.get("https://www.livehindustan.com/astrology/rashifal/aries")
    soup = BeautifulSoup(r.text, "lxml")
    script = soup.select_one("script#__NEXT_DATA__")
    if script:
        try:
            data = _json.loads(script.string)
            rashi_data = data.get("props", {}).get("pageProps", {}).get("rashiData", {})
            for sign, key in rashi_keys.items():
                text = rashi_data.get(key, "")
                if text and len(text) > 10:
                    # Strip HTML tags if any
                    s = BeautifulSoup(text, "lxml")
                    results[sign] = s.get_text(strip=True)[:500]
        except (ValueError, KeyError):
            pass
    return "livehindustan.com", "hi", results


async def myastro_gr(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """Greek — myastro.gr (ζώδια σήμερα)"""
    sign_map = {
        "aries": "krios", "taurus": "tavros", "gemini": "didimoi", "cancer": "karkinos",
        "leo": "leon", "virgo": "parthenos", "libra": "zigros", "scorpio": "skorpios",
        "sagittarius": "toxotis", "capricorn": "egokeros", "aquarius": "idrohoos", "pisces": "ihthis",
    }
    results = {}
    for sign, gr_name in sign_map.items():
        r = await client.get(f"https://www.myastro.gr/zodia/zodia-simera/{gr_name}.html")
        soup = BeautifulSoup(r.text, "lxml")
        ps = soup.select("div.divBody > p")
        # Skip first p (intro), take subsequent ones
        texts = [p.get_text(strip=True) for p in ps[1:] if p.get_text(strip=True)]
        if texts:
            results[sign] = " ".join(texts)[:500]
    return "myastro.gr", "el", results


async def wolipop_id(client: httpx.AsyncClient) -> tuple[str, str, dict[str, str]]:
    """Indonesian — wolipop.detik.com (zodiak)"""
    results = {}
    for sign in SIGNS:
        r = await client.get(f"https://wolipop.detik.com/zodiak/{sign}")
        soup = BeautifulSoup(r.text, "lxml")
        content = soup.select_one("div.detail__body p") or soup.select_one("section.grid p")
        if content:
            results[sign] = content.get_text(strip=True)[:500]
    return "wolipop.detik.com", "id", results


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_SOURCES = [
    # Western
    horoscope_com,          # en — horoscope.com
    astrosage_com,          # en-in — astrosage.com
    elle_horoscope_fr,      # fr — elle.fr
    sunsigns_com,           # en — sunsigns.com
    oroscopo_it,            # it — oroscopo.it
    horoscopo_negro_com,    # es-dark — horoscoponegro.com
    zodiacsign_com,         # en — zodiacsign.com
    ganeshaspeaks_com,      # en-in — ganeshaspeaks.com
    astrostyle_com,         # en — astrostyle.com
    personare_br,           # pt-br — personare.com.br
    astroyogi_com,          # en-in — astroyogi.com
    horo_mail_ru,           # ru — horo.mail.ru
    huffpost_horoscopes,    # en — huffpost.com
    # Non-Western
    elabraj_ar,             # ar — elabraj.net (Arabic)
    arabhaz_ar,             # ar — arabhaz.com (Arabic)
    hurriyet_tr,            # tr — hurriyet.com.tr (Turkish)
    xzw_cn,                 # zh — xzw.com (Chinese)
    cainer_jp,              # ja — cainer.jp (Japanese)
    naver_ko,               # ko — naver.com (Korean)
    thairath_th,            # th — thairath.co.th (Thai)
    ngaydep_vi,             # vi — ngaydep.com (Vietnamese)
    livehindustan_hi,       # hi — livehindustan.com (Hindi)
    myastro_gr,             # el — myastro.gr (Greek)
    wolipop_id,             # id — wolipop.detik.com (Indonesian)
]


async def scrape_all(run_date: str | None = None) -> dict[str, int]:
    """Scrape all sources, store in DB. Returns {source_name: sign_count}."""
    run_date = run_date or date.today().isoformat()
    conn = get_db()
    stats: dict[str, int] = {}

    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=True,
        limits=httpx.Limits(max_connections=5, max_keepalive_connections=3),
    ) as client:
        tasks = [source(client) for source in ALL_SOURCES]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            print(f"  FAILED: {result.__class__.__name__}: {result}")
            continue
        source_name, lang, sign_texts = result
        count = 0
        for sign, text in sign_texts.items():
            if text and len(text.strip()) > 10:
                store_raw(conn, run_date, source_name, lang, sign, text.strip())
                count += 1
        stats[source_name] = count
        print(f"  {source_name} ({lang}): {count}/12 signs")

    conn.commit()
    conn.close()
    return stats


if __name__ == "__main__":
    print("=== Scraping horoscopes from all sources ===")
    results = asyncio.run(scrape_all())
    total = sum(results.values())
    print(f"\nTotal: {total} horoscope texts from {len(results)} sources")
