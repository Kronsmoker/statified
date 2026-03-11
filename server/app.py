from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

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

@app.post("/probability")
def probability(payload: ProbabilityRequest) -> Dict[str, Any]:
    n = len(payload.selected_stats)
    base = 0.50
    p_home_win = min(0.70, max(0.30, base + (n - 3) * 0.02))

    return {
        "home_team": payload.home_team,
        "away_team": payload.away_team,
        "p_home_win": round(p_home_win, 3),
        "p_away_win": round(1 - p_home_win, 3),
        "message": "You've been Statified",
        "selected_stats_count": n,
    }
