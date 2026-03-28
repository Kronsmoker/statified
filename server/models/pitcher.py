from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class PitcherStats:
    name: str
    handedness: str
    k_percent: float
    bb_percent: float
    hr_per_9: float
    hard_hit_percent: float
    innings_per_start: float
    whip: Optional[float] = None
    fip: Optional[float] = None
    gb_percent: Optional[float] = None
    xwoba_allowed: Optional[float] = None


@dataclass
class TeamStats:
    team_name: str
    handedness_split: str
    k_percent: float
    bb_percent: float
    iso: float
    hard_hit_percent: float
    wrc_plus: Optional[float] = None


@dataclass
class GameContext:
    park_factor: float = 100.0
    weather_factor: float = 0.0
    home_pitcher: bool = True
    travel_fatigue: float = 0.0


def clamp(value: float, min_value: float = 0.0, max_value: float = 100.0) -> float:
    return max(min_value, min(value, max_value))


def scale_stat(value: float, low: float, high: float, higher_is_better: bool = True) -> float:
    if high == low:
        return 50.0
    pct = (value - low) / (high - low) * 100.0
    if higher_is_better:
        return clamp(pct)
    return clamp(100.0 - pct)


def k_score(p: PitcherStats) -> float:
    return scale_stat(p.k_percent, 15.0, 35.0, True)


def bb_score(p: PitcherStats) -> float:
    return scale_stat(p.bb_percent, 4.0, 12.0, False)


def hr_score(p: PitcherStats) -> float:
    return scale_stat(p.hr_per_9, 0.5, 2.0, False)


def contact_score(p: PitcherStats) -> float:
    return scale_stat(p.hard_hit_percent, 28.0, 48.0, False)


def depth_score(p: PitcherStats) -> float:
    return scale_stat(p.innings_per_start, 4.0, 7.0, True)


def pitcher_base_strength(p: PitcherStats) -> Dict[str, Any]:
    ks = k_score(p)
    bbs = bb_score(p)
    hrs = hr_score(p)
    cs = contact_score(p)
    ds = depth_score(p)

    base = (
        0.30 * ks +
        0.20 * bbs +
        0.20 * hrs +
        0.20 * cs +
        0.10 * ds
    )

    return {
        "pitcher": p.name,
        "base_strength_score": round(base, 2),
        "components": {
            "k_score": round(ks, 2),
            "bb_score": round(bbs, 2),
            "hr_score": round(hrs, 2),
            "contact_score": round(cs, 2),
            "depth_score": round(ds, 2),
        }
    }


def team_k_adjustment(p: PitcherStats, t: TeamStats) -> float:
    pk = k_score(p)
    tk = scale_stat(t.k_percent, 18.0, 28.0, True)
    return round(((pk - 50) * 0.6 + (tk - 50) * 0.4) / 10.0, 2)


def team_power_adjustment(p: PitcherStats, t: TeamStats) -> float:
    iso_score = scale_stat(t.iso, 0.120, 0.220, True)
    hr_risk = 100 - hr_score(p)
    contact_risk = 100 - contact_score(p)

    danger = (0.5 * iso_score + 0.3 * hr_risk + 0.2 * contact_risk)
    return round(-((danger - 50) / 10.0), 2)


def team_walk_adjustment(p: PitcherStats, t: TeamStats) -> float:
    team_bb = scale_stat(t.bb_percent, 6.0, 11.0, True)
    pitcher_walk = 100 - bb_score(p)

    danger = (0.5 * team_bb + 0.5 * pitcher_walk)
    return round(-((danger - 50) / 12.0), 2)


def park_adjustment(context: GameContext) -> float:
    return round((100 - context.park_factor) / 10.0, 2)


def home_adjustment(context: GameContext) -> float:
    return 0.25 if context.home_pitcher else 0.0


def f5_pitching_edge(p: PitcherStats, t: TeamStats, c: GameContext) -> Dict[str, Any]:
    base = pitcher_base_strength(p)
    base_score = base["base_strength_score"]

    centered = (base_score - 50.0) / 8.0

    k_adj = team_k_adjustment(p, t)
    power_adj = team_power_adjustment(p, t)
    walk_adj = team_walk_adjustment(p, t)
    park_adj = park_adjustment(c)
    home_adj = home_adjustment(c)

    edge = centered + k_adj + power_adj + walk_adj + park_adj + home_adj

    return {
        "pitcher": p.name,
        "opponent": t.team_name,
        "base_score": base_score,
        "adjustments": {
            "k_edge": k_adj,
            "power_risk": power_adj,
            "walk_risk": walk_adj,
            "park": park_adj,
            "home": home_adj
        },
        "f5_edge": round(edge, 2)
    }


def edge_to_probability(edge: float) -> float:
    prob = 0.50 + (edge * 0.03)
    return round(clamp(prob * 100, 1, 99) / 100, 4)


def probability_to_odds(prob: float) -> int:
    if prob >= 0.5:
        return int(round(-(prob / (1 - prob)) * 100))
    return int(round(((1 - prob) / prob) * 100))


def build_pitcher_report(p: PitcherStats, t: TeamStats, c: GameContext) -> Dict[str, Any]:
    base = pitcher_base_strength(p)
    edge = f5_pitching_edge(p, t, c)

    prob = edge_to_probability(edge["f5_edge"])
    odds = probability_to_odds(prob)

    return {
        "base": base,
        "f5": edge,
        "win_probability": prob,
        "fair_odds": odds
    }


if __name__ == "__main__":
    pitcher = PitcherStats(
        name="Cam Schlittler",
        handedness="R",
        k_percent=27.0,
        bb_percent=8.8,
        hr_per_9=0.95,
        hard_hit_percent=40.2,
        innings_per_start=5.4,
    )

    team = TeamStats(
        team_name="Giants",
        handedness_split="vs_RHP",
        k_percent=23.5,
        bb_percent=8.5,
        iso=0.155,
        hard_hit_percent=38.0,
    )

    context = GameContext(park_factor=95.0, home_pitcher=False)

    print(build_pitcher_report(pitcher, team, context))
