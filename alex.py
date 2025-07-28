import json
import datetime
import time
import pytz
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
import sys
import locale
# === ✅ Konfiguration laden ===
CONFIG_DIR = "C:\\Users\\gamin\\OneDrive\\Dokumente"
if CONFIG_DIR not in sys.path:
    sys.path.append(CONFIG_DIR)

try:
    import config_alex  # pyright: ignore[reportMissingImports]
except ImportError:
    print("❌ Konfigurationsdatei 'config_alex.py' nicht gefunden!")
    exit()

RIOT_API = config_alex.RIOT_API
puuid = config_alex.puuid
region_full = config_alex.region_full
SERVICE_ACCOUNT_FILE = config_alex.SERVICE_ACCOUNT_FILE
SCOPES = config_alex.SCOPES
SPREADSHEET_ID = config_alex.SPREADSHEET_ID
locale.setlocale(locale.LC_TIME, 'deu')  # manchmal auch 'German_Germany' oder 'deu_deu'

def get_timestamp():
    return int(datetime.datetime.now().timestamp() * 1000)

def get_german_day_timestamps():
    tz = pytz.timezone("Europe/Berlin")
    now = datetime.datetime.now(tz)
    start_of_day = tz.localize(datetime.datetime(now.year, now.month, now.day, 0, 1, 0))
    end_of_day = start_of_day + datetime.timedelta(days=1) - datetime.timedelta(minutes=1)
    return int(start_of_day.timestamp()), int(end_of_day.timestamp())

def get_day_matches(puuid, start_ts, end_ts, region=region_full):
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?startTime={start_ts}&endTime={end_ts}&type=ranked&start=0&count=20&api_key={RIOT_API}"
    #url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?startTime=1753567200&endTime=1753653599&type=ranked&start=0&count=20&api_key={RIOT_API}"
    r = requests.get(url)
    return r.json() if r.status_code == 200 else []

def get_matchdata_day(puuid, matches, region=region_full):
    match_data = []
    for match_id in matches:
        url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={RIOT_API}"
        r = requests.get(url)
        if r.status_code == 200:
            match_data.append(r.json())
    return match_data

def was_afk_by_timeline(match_id, puuid, region=region_full):
    r = requests.get(f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline?api_key={RIOT_API}")
    if r.status_code != 200:
        return False
    timeline = r.json()
    frames = timeline.get("info", {}).get("frames", [])
    participant_id = next((p['participantId'] for p in timeline['info']['participants'] if p['puuid'] == puuid), None)
    if not participant_id:
        return False
    last_action = max((i for i, frame in enumerate(frames) for e in frame.get("events", []) if e.get("participantId") == participant_id), default=0)
    return (len(frames) - last_action) >= 5

def Q_type(matches):
    return "offday" if len(matches) == 0 else "Solo Q"

def parse_sessions(match_data, puuid):
    from datetime import datetime, timedelta
    match_data.sort(key=lambda m: m['info']['gameStartTimestamp'])
    sessions = []
    current = []
    last_time = None
    for match in match_data:
        game_time = datetime.fromtimestamp(match['info']['gameStartTimestamp'] / 1000)
        player = next((p for p in match['info']['participants'] if p['puuid'] == puuid), None)
        if not player:
            continue
        if last_time and (game_time - last_time) > timedelta(hours=1):
            if current: sessions.append(current)
            current = []
        afk = was_afk_by_timeline(match['metadata']['matchId'], puuid)
        current.append({'outcome': 'win' if player['win'] else 'loss', 'afk': afk})
        last_time = game_time
    if current: sessions.append(current)
    return ', '.join(f"{sum(1 for g in s if g['outcome']=='win')}|{sum(1 for g in s if g['outcome']=='loss')}{'*' if any(g['afk'] for g in s) else ''}" for s in sessions)

def get_day_wins(matches, puuid):
    return sum(1 for m in matches for p in m['info']['participants'] if p['puuid'] == puuid and p['win'])
def get_deaths_min12(match_data, puuid, region=region_full):
    total_deaths = 0
    count = 0
    for match in match_data:
        player = next((p for p in match['info']['participants'] if p['puuid'] == puuid), None)
        if player.get('teamPosition') != "JUNGLE":
            continue

        match_id = match['metadata']['matchId']
        timeline_url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline?api_key={RIOT_API}"
        r = requests.get(timeline_url)
        if r.status_code != 200:
            continue

        frames = r.json().get("info", {}).get("frames", [])
        if len(frames) < 12:
            continue

        frame = frames[11]
        your_stats = frame['participantFrames'].get(str(player['participantId']))
        if not your_stats:
            continue

        deaths = your_stats.get('deaths', 0)
        total_deaths += deaths
        count += 1

    return total_deaths / count if count > 0 else None

def get_avg_udyr_jungle_stats_at_15min(matches, puuid, region=region_full):
    total_cs_diff = total_gold_diff = count = 0
    for match in matches:
        player = next((p for p in match['info']['participants'] if p['puuid'] == puuid), None)
        if not player or player['championName'] != "Udyr" or player.get('teamPosition') != "JUNGLE":
            continue
        timeline_url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match['metadata']['matchId']}/timeline?api_key={RIOT_API}"
        r = requests.get(timeline_url)
        if r.status_code != 200:
            continue
        frames = r.json().get("info", {}).get("frames", [])
        if len(frames) < 16:
            continue
        frame = frames[15]
        your_stats = frame['participantFrames'].get(str(player['participantId']))
        if not your_stats:
            continue
        enemy = next((p for p in match['info']['participants'] if p['teamId'] != player['teamId'] and p['teamPosition'] == "JUNGLE"), None)
        if not enemy:
            continue
        enemy_stats = frame['participantFrames'].get(str(enemy['participantId']))
        if not enemy_stats:
            continue
        your_cs = your_stats['jungleMinionsKilled'] + your_stats['minionsKilled']
        enemy_cs = enemy_stats['jungleMinionsKilled'] + enemy_stats['minionsKilled']
        cs_diff = your_cs - enemy_cs
        gold_diff = your_stats['totalGold'] - enemy_stats['totalGold']
        total_cs_diff += cs_diff
        total_gold_diff += gold_diff
        count += 1
    if count == 0:
        return None
    return {
        "avg_cs_diff": total_cs_diff / count,
        "avg_gold_diff": total_gold_diff / count,
        "count": count
    }

