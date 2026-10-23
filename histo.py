import datetime
import requests
from functools import lru_cache
import os
import shutil
from collections import defaultdict
from tqdm import tqdm

from mwrogue.esports_client import EsportsClient
from mwrogue.auth_credentials import AuthCredentials

from get_regions import get_team_region, exceptions

WIKI_USER = "NokatirBot@Histo" 
WIKI_PASS = "6ug2nflvpnr5recl05uijq0gpo74h9bq"

credentials = AuthCredentials(username=WIKI_USER, password=WIKI_PASS)
site = EsportsClient('lol', credentials=credentials)

team_regions = get_team_region(site)

TOP_LEAGUES = ["LCK", "LPL", "LEC", "LCS", "PCS", "VCS", "CBLOL", "LJL", "LCP",
               "LCO", "LLA", "LTA", "World", "MSI", "First Stand", "FST", "EWC"]
league_where = [f"T.Name LIKE '%{league}%'" for league in TOP_LEAGUES]
FLOP_LEAGUES = ["qualifier", "academy", "challenger", "LCK AS", "Promotion", "LCK CL", "Schneider", "LPLOL", "Fan Clash", "Marbella", 
                "All-Star", "Game Changers", "Proving Grounds", "Academic", "GIRLGAMER", "Wildcard", "LCP OPQ"]
not_league_where = [f"T.Name NOT LIKE '%{league}%'" for league in FLOP_LEAGUES]
start_2023 = "2023-01-01"
where=f"""
(
    {" OR ".join(league_where)}
)
AND {" AND ".join(not_league_where)}
AND MS.DateTime_UTC >= '{start_2023}'
AND MS.Winner IS NOT NULL
"""

print("Building team name rename tracking dictionary...")
rename_timeline = []
offset = 0
limit = 500

while True:
    rename_resp = site.cargo_client.query(
        tables="TeamRenames",
        fields="OriginalName, NewName, Date", 
        order_by="Date ASC", 
        limit=limit,
        offset=offset
    )
    if not rename_resp:
        break
        
    for row in rename_resp:
        rename_timeline.append({
            'old': row['OriginalName'],
            'new': row['NewName'],
            'date': row['Date']
        })
    offset += limit

tbans = ["Cloud9"]
rename_timeline = [row for row in rename_timeline if all(v not in tbans for v in row.values())]

@lru_cache(maxsize=None)
def get_current_name(team_name, start_date="0000-00-00"):
    current_name = team_name
    current_date = start_date
    
    while True:
        found_next_rename = False
        for rename in rename_timeline:
            if rename['old'] == current_name and rename['date'] > current_date:
                current_name = rename['new']
                current_date = rename['date']
                found_next_rename = True
                break 
        
        if not found_next_rename:
            break
    
    if current_name in exceptions.keys():
        region = exceptions[current_name]
    else:
        region = team_regions[current_name]

    return current_name, region

def get_matches(cut = True):
    print(f"Fetching competitive match history from {start_2023} onward...")
    all_matches = []
    offset = 0

    while True:
        response = site.cargo_client.query(
            tables="MatchSchedule=MS, Tournaments=T",
            join_on="MS.OverviewPage=T.OverviewPage",
            fields=(
                "MS.MatchId, MS.DateTime_UTC, T.Name=Tournament, "
                "MS.Team1, MS.Team2, MS.Team1Score, MS.Team2Score, MS.Winner"
            ),
            where=where,
            order_by="MS.DateTime_UTC DESC",
            limit=limit,
            offset=offset
        )
        
        if not response:
            break
            
        all_matches.extend(response)
        offset += limit
        print(f"Retrieved {len(all_matches)} series...")
        
        if cut and len(all_matches) >= 1000: break 
    return all_matches

all_matches = get_matches(cut = False)

print(f"\nSuccessfully found {len(all_matches)} series. Fetching in-game kill metrics...")
game_kills_map = {}

