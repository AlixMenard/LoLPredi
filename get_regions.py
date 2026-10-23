import datetime
import requests
from functools import lru_cache
from mwrogue.esports_client import EsportsClient
from mwrogue.auth_credentials import AuthCredentials

def get_team_region(site):
    TARGET_REGIONS = ["Korea", "China", "EMEA", "North America", "Asia Pacific", "Brazil"]
    renames = {"Korea":"KR", "China":"CH", "EMEA":"EMEA","North America":"NA", "Asia Pacific":"APAC","Brazil":"BRZ"}
    region_where = " OR ".join([f"Region = '{r}'" for r in TARGET_REGIONS])

    print("Building filtered team region lookup dictionary...")
    team_regions = {}
    offset = 0
    limit = 500

    while True:
        region_resp = site.cargo_client.query(
            tables="Teams",
            fields="Name, Region", 
            where=region_where,  
            limit=limit,
            offset=offset
        )
        if not region_resp:
            break
            
        for row in region_resp:
            if row['Name'] and row['Region']:
                team_regions[row['Name']] = renames[row['Region']]
                
        offset += limit
    
    return team_regions

exceptions = {
    "LYON (2024 American Team)":          "NA",
    "ZEN Esports (Vietnamese Team)":      "APAC",
    "9Gaming":                            "APAC",
    "Ninjas in Pyjamas.CN":               "CH",
    "One Round Specialists":              "APAC",
    "100 Thieves":                        "NA",
    "QT DIG":                             "APAC",
    "Dplus KIA":                          "KR",
    "West Point Esports Philippines":     "APAC",
    "Never Give Up (Vietnamese Team)":    "APAC",
    "Team Flash.Vietnam":                 "APAC",
    "Dream in 24":                        "APAC",
    "Vortex (Japanese Team)" :            "APAC",
    "Deltan Gaming":                      "APAC",
    "GenZ Gaming (2025 Vietnamese Team)": "APAC",
    "Night Cap":                          "APAC",
    "Hungkuang Falcon":                   "APAC",
    "Black Dog":                          "APAC",
    "VeLocitY (Japanese Team)":           "APAC",
    "Hands":                              "APAC",
    "Movistar R7":                        "BRZ",
    "INFINITY":                           "BRZ",
    "Team Secret (Vietnamese Team)":      "APAC",
    "CERBERUS Esports (Vietnamese Team)": "APAC",
    "Six Karma":                          "BRZ",
    "All Knights":                        "BRZ",
    "Rainbow Warriors":                   "APAC",
    "Team Aze":                           "BRZ",
    "SBTC Esports":                       "APAC",
    "The Kings":                          "BRZ",
    "PEACE (Oceanic Team)":               "APAC",
    "Istanbul Wildcats":                  "EMEA",
    "Misfits Gaming":                     "EMEA",
    "Genius Esports":                     "APAC",
    "Rainbow7":                           "BRZ",
    "AS Esports":                         "APAC",
    "Rensga Esports":                     "BRZ",
    "XTEN Esports":                       "BRZ",
    "Globant Emerald":                    "BRZ",
    "Burst The Sky Esports":              "APAC",
    "Galatasaray Esports":                "EMEA",
    "Unicorns of Love.CIS":               "EMEA",
    "Furious Gaming":                     "BRZ",
    "Kaos Latin Gamers":                  "BRZ",
    "Ranking Esports":                    "APAC",
    "AG.AL":                              "CH",
    "MIBR.LOS":                           "BRZ",
    "1TAP DINO":                        "APAC",
}