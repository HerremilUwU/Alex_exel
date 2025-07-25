import json
import datetime
import pytz
import requests

RIOT_API = "RGAPI-2dd294d1-1c00-4055-9023-1ae7ea840f00"
puuid = "CEZXdYaW1s-lZZcYQ_-6m8SJPW6qM5Gd06k0ywMDAemcDUiKg0hhTyzOiVYhc967bWvBcpbtp8hGfg"
id = "O6Aw8vR7NULDpiULDlyZ-chsOa8tqB2oH6jwJs23VSMqlo7H1_s-lL0h8Q"
region = "euw1"
region_full = "europe"

def get_timestamp():
    return int(datetime.datetime.now().timestamp() * 1000)

def get_german_day_timestamps():
    tz = pytz.timezone("Europe/Berlin")
    now = datetime.datetime.now(tz)
    start_of_day = tz.localize(datetime.datetime(now.year, now.month, now.day, 0, 1, 0))
    end_of_day = start_of_day + datetime.timedelta(days=1) - datetime.timedelta(minutes=1)
    start_ts = int(start_of_day.timestamp())
    end_ts = int(end_of_day.timestamp())
    # Speichern als Beispiel in einer Datei
    with open("german_day_timestamps.json", "w") as f:
        json.dump({"start": start_ts, "end": end_ts}, f)
    return start_ts, end_ts

print(f"Current timestamp: {get_german_day_timestamps()}")

print(f"Starting at {get_timestamp()}")
# https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/CEZXdYaW1s-lZZcYQ_-6m8SJPW6qM5Gd06k0ywMDAemcDUiKg0hhTyzOiVYhc967bWvBcpbtp8hGfg/ids?startTime=1751903271&endTime=1752003372077&type=ranked&start=0&count=20&api_key=RGAPI-2dd294d1-1c00-4055-9023-1ae7ea840f00

def get_day_matches(puuid, start_ts, end_ts, region=region_full):
    day_match_url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?startTime={start_ts}&endTime={end_ts}&type=ranked&start=0&count=20&api_key={RIOT_API}"
    response_matches_day = requests.get(day_match_url)
    if response_matches_day.status_code == 200:
        matches = response_matches_day.json()
        print(f"Anzahl gespielter Matches: {len(matches)}")
        return matches
    else:
        print(f"Error fetching matches: {response_matches_day.status_code}")
        return []

print(f"Fetching matches from {get_day_matches(puuid, *get_german_day_timestamps())}")