def build_conditional_formatting_requests():
    # Sehr simples Beispiel: Markiere die Zellen in Spalte F (Wins) grün, wenn Wert > 0
    return {
        "requests": [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,  # Standardmäßig erstes Tabellenblatt
                                "startRowIndex": 1,  # Überspringe Kopfzeile
                                "endRowIndex": 1000,
                                "startColumnIndex": 5,  # Spalte F (0-basiert)
                                "endColumnIndex": 6
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_GREATER",
                                "values": [{"userEnteredValue": "0"}]
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": 0.8,
                                    "green": 1.0,
                                    "blue": 0.8
                                }
                            }
                        }
                    },
                    "index": 0
                }
            }
        ]
    }
def apply_conditional_formatting(service, spreadsheet_id):
    requests_body = build_conditional_formatting_requests()
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=requests_body
    ).execute()

def get_played_champions(matches, puuid):
    return list({p['championName'] for m in matches for p in m['info']['participants'] if p['puuid'] == puuid})

def update_or_append_sheet(service, today_str, session_summary, matches, match_data):
    sheet = service.spreadsheets()
    deaths = get_deaths_min12(match_data, puuid)  
    rows = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="Tabellenblatt1!A1:Z1000").execute().get('values', [])

    # Finde Zeile mit passendem Datum in Spalte A
    row_index = None
    for i, row in enumerate(rows):
        if len(row) > 0 and row[0].strip() == today_str:
            row_index = i
            break

    q_type_value = Q_type(matches)
    wins = get_day_wins(match_data, puuid)
    g_value = (wins / len(matches)) * 100 if len(matches) > 0 else ""
    cs_diff = get_avg_udyr_jungle_stats_at_15min(match_data, puuid)
    champions = ", ".join(get_played_champions(match_data, puuid))

    # 📅 Datum als Wochentag (optional)
    try:
        date_obj = datetime.datetime.strptime(today_str + "-" + str(datetime.datetime.now().year), "%d-%B-%Y")
    except Exception:
        date_obj = datetime.datetime.now()
    weekday_name = date_obj.strftime("%A")

    # Schutz gegen fehlende Schlüssel in cs_diff
    cs_diff_avg = cs_diff.get("avg_cs_diff", "") if cs_diff else ""
    cs_diff_count = cs_diff.get("count", "") if cs_diff else ""
    cs_diff_gold = cs_diff.get("avg_gold_diff", "") if cs_diff else ""

    values = [
        today_str,            # A - Datum
        q_type_value,         # B - Q-Typ
        len(matches),         # C - Anzahl Spiele
        session_summary,      # D - Sitzungsübersicht
        "",                   # E - leer
        wins,                 # F - Wins
        g_value,              # G - Winrate
        champions,            # H - gespielte Champions
        deaths,               # I - Deaths @12min
        "",                   # J - leer
        "",                   # K - leer
        cs_diff_avg,          # L - CS-Diff @15min       # M - Anzahl Spiele mit Udyr Jungle
        cs_diff_gold          # N - Gold-Diff @15min
    ]

    # Fülle auf bis Spalte Z (26 Spalten)
    while len(values) < 26:
        values.append("")

    # === Zeile aktualisieren oder anhängen ===
    if row_index is not None:
        # ✅ Zeile aktualisieren (z. B. Zeile 5 → "A5:Z5")
        range_to_update = f"Tabellenblatt1!A{row_index+1}:Z{row_index+1}"
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_to_update,
            valueInputOption='RAW',
            body={'values': [values]}
        ).execute()
        print(f"🔁 Zeile {row_index+1} aktualisiert.")
    else:
# ➕ Neue Zeile anhängen (explizit 26 Spalten A bis Z)
        sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Tabellenblatt1!A1:Z1",  # Achte auf den exakten Bereich
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [values]}
        ).execute()

        print(f"➕ Neue Zeile für {today_str} hinzugefügt.")
    
    apply_conditional_formatting(service, SPREADSHEET_ID)

# === 🕒 Endlosschleife für regelmäßige Aktualisierung ===
if __name__ == "__main__":
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)

    while True:
        print(f"\n🔄 Neue Abfrage um {datetime.datetime.now().strftime('%H:%M:%S')}...")
        start_ts, end_ts = get_german_day_timestamps()
        matches = get_day_matches(puuid, start_ts, end_ts)
        if matches:
            match_data = get_matchdata_day(puuid, matches)
            session_summary = parse_sessions(match_data, puuid)
            today_str = datetime.datetime.now().strftime("%d-%B")
            update_or_append_sheet(service, today_str, session_summary, matches, match_data)
        else:
            print("ℹ️ Keine Ranked-Spiele heute.")
        print("⏳ Warte 45 Minuten...\n")
        time.sleep(45 * 60)  # 45 Minuten warten
        print("⏳ Warte 45 Minuten...\n")
        time.sleep(45 * 60)  # 45 Minuten warten
