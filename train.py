import numpy as np
from scipy.special import xlogy
from scipy.optimize import minimize
from tqdm import tqdm
from teams import Schedule, Teams, Regions, Team, Region
import matplotlib.pyplot as plt

print("Initiating...")
schedule = Schedule()
games = schedule.games #[:1000]

teams_container = Teams()
regions_container = Regions()

all_teams = sorted(list(teams_container.names))
all_regions = sorted(list(regions_container.names))

team_to_idx = {name: i for i, name in enumerate(all_teams)}
region_to_idx = {name: i for i, name in enumerate(all_regions)}

num_teams = len(all_teams)
num_regions = len(all_regions)

HALF_LIFE_YEARS = 1.0
LAMBDA_DECAY = np.log(2) / HALF_LIFE_YEARS

def get_game_weight(game_year, current_year=2026):
    age = current_year - game_year
    return np.exp(-LAMBDA_DECAY * age)

# Pre-extract data into numpy arrays for extreme optimization speed
weights = np.array([get_game_weight(getattr(g, 'year', 2026)) for g in games])
t1_idxs = np.array([team_to_idx[g.team1.name] for g in games])
t2_idxs = np.array([team_to_idx[g.team2.name] for g in games])
r1_idxs = np.array([region_to_idx[g.team1.region.name] for g in games])
r2_idxs = np.array([region_to_idx[g.team2.region.name] for g in games])

t1_kills = np.array([g.team1_stats["kills"] for g in games])
t2_kills = np.array([g.team2_stats["kills"] for g in games])
t1_golds = np.array([g.team1_stats["golds"] for g in games])
t2_golds = np.array([g.team2_stats["golds"] for g in games])

def loss_function(params, return_components=False):
    global first_losses, ratio
    exp_params = np.exp(params)
    
    offenses = exp_params[0 : num_teams]
    safes    = exp_params[num_teams : 2*num_teams]
    converts = exp_params[2*num_teams : 3*num_teams] * 4000.0
    resists  = exp_params[3*num_teams : 4*num_teams]
    
    reg_offenses = exp_params[4*num_teams : 4*num_teams + num_regions]
    reg_safes    = exp_params[4*num_teams + num_regions : 4*num_teams + 2*num_regions]
    reg_converts = exp_params[4*num_teams + 2*num_regions : 4*num_teams + 3*num_regions]
    reg_resists  = exp_params[4*num_teams + 3*num_regions : 4*num_teams + 4*num_regions]

    flat_gold = 30000
    beta_rate_base = 0.08
    
    # --- Vectorized Match Calculations ---
    # Team 1 Kills
    lambda_t1_k = np.maximum((offenses[t1_idxs] * reg_offenses[r1_idxs]) / 
                             np.maximum(safes[t2_idxs] * reg_safes[r2_idxs], 1e-3), 1e-3)
    loss_t1_k = 2.0 * (xlogy(t1_kills, t1_kills / lambda_t1_k) - (t1_kills - lambda_t1_k))
    
    # Team 1 Gold
    alpha_t1 = (
        converts[t1_idxs] * reg_converts[r1_idxs]
    )
    beta_t1 = beta_rate_base / np.maximum(
        resists[t2_idxs] * reg_resists[r2_idxs], 1e-3
    )
    exp_t1_g = flat_gold + alpha_t1 * np.log1p(
        t1_kills * beta_t1
    )
    
    loss_t1_g = 100.0 * (
        (t1_golds - exp_t1_g) / np.maximum(t1_golds, 1.0)
    ) ** 2

    # Team 2 Kills
    lambda_t2_k = np.maximum((offenses[t2_idxs] * reg_offenses[r2_idxs]) / 
                             np.maximum(safes[t1_idxs] * reg_safes[r1_idxs], 1e-3), 1e-3)
    loss_t2_k = 2.0 * (xlogy(t2_kills, t2_kills / lambda_t2_k) - (t2_kills - lambda_t2_k))
    
    # Team 2 Gold
    alpha_t2 = (
        converts[t2_idxs] * reg_converts[r2_idxs]
    ) 
    beta_t2 = beta_rate_base / np.maximum(
        resists[t1_idxs] * reg_resists[r1_idxs], 1e-3
    )  
    exp_t2_g = flat_gold + alpha_t2 * np.log1p(
        t2_kills * beta_t2
    ) 
    loss_t2_g = 100.0 * (
        (t2_golds - exp_t2_g) / np.maximum(t2_golds, 1.0)
    ) ** 2


    kills_loss = loss_t1_k + loss_t2_k
    gold_loss = loss_t1_g + loss_t2_g

    match_loss = kills_loss + gold_loss


    reg_penalty = 0.01 * np.sum((params[4*num_teams:] - 0.0) ** 2)
    team_penalty = 0.01 * np.sum((params[0:4*num_teams] - 0.0) ** 2)

    denom = np.maximum(np.sum(weights), 1e-5)
    total = (np.sum(weights * match_loss) / denom) + reg_penalty + team_penalty

    if return_components:
        return total, {
            "kills_loss": np.sum(weights * kills_loss) / denom,
            "gold_loss": np.sum(weights * gold_loss) / denom,
            "reg_penalty": reg_penalty,
            "team_penalty": team_penalty,
        }
    return total


