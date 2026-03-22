from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import requests

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
# THese are fake stats to test pipeline befo0re pull;ong actual MLB stats
def get_mock_team_stats(team_name: str) -> dict:
    """
    Temporary mock stats so we can test the model pipeline.
    Replace later with real MLB API stats.
    """
    mock_data = {
        "Dodgers": {
            "win_pct": 0.620,
            "run_diff_per_game": 1.2,
            "starter_era": 3.20,
            "home_win_pct": 0.650,
            "away_win_pct": 0.590,
            "last10_win_pct": 0.700,
            "rest_days": 1,
        },
        "Giants": {
            "win_pct": 0.510,
            "run_diff_per_game": 0.1,
            "starter_era": 4.05,
            "home_win_pct": 0.540,
            "away_win_pct": 0.470,
            "last10_win_pct": 0.500,
            "rest_days": 0,
        },
    }

    return mock_data.get(
        team_name,
        {
            "win_pct": 0.500,
            "run_diff_per_game": 0.0,
            "starter_era": 4.00,
            "home_win_pct": 0.500,
            "away_win_pct": 0.500,
            "last10_win_pct": 0.500,
            "rest_days": 0,
        },
    )


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

        # get mock stats
        home_stats = get_mock_team_stats(home)
        away_stats = get_mock_team_stats(away)

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
        pitcher_edge = pitcher_era_edge(
            home_stats["starter_era"],
            away_stats["starter_era"]
        )

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
    
@app.get("/mlb-probability")
def mlb_probability():
    game = get_today_mlb_game()

    if game is None:
        return {"error": "No MLB games found today"}

    home = game["home_team"]
    away = game["away_team"]

    team_a_score = 100
    team_b_score = 95

    p_home_win = win_probability(
        team_a_score,
        team_b_score,
        home,
        away
    )

    return {
        "home_team": home,
        "away_team": away,
        "p_home_win": round(p_home_win, 3),
        "p_away_win": round(1 - p_home_win, 3),
        "message": "MLB game auto-statified"
    }

@app.post("/probability")
def probability(payload: ProbabilityRequest) -> Dict[str, Any]:
    team_a_score = 50.0
    team_b_score = 50.0

    selected = {stat.stat_key: stat.weight for stat in payload.selected_stats}
    timezone_weight = selected.get("timezone", 0.0)

    if "net_rating_last10" in selected:
        team_a_score += 20 * selected["net_rating_last10"]

    if "rest_days" in selected:
        team_a_score += 10 * selected["rest_days"]

    if "home_away_split" in selected:
        team_a_score += 15 * selected["home_away_split"]

    p_home_win = win_probability(
        team_a_score,
        team_b_score,
        payload.home_team,
        payload.away_team,
        timezone_weight=timezone_weight
    )

    return {
        "home_team": payload.home_team,
        "away_team": payload.away_team,
        "p_home_win": round(p_home_win, 3),
        "p_away_win": round(1 - p_home_win, 3),
        "message": "You've been Statified",
        "inputs_used": {
            "team_a_score": team_a_score,
            "team_b_score": team_b_score,
            "timezone_weight": timezone_weight,
            "selected_stats": list(selected.keys())
        },
        "selected_stats_count": len(payload.selected_stats),
    }