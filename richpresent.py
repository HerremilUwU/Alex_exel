#ᓚᘏᗢ✮⋆˙✮ ⋆ ⭒˚｡⋆
import requests
import sys
import time
from pypresence import Presence

# === Konfiguration laden ===
CONFIG_DIR = r"C:\Users\gamin\OneDrive\Dokumente"
if CONFIG_DIR not in sys.path:
    sys.path.append(CONFIG_DIR)

try:
    import config_alex  # pyright: ignore[reportMissingImports]
except ImportError:
    print("❌ Konfigurationsdatei 'config_alex.py' nicht gefunden!")
    sys.exit()

# === Variablen aus config_alex ===
RIOT_API_KEY = config_alex.RIOT_API
puuid = config_alex.puuid
REGION = config_alex.region
CLIENT_ID = config_alex.client_id

HEADERS = {"X-Riot-Token": RIOT_API_KEY}

# === Symbol-Zuordnung für Ränge ===
RANK_SYMBOLS = {
    "IRON": "",
    "BRONZE": "",
    "SILVER": "",
    "GOLD": "",
    "PLATINUM": "",
    "DIAMOND": "",
    "MASTER": "",
    "GRANDMASTER": "",
    "CHALLENGER": ""
}

# === Riot API Abfragen ===
def get_summoner_data():
    url = f"https://{REGION}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()

def get_version():
    r = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
    r.raise_for_status()
    versions = r.json()
    return versions[0] if versions else None

def get_ranked_stats():
    url = f"https://{REGION}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()

def get_cutoff(tier):
    """Nur Cutoff für relevanten Rang abfragen."""
    if tier == "MASTER":
        url = f"https://{REGION}.api.riotgames.com/lol/league/v4/grandmasterleagues/by-queue/RANKED_SOLO_5x5"
    elif tier == "GRANDMASTER":
        url = f"https://{REGION}.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5"
    else:
        return None

    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    entries = r.json().get("entries", [])
    if entries:
        return min(player["leaguePoints"] for player in entries)
    return None

# === Fortschrittsbalken ===
def progress_bar(lp, max_lp=100):
    filled_blocks = int((lp / max_lp) * 10)
    empty_blocks = 10 - filled_blocks
    return f"[{'█' * filled_blocks}{'░' * empty_blocks}]"

# === Anzeige-Logik ===
def format_rank_display(rank_stats):
    if not rank_stats:
        return "Unranked", "", "unranked_icon", "UNRANKED"

    entry = rank_stats[0]
    tier = entry.get("tier", "").upper()
    rank = entry.get("rank", "")
    lp = entry.get("leaguePoints", 0)

    bar = progress_bar(lp)
    details = f"{tier.title()} {rank} {bar} {lp} LP"
    cutoff_text = ""

    if tier in ["MASTER", "GRANDMASTER"]:
        cutoff_lp = get_cutoff(tier)
        if cutoff_lp:
            if tier == "MASTER":
                cutoff_text = f"Cutoff zu GM: {cutoff_lp} LP"
            elif tier == "GRANDMASTER":
                cutoff_text = f"Cutoff zu Challenger: {cutoff_lp} LP"
    else:
        divisions = ["IV", "III", "II", "I"]
        if rank in divisions:
            idx = divisions.index(rank)
            if idx < len(divisions) - 1:
                next_rank = divisions[idx + 1]
                cutoff_text = f"{100 - lp} LP bis {tier.title()} {next_rank}"
            else:
                next_tier_map = {
                    "IRON": "BRONZE",
                    "BRONZE": "SILVER",
                    "SILVER": "GOLD",
                    "GOLD": "PLATINUM",
                    "PLATINUM": "DIAMOND",
                    "DIAMOND": "MASTER"
                }
                next_tier = next_tier_map.get(tier, "Unbekannt")
                cutoff_text = f"{100 - lp} LP bis {next_tier.title()} IV"

    small_icon_key = f"{tier.lower()}_icon"
    return details, cutoff_text, small_icon_key, tier

# === Discord RPC ===
def setup_rpc():
    rpc = Presence(CLIENT_ID)
    rpc.connect()
    print("🔗 Verbunden mit Discord RPC")
    return rpc

# === Hauptprogramm ===
if __name__ == "__main__":
    # Diese Daten nur EINMAL laden → ändert sich selten
    summoner = get_summoner_data()
    summoner_name = summoner.get("name", "Unknown Summoner")
    version = get_version()
    rpc = setup_rpc()

    while True:
        try:
            rank_stats = get_ranked_stats()
            account_level = summoner["summonerLevel"]  # schon geladen → kein extra Call

            details, cutoff_text, small_icon_key, tier = format_rank_display(rank_stats)

            rpc.update(
                details=details,
                state=cutoff_text,
                large_image=f"https://ddragon.leagueoflegends.com/cdn/{version}/img/profileicon/{summoner['profileIconId']}.png",
                large_text=f"VIT VALYO#LVNDR | LvL {account_level})",
                small_image=small_icon_key,
                small_text=tier.title(),
                buttons=[
                    {"label": "X", "url": "https://x.com/Valyoww"},
                    {"label": "Twitch", "url": "https://www.twitch.tv/valyoww"}
                ]
            )

            print(f"✅ Status aktualisiert: {details} | {cutoff_text}")
            time.sleep(300)

        except Exception as e:
            print(f"⚠️ Fehler: {e}")
            time.sleep(300)
