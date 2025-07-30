from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
import sys
import datetime

CONFIG_DIR = "C:\\Users\\gamin\\OneDrive\\Dokumente"
if CONFIG_DIR not in sys.path:
    sys.path.append(CONFIG_DIR)

try:
    import config_alex  # pyright: ignore[reportMissingImports]
except ImportError:
    print("❌ Konfigurationsdatei 'config_alex.py' nicht gefunden!")
    exit()
# === Google API einrichten ===
SERVICE_ACCOUNT_FILE = config_alex.SERVICE_ACCOUNT_FILE
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SPREADSHEET_ID = config_alex.SPREADSHEET_ID

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build("sheets", "v4", credentials=creds)

# === Formatierungsregeln abrufen ===
spreadsheet = service.spreadsheets().get(
    spreadsheetId=SPREADSHEET_ID,
    fields="sheets(properties(sheetId,title),conditionalFormats)"
).execute()

print(json.dumps(spreadsheet, indent=2))

# Beispiel: Ermitteln ob heute Dienstag oder Donnerstag ist
today = datetime.datetime.now()
weekday = today.strftime("%A")  # Gibt z.B. "Tuesday" oder "Thursday" zurück

if weekday in ["Tuesday", "Thursday"]:
    # Style-Code aktivieren (hier nur Beispielausgabe)
    print("🔶 Heute ist Dienstag oder Donnerstag! Style-Code aktivieren.")
    # Hier könntest du z.B. eine Funktion aufrufen:
    # apply_special_style(service, SPREADSHEET_ID)
else:
    print("ℹ️ Heute ist kein Dienstag oder Donnerstag.")

