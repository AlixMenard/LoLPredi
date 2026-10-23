from teams import *
import numpy as np
from itertools import combinations
from collections import defaultdict

class BO:
    def __init__(self, t1: str, t2: str, t1score: int, t2score:int):
        self.t1: str = t1
        self.t2: str = t2
        self.t1score: int = t1score
        self.t2score: int = t2score
        self.winner: str = t1 if t1score>t2score else t2
        self.size = max(t1score, t2score) * 2 - 1

    def score(self, team:str):
        if team == self.t1:
            return team == self.winner, self.t1score, self.t2score
        return team == self.winner, self.t2score, self.t1score

    def __repr__(self):
        if self.t1 == self.winner:
            return f"{self.t1} {self.t1score} - {self.t2score} {self.t2}"
        return f"{self.t2} {self.t2score} - {self.t1score} {self.t1}"

class Record:
    def __init__(self, team: str):
        self.team: str = team

        self.local_histo: list[BO] = []
        self.inter_histo: list[BO] = []

    @property
    def local_score(self):
        bos = [0, 0]
        nexus = [0, 0]

        for bo in self.local_histo:
            win, won, lost = bo.score(self.team)

            bos[int(not win)] += 1
            nexus[0] += won
            nexus[1] += lost

        return bos, nexus

    @property
    def inter_score(self):
        bos = [0, 0]
        nexus = [0, 0]

        for bo in self.inter_histo:
            win, won, lost = bo.score(self.team)

            bos[int(not win)] += 1
            nexus[0] += won
            nexus[1] += lost

        return bos, nexus

    @property
    def local_f2f(self, opponent: str):
        bos = [0, 0]
        nexus = [0, 0]

        for bo in self.local_histo:
            if bo.t1 != opponent and bo.t2 != opponent:
                continue
            win, won, lost = bo.score(self.team)

            bos[int(not win)] += 1
            nexus[0] += won
            nexus[1] += lost

        return bos, nexus

    @property
    def inter_f2f(self, opponent: str):
        bos = [0, 0]
        nexus = [0, 0]

        for bo in self.inter_histo:
            if bo.t1 != opponent and bo.t2 != opponent:
                continue
            win, won, lost = bo.score(self.team)

            bos[int(not win)] += 1
            nexus[0] += won
            nexus[1] += lost

        return bos, nexus

    def __repr__(self):
        n = len(self.team)
        L = 20 - n
        text = "-"*(L//2) + self.team + "-"*(L//2 + L%2) + "\n"

        texts = []
        for bo in self.local_histo:
            texts.append(bo.__repr__())
        texts = "\n".join(texts)

        return text + texts + "\n"*3

def game(team1: Team, team2: Team):
    #print(f"Game {team1.name} vs {team2.name}")

    limit = 2000

    expected_k1 = (team1.offense * team1.region.offense_modifier) / (team2.safe * team2.region.safe_modifier)
    expected_k2 = (team2.offense * team2.region.offense_modifier) / (team1.safe * team1.region.safe_modifier)

    k1 = np.random.poisson(expected_k1)
    k2 = np.random.poisson(expected_k2)

    alpha1 = team1.convert * team1.region.convert_modifier
    beta1 = 0.08 / np.maximum(team2.resist * team2.region.resist_modifier, 1e-3)
    expected_g1 = 30000 + alpha1 * np.log1p(k1 * beta1)
    g1 = np.random.poisson(expected_g1)

    alpha2 = team2.convert * team2.region.convert_modifier
    beta2 = 0.08 / np.maximum(team1.resist * team1.region.resist_modifier, 1e-3)
    expected_g2 = 30000 + alpha2 * np.log1p(k2 * beta2)
    g2 = np.random.poisson(expected_g2)

    #print(f"kills : {k1} vs {k2}")
    #print(f"golds : {g1} vs {g2}")

    diff = abs(g1 - g2)
    if  diff > limit:
        return (1, 0) if g1 > g2 else (0, 1)

    proba = (limit+diff) / (2*limit)

    result = np.random.random()

    success = result <= proba

    if g1 >= g2:
        return (1, 0) if success else (0, 1)
    return (0, 1) if success else (1, 0)

class League:
    def __init__(self, key: Region|list[str], teams: Teams):
        self.all_teams: Teams = teams

        if type(key) == Region:
            self.region: Region = key
            self.teams: list[str] = [t for t in teams.names if teams[t].region.name == self.region.name]
        if type(key) == list:
            self.teams: list[str] = [t for t in key]

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

        top_cut = min(2**int(np.log2(len(self.teams))) , 8)

        r = self.rank()
        for i, (team, record, detail) in enumerate(r):
            print(f"{i+1}) {team} {record[0]}-{record[1]} ({detail[0]}-{detail[1]})")

        top_teams = [t[0] for t in r][:top_cut]

        matches = []
        for i in range(top_cut//2):
            matches.insert((len(matches)+1)//2, (top_teams[i], top_teams[-i-1]))

        rounds = []
        while matches:
            next = []
            round = []
            for t1, t2 in matches:
                s1, s2 = play_engine(5, t1, t2)
                print(f"{t1} {s1} - {s2} {t2}")
                if s1>s2:
                    next.append(t1)
                else:
                    next.append(t2)
            matches = [(next[2*i], next[2*i+1]) for i in range(len(next)//2)]
        


if __name__ == "__main__":
    teams = Teams()
    regions = Regions() 

    regions.load("regions_data.json")
    teams.load("teams_data.json")

    case_n = 0

    match case_n:
        case 0:
            league = League(regions["EMEA"], teams)
            league.set()
            league.play_regular()
            league.play_po()
        case 1:
            top100 = [t.name for t in teams.rank[:100]]
            memory = {t: [i] for i, t in enumerate(top100)}
            league = League(top100, teams)
            league.set()
            league.play_regular(multi=1000)
            rank = [t[0] for t in league.rank()]
            for i, t in enumerate(rank):
                mrank = memory.get(t)[0]
                memory[t].extend([i, mrank - i])
                
            deltas = [memory[t][2] for t in top100]
            print("std. delta", np.std(deltas))