def get_games(cut = True):
    global all_matches
    offset = 0
    fails = set()
    while True:
        games_response = site.cargo_client.query(
            tables="ScoreboardGames=SG, MatchSchedule=MS, Tournaments=T",
            join_on="SG.MatchId=MS.MatchId, MS.OverviewPage=T.OverviewPage",
            fields="SG.Tournament=Tournament, SG.MatchId, SG.Team1, SG.Team1Kills, SG.Team1Gold, SG.Team2, SG.Team2Kills, SG.Team2Gold, SG.N_GameInMatch=GameInMatch, SG.WinTeam ",
            where=where,
            order_by="MS.DateTime_UTC DESC",
            limit=limit,
            offset=offset
        )
        
        if not games_response:
            break
            
        for game in games_response:
            m_id = game['MatchId']
            if m_id not in game_kills_map:
                game_kills_map[m_id] = []

            do = True
            try:
                t1_name, t1_region = get_current_name(game.get("Team1"))
            except Exception as e:
                if (t := game.get("Team1")) in fails:
                    continue
                fails.add(t)
                do = False
                print(game, "t1")
                print(e)
                input()
            try:
                t2_name, t2_region = get_current_name(game.get("Team2"))
            except Exception as e:
                if (t := game.get("Team2")) in fails:
                    continue
                fails.add(t)
                do = False
                print(game, "t2")
                print(e)
                input()
            
            if do:
                game_kills_map[m_id].append({
                    'game_num': game['GameInMatch'],
                    "Team1" : {"Name": t1_name, "Kills": game.get("Team1Kills"), "Golds": game.get("Team1Gold"), "Region": t1_region},
                    "Team2" : {"Name": t2_name, "Kills": game.get("Team2Kills"), "Golds": game.get("Team2Gold"), "Region": t2_region},
                    "Winner": game["WinTeam"]
                })
            
        offset += limit

    tbans = ["LOL Legends Match on CHZZK"]
    all_matches = [match for match in all_matches if match["Tournament"] not in tbans]

    return all_matches

all_matches = get_games(cut = False)

dates = [x["DateTime UTC"] for x in all_matches]
max_year = int(max(dates)[:4])



if os.path.exists("match_records"):
    shutil.rmtree("match_records")
os.mkdir("match_records")

all_matches = sorted(all_matches, key=lambda x: x["DateTime UTC"])
years = defaultdict(list)
for match in tqdm(all_matches):
    date = match["DateTime UTC"]
    year = int(date[:4])

    match_id = match["MatchId"]

    games = game_kills_map.get(match_id, False)
    if not games:
        continue

    for game in games:
        t1, t2 = game["Team1"]["Name"], game["Team2"]["Name"]
        team1 = {
            "name": t1,
            "region": game["Team1"]["Region"],
            "kills": game["Team1"]["Kills"],
            "golds": game["Team1"]["Golds"]
        }
        team2 = {
            "name": t2,
            "region": game["Team2"]["Region"],
            "kills": game["Team2"]["Kills"],
            "golds": game["Team2"]["Golds"]
        }

        if game["Winner"] == t2:
            team1, team2 = team2, team1

        m_rec = {
            "team1" : team1,
            "team2" : team2,
            "date" : date,
            "num" : game["game_num"]
        }
        years[year].append(dict(m_rec))

for year in range(2023, max_year+1):
    games = years[year]
    games = sorted(games, key=lambda x: (x["date"], x["num"]))

    lines = []
    for g in tqdm(games):
        t1, t2 = g["team1"], g["team2"]
        line = f"{t1["name"]},{t1["region"]},{t1["kills"]},{t1["golds"]};{t2["name"]},{t2["region"]},{t2["kills"]},{t2["golds"]}"
        lines.append(line)

    logs = "\n".join(lines)
    with open(fr"match_records/{year}.lol", "w", encoding='utf-8') as f:
        f.write(logs)

from things import func1, renames, func2
func1()
func2()
renames()