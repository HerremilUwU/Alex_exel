from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
import sys
# === ✅ Konfiguration laden (aus externem Ordner) ===
CONFIG_DIR = "C:\\Users\\gamin\\OneDrive\\Dokumente"
if CONFIG_DIR not in sys.path:
    sys.path.append(CONFIG_DIR)

try:
    import config_alex # pyright: ignore[reportMissingImports]
except ImportError:
    print("❌ Konfigurationsdatei 'config_alex.py' nicht gefunden!")
    exit()

# === 🎯 Konfigvariablen verwenden ===
RIOT_API = config_alex.RIOT_API
puuid = config_alex.puuid
region_full = config_alex.region_full

# === 🛡️ Pfad zur Service-Account-JSON-Datei ===
SERVICE_ACCOUNT_FILE = 'C:\\Users\\gamin\\Downloads\\lol-match-stats-59320eae7a21.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Spreadsheet-ID & Ziel-Tabellenblatt
SPREADSHEET_ID = '1vahfeW44czKpTnO5scZZZmIm-sgWObMFs16Y-py2MO0'
RANGE_NAME = "Tabellenblatt1!A1"


# Google Sheets Dienst starten
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()

# Beispiel: Matchdaten aus Datei laden (vorher gespeichert)
with open("match_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Nur Spielername, Champion und KDA extrahieren als Beispiel
values = [["Summoner", "Champion", "Kills", "Deaths", "Assists"]]  # Header

for match in data:
    for player in match['info']['participants']:
        if player['puuid'] == puuid:  # nur eigener Spieler
            row = [
                player['summonerName'],
                player['championName'],
                player['kills'],
                player['deaths'],
                player['assists']
            ]
            values.append(row)

# Daten an Google Sheets senden
body = {
    'values': values
}

result = sheet.values().update(
    spreadsheetId=SPREADSHEET_ID,
    range=RANGE_NAME,
    valueInputOption='RAW',
    body=body
).execute()

print(f"✅ {result.get('updatedCells')} Zellen aktualisiert.")
