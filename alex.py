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
            if current:
                sessions.append(current)
            current = []
        
        afk = was_afk_by_timeline(match['metadata']['matchId'], puuid)
        current.append({'outcome': 'win' if player['win'] else 'loss', 'afk': afk})
        last_time = game_time
    
    if current:
        sessions.append(current)
    
    # Original-Format für Zelle
    cell_values = []
    
    # Nur für Print: Totals berechnen
    totals_for_print = []
    
    for s in sessions:
        wins = sum(1 for g in s if g['outcome'] == 'win')
        losses = sum(1 for g in s if g['outcome'] == 'loss')
        afk_flag = '*' if any(g['afk'] for g in s) else ''
        
        # Zellwert bleibt wie vorher
        cell_values.append(f"{wins}|{losses}{afk_flag}")
        
        # Nur für print – Total pro Session
        totals_for_print.append(wins + losses)
    
    # Debug-Ausgabe mit Totals
    print("📊 Session Totals:", totals_for_print)
    
    return ', '.join(cell_values)

def session_color(match_data, puuid, totals_for_print):
    # Diese Funktion könnte verwendet werden, um die Farben für die Sitzungen zu setzen
    # Hier wird nur ein Beispiel gezeigt
    if totals_for_print < 2 or totals_for_print > 5:
        return {"red": 1, "green": 0.2, "blue": 0.2}
    else:
        return {"red": 0.2, "green": 1, "blue": 0.2}
    return {
        "requests": [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,
                                "startRowIndex": 0,
                                "endRowIndex": 1,
                                "startColumnIndex": 3,  # Spalte D
                                "endColumnIndex": 4
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "CUSTOM_FORMULA",
                                "values": [
                                    {"userEnteredValue": "=LEN(D1)>0"}
                                ]
                            },
                            "format": {"backgroundColor": session_color(match_data, puuid, totals_for_print)}
                        }
                    },
                    "index": 0
                }
            }
        ]
    }

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

def get_played_champions(matches, puuid):
    return list({p['championName'] for m in matches for p in m['info']['participants'] if p['puuid'] == puuid})

#green
green_red = 0.7137254901960784
green_green = 0.8431372549019608
green_blue = 0.6588235294117647

#red
red_red = 0.9176470588235294
red_green = 0.6
red_blue = 0.6               

#gelb
yellow_red = 1.0
yellow_green = 0.9490196078431372
yellow_blue = 0.8
def Weekday_color(row_index):
    today = datetime.datetime.now()
    weekday = today.strftime("%A")

    start_row = row_index
    end_row = row_index + 1

    if weekday in ["Dienstag", "Donnerstag"]:
        color = {"red": 1, "green": 0.6, "blue": 0.2}  # Orange
    elif weekday in ["Sonntag"]:
        color = {"red": 0.5568627450980392, "green": 0.48627450980392156, "blue": 0.7647058823529411}  # Blau
    else:
        color = {"red": 0.8509803921568627, "green": 0.8235294117647058, "blue": 0.9137254901960784}  # Standardfarbe (Lila/Weiß)

    return {
        "requests": [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,
                                "startRowIndex": start_row,
                                "endRowIndex": end_row,
                                "startColumnIndex": 0,
                                "endColumnIndex": 1
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "CUSTOM_FORMULA",
                                "values": [
                                    {"userEnteredValue": f"=LEN(A{row_index+1})>0"}
                                ]
                            },
                            "format": {"backgroundColor": color}
                        }
                    },
                    "index": 0
                }
            }
        ]
    }
def clear_row_background(service, row_index):
    clear_request = {
        "requests": [
            {
                "updateCells": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": row_index,
                        "endRowIndex": row_index + 1
                    },
                    "fields": "userEnteredFormat.backgroundColor"
                }
            }
        ]
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body=clear_request
    ).execute()
def champion2_color(row_index):
    return {
        "requests": [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,
                                "startRowIndex": row_index,
                                "endRowIndex": row_index + 1,
                                "startColumnIndex": 7,  # Spalte H
                                "endColumnIndex": 8
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "NOT_BLANK"  # Bedingung: Feld ist nicht leer
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": green_red,
                                    "green": green_green,
                                    "blue": green_blue
                                }
                            }
                        }
                    },
                    "index": 0
                }
            }
        ]
    }
def I_color(row_index):
    return {
        "requests": [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,
                                "startRowIndex": row_index,
                                "endRowIndex": row_index + 1,
                                "startColumnIndex": 8,  # Spalte I
                                "endColumnIndex": 9
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "NOT_BLANK"  # Bedingung: Feld ist nicht leer
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": yellow_red,
                                    "green": yellow_green,
                                    "blue": yellow_blue
                                }
                            }
                        }
                    },
                    "index": 0
                }
            }
        ]
    }

