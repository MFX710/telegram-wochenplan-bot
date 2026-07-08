#!/usr/bin/env python3
"""
Sendet die zur aktuellen Uhrzeit (Europe/Berlin) und zum aktuellen Wochentag
passende Nachricht aus data/wochenplan.json an die konfigurierte Telegram-Gruppe.

Logik: Eine Nachricht wird gesendet, sobald ihre Uhrzeit erreicht/überschritten
ist - auch verspätet (bis LATE_MINUTES danach), aber nie zu früh und nie doppelt
(Statusdatei state.json). Das macht den Bot robust gegen verspätete
GitHub-Actions-Zeitpläne.

Benötigte Umgebungsvariablen:
    TELEGRAM_BOT_TOKEN  - Bot-Token von @BotFather
    TELEGRAM_CHAT_ID    - Chat-ID der Zielgruppe (siehe find_chat_id.py)

Optional:
    LATE_MINUTES        - wie viele Minuten nach der Soll-Uhrzeit noch gesendet wird (Default 60)
    STATE_FILE          - Pfad zur Statusdatei (Default state.json)
    DRY_RUN             - "1" = nicht wirklich senden, nur anzeigen was gesendet würde
"""
import json
import os
import sys
from datetime import datetime, time
from zoneinfo import ZoneInfo

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLAN_FILE = os.path.join(BASE_DIR, "data", "wochenplan.json")

GERMAN_WEEKDAYS = [
    "MONTAG", "DIENSTAG", "MITTWOCH", "DONNERSTAG",
    "FREITAG", "SAMSTAG", "SONNTAG",
]


def load_plan():
    with open(PLAN_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_state(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def save_state(path, state):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def parse_hhmm(s):
    parts = str(s).strip().split(":")
    if len(parts) < 2:
        raise ValueError(f"Ungültiges Uhrzeit-Format: {s!r}")
    return time(int(parts[0]), int(parts[1]))


def minutes_since(now_t, slot_t):
    """Minuten seit der Slot-Zeit (negativ = Slot liegt noch in der Zukunft)."""
    return (now_t.hour * 60 + now_t.minute) - (slot_t.hour * 60 + slot_t.minute)


def send_telegram_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=20,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Telegram API Fehler {resp.status_code}: {resp.text}")
    return resp.json()


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    dry_run = os.environ.get("DRY_RUN") == "1"
    late_minutes = int(os.environ.get("LATE_MINUTES", "60"))
    state_path = os.environ.get("STATE_FILE", os.path.join(BASE_DIR, "state.json"))

    if not token or not chat_id:
        print("FEHLER: TELEGRAM_BOT_TOKEN und/oder TELEGRAM_CHAT_ID nicht gesetzt.", file=sys.stderr)
        sys.exit(1)

    plan = load_plan()
    now = datetime.now(ZoneInfo("Europe/Berlin"))
    today_key = now.date().isoformat()
    weekday_name = GERMAN_WEEKDAYS[now.weekday()]

    state = load_state(state_path)
    # alte Tage aus dem State entfernen, damit die Datei nicht unbegrenzt wächst
    state = {k: v for k, v in state.items() if k.startswith(today_key)}

    due = []
    for row in plan:
        if row["tag"] != weekday_name:
            continue
        try:
            slot_time = parse_hhmm(row["uhrzeit"])
        except Exception as e:
            print(f"WARNUNG: ungültige Uhrzeit {row.get('uhrzeit')!r} bei {row.get('tag')} "
                  f"({row.get('slot')}) - Zeile wird übersprungen: {e}")
            continue

        delay = minutes_since(now.time(), slot_time)
        if 0 <= delay <= late_minutes:
            dedup_key = f"{today_key}_{weekday_name}_{row['uhrzeit']}"
            if dedup_key in state:
                continue
            due.append((slot_time, dedup_key, row))

    if not due:
        print(f"[{now.isoformat()}] Kein fälliger Slot für {weekday_name}. Nichts zu tun.")
        return

    # Falls mehrere Slots offen sind (z. B. nach längerem Ausfall): in zeitlicher
    # Reihenfolge alle nachsenden.
    due.sort(key=lambda x: (x[0].hour, x[0].minute))
    for slot_time, dedup_key, row in due:
        print(f"[{now.isoformat()}] Sende Slot {weekday_name} {row['uhrzeit']} ({row['slot']}) ...")
        if dry_run:
            print("DRY_RUN=1 -> Nachricht wird NICHT gesendet. Inhalt:\n" + row["text"])
        else:
            send_telegram_message(token, chat_id, row["text"])
            print("Nachricht erfolgreich gesendet.")
        state[dedup_key] = now.isoformat()
        save_state(state_path, state)


if __name__ == "__main__":
    main()
