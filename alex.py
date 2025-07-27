import json
import datetime
import sys
import pytz
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build

# === ✅ Konfiguration laden (aus externem Ordner) ===
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
RANGE_NAME = config_alex.RANGE_NAME  # z. B. "Tabelle1!A:B"

def get_timestamp():
    return int(datetime.datetime.now().timestamp() * 1000)

def get_german_day_timestamps():
    tz = pytz.timezone("Europe/Berlin")
    now = datetime.datetime.now(tz)
    start_of_day = tz.localize(datetime.datetime(now.year, now.month, now.day, 0, 1, 0))
    end_of_day = start_of_day + datetime.timedelta(days=1) - datetime.timedelta(minutes=1)
    return int(start_of_day.timestamp()), int(end_of_day.timestamp())

def get_day_matches(puuid, start_ts, end_ts, region=region_full):
    url = (
        f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/"
        f"{puuid}/ids?startTime={start_ts}&endTime={end_ts}&type=ranked&start=0&count=20&api_key={RIOT_API}"
    )
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
    timeline_url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline?api_key={RIOT_API}"
    r = requests.get(timeline_url)
    if r.status_code != 200:
        return False

    timeline = r.json()
    info = timeline.get("info", {})
    frames = info.get("frames", [])
    participant_id = None

    for p in info.get("participants", []):
        if p.get("puuid") == puuid:
            participant_id = p.get("participantId")
            break

    if not participant_id:
        return False

    last_action_minute = 0
    for i, frame in enumerate(frames):
        for e in frame.get("events", []):
            if e.get("participantId") == participant_id:
                last_action_minute = i

    total_minutes = len(frames)
    return (total_minutes - last_action_minute) >= 5

def Q_type(matches):
    if len(matches) == 0:
        return "offday"
    else:
        return "SOLO_Q"
    
def parse_sessions(match_data, puuid):
    from datetime import datetime, timedelta
    match_data.sort(key=lambda m: m['info']['gameStartTimestamp'])
    sessions = []
    current_session = []
    last_game_time = None

    for match in match_data:
        game_time = datetime.fromtimestamp(match['info']['gameStartTimestamp'] / 1000)
        match_id = match['metadata']['matchId']
        player_data = next((p for p in match['info']['participants'] if p['puuid'] == puuid), None)
        if not player_data:
            continue

        if last_game_time and (game_time - last_game_time) > timedelta(hours=1):
            if current_session:
                sessions.append(current_session)
            current_session = []

        afk = was_afk_by_timeline(match_id, puuid)
        outcome = 'win' if player_data['win'] else 'loss'
        current_session.append({'outcome': outcome, 'afk': afk})
        last_game_time = game_time

    if current_session:
        sessions.append(current_session)

    session_strings = []
    for session in sessions:
        wins = sum(1 for g in session if g['outcome'] == 'win')
        losses = sum(1 for g in session if g['outcome'] == 'loss')
        afk = '*' if any(g['afk'] for g in session) else ''
        session_strings.append(f"{wins}|{losses}{afk}")

    return ', '.join(session_strings)
def get_day_wins(matches, puuid):
    wins = 0
    for match in matches:
        for player in match['info']['participants']:
            if player['puuid'] == puuid and player['win']:
                wins += 1
                break
    return wins

def get_cs_diff_at_15minute(match, puuid):
    participants = match['info']['participants']
    player = next((p for p in participants if p['puuid'] == puuid), None)
    if not player:
        print("Spieler nicht gefunden")
        return None

    lane = player.get('teamPosition')
    team_id = player.get('teamId')
    
    if not lane:
        print("Kein teamPosition für Spieler")
        return None

    enemy = next(
        (p for p in participants if p.get('teamPosition') == lane and p.get('teamId') != team_id),
        None
    )
    if not enemy:
        print("Kein Gegner mit gleicher Lane gefunden")
        return None

    player_challenges = player.get('challenges', {})
    enemy_challenges = enemy.get('challenges', {})

    player_cs15 = player_challenges.get('csAt15Minutes')
    enemy_cs15 = enemy_challenges.get('csAt15Minutes')

    print(f"player_cs15: {player_cs15}, enemy_cs15: {enemy_cs15}")

    if player_cs15 is None or enemy_cs15 is None:
        print("csAt15Minutes fehlt bei einem der Spieler")
        return None

    return player_cs15 - enemy_cs15

def get_played_champions(matches, puuid):
    champions = set()
    for match in matches:
        for player in match['info']['participants']:
            if player['puuid'] == puuid:
                champions.add(player['championName'])
                break
    return list(champions)
def update_or_append_sheet(service, today_str, session_summary):
    sheet = service.spreadsheets()
    # hole alle Werte in Spalte A
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="Tabellenblatt1!A:A").execute()
    rows = result.get('values', [])
    
    for idx, row in enumerate(rows):
        if row and row[0] == today_str:
            range_to_update = f"Tabellenblatt1!B{idx + 1}"
            body = {'values': [[session_summary]]}
            sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=range_to_update,
                valueInputOption='RAW',
                body=body
            ).execute()
            print(f"🔁 Bestehende Zeile für {today_str} aktualisiert.")
            return

    # wenn nicht gefunden → neue Zeile anhängen
    q_type_value = Q_type(matches)  # Call the function to get the string
    wins = get_day_wins(match_data, puuid)
    cs_diff = get_cs_diff_at_15minute(match_data[0], puuid) if match_data else None
    champions = get_played_champions(match_data, puuid)
    champions_str = ", ".join(champions)
    body = {'values': [[today_str, q_type_value, len(matches), session_summary,"", wins, "", champions_str, "", "", cs_diff]]}
    sheet.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Tabellenblatt1!A:Z",
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body=body
    ).execute()
    print(f"➕ Neue Zeile für {today_str} hinzugefügt.")

# === 🏁 Hauptprogramm ===
if __name__ == "__main__":
    print(f"🕒 Timestamp: {get_timestamp()}")
    start_ts, end_ts = get_german_day_timestamps()

    matches = get_day_matches(puuid, start_ts, end_ts)
    if matches:
        match_data = get_matchdata_day(puuid, matches)
        session_summary = parse_sessions(match_data, puuid)

        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)

        today_str = datetime.datetime.now().strftime("%d-%B")
        update_or_append_sheet(service, today_str, session_summary)

        with open("match_data.json", "w", encoding="utf-8") as f:
            json.dump(match_data, f, indent=2, ensure_ascii=False)
    else:
        print("ℹ️ Keine Ranked-Matches gefunden.")
