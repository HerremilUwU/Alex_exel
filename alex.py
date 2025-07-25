import json
import datetime
import sys
import pytz
import requests
import os

# === ✅ Konfiguration laden (aus externem Ordner) ===
CONFIG_DIR = "C:\\Users\\gamin\\OneDrive\\Dokumente"
if CONFIG_DIR not in sys.path:
    sys.path.append(CONFIG_DIR)

try:
    import config_alex
except ImportError:
    print("❌ Konfigurationsdatei 'config_alex.py' nicht gefunden!")
    exit()

# === 🎯 Konfigvariablen verwenden ===
RIOT_API = config_alex.RIOT_API
puuid = config_alex.puuid
region_full = config_alex.region_full

# === 🔢 Unix-Timestamp in Millisekunden ===
def get_timestamp():
    return int(datetime.datetime.now().timestamp() * 1000)

# === 🇩🇪 Tagesstart & -ende in deutscher Zeitzone ===
def get_german_day_timestamps():
    tz = pytz.timezone("Europe/Berlin")
    now = datetime.datetime.now(tz)
    start_of_day = tz.localize(datetime.datetime(now.year, now.month, now.day, 0, 1, 0))
    end_of_day = start_of_day + datetime.timedelta(days=1) - datetime.timedelta(minutes=1)

    start_ts = int(start_of_day.timestamp())
    end_ts = int(end_of_day.timestamp())

    # Zum Debuggen speichern (optional)
    with open("german_day_timestamps.json", "w") as f:
        json.dump({"start": start_ts, "end": end_ts}, f)

    return start_ts, end_ts

# === 🕹️ Matches des Tages abfragen ===
def get_day_matches(puuid, start_ts, end_ts, region=region_full):
    day_match_url = (
        f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/"
        f"{puuid}/ids?startTime={start_ts}&endTime={end_ts}&type=ranked&start=0&count=20&api_key={RIOT_API}"
    )

    response = requests.get(day_match_url)

    if response.status_code == 200:
        matches = response.json()
        print(f"✅ Anzahl gespielter Ranked-Matches heute: {len(matches)}")
        return matches
    else:
        print(f"❌ Fehler beim Abrufen der Matches: {response.status_code}")
        print(response.text)
        return []

# === 🏁 Start ===
if __name__ == "__main__":
    print(f"🕒 Aktueller Timestamp: {get_timestamp()}")
    start_ts, end_ts = get_german_day_timestamps()
    print(f"📅 Zeitfenster: {start_ts} - {end_ts}")

    matches = get_day_matches(puuid, start_ts, end_ts)
    print(f"📦 Matches: {matches}")