init_params = np.zeros(4 * num_teams + 4 * num_regions)

pbar = tqdm(desc="Optimizing Loss", unit=" iter")

losses = []
components_log = []
def callback(xk):
    current_loss, components = loss_function(xk, return_components=True)
    losses.append(current_loss)
    components_log.append(components)
    pbar.set_postfix({
        "Loss": f"{current_loss:.4f}",
        "kills": f"{components['kills_loss']:.4f}",
        "gold": f"{components['gold_loss']:.4f}",
    })
    pbar.update(1)

res = minimize(
    loss_function, 
    init_params, 
    method='L-BFGS-B', 
    callback=callback,
    options={'maxiter': 2000, 'ftol': 1e-6, 'gtol': 1e-5, 'maxfun': 50000}
)
pbar.close()

print(f"Converged: {res.success} | Iterations: {res.nit} | Message: {res.message}")
if components_log:
    last = components_log[-1]
    print(f"Final loss breakdown -> kills: {last['kills_loss']:.4f}  "
          f"gold: {last['gold_loss']:.4f}  reg_penalty: {last['reg_penalty']:.4f}  "
          f"team_penalty: {last['team_penalty']:.4f}")

if res.success or "STOP" in res.message:
    optimized_exp = np.exp(res.x)
    print("Optimization Finished!")
    
    offenses = optimized_exp[0 : num_teams]
    safes    = optimized_exp[num_teams : 2*num_teams]
    converts = optimized_exp[2*num_teams : 3*num_teams] * 4000.0
    resists  = optimized_exp[3*num_teams : 4*num_teams]
    
    for name, idx in team_to_idx.items():
        team = teams_container[name]
        team.offense = float(offenses[idx])
        team.safe = float(safes[idx])
        team.convert = float(converts[idx])
        team.resist = float(resists[idx])

    reg_offenses = optimized_exp[4*num_teams : 4*num_teams + num_regions]
    reg_safes    = optimized_exp[4*num_teams + num_regions : 4*num_teams + 2*num_regions]
    reg_converts = optimized_exp[4*num_teams + 2*num_regions : 4*num_teams + 3*num_regions]
    reg_resists  = optimized_exp[4*num_teams + 3*num_regions : 4*num_teams + 4*num_regions]
    
    for name, idx in region_to_idx.items():
        reg = regions_container[name]
        reg.offense_modifier = float(reg_offenses[idx])
        reg.safe_modifier = float(reg_safes[idx])
        reg.convert_modifier = float(reg_converts[idx])
        reg.resist_modifier = float(reg_resists[idx])

    teams_container.save("teams_data.json")
    print("Saved optimized parameters to disk.")

    r = teams_container.rank

    print("\n"*2, "Top 5")
    for t in r[:5]:
        print(t.to_dict())
    print("\n"*2, "Bot 5")
    for t in r[-5:]:
        print(t.to_dict())
    print("\n"*2, "Regions")
    for reg in regions_container.names:
        print(regions_container[reg].to_dict())

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].plot(losses)
    axes[0].set_title("Total Loss")
    axes[1].plot([c["kills_loss"] for c in components_log], label="kills")
    axes[1].plot([c["gold_loss"] for c in components_log], label="gold")
    axes[1].set_title("Loss by Channel")
    axes[1].legend()
    plt.tight_layout()
    plt.show()

    t1: Team = teams_container["T1"]
    t2: Team = teams_container["Gen.G"]
    t3: Team = teams_container["HELL PIGS"]
    t4: Team = teams_container["VelbeliKaizokudan"]

    def evaluate_match_printout(team_a, team_b, label_a, label_b):
        k1 = (team_a.offense * team_a.region.offense_modifier) / (
            team_b.safe * team_b.region.safe_modifier
        )
        k2 = (team_b.offense * team_b.region.offense_modifier) / (
            team_a.safe * team_a.region.safe_modifier
        )

        alpha1 = team_a.convert * team_a.region.convert_modifier
        beta1 = 0.08 / np.maximum(
            team_b.resist * team_b.region.resist_modifier, 1e-3
        )
        g1 = 30000 + alpha1 * np.log1p(k1 * beta1)

        alpha2 = team_b.convert * team_b.region.convert_modifier
        beta2 = 0.08 / np.maximum(
            team_a.resist * team_a.region.resist_modifier, 1e-3
        )
        g2 = 30000 + alpha2 * np.log1p(k2 * beta2)

        print(f"{label_a} vs {label_b}")
        print(f"{k1:.2f} kills vs {k2:.2f} kills")
        print(f"{g1:.1f} golds vs {g2:.1f} golds\n")

    print("\n" * 3)
    evaluate_match_printout(t1, t2, "T1", "GEN")  
    evaluate_match_printout(t1, t3, "T1", "nul")  
    evaluate_match_printout(t4, t3, "nul", "nul") 
else:
    print("Optimization failed:", res.message)