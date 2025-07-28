# Alex_exel
---
Hmm DU fragst dich was soll das hier? Ja ich erkläre dir was hier abgeht 
<div>
<image style="width:20%" src="https://mailmeteor.com/logos/assets/PNG/Google_Sheets_Logo_512px.png">
<image style="width:25%;" src="https://raw.githubusercontent.com/github/explore/206772d6289c3cdd1b4dca05aacdeac7e1834dc9/topics/riot-games/riot-games.png">
</div>
## ⚙️ Funktionen

 - 📅 Tägliche Aufzeichnung deiner Ranked-Spiele (0 Uhr – 23:59)
 - 📊 Berechnung von: - Anzahl Spiele & Wins - Winrate - Session-Performance (z. B. `2|1` für 2 Wins, 1 Loss) 
 - \*\*Durchschnittliche Tode bis Minute 12\*\* 
 - \*\*CS-Diff & Gold-Diff @15min\*\* für Udyr als Jungler 
 - 🔍 Erkennt AFK-Verhalten anhand der Timeline-Daten - 🌈 \*\*Automatische Formatierung in Google Sheets\*\* (z. B. grüne Markierung bei Wins) 
 
  ## 🚀 Installation & Nutzung 1.
   <h3>Voraussetzungen:</h3>
   - Python 3.7+ 
   - Bibliotheken: `requests`, `google-auth`, `google-api-python-client`, `pytz` Installiere fehlende Pakete mit: 
   ```bash
    pip install requests google-auth google-api-python-client
    ```
    pytz Riot API Key besorgen: Registriere dich auf developer.riotgames.com und erstelle einen API-Key. Google Service Account anlegen: Erstelle einen Service Account in der Google Cloud Console. Lade die JSON-Datei herunter. Teile deine Google Sheets Datei mit der Service Account Email (z.B. your-service-account@project.iam.gserviceaccount.com). Konfigurationsdatei erstellen: Lege eine Datei config\_alex.py im selben Verzeichnis oder im angegebenen CONFIG\_DIR an mit folgendem Inhalt: RIOT\_API = "dein\_riot\_api\_key" puuid = "deine\_puuid" region\_full = "euw1" # z.B. "euw1", "na1", etc. SERVICE\_ACCOUNT\_FILE = "pfad/zur/service\_account.json" SCOPES = ["https://www.googleapis.com/auth/spreadsheets"] SPREADSHEET\_ID = "deine\_google\_sheet\_id" Script starten: python dein\_scriptname.py Das Skript läuft in einer Endlosschleife und aktualisiert alle 45 Minuten. 📝 Erklärung der wichtigsten Funktionen get\_german\_day\_timestamps(): Ermittelt Start- und Endzeit (Unix-Timestamp) des aktuellen Tages in Berliner Zeitzone. get\_day\_matches(): Holt Match-IDs für den Tag vom Riot API. get\_matchdata\_day(): Ruft detailierte Matchdaten für die Matches ab. was\_afk\_by\_timeline(): Prüft, ob Spieler AFK war (basierend auf Timeline-Frames). parse\_sessions(): Gruppiert Spiele zu Sessions (max. 1 Stunde Pause dazwischen) und fasst Ergebnisse zusammen. get\_deaths\_min12(): Berechnet durchschnittliche Tode bis Minute 12 für Jungler. get\_avg\_udyr\_jungle\_stats\_at\_15min(): Durchschnittliche CS- und Gold-Differenz bei Udyr Jungle nach 15 Minuten. update\_or\_append\_sheet(): Aktualisiert die Google Sheets Tabelle mit den gesammelten Daten und formatiert sie.