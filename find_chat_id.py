#!/usr/bin/env python3
"""
Einmalig ausführen, um die Chat-ID deiner Telegram-Gruppe herauszufinden.

Voraussetzung:
1. Der Bot wurde bereits zur Gruppe hinzugefügt.
2. Der Privacy-Modus des Bots ist deaktiviert ODER der Bot ist Admin der Gruppe
   (sonst sieht der Bot keine normalen Textnachrichten der Gruppe).
   -> Bei @BotFather: /setprivacy -> deinen Bot auswählen -> Disable
3. Direkt VOR dem Ausführen dieses Skripts: irgendeine Nachricht in der Gruppe schreiben.

Benötigte Umgebungsvariable: TELEGRAM_BOT_TOKEN
"""
import os
import sys

import requests


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("FEHLER: TELEGRAM_BOT_TOKEN nicht gesetzt.", file=sys.stderr)
        sys.exit(1)

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    if not data.get("ok"):
        print("Telegram API Fehler:", data)
        sys.exit(1)

    updates = data.get("result", [])
    if not updates:
        print(
            "Keine Updates gefunden. Hast du gerade eben eine Nachricht in der Gruppe "
            "geschrieben, NACHDEM der Bot hinzugefügt wurde und der Privacy-Modus "
            "deaktiviert ist? Dann diesen Workflow erneut ausführen."
        )
        return

    seen = {}
    for u in updates:
        msg = u.get("message") or u.get("channel_post")
        if not msg:
            continue
        chat = msg.get("chat", {})
        seen[chat.get("id")] = chat

    print("Gefundene Chats:")
    for chat_id, chat in seen.items():
        print(f"  chat_id = {chat_id}   type = {chat.get('type')}   title/name = {chat.get('title') or chat.get('first_name')}")

    print("\nTrage die passende chat_id (für deine Gruppe, meist eine negative Zahl "
          "wie -1001234567890) als GitHub-Secret TELEGRAM_CHAT_ID ein.")


if __name__ == "__main__":
    main()
