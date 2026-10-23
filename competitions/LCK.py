from teams import *
import numpy as np
from itertools import combinations
from collections import defaultdict

from matches import BO, Record, game

class LEC:
    def __init__(self):
        self.all_teams: Teams = Teams()

        regions = Regions()
        regions.load("regions_data.json")
        self.all_teams.load("teams_data.json")

        self.region: Region = regions["KR"]
        self.teams: list[str] = [t for t in self.all_teams.names if self.all_teams[t].region.name == self.region.name]

        self.has_ranking = False

    def __getitem__(self, team: str) -> Team|None:
        if not isinstance(team, str):
            raise Exception()

        if team not in self.teams:
            return None

        return self.all_teams[team]

    def reset(self):
        self.records = {team : Record(team) for team in self.teams}
        self.has_ranking = False
    set = reset

    def play_bo(self, size: int, t1: str, t2: str):
        team1 = self.all_teams[t1]
        team2 = self.all_teams[t2]

        scores = [0, 0]
        while all([s < size / 2 for s in scores]):
            res = game(team1, team2)
            #print(f"{t1 if res == (1, 0) else t2} wins.")
            scores[0] += res[0]
            scores[1] += res[1]

        return scores

    def multi_play_bo(self, size: int, t1: str, t2: str, n:int):
        scores = defaultdict(int)
        for _ in range(n):
            s = tuple(self.play_bo(size, t1, t2))
            scores[s] += 1
        return max(scores, key=lambda x: scores[x])

    def play_regular(self, multi = 0):
        if not multi:
            play_engine = self.play_bo
        else:
            play_engine = lambda x, y, z : self.multi_play_bo(x, y, z, multi)

        for t1, t2 in combinations(self.teams, 2):
            scores = play_engine(3, t1, t2)

            bo = BO(t1, t2, *scores)
            self.records[t1].local_histo.append(bo)
            self.records[t2].local_histo.append(bo)

        self.has_ranking = True

    def rank(self):
        teams = list(self.records.keys())

        teams = [(t, *self.records[t].local_score) for t in teams]

        teams = sorted(teams, key = lambda x : (x[1][0] - x[1][1], x[2][0] - x[2][1]), reverse=True)
        return teams

    def play_po(self, multi = 0):
        if not multi:
            play_engine = self.play_bo
        else:
            play_engine = lambda x, y, z : self.multi_play_bo(x, y, z, multi)

        if not self.has_ranking :
            return

        top_cut = 6

        r = self.rank()
        print("### Regular season results")
        for i, (team, record, detail) in enumerate(r):
            print(f"{i+1}) {team} {record[0]}-{record[1]} ({detail[0]}-{detail[1]})")

        top_teams = [t[0] for t in r][:top_cut]

        # Round 1
        print("### Round 1")
        m11s1, m11s2 = play_engine(5, top_teams[0], top_teams[3])
        m11w = top_teams[0] if m11s1 > m11s2 else top_teams[3]
        m11l = top_teams[0] if m11s1 < m11s2 else top_teams[3]
        
        m12s1, m12s2 = play_engine(5, top_teams[1], top_teams[2])
        m12w = top_teams[1] if m12s1 > m12s2 else top_teams[2]
        m12l = top_teams[1] if m12s1 < m12s2 else top_teams[2]

        print(f"{top_teams[0]} {m11s1} - {m11s2} {top_teams[3]}")
        print(f"{top_teams[1]} {m12s1} - {m12s2} {top_teams[2]}")
        
        # Round 2
        print("### Round 2")
        m21s1, m21s2 = play_engine(5, m11w, m12w)
        m21w = m11w if m21s1 > m21s2 else m12w
        m21l = m11w if m21s1 < m21s2 else m12w
        
        m22s1, m22s2 = play_engine(5, m12l, top_teams[4])
        m22w = m12l if m22s1 > m22s2 else top_teams[4]
        
        m23s1, m23s2 = play_engine(5, m11l, top_teams[5])
        m23w = m11l if m23s1 > m23s2 else top_teams[5]

        print(f"{m11w} {m21s1} - {m21s2} {m12w}")
        print(f"{m12l} {m22s1} - {m22s2} {top_teams[4]}")
        print(f"{m11l} {m23s1} - {m23s2} {top_teams[5]}")
        
        # Round 3
        print("### Round 3")
        m31s1, m31s2 = play_engine(5, m22w, m23w)
        m31w = m22w if m31s1 > m31s2 else m23w
        
        m32s1, m32s2 = play_engine(5, m21l, m31w)
        m32w = m21l if m32s1 > m32s2 else m31w
        
        print(f"{m22w} {m31s1} - {m31s2} {m23w}")
        print(f"{m21l} {m32s1} - {m32s2} {m31w}")

        #Final
        print("### Final")
        mfs1, mfs2 = play_engine(5, m21w, m32w)
        champion = m21w if mfs1 > mfs2 else m32w    
        
        print(f"{m21w} {mfs1} - {mfs2} {m32w}")

        print(f"Champion : {champion}")


if __name__ == "__main__":
    case_n = 0
    match case_n:
        case 0 :
            league = LEC()
            league.set()
            league.play_regular()
            league.play_po()
        case 1 :
            league = LEC()
            league.set()
            league.play_regular(multi = 10)
            league.play_po(multi = 10)
        case 2 :
            league = LEC()
            league.set()
            league.play_regular(multi = 100)
            league.play_po(multi = 100)