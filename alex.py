#ᓚᘏᗢ✮⋆˙✮ ⋆ ⭒˚｡⋆
import json
import datetime
import time
import pytz
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
import sys
import locale
from coloring import Weekday_color, offday_color, session_color, clear_row_background, champion2_color, I_color, color_golddiff_color, JK, N_color, E_color, played_matches_color, B_color, cs_diff_color

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
locale.setlocale(locale.LC_TIME, 'deu')

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

def was_afk_by_timeline(match_id, puuid, timeline_cache=None, region=region_full):
    if timeline_cache is not None and match_id in timeline_cache:
        timeline = timeline_cache[match_id]
    else:
        r = requests.get(f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline?api_key={RIOT_API}")
        if r.status_code != 200:
            return False
        timeline = r.json()
        if timeline_cache is not None:
            timeline_cache[match_id] = timeline

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
    timeline_cache = {}

    for match in match_data:
        game_time = datetime.fromtimestamp(match['info']['gameStartTimestamp'] / 1000)
        player = next((p for p in match['info']['participants'] if p['puuid'] == puuid), None)
        if not player:
            continue

        if last_time and (game_time - last_time) > timedelta(hours=1):
            if current:
                sessions.append(current)
            current = []

        afk = was_afk_by_timeline(match['metadata']['matchId'], puuid, timeline_cache)
        current.append({'outcome': 'win' if player['win'] else 'loss', 'afk': afk})
        last_time = game_time

    if current:
        sessions.append(current)

    cell_values = []
    totals_for_print = []

    for s in sessions:
        wins = sum(1 for g in s if g['outcome'] == 'win')
        losses = sum(1 for g in s if g['outcome'] == 'loss')
        afk_flag = '*' if any(g['afk'] for g in s) else ''

        cell_values.append(f"{wins}|{losses}{afk_flag}")
        totals_for_print.append(wins + losses)

    print("📊 Session Totals:", totals_for_print)

    session_summary = ', '.join(cell_values)
    return session_summary, totals_for_print

def get_day_wins(matches, puuid):
    return sum(1 for m in matches for p in m['info']['participants'] if p['puuid'] == puuid and p['win'])

def offday(matches):
    if not matches:
        print("ℹ️ Keine Ranked-Spiele heute.")
        return True
    return False

def update_or_append_sheet(service, today_str, session_summary, totals_for_print, matches, match_data):
    sheet = service.spreadsheets()
    deaths = 0
    rows = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range="Tabellenblatt1!A1:Z1000"
    ).execute().get('values', [])

    row_index = next((i for i, row in enumerate(rows) if len(row) > 0 and row[0].strip() == today_str), None)

    q_type_value = Q_type(matches)
    wins = get_day_wins(match_data, puuid)
    g_value = (wins / len(matches)) * 100 if len(matches) > 0 else ""
    cs_diff = get_avg_udyr_jungle_stats_at_15min(match_data, puuid)
    champions = ", ".join({p['championName'] for m in match_data for p in m['info']['participants'] if p['puuid'] == puuid})

    try:
        date_obj = datetime.datetime.strptime(today_str + "-" + str(datetime.datetime.now().year), "%d-%B-%Y")
    except Exception:
        date_obj = datetime.datetime.now()

    if offday(matches):
        values = [today_str, "Offday"] + ["."] * (14 - 2)
        if row_index is not None:
            clear_row_background(service, row_index)
            range_to_update = f"Tabellenblatt1!A{row_index+1}:Z{row_index+1}"
            sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=range_to_update,
                valueInputOption='RAW',
                body={'values': [values]}
            ).execute()
        else:
            sheet.values().append(
                spreadsheetId=SPREADSHEET_ID,
                range="Tabellenblatt1!A:Z",
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': [values]}
            ).execute()
            row_index = len(rows)

        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=offday_color(row_index)
        ).execute()
        return

    cs_diff_avg = cs_diff.get("avg_cs_diff", "") if cs_diff else ""
    cs_diff_count = cs_diff.get("count", "") if cs_diff else ""
    cs_diff_gold = cs_diff.get("avg_gold_diff", "") if cs_diff else ""
    values = [
        today_str, q_type_value, len(matches), session_summary, ". ", wins,
        g_value, champions, deaths, ". ", ". ", cs_diff_avg, cs_diff_gold, ". "
    ] + [""] * (26 - 14)

    if row_index is not None:
        clear_row_background(service, row_index)
        range_to_update = f"Tabellenblatt1!A{row_index+1}:Z{row_index+1}"
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_to_update,
            valueInputOption='RAW',
            body={'values': [values]}
        ).execute()

        rules = [
            cs_diff_color(row_index, cs_diff_avg),
            color_golddiff_color(row_index, cs_diff_gold),
            session_color(row_index, totals_for_print),
            E_color(row_index),
            champion2_color(row_index),
            B_color(row_index),
            I_color(row_index),
            N_color(row_index),
            Weekday_color(row_index),
            played_matches_color(row_index, matches),
            JK(row_index)
        ]
        for rule in rules:
            if rule:
                service.spreadsheets().batchUpdate(
                    spreadsheetId=SPREADSHEET_ID,
                    body=rule
                ).execute()
    else:
        sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Tabellenblatt1!A:Z",
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [values]}
        ).execute()

if __name__ == "__main__":
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)

    while True:
        print(f"\n🔄 Neue Abfrage um {datetime.datetime.now().strftime('%H:%M:%S')}...")
        start_ts, end_ts = get_german_day_timestamps()
        matches = get_day_matches(puuid, start_ts, end_ts)
        match_data = get_matchdata_day(puuid, matches) if matches else []

        session_summary, totals_for_print = parse_sessions(match_data, puuid) if matches else ("", [])
        today_str = datetime.datetime.now().strftime("%d-%B")
        update_or_append_sheet(service, today_str, session_summary, totals_for_print, matches, match_data)
        print("⏳ Warte 45 Minuten...\n")
        time.sleep(45 * 60)
