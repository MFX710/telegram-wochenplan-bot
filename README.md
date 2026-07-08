# Telegram-Wochenplan-Bot für @mfx555

Dieser Bot liest den Wochenplan aus `data/wochenplan.json` (erzeugt aus deiner
Exceltabelle `Telegram_Wochenplan_mfx555.xlsx`) und schickt automatisch zur
richtigen Uhrzeit die passende Nachricht in deine Telegram-Gruppe – jeden Tag,
jede Woche, ohne dass dein Computer laufen muss.

Er läuft komplett kostenlos über **GitHub Actions** (die Cloud-Umgebung, in der
dieser Chat gerade läuft, darf aus Sicherheitsgründen selbst keine Verbindung
zu api.telegram.org aufbauen – GitHub Actions hat diese Einschränkung nicht).

## Wie es funktioniert

- `send_signal.py` läuft alle 15 Minuten (per GitHub Actions Zeitplan).
- Es prüft: welcher Wochentag ist heute (Europe/Berlin-Zeit) und ist gerade
  eine der 8 Uhrzeiten (07:00, 10:00, 12:30, 15:00, 17:00, 19:00, 21:00, 23:00)
  fällig (±7 Minuten Toleranz)?
- Falls ja: die passende Nachricht aus dem Wochenplan wird per Telegram Bot API
  gesendet, und in `state.json` vermerkt, damit sie am selben Tag nicht doppelt
  verschickt wird.
- Die Zeitumrechnung berücksichtigt automatisch Sommer-/Winterzeit.

## Einmalige Einrichtung

### 1. GitHub-Repository erstellen

Falls du noch keinen GitHub-Account hast: kostenlos auf https://github.com
registrieren. Dann oben rechts **"+" → "New repository"**, z. B. Name
`telegram-wochenplan-bot`, Sichtbarkeit **Private** (empfohlen, da der Bot-Token
später als Secret hinterlegt wird – Secrets sind zwar auch bei public Repos
verschlüsselt und nicht einsehbar, "Private" ist aber die sichere Standardwahl).

### 2. Dateien hochladen

Lade den kompletten Ordner (den du von Claude bekommen hast) in das neue Repo:

- Einfachster Weg: auf der GitHub-Repo-Seite auf **"uploading an existing file"**
  klicken und alle Dateien/Ordner per Drag & Drop hochladen (Ordnerstruktur
  bleibt erhalten), dann **"Commit changes"**.
- Alternativ per Git: `git init`, `git add .`, `git commit -m "init"`,
  `git remote add origin <dein-repo-url>`, `git push -u origin main`.

Wichtig: die Ordnerstruktur `.github/workflows/...` muss erhalten bleiben,
sonst erkennt GitHub die Workflows nicht.

### 3. Bot-Token als Secret hinterlegen

Im Repo: **Settings → Secrets and variables → Actions → New repository secret**

- Name: `TELEGRAM_BOT_TOKEN`
- Value: dein Bot-Token von @BotFather

### 4. Chat-ID der Gruppe ermitteln

Falls du die Chat-ID deiner Gruppe noch nicht kennst:

1. Bei @BotFather: `/setprivacy` → deinen Bot auswählen → **Disable**
   (sonst sieht der Bot keine normalen Gruppennachrichten – für den späteren
   Versand deiner Wochenplan-Nachrichten ist das nicht nötig, aber für diesen
   Schritt schon).
2. Stelle sicher, dass der Bot bereits Mitglied deiner Telegram-Gruppe ist.
3. Schreibe **irgendeine** Nachricht in die Gruppe (z. B. "Test").
4. Im Repo: Tab **Actions → "Telegram Chat-ID ermitteln" → Run workflow**.
5. Nach ca. 10–20 Sekunden auf den Lauf klicken → Log öffnen → dort steht z. B.:
   ```
   chat_id = -1001234567890   type = supergroup   title/name = mfx555 Trading Signale
   ```
6. Diese Zahl (inkl. Minuszeichen) kopieren.

### 5. Chat-ID als Secret hinterlegen

Wieder **Settings → Secrets and variables → Actions → New repository secret**

- Name: `TELEGRAM_CHAT_ID`
- Value: die gefundene Zahl, z. B. `-1001234567890`

### 6. Testen

Tab **Actions → "Telegram Wochenplan senden" → Run workflow** manuell
ausführen. Im Log siehst du entweder "Kein fälliger Slot ... Nichts zu tun"
(wenn gerade keine der 8 Uhrzeiten in der Nähe ist) oder eine gesendete
Testnachricht in der Gruppe.

Zum risikofreien Testen ohne echten Versand kannst du im Workflow
`send_signals.yml` vorübergehend `DRY_RUN: "1"` als zusätzliche `env`-Variable
setzen – dann wird die Nachricht nur im Log ausgegeben, nicht wirklich
verschickt.

Ab jetzt läuft alles automatisch. Du musst nichts mehr tun.

## Wochenplan später ändern

1. `data/Telegram_Wochenplan_mfx555.xlsx` bearbeiten (Spalten: Tag, Uhrzeit,
   Slot, Text – Tag in Großbuchstaben wie `MONTAG`, Uhrzeit im Format `HH:MM`).
2. Lokal `pip install openpyxl` und dann `python regenerate_json.py` ausführen
   – das erzeugt `data/wochenplan.json` neu.
3. Beide Dateien (`.xlsx` und `.json`) committen und pushen (oder einfach
   `wochenplan.json` direkt über die GitHub-Weboberfläche bearbeiten, wenn dir
   das JSON-Format nicht zu unhandlich ist).

Neue Uhrzeiten außerhalb der bestehenden 8 Slots funktionieren ebenfalls –
das Skript liest die Uhrzeiten direkt aus der JSON-Datei, es gibt keine feste
Liste im Code.

## Kosten

GitHub Actions ist für private Repos im Free-Plan mit 2.000 Minuten/Monat
kostenlos. Ein Lauf dieses Bots dauert ca. 10–15 Sekunden, alle 15 Minuten,
also ca. 96 Läufe/Tag × 15 Sek ≈ 24 Minuten/Tag ≈ 720 Minuten/Monat – das
passt bequem in den kostenlosen Rahmen.

## Sicherheit

- Der Bot-Token liegt ausschließlich als verschlüsseltes GitHub-Secret vor,
  nicht im Klartext im Code.
- Gib den Token niemals in öffentlichen Repos, Screenshots oder Chats weiter.
  Falls er doch mal versehentlich sichtbar wird: bei @BotFather mit
  `/revoke` bzw. `/token` einen neuen Token generieren und das Secret
  aktualisieren.

## Fehlersuche

- **Keine Nachrichten kommen an:** Tab Actions → letzten Lauf von
  "Telegram Wochenplan senden" öffnen → Log lesen. Häufigste Ursachen:
  Secrets falsch benannt/leer, Bot wurde aus der Gruppe entfernt, Bot darf in
  der Gruppe keine Nachrichten schreiben (Gruppeneinstellungen prüfen).
- **"Telegram API Fehler 403":** Bot wurde blockiert/aus der Gruppe entfernt,
  oder Chat-ID stimmt nicht mehr.
- **Nachricht kommt doppelt/gar nicht zur exakten Minute:** ist normal –
  GitHub Actions Cron-Zeitpläne sind nicht auf die Sekunde/Minute exakt
  (können je nach Auslastung ein paar Minuten später laufen), daher das
  ±7-Minuten-Toleranzfenster im Skript.
