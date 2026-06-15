import requests
import csv
import os
import pandas as pd
import sqlite3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import date, datetime, timedelta
from models.bullpen import calculate_bullpen_breakdown_score
from models.pitcher import build_pitcher_report, PitcherStats, TeamStats, GameContext
from models.run_regression_index import build_run_regression_index
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
from fastapi.responses import FileResponse

app = FastAPI(title="Statified API")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "statified.db")

print("DB_FILE =", DB_FILE)

@app.get("/debug-db")
def debug_db():
    return {
        "DB_FILE": DB_FILE,
        "absolute": os.path.abspath(DB_FILE),
        "exists": os.path.exists(DB_FILE)
    }

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            home_team TEXT,
            away_team TEXT,
            p_home_win REAL,
            expected_home_runs REAL,
            expected_away_runs REAL,
            selected_stats TEXT,
            rating_diff REAL,
            pitcher_edge REAL,
            rest_edge REAL,
            form_edge REAL,
            split_edge REAL,
            timezone_edge REAL,
            actual_result INTEGER,
            model_name TEXT
        )
    """)
    
    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN model_name TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","https://statified.vercel.app", "https://statified.app", "https://www.statified.app"],
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
    model_name: str = "manual"


MODEL_PRESETS = {
    "model_1_pitcher_bullpen_last10": [
        StatSelection(stat_key="pitcher_stats", weight=0.40),
        StatSelection(stat_key="bullpen_breakdown_score", weight=0.35),
        StatSelection(stat_key="last10", weight=0.25),
    ],
    "model_2_pitcher_rest": [
        StatSelection(stat_key="pitcher_stats", weight=0.70),
        StatSelection(stat_key="rest_days", weight=0.30),
    ],
    "model_3_pitcher_bullpen": [
        StatSelection(stat_key="pitcher_stats", weight=0.55),
        StatSelection(stat_key="bullpen_breakdown_score", weight=0.45),
    ],
}


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

def get_game_by_teams(home_team: str, away_team: str):
    games = get_today_mlb_games()

    for game in games:
        if game["home_team"] == home_team and game["away_team"] == away_team:
            return game

    return None


def get_actual_result_from_game(game: dict):
    if not game:
        return None

    status = game.get("status", "").lower()

    # allow more "final-like" states
    if not any(s in status for s in ["final", "game over"]):
        return None

    home_score = game.get("home_score")
    away_score = game.get("away_score")

    if home_score is None or away_score is None:
        return None

    return 1 if home_score > away_score else 0


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
            "rri_5": 0.0,
        }

    rri_df = pd.DataFrame([
        {
            "team": team_name,
            "date": g["game_date"],
            "runs_scored": g["team_score"],
        }
        for g in final_games
    ])

    rri_df = build_run_regression_index(rri_df)
    latest_rri = rri_df.iloc[-1]["rri_5"]

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

    last_game_dt = datetime.fromisoformat(
        final_games[-1]["game_date"].replace("Z", "+00:00")
    ).date()
    rest_days = max((today - last_game_dt).days - 1, 0)

    return {
        "win_pct": round(pct(wins, losses), 3),
        "run_diff_per_game": round(run_diff_per_game, 3),
        "starter_era": None,
        "home_win_pct": round(pct(home_wins, home_losses), 3),
        "away_win_pct": round(pct(away_wins, away_losses), 3),
        "last10_win_pct": round(pct(last10_wins, last10_losses), 3),
        "rest_days": rest_days,
        "rri_5": round(float(latest_rri), 3) if pd.notna(latest_rri) else 0.0,
    }
    
def get_mlb_games_by_date(game_date: str):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={game_date}"

    response = requests.get(url)
    data = response.json()

    dates = data.get("dates", [])

    if not dates:
        return []

    games = []

    for game in dates[0].get("games", []):
        home_team = game["teams"]["home"]["team"]["name"]
        away_team = game["teams"]["away"]["team"]["name"]

        home_score = game["teams"]["home"].get("score")
        away_score = game["teams"]["away"].get("score")

        status = game["status"]["detailedState"]

        games.append({
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_score,
            "away_score": away_score,
            "status": status,
            "game_date": game_date
        })

    return games

@app.get("/mlb-games")
def mlb_games(game_date: str = None):
    if game_date is None:
        game_date = date.today().isoformat()

    games = get_mlb_games_by_date(game_date)

    if not games:
        return {
            "date": game_date,
            "games": []
        }

    return {
        "date": game_date,
        "games": games
    }
    
def prediction_exists_today(home_team: str, away_team: str, model_name: str = None) -> bool:
    today = date.today().isoformat()
    return prediction_exists_for_date(home_team, away_team, today, model_name)


def prediction_exists_for_date(
    home_team: str,
    away_team: str,
    game_date: str,
    model_name: str = None
) -> bool:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        if model_name:
            cursor.execute("""
                SELECT COUNT(*)
                FROM predictions
                WHERE DATE(date) = ?
                  AND home_team = ?
                  AND away_team = ?
                  AND model_name = ?
            """, (game_date, home_team, away_team, model_name))
        else:
            cursor.execute("""
                SELECT COUNT(*)
                FROM predictions
                WHERE DATE(date) = ?
                  AND home_team = ?
                  AND away_team = ?
            """, (game_date, home_team, away_team))

        count = cursor.fetchone()[0]
        conn.close()

        return count > 0

    except Exception:
        return False
    
@app.get("/generate-daily-predictions")
def generate_daily_predictions():
    games = get_today_mlb_games()

    if not games:
        return {
            "ok": False,
            "message": "No MLB games found today",
            "saved": 0
        }

    saved = 0
    skipped = 0
    results = []

    for game in games:
        home = game["home_team"]
        away = game["away_team"]

        for model_name, selected_stats in MODEL_PRESETS.items():

            # Skip if this exact game + model already exists today
            if prediction_exists_today(home, away, model_name):
                skipped += 1
                continue

            payload = ProbabilityRequest(
                sport="baseball",
                league="mlb",
                home_team=home,
                away_team=away,
                selected_stats=selected_stats,
                model_name=model_name
            )

            result = probability(payload)

            #log_prediction(result)
            saved += 1
            results.append(result)
    return {
        "ok": True,
        "message": "Daily model predictions generated",
        "saved": saved,
        "skipped": skipped,
        "results": results
    }

@app.get("/mlb-games-with-probabilities")
def mlb_games_with_probabilities():
    games = get_today_mlb_games()

    if not games:
        return {"error": "No MLB games found today"}

    results = []
    saved = 0
    skipped = 0

    for game in games:
        home = game["home_team"]
        away = game["away_team"]

        if prediction_exists_today(home, away):
            skipped += 1

        home_stats = get_real_team_stats(home)
        away_stats = get_real_team_stats(away)

        home_rating = team_power_rating(
            home_stats["win_pct"],
            home_stats["run_diff_per_game"]
        )
        away_rating = team_power_rating(
            away_stats["win_pct"],
            away_stats["run_diff_per_game"]
        )

        rating_diff = team_rating_diff(home_rating, away_rating)

        pitcher_edge = 0.0
        timezone_edge = 0.0
        home_field = home_field_advantage()

        rest_edge = rest_days_edge(
            home_stats["rest_days"],
            away_stats["rest_days"]
        )

        form_edge = last10_edge(
            home_stats["last10_win_pct"],
            away_stats["last10_win_pct"]
        )

        rri_edge = (away_stats["rri_5"] - home_stats["rri_5"]) * 0.15

        split_edge = home_away_split_edge(
            home_stats["home_win_pct"],
            away_stats["away_win_pct"]
        )

        home_runs = expected_home_runs(
            base_runs=4.5,
            rating_diff=rating_diff,
            pitcher_edge=pitcher_edge,
            home_field=home_field,
            rest_edge=rest_edge + timezone_edge,
            form_edge=form_edge,
            split_edge=split_edge,
            rri_edge=rri_edge,
        )

        away_runs = expected_away_runs(
            base_runs=4.5,
            rating_diff=rating_diff,
            pitcher_edge=pitcher_edge,
            home_field=home_field,
            rest_edge=rest_edge + timezone_edge,
            form_edge=form_edge,
            split_edge=split_edge,
            rri_edge=rri_edge,
        )

        p_home_win = win_probability_from_expected_runs(home_runs, away_runs)

        result = {
            "home_team": home,
            "away_team": away,
            "away_score": game["away_score"],
            "home_score": game["home_score"],
            "status": game["status"],
            "expected_home_runs": round(home_runs, 2),
            "expected_away_runs": round(away_runs, 2),
            "p_home_win": round(p_home_win, 3),
            "p_away_win": round(1 - p_home_win, 3),
            "model_name": "daily_mlb_auto",
            "actual_result": get_actual_result_from_game(game),
            "inputs_used": {
                "selected_stats": [
                    "last10",
                    "rest_days",
                    "home_away_split",
                    "timezone",
                    "rating_diff",
                    "rri"
                ],
                "rating_diff": round(rating_diff, 3),
                "pitcher_edge": round(pitcher_edge, 3),
                "rest_edge": round(rest_edge, 3),
                "form_edge": round(form_edge, 3),
                "split_edge": round(split_edge, 3),
                "timezone_edge": round(timezone_edge, 3),
            }
        }

        print(f"{away} @ {home} -> {win_probability}")
        results.append(result)
    print(f"Generated {len(results)} games")
    print(f"Saved {saved} predictions")
    return {
        "ok": True,
        "saved": saved,
        "skipped": skipped,
        "games": results
    }

def log_prediction(result: dict):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    inputs = result.get("inputs_used", {})

    cursor.execute("PRAGMA table_info(predictions)")
    columns = [row[1] for row in cursor.fetchall()]

    selected_stats = ",".join(inputs.get("selected_stats", []))

    if "model_name" in columns:
        cursor.execute("""
            INSERT INTO predictions (
                date, home_team, away_team, p_home_win,
                expected_home_runs, expected_away_runs,
                selected_stats, rating_diff, pitcher_edge,
                rest_edge, form_edge, split_edge,
                timezone_edge, actual_result, model_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date.today().isoformat(),
            result.get("home_team"),
            result.get("away_team"),
            result.get("p_home_win"),
            result.get("expected_home_runs"),
            result.get("expected_away_runs"),
            selected_stats,
            inputs.get("rating_diff"),
            inputs.get("pitcher_edge"),
            inputs.get("rest_edge"),
            inputs.get("form_edge"),
            inputs.get("split_edge"),
            inputs.get("timezone_edge"),
            result.get("actual_result"),
            result.get("model_name", "manual"),
        ))
    else:
        cursor.execute("""
            INSERT INTO predictions (
                date, home_team, away_team, p_home_win,
                expected_home_runs, expected_away_runs,
                selected_stats, rating_diff, pitcher_edge,
                rest_edge, form_edge, split_edge,
                timezone_edge, actual_result
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date.today().isoformat(),
            result.get("home_team"),
            result.get("away_team"),
            result.get("p_home_win"),
            result.get("expected_home_runs"),
            result.get("expected_away_runs"),
            selected_stats,
            inputs.get("rating_diff"),
            inputs.get("pitcher_edge"),
            inputs.get("rest_edge"),
            inputs.get("form_edge"),
            inputs.get("split_edge"),
            inputs.get("timezone_edge"),
            result.get("actual_result"),
        ))

    conn.commit()
    conn.close()

#PROBABILITY***********************************************************
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
        ) * 0.10 * selected["rest_days"]

    if "home_away_split" in selected:
        home_field = home_field_advantage()
        split_edge = home_away_split_edge(
            home_stats["home_win_pct"],
            away_stats["away_win_pct"]
        ) * 0.12 * selected["home_away_split"]

    if "timezone" in selected:
        timezone_edge = 0.02 * selected["timezone"]

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

        pitcher_edge = (home_report["f5"]["f5_edge"] - away_report["f5"]["f5_edge"]) * 0.08
    
    rri_edge = (away_stats["rri_5"] - home_stats["rri_5"]) * 0.07

    home_bullpen = calculate_bullpen_breakdown_score(
        bullpen_innings_yesterday=3.5,
        back_to_back_relievers=2,
        closer_used_yesterday=True,
        setup_used_yesterday=True,
        bullpen_era_penalty=1.0,
    )

    away_bullpen = calculate_bullpen_breakdown_score(
        bullpen_innings_yesterday=1.0,
        back_to_back_relievers=0,
        closer_used_yesterday=False,
        setup_used_yesterday=False,
        bullpen_era_penalty=0.2,
    )

    home_bullpen_edge = away_bullpen["opponent_expected_run_boost"]
    away_bullpen_edge = home_bullpen["opponent_expected_run_boost"]
    
    home_runs = expected_home_runs(
        base_runs=4.5,
        rating_diff=rating_diff,
        pitcher_edge=pitcher_edge,
        home_field=home_field,
        rest_edge=rest_edge + timezone_edge,
        form_edge=form_edge,
        split_edge=split_edge,
        rri_edge=rri_edge,
        bullpen_edge=home_bullpen_edge,
    )

    away_runs = expected_away_runs(
        base_runs=4.5,
        rating_diff=rating_diff,
        pitcher_edge=pitcher_edge,
        home_field=home_field,
        rest_edge=rest_edge + timezone_edge,
        form_edge=form_edge,
        split_edge=split_edge,
        rri_edge=rri_edge,
        bullpen_edge=away_bullpen_edge,
    )

    p_home_win = win_probability_from_expected_runs(home_runs, away_runs)

    # Compress probabilities harder until model is calibrated
    p_home_win = 0.5 + ((p_home_win - 0.5) * 0.45)

    # Clamp probabilities to realistic MLB range
    p_home_win = max(0.40, min(0.60, p_home_win))

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
        "home_bullpen_edge": home_bullpen_edge,
        "away_bullpen_edge": away_bullpen_edge,
    }

    if edge_map:
        biggest_edge_name = max(edge_map, key=lambda k: abs(edge_map[k]))
        biggest_edge_value = edge_map[biggest_edge_name]
    
    actual_result = None
    result = {
        "home_team": payload.home_team,
        "away_team": payload.away_team,
        "p_home_win": round(p_home_win, 3),
        "p_away_win": round(1 - p_home_win, 3),
        "expected_home_runs": round(home_runs, 2),
        "expected_away_runs": round(away_runs, 2),
        "model_name": payload.model_name,
        "message": "You've been Statified",
        "selected_stats_count": len(payload.selected_stats),
        "actual_result": actual_result,
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
            "home_bullpen_edge": round(home_bullpen_edge, 3),
            "away_bullpen_edge": round(away_bullpen_edge, 3),
            "home_bullpen": home_bullpen,
            "away_bullpen": away_bullpen,
        }
        }
    try:
        print("CALLING LOG_PREDICTION")
        log_prediction(result)
        print("DONE LOGGING")
    except Exception as e:
        print("LOGGING FAILED:", e)

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

@app.get("/predictions")
def get_predictions():
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM predictions
            ORDER BY date DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        predictions = [dict(row) for row in rows]

        return {
            "ok": True,
            "count": len(predictions),
            "predictions": predictions
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }

class BullpenBreakdownRequest(BaseModel):
    team: str
    bullpen_innings_yesterday: float = 0
    back_to_back_relievers: int = 0
    closer_used_yesterday: bool = False
    setup_used_yesterday: bool = False
    bullpen_era_penalty: float = 0

@app.post("/bullpen-breakdown-score")
def bullpen_breakdown_score(data: BullpenBreakdownRequest):
    result = calculate_bullpen_breakdown_score(
        bullpen_innings_yesterday=data.bullpen_innings_yesterday,
        back_to_back_relievers=data.back_to_back_relievers,
        closer_used_yesterday=data.closer_used_yesterday,
        setup_used_yesterday=data.setup_used_yesterday,
        bullpen_era_penalty=data.bullpen_era_penalty,
    )

    return {
        "team": data.team,
        "stat": "Bullpen Breakdown Score",
        "short_name": "BBS",
        "stat_key": "bullpen_breakdown_score",
        **result,
        "message": f"{data.team} bullpen risk: {result['risk_level']}",
    }

@app.get("/clear-today-predictions")
def clear_today_predictions():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    today = date.today().isoformat()

    cursor.execute("""
        DELETE FROM predictions
        WHERE DATE(date) = ?
    """, (today,))

    deleted = cursor.rowcount

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "deleted": deleted,
        "date": today
    }
    

@app.get("/export-predictions-csv")
def export_predictions_csv():
    csv_file = os.path.join(BASE_DIR, "predictions_export.csv")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM predictions")
    rows = cursor.fetchall()

    column_names = [description[0] for description in cursor.description]

    conn.close()

    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(column_names)
        writer.writerows(rows)

    return FileResponse(
        csv_file,
        media_type="text/csv",
        filename="predictions_export.csv"
    )

@app.get("/prediction-counts")
def prediction_counts():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT date, COUNT(*)
        FROM predictions
        GROUP BY date
        ORDER BY date DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return {
        "ok": True,
        "counts": rows
    }
