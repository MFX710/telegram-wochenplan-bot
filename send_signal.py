#!/usr/bin/env python3
"""
Sendet die zur aktuellen Uhrzeit (Europe/Berlin) und zum aktuellen Wochentag
passende Nachricht aus data/wochenplan.json an die konfigurierte Telegram-Gruppe.

Gedacht zum Aufruf durch GitHub Actions (siehe .github/workflows/send_signals.yml),
alle 15 Minuten. Das Skript selbst entscheidet anhand der Uhrzeit, ob gerade ein
Slot "fällig" ist (Toleranzfenster), und verhindert über eine Statusdatei
(state.json, wird per actions/cache zwischengespeichert), dass eine Nachricht
zweimal am selben Tag verschickt wird.

Benötigte Umgebungsvariablen:
    TELEGRAM_BOT_TOKEN  - Bot-Token von @BotFather
    TELEGRAM_CHAT_ID    - Chat-ID der Zielgruppe (siehe find_chat_id.py)

Optional:
    TOLERANCE_MINUTES   - wie viele Minuten Toleranz um die Soll-Uhrzeit (Default 7)
    STATE_FILE          - Pfad zur Statusdatei (Default state.json)
    DRY_RUN             - "1" = nicht wirklich senden, nur anzeigen was gesendet würde
"""
import json
import os
import sys
from datetime import datetime, date, time
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
    h, m = s.strip().split(":")
    return time(int(h), int(m))


def minutes_diff(t1, t2):
    """Absolute Differenz in Minuten zwischen zwei time-Objekten (gleicher Tag)."""
    d1 = t1.hour * 60 + t1.minute
    d2 = t2.hour * 60 + t2.minute
    return abs(d1 - d2)


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
    tolerance = int(os.environ.get("TOLERANCE_MINUTES", "7"))
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

    candidates = [row for row in plan if row["tag"] == weekday_name]

    best = None
    best_diff = None
    for row in candidates:
        slot_time = parse_hhmm(row["uhrzeit"])
        diff = minutes_diff(now.time(), slot_time)
        if diff <= tolerance:
            dedup_key = f"{today_key}_{weekday_name}_{row['uhrzeit']}"
            if dedup_key in state:
                continue
            if best_diff is None or diff < best_diff:
                best = row
                best_diff = diff
                best_key = dedup_key

    if best is None:
        print(f"[{now.isoformat()}] Kein fälliger Slot für {weekday_name} (Toleranz {tolerance} Min). Nichts zu tun.")
        return

    print(f"[{now.isoformat()}] Sende Slot {weekday_name} {best['uhrzeit']} ({best['slot']}) ...")

    if dry_run:
        print("DRY_RUN=1 -> Nachricht wird NICHT gesendet. Inhalt:\n" + best["text"])
    else:
        send_telegram_message(token, chat_id, best["text"])
        print("Nachricht erfolgreich gesendet.")

    state[best_key] = now.isoformat()
    save_state(state_path, state)


if __name__ == "__main__":
    main()
