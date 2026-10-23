import os
import json
import numpy as np
from things import get_last_names

class Region:
    def __init__(self, name: str):
        self.name: str = name
        self.offense_modifier: float = 1.0
        self.safe_modifier: float = 1.0
        self.convert_modifier: float = 1.0
        self.resist_modifier: float = 1.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "offense_modifier": self.offense_modifier,
            "safe_modifier": self.safe_modifier,
            "convert_modifier": self.convert_modifier,
            "resist_modifier": self.resist_modifier,
        }

    def from_dict(self, data: dict):
        self.offense_modifier = data.get("offense_modifier", 1.0)
        self.safe_modifier = data.get("safe_modifier", 1.0)
        self.convert_modifier = data.get("convert_modifier", 1.0)
        self.resist_modifier = data.get("resist_modifier", 1.0)


class Regions:
    _instance = None

    # Singleton pattern to ensure global state shared across Teams/Games
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Regions, cls).__new__(cls)
            cls._instance.regions = {}
            cls._instance.names = set()
        return cls._instance

    def __getitem__(self, name: str) -> Region:
        if name not in self.regions:
            r = Region(name)
            self.regions[name] = r
            self.names.add(name)
        return self.regions[name]

    def save(self, filepath: str = "regions_data.json"):
        data = {name: reg.to_dict() for name, reg in self.regions.items()}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def load(self, filepath: str = "regions_data.json"):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for name, reg_data in data.items():
            reg = self[name]
            reg.from_dict(reg_data)


class Team:
    def __init__(self, name: str, region_name: str = None):
        self.name: str = name
        self.region: Region = Regions()[region_name] if region_name else None

        self.offense: float = 5.5
        self.safe: float = 1.0
        self.convert: float = 4000.0
        self.resist: float = 1.0

    def score(self, medians):
        eff_offense = self.offense * self.region.offense_modifier
        eff_safe = self.safe * self.region.safe_modifier
        eff_convert = self.convert * self.region.convert_modifier
        eff_resist = self.resist * self.region.resist_modifier

        baseline_offense = medians[0]
        baseline_safe = medians[1]
        baseline_convert = medians[2]
        baseline_resist = medians[3]

        exp_kills_for = eff_offense / baseline_safe
        exp_kills_against = baseline_offense / eff_safe

        beta_for = 0.08 / baseline_resist
        gold_for = 30000 + eff_convert * np.log1p(exp_kills_for * beta_for)

        beta_against = 0.08 / eff_resist
        gold_against = 30000 + baseline_convert * np.log1p(exp_kills_against * beta_against)
        
        net_gold = gold_for - gold_against

        return net_gold

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "region": self.region.name if self.region else None,
            "offense": self.offense,
            "safe": self.safe,
            "convert": self.convert,
            "resist": self.resist,
        }

    def from_dict(self, data: dict):
        if data.get("region"):
            self.region = Regions()[data["region"]]
        self.offense = data.get("offense", 5.5)
        self.safe = data.get("safe", 1.0)
        self.convert = data.get("convert", 4000.0)
        self.resist = data.get("resist", 1.0)

    def __add__(self, other: "Team"):
        own_kills = (self.offense * self.region.offense_modifier) / (other.safe * other.region.safe_modifier)
        enn_kills = (other.offense * other.region.offense_modifier) / (self.safe * self.region.safe_modifier)
        gold_r_own = (self.convert * self.region.convert_modifier) / np.maximum(other.resist * other.region.resist_modifier, 1e-3)
        own_gold = own_kills * np.maximum(gold_r_own, 1e-3)
        gold_r_enn = (other.convert * other.region.convert_modifier) / np.maximum(self.resist * self.region.resist_modifier, 1e-3)
        enn_gold = enn_kills * np.maximum(gold_r_enn, 1e-3)
        return (self.name, own_kills, own_gold), (other.name, enn_kills, enn_gold)

class Teams:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Teams, cls).__new__(cls)
            cls._instance.teams = {}
            cls._instance.names = set()
        return cls._instance

    def __getitem__(self, item) -> Team:
        if isinstance(item, tuple):
            name, region = item
        else:
            name, region = item, None

        if not isinstance(name, str):
            raise Exception()

        if name not in self.teams:
            t = Team(name, region)
            self.teams[name] = t
            self.names.add(name)
        elif region and not self.teams[name].region:
            self.teams[name].region = Regions()[region]

        return self.teams[name]

    @property
    def medians(self):
        off, safe, conv, res = [], [], [], []
        for team_name in self.names:
            team = self.teams[team_name]
            off.append(team.offense * team.region.offense_modifier)
            safe.append(team.safe * team.region.safe_modifier)
            conv.append(team.convert * team.region.convert_modifier)
            res.append(team.resist * team.region.resist_modifier)

        return np.median(off), np.median(safe), np.median(conv), np.median(res)

    @property
    def rank(self) -> list[Team]:
        m = self.medians
        ranking = [self.teams[name] for name in self.names]
        ranking.sort(key=lambda x: x.score(m), reverse=True)
        return ranking

    def save(self, filepath: str = "teams_data.json", save_regions: bool = True):
        last_names = get_last_names()
        data = {name: team.to_dict() for name, team in self.teams.items() if name in last_names}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        
        if save_regions:
            Regions().save()

    def load(self, filepath: str = "teams_data.json", load_regions: bool = True):
        if load_regions and os.path.exists("regions_data.json"):
            Regions().load()
            
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        for name, team_data in data.items():
            team = self[name, team_data.get("region")]
            team.from_dict(team_data)


class Game:
    def __init__(self, team1_name, team1_region, team1_kills, team1_golds, team2_name, team2_region, team2_kills, team2_golds, year):
        t = Teams()
        self.team1: Team = t[team1_name, team1_region]
        self.team2: Team = t[team2_name, team2_region]
        self.team1_stats = {"kills": team1_kills, "golds": team1_golds}
        self.team2_stats = {"kills": team2_kills, "golds": team2_golds}
        self.year: int = year


class Schedule:
    def __init__(self):
        self.games: list[Game] = []

        years = os.listdir("match_records")
        for year in years:
            with open(f"match_records/{year}", "r", encoding="utf8") as f:
                t = f.read()
            games = t.strip().split("\n")

            for game in games:
                if not game:
                    continue
                sides = game.split(";")
                sides = [s.split(",") for s in sides]

                g = Game(sides[0][0], sides[0][1], int(sides[0][2]), int(sides[0][3]),
                         sides[1][0], sides[1][1], int(sides[1][2]), int(sides[1][3]),
                         int(year[:-4]))

                self.games.append(g)