def color_golddiff_color(row_index, gold_diff):
    if gold_diff < 0:
        color = {"red": 1, "green": 0.2, "blue": 0.2}  # Rot
    elif gold_diff < 1000:
        color = {"red": 1, "green": 1, "blue": 0}      # Gelb
    else:
        color = {"red": 0.2, "green": 1, "blue": 0.2}  # Grün
    return {
        "requests": [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,
                                "startRowIndex": row_index,
                                "endRowIndex": row_index + 1,
                                "startColumnIndex": 5, # Spalte F
                                "endColumnIndex": 6
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "CUSTOM_FORMULA",
                                "values": [
                                    {"userEnteredValue": "=LEN(F{})>0".format(row_index+1)}
                                ]
                            },
                            "format": {"backgroundColor": color}
                        }
                    },
                    "index": 0
                }
            }
        ]
    }
def JK(row_index):
    return {
        "requests": [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,
                                "startRowIndex": row_index,
                                "endRowIndex": row_index + 1,
                                "startColumnIndex": 9,  # Spalte J
                                "endColumnIndex": 10
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "NOT_BLANK"  # Bedingung: Feld ist nicht leer
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": 0.8352941176470589,
                                    "green": 0.6509803921568628,
                                    "blue": 0.7411764705882353
                                }
                            }
                        }
                    },
                    "index": 0
                }
            }
        ]
    }
def E_color(row_index):
    return {
        "requests": [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,
                                "startRowIndex": row_index,
                                "endRowIndex": row_index + 1,
                                "startColumnIndex": 4,  # Spalte E
                                "endColumnIndex": 5
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "NOT_BLANK"  # Bedingung: Feld ist nicht leer
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": 0.2,
                                    "green": 0.2,
                                    "blue": 1
                                }
                            }
                        }
                    },
                    "index": 0
                }
            }
        ]
    }
def played_matches_color(row_index, matches):
    played_matches = len(matches)
    if played_matches < 3:
        color = {"red": red_red, "green": red_green, "blue": red_blue}  # Rot
    elif played_matches < 5:
        color = {"red": yellow_red, "green": yellow_green, "blue": yellow_blue}      # Gelb
    elif played_matches >= 5:
        color = {"red": green_red, "green": green_green, "blue": green_blue}  # Grün
    else:
        color = {"red": 1, "green": 1, "blue": 1}      # Weiß
    return {
        "requests": [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,
                                "startRowIndex": row_index,
                                "endRowIndex": row_index + 1,
                                "startColumnIndex": 2, # Spalte C
                                "endColumnIndex": 3
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "CUSTOM_FORMULA",
                                "values": [
                                    {"userEnteredValue": "=LEN(C{})>0".format(row_index+1)}
                                ]
                            },
                            "format": {"backgroundColor": color}
                        }
                    },
                    "index": 0
                }
            }
        ]
    }



def update_or_append_sheet(service, today_str, session_summary, matches, match_data):
    sheet = service.spreadsheets()
    deaths = get_deaths_min12(match_data, puuid)  
    rows = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range="Tabellenblatt1!A1:Z1000"
    ).execute().get('values', [])

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

    try:
        date_obj = datetime.datetime.strptime(today_str + "-" + str(datetime.datetime.now().year), "%d-%B-%Y")
    except Exception:
        date_obj = datetime.datetime.now()
    weekday_name = date_obj.strftime("%A")

    cs_diff_avg = cs_diff.get("avg_cs_diff", "") if cs_diff else ""
    cs_diff_count = cs_diff.get("count", "") if cs_diff else ""
    cs_diff_gold = cs_diff.get("avg_gold_diff", "") if cs_diff else ""

    values = [
        today_str,
        q_type_value,
        len(matches),
        session_summary,
        " ",
        wins,
        g_value,
        champions,
        deaths,
        " ",
        " ",
        cs_diff_avg,
        cs_diff_gold
    ]

    while len(values) < 26:
        values.append("")

    if row_index is not None:
        clear_row_background(service, row_index)
        # ✅ Vorhandene Zeile aktualisieren
        range_to_update = f"Tabellenblatt1!A{row_index+1}:Z{row_index+1}"
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_to_update,
            valueInputOption='RAW',
            body={'values': [values]}
        ).execute()
        print(f"🔁 Zeile {row_index+1} aktualisiert.")
        # Formatierungsregeln anwenden
        
        E_color_rules = E_color(row_index)
        if E_color_rules:
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=E_color_rules
            ).execute()
        champion2_color_rules = champion2_color(row_index)
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=champion2_color_rules
        ).execute()

        # Gold-Diff-Farbe anwenden
        if g_value != "":
            gold_diff_color_rules = color_golddiff_color(row_index, g_value)
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=gold_diff_color_rules
            ).execute()

        # H_color anwenden
        h_color_rules = I_color(row_index)
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=h_color_rules
        ).execute()

        # Farben anwenden
        dodi_rules = Weekday_color(row_index)
        if dodi_rules:
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=dodi_rules
            ).execute()
        
        played_color_rules = played_matches_color(row_index, matches)
        if played_color_rules:
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=played_color_rules
            ).execute()
        
        jk_rules = JK(row_index)
        if jk_rules:
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=jk_rules
            ).execute()
    else:
        # 🚀 Neue Zeile anhängen
        sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Tabellenblatt1!A:Z",
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [values]}
        ).execute()
        print("➕ Neue Zeile hinzugefügt.")


def parse_json_date(date_str):
    # Erwartet z.B. "2021-01-01 10:00:00"
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

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
    time.sleep(45 * 60)
