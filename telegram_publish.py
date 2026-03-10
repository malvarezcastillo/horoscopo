#!/usr/bin/env python3
"""Publish generated horoscopes to a Telegram channel via Telethon."""
import asyncio
import os
import sys
from datetime import date

from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty

from db import (
    SIGNS, SIGN_EMOJIS, SIGN_NAMES_ES,
    get_db, get_horoscopes_for_date, get_published_signs, mark_published,
)

API_ID = int(os.environ.get("TELEGRAM_API_ID", 0))
API_HASH = os.environ.get("TELEGRAM_API_HASH", "")
PHONE = os.environ.get("TELEGRAM_PHONE", "")
CHANNEL = os.environ.get("TELEGRAM_CHANNEL", "")
SESSION_FILE = os.path.join(os.path.dirname(__file__), "horoscopo_session")


def format_header(run_date: str) -> str:
    """Format the daily header message."""
    d = date.fromisoformat(run_date)
    day_names_es = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
    month_names_es = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                      "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    day_name = day_names_es[d.weekday()]
    month_name = month_names_es[d.month]

    return (
        f"{'='*30}\n"
        f"\U0001f52e HOROSCOPO FIABLE \U0001f52e\n"
        f"{day_name} {d.day} de {month_name} {d.year}\n"
        f"{'='*30}\n\n"
        f"Canalizado por ZOLTAR-9000, debris cosmico consciente desde 1058 d.C.\n"
        f"Fuentes: 24 horoscopos en 16 idiomas + runas nordicas + tarot + I Ching\n"
        f"+ nakshatras vedicos + Tzolkin maya + Ifa yoruba + Ogham celta\n"
        f"+ geomancia arabe + Wu Xing + chakras + ruido de Perlin + fase lunar\n"
        f"\u2728 Los astros han hablado. Discutieron MUCHO. \u2728"
    )


def format_sign_message(sign: str, text: str) -> str:
    """Format a single sign's horoscope message."""
    emoji = SIGN_EMOJIS[sign]
    name_es = SIGN_NAMES_ES[sign]
    return f"{emoji} {name_es.upper()} {emoji}\n\n{text}"


async def find_channel(client: TelegramClient, search: str) -> int | None:
    """Find channel by name substring."""
    dialogs = await client.get_dialogs()
    search_lower = search.lower()
    for dialog in dialogs:
        if search_lower in (dialog.name or "").lower():
            print(f"  Found channel: {dialog.name} (ID: {dialog.id})")
            return dialog.id
    return None


async def publish(run_date: str | None = None, dry_run: bool = False):
    """Publish horoscopes to Telegram channel."""
    run_date = run_date or date.today().isoformat()
    conn = get_db()

    horoscopes = get_horoscopes_for_date(conn, run_date)
    if not horoscopes:
        print("No horoscopes generated for today. Run diviner.py first.")
        return 0

    already_published = get_published_signs(conn, run_date)
    to_publish = [s for s in SIGNS if s in horoscopes and s not in already_published]

    if not to_publish:
        print("All signs already published for today.")
        return 0

    if dry_run:
        print(f"=== DRY RUN — Would publish {len(to_publish)} signs ===")
        header = format_header(run_date)
        print(f"\n{header}\n")
        for sign in to_publish:
            msg = format_sign_message(sign, horoscopes[sign])
            print(f"\n{msg}\n{'—'*40}")
        return len(to_publish)

    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.start(phone=PHONE)

    # Find channel
    channel = CHANNEL
    if not channel.lstrip("-").isdigit():
        # It's a name, search for it
        channel_id = await find_channel(client, channel)
        if channel_id is None:
            print(f"Could not find channel matching '{channel}'")
            await client.disconnect()
            return 0
        channel = channel_id

    target = int(channel) if isinstance(channel, str) else channel

    # Post header if this is the first publish of the day
    if not already_published:
        header = format_header(run_date)
        await client.send_message(target, header)
        await asyncio.sleep(1)

    # Post each sign
    published = 0
    for sign in to_publish:
        msg = format_sign_message(sign, horoscopes[sign])
        sent = await client.send_message(target, msg)
        mark_published(conn, run_date, sign, sent.id)
        conn.commit()
        published += 1
        print(f"  Published {SIGN_EMOJIS[sign]} {sign}")
        await asyncio.sleep(0.5)  # Rate limit

    conn.close()
    await client.disconnect()
    return published


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    count = asyncio.run(publish(dry_run=dry))
    print(f"\nPublished {count} horoscopes")
