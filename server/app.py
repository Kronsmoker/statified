from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import requests
import csv
import os
from datetime import date, datetime, timedelta
from models.pitcher import build_pitcher_report, PitcherStats, TeamStats, GameContext

from models.probability import win_probability, win_probability_from_expected_runs
from models.ratings import team_power_rating, team_rating_diff
from models.baseball_stats import (
    pitcher_era_edge,
    home_field_advantage,
    rest_days_edge,
    last10_edge,
    home_away_split_edge,
)
from models.expected_runs import expected_home_runs, expected_away_runs

app = FastAPI(title="Statified API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StatSelection(BaseModel):
    stat_key: str
    weight: float = 1.0


class ProbabilityRequest(BaseModel):
    sport: str
    league: str
    home_team: str
    away_team: str
    selected_stats: List[StatSelection]


@app.get("/health")
def health():
    return {"status": "ok"}


def get_today_mlb_games():
    url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1"
    res = requests.get(url, timeout=10)
    res.raise_for_status()
    data = res.json()

    dates = data.get("dates", [])
    if not dates:
        return []

    games = dates[0].get("games", [])
    all_games = []

    for game in games:
        away = game["teams"]["away"]["team"]["name"]
        home = game["teams"]["home"]["team"]["name"]
        status = game["status"]["detailedState"]
        away_score = game["teams"]["away"].get("score")
        home_score = game["teams"]["home"].get("score")

        all_games.append(
            {
                "away_team": away,
                "home_team": home,
                "away_score": away_score,
                "home_score": home_score,
                "status": status,
            }
        )

    return all_games


def get_today_mlb_game():
    games = get_today_mlb_games()

    if not games:
        return None

    for game in games:
        if game["status"] == "Scheduled":
            return game

    return games[0]
# THese are real actual MLB stats from current season
def get_team_id_map() -> dict:
    url = "https://statsapi.mlb.com/api/v1/teams"
    res = requests.get(url, params={"sportId": 1}, timeout=10)
    res.raise_for_status()
    data = res.json()

    teams = data.get("teams", [])
    return {team["name"]: team["id"] for team in teams}


def get_team_games(team_id: int, start_date: str, end_date: str) -> list:
    url = "https://statsapi.mlb.com/api/v1/schedule"
    params = {
        "sportId": 1,
        "teamId": team_id,
        "startDate": start_date,
        "endDate": end_date,
    }
    res = requests.get(url, params=params, timeout=10)
    res.raise_for_status()
    data = res.json()

    all_games = []
    for d in data.get("dates", []):
        all_games.extend(d.get("games", []))
    return all_games


def pct(wins: int, losses: int) -> float:
    total = wins + losses
    if total == 0:
        return 0.500
    return wins / total


def did_team_win(game: dict, team_id: int) -> bool:
    away_team_id = game["teams"]["away"]["team"]["id"]
    home_team_id = game["teams"]["home"]["team"]["id"]

    away_score = game["teams"]["away"].get("score", 0)
    home_score = game["teams"]["home"].get("score", 0)

    if team_id == home_team_id:
        return home_score > away_score
    return away_score > home_score


def get_real_team_stats(team_name: str) -> dict:
    team_ids = get_team_id_map()
    team_id = team_ids.get(team_name)

    if team_id is None:
        raise ValueError(f"Unknown MLB team: {team_name}")

    today = date.today()
    season = today.year

    # good enough for regular season data pull
    season_start = date(season, 3, 1).isoformat()
    today_str = today.isoformat()

    games = get_team_games(team_id, season_start, today_str)

    final_games = []
    for game in games:
        state = game.get("status", {}).get("abstractGameState")
        if state != "Final":
            continue

        away_team_id = game["teams"]["away"]["team"]["id"]
        home_team_id = game["teams"]["home"]["team"]["id"]

        away_score = game["teams"]["away"].get("score", 0)
        home_score = game["teams"]["home"].get("score", 0)

        if team_id == home_team_id:
            is_home = True
            team_score = home_score
            opp_score = away_score
        elif team_id == away_team_id:
            is_home = False
            team_score = away_score
            opp_score = home_score
        else:
            continue

        game_date = game.get("gameDate", "")

        final_games.append({
            "game_date": game_date,
            "is_home": is_home,
            "team_score": team_score,
            "opp_score": opp_score,
            "won": team_score > opp_score,
        })

    final_games.sort(key=lambda g: g["game_date"])

    if not final_games:
        return {
            "win_pct": 0.500,
            "run_diff_per_game": 0.0,
            "starter_era": None,
            "home_win_pct": 0.500,
            "away_win_pct": 0.500,
            "last10_win_pct": 0.500,
            "rest_days": 0,
        }

    wins = sum(1 for g in final_games if g["won"])
    losses = len(final_games) - wins

    runs_for = sum(g["team_score"] for g in final_games)
    runs_against = sum(g["opp_score"] for g in final_games)
    run_diff_per_game = (runs_for - runs_against) / len(final_games)

    home_games = [g for g in final_games if g["is_home"]]
    away_games = [g for g in final_games if not g["is_home"]]

    home_wins = sum(1 for g in home_games if g["won"])
    home_losses = len(home_games) - home_wins

    away_wins = sum(1 for g in away_games if g["won"])
    away_losses = len(away_games) - away_wins

    last10 = final_games[-10:]
    last10_wins = sum(1 for g in last10 if g["won"])
    last10_losses = len(last10) - last10_wins

    last_game_dt = datetime.fromisoformat(final_games[-1]["game_date"].replace("Z", "+00:00")).date()
    rest_days = max((today - last_game_dt).days - 1, 0)

    return {
        "win_pct": round(pct(wins, losses), 3),
        "run_diff_per_game": round(run_diff_per_game, 3),
        "starter_era": None,
        "home_win_pct": round(pct(home_wins, home_losses), 3),
        "away_win_pct": round(pct(away_wins, away_losses), 3),
        "last10_win_pct": round(pct(last10_wins, last10_losses), 3),
        "rest_days": rest_days,
    }


@app.get("/mlb-games")
def mlb_games():
    games = get_today_mlb_games()

    if not games:
        return {"error": "No MLB games found today"}

    return {"games": games}

@app.get("/mlb-games-with-probabilities")
def mlb_games_with_probabilities():
    games = get_today_mlb_games()

    if not games:
        return {"error": "No MLB games found today"}

    results = []

    for game in games:
        home = game["home_team"]
        away = game["away_team"]

        # get real stats
        home_stats = get_real_team_stats(home)
        away_stats = get_real_team_stats(away)

        # ratings
        home_rating = team_power_rating(
            home_stats["win_pct"],
            home_stats["run_diff_per_game"]
        )
        away_rating = team_power_rating(
            away_stats["win_pct"],
            away_stats["run_diff_per_game"]
        )

        rating_diff = team_rating_diff(home_rating, away_rating)

        # edges
        pitcher_edge = 0.0

        home_field = home_field_advantage()

        rest_edge = rest_days_edge(
            home_stats["rest_days"],
            away_stats["rest_days"]
        )

        form_edge = last10_edge(
            home_stats["last10_win_pct"],
            away_stats["last10_win_pct"]
        )

        split_edge = home_away_split_edge(
            home_stats["home_win_pct"],
            away_stats["away_win_pct"]
        )

        # expected runs
        home_runs = expected_home_runs(
            base_runs=4.5,
            rating_diff=rating_diff,
            pitcher_edge=pitcher_edge,
            home_field=home_field,
            rest_edge=rest_edge,
            form_edge=form_edge,
            split_edge=split_edge,
        )

        away_runs = expected_away_runs(
            base_runs=4.5,
            rating_diff=rating_diff,
            pitcher_edge=pitcher_edge,
            home_field=home_field,
            rest_edge=rest_edge,
            form_edge=form_edge,
            split_edge=split_edge,
        )

        # probability
        p_home_win = win_probability_from_expected_runs(home_runs, away_runs)

        results.append({
            "home_team": home,
            "away_team": away,
            "away_score": game["away_score"],
            "home_score": game["home_score"],
            "status": game["status"],
            "expected_home_runs": round(home_runs, 2),
            "expected_away_runs": round(away_runs, 2),
            "p_home_win": round(p_home_win, 3),
            "p_away_win": round(1 - p_home_win, 3),
        })

    return {"games": results}
    
# @app.get("/mlb-probability")
# def mlb_probability():
#     game = get_today_mlb_game()

#     if game is None:
#         return {"error": "No MLB games found today"}

#     home = game["home_team"]
#     away = game["away_team"]

#     team_a_score = 100
#     team_b_score = 95

#     p_home_win = win_probability(
#         team_a_score,
#         team_b_score,
#         home,
#         away
#     )

#     return {
#         "home_team": home,
#         "away_team": away,
#         "p_home_win": round(p_home_win, 3),
#         "p_away_win": round(1 - p_home_win, 3),
#         "message": "MLB game auto-statified"
#     }

def log_prediction(result):
    file_path = "predictions.csv"

    row = {
        "date": datetime.now().isoformat(),
        "home_team": result["home_team"],
        "away_team": result["away_team"],
        "p_home_win": result["p_home_win"],
        "expected_home_runs": result["expected_home_runs"],
        "expected_away_runs": result["expected_away_runs"],
        "selected_stats": "|".join(result["inputs_used"]["selected_stats"]),
        # 🔥 IMPORTANT — model features (for ML later)
        "rating_diff": result["inputs_used"].get("rating_diff", 0),
        "pitcher_edge": result["inputs_used"].get("pitcher_edge", 0),
        "rest_edge": result["inputs_used"].get("rest_edge", 0),
        "form_edge": result["inputs_used"].get("form_edge", 0),
        "split_edge": result["inputs_used"].get("split_edge", 0),
        "timezone_edge": result["inputs_used"].get("timezone_edge", 0),

        # 🔥 add later manually
        "actual_result": "",
        
    }

    file_exists = os.path.isfile(file_path)

    with open(file_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


@app.post("/probability")
def probability(payload: ProbabilityRequest) -> Dict[str, Any]:
    selected = {stat.stat_key: stat.weight for stat in payload.selected_stats}
    pitcher_stats_selected = "pitcher_stats" in selected

    home_stats = get_real_team_stats(payload.home_team)
    away_stats = get_real_team_stats(payload.away_team)

    home_rating = team_power_rating(
        home_stats["win_pct"],
        home_stats["run_diff_per_game"]
    )
    away_rating = team_power_rating(
        away_stats["win_pct"],
        away_stats["run_diff_per_game"]
    )

    base_rating_diff = team_rating_diff(home_rating, away_rating)

    rating_diff = base_rating_diff * 0.10
    pitcher_edge = 0.0
    home_field = 0.0
    rest_edge = 0.0
    form_edge = 0.0
    split_edge = 0.0
    timezone_edge = 0.0

    if "last10" in selected:
        form_edge = last10_edge(
            home_stats["last10_win_pct"],
            away_stats["last10_win_pct"]
        ) * 0.20 * selected["last10"]

    if "rest_days" in selected:
        rest_edge = rest_days_edge(
            home_stats["rest_days"],
            away_stats["rest_days"]
        ) * 0.25 * selected["rest_days"]

    if "home_away_split" in selected:
        home_field = home_field_advantage()
        split_edge = home_away_split_edge(
            home_stats["home_win_pct"],
            away_stats["away_win_pct"]
        ) * 0.25 * selected["home_away_split"]

    if "timezone" in selected:
        timezone_edge = 0.05 * selected["timezone"]

    if pitcher_stats_selected:
        home_pitcher = PitcherStats(
            name="Home Pitcher",
            handedness="R",
            k_percent=25.0,
            bb_percent=7.0,
            hr_per_9=1.0,
            hard_hit_percent=38.0,
            innings_per_start=5.5,
        )

        away_pitcher = PitcherStats(
            name="Away Pitcher",
            handedness="R",
            k_percent=22.0,
            bb_percent=9.0,
            hr_per_9=1.3,
            hard_hit_percent=42.0,
            innings_per_start=5.0,
        )

        home_team_ctx = TeamStats(
            team_name=payload.away_team,
            handedness_split="vs_RHP",
            k_percent=23.0,
            bb_percent=8.0,
            iso=0.150,
            hard_hit_percent=38.0,
        )

        away_team_ctx = TeamStats(
            team_name=payload.home_team,
            handedness_split="vs_RHP",
            k_percent=23.0,
            bb_percent=8.0,
            iso=0.150,
            hard_hit_percent=38.0,
        )

        home_context = GameContext(home_pitcher=True)
        away_context = GameContext(home_pitcher=False)

        home_report = build_pitcher_report(home_pitcher, home_team_ctx, home_context)
        away_report = build_pitcher_report(away_pitcher, away_team_ctx, away_context)

        pitcher_edge = (home_report["f5"]["f5_edge"] - away_report["f5"]["f5_edge"]) * 0.15

    home_runs = expected_home_runs(
        base_runs=4.5,
        rating_diff=rating_diff,
        pitcher_edge=pitcher_edge,
        home_field=home_field,
        rest_edge=rest_edge + timezone_edge,
        form_edge=form_edge,
        split_edge=split_edge,
    )

    away_runs = expected_away_runs(
        base_runs=4.5,
        rating_diff=rating_diff,
        pitcher_edge=pitcher_edge,
        home_field=home_field,
        rest_edge=rest_edge + timezone_edge,
        form_edge=form_edge,
        split_edge=split_edge,
    )

    p_home_win = win_probability_from_expected_runs(home_runs, away_runs)

    biggest_edge_name = "None"
    biggest_edge_value = 0.0

    edge_map = {
        "rating_diff": rating_diff,
        "pitcher_edge": pitcher_edge,
        "home_field": home_field,
        "rest_edge": rest_edge,
        "form_edge": form_edge,
        "split_edge": split_edge,
        "timezone_edge": timezone_edge,
    }

    if edge_map:
        biggest_edge_name = max(edge_map, key=lambda k: abs(edge_map[k]))
        biggest_edge_value = edge_map[biggest_edge_name]

    result = {
        "home_team": payload.home_team,
        "away_team": payload.away_team,
        "p_home_win": round(p_home_win, 3),
        "p_away_win": round(1 - p_home_win, 3),
        "expected_home_runs": round(home_runs, 2),
        "expected_away_runs": round(away_runs, 2),
        "message": "You've been Statified",
        "selected_stats_count": len(payload.selected_stats),
        "biggest_edge": {
            "name": biggest_edge_name,
            "value": round(biggest_edge_value, 3),
        },
        "inputs_used": {
            "selected_stats": list(selected.keys()),
            "home_stats": home_stats,
            "away_stats": away_stats,
            "pitcher_stats_selected": pitcher_stats_selected,
            "rating_diff": round(rating_diff, 3),
            "pitcher_edge": round(pitcher_edge, 3),
            "rest_edge": round(rest_edge, 3),
            "form_edge": round(form_edge, 3),
            "split_edge": round(split_edge, 3),
            "timezone_edge": round(timezone_edge, 3),
        }
        },

    log_prediction(result)

    return result

@app.get("/test-pitcher")
def test_pitcher():
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

    return build_pitcher_report(pitcher, team, context)
