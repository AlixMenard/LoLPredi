from teams import *
from matches import game
from collections import defaultdict
import pandas as pd
from pprint import pprint

def play_bo(team1, team2, size=1):
        team1 = teams[team1]
        team2 = teams[team2]

        score = [0, 0]
        while all([s < size / 2 for s in score]):
            res = game(team1, team2)
            score[0] += res[0]
            score[1] += res[1]

        return score

def multi_bo(team1, team2, size = 3, repeat=10):
    scores = defaultdict(int)
    for _ in range(repeat):
        s = tuple(play_bo(team1, team2, size))
        scores[s] += 1

    scores_mapped = []
    for s in scores:
        score_key = s[0] - s[1]
        count = scores[s]

        scores_mapped.append((s, score_key, count))
    scores_mapped = sorted(scores_mapped, key=lambda x: x[1], reverse=True)

    res_max = max(scores_mapped, key=lambda x: x[2])[0]

    tot = 0
    for score, _, count in scores_mapped:
        tot += count
        if tot > repeat / 2:
            res_med = score
            break

    return res_max, res_med

teams = Teams()
regions = Regions()

regions.load("regions_data.json")
teams.load("teams_data.json")

world_teams = ["G2 Esports", "Movistar KOI", "Karmine Corp",
               "Team Liquid", "LYON",
               "Team Secret Whales", "CTBC Flying Oyster",
               "LØS",
               "Anyone's Legend", "Bilibili Gaming", "Top Esports", "Invictus Gaming",
               "Gen.G", "Hanwha Life Esports", "T1", "Dplus Kia"]

day1 = (
    ["Gen.G", "Invictus Gaming", 1],
    ["Hanwha Life Esports", "Top Esports", 1],
    ["Bilibili Gaming", "Movistar KOI", 1],
    ["Anyone's Legend", "Karmine Corp", 1],
    ["G2 Esports", "Dplus Kia", 1],
    ["Team Liquid", "CTBC Flying Oyster", 1],
    ["LØS", "T1", 1],
    ["Team Secret Whales", "LYON", 1]
)

for t in world_teams:
    print(t, t in teams.names)

if __name__ == "__main__":
    game_day = pd.DataFrame(columns=["Match", "Raw prediction", "10 Predictions max", "10 Predictions median", "100 Predictions max", "100 Predictions median"])
    for t1, t2, size in day1:
        res1 = play_bo(t1, t2, size)
        res10max, res10med = multi_bo(t1, t2, size=size, repeat=11)
        res100max, res100med = multi_bo(t1, t2, size=size, repeat=101)

        game_day.loc[len(game_day)] = [f"{t1} - {t2}", res1, res10max, res10med, res100max, res100med]

    print(game_day)
    pprint(game_day)

