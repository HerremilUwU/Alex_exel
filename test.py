#ᓚᘏᗢ✮⋆˙✮ ⋆ ⭒˚｡⋆
import requests

RIOT_API_KEY = "RGAPI-2dd294d1-1c00-4055-9023-1ae7ea840f00"
REGION = "euw1"  # Für EUW1

def get_challenger_cutoff():
    url = f"https://{REGION}.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    entries = data.get("entries", [])
    # Finde niedrigste LP unter allen Challenger-Spielern
    if entries:
        lowest_lp = min(player["leaguePoints"] for player in entries)
        return lowest_lp
    else:
        return None

def get_grandmaster_cutoff():
    url = f"https://{REGION}.api.riotgames.com/lol/league/v4/grandmasterleagues/by-queue/RANKED_SOLO_5x5"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    entries = data.get("entries", [])
    if entries:
        lowest_lp = min(player["leaguePoints"] for player in entries)
        return lowest_lp
    else:
        return None
if __name__ == "__main__":
    cutoff = get_challenger_cutoff()
    print(f"Challenger Cutoff LP: {cutoff}")
    print(f"Grandmaster Cutoff LP: {get_grandmaster_cutoff()}")
