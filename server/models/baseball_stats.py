def pitcher_era_edge(home_pitcher_era: float, away_pitcher_era: float) -> float:
    """
    Lower ERA is better.
    Positive result means advantage for home team.
    """
    return away_pitcher_era - home_pitcher_era


def home_field_advantage() -> float:
    """
    Simple fixed home field edge in runs.
    """
    return 0.30


def rest_days_edge(home_rest_days: int, away_rest_days: int) -> float:
    """
    Positive means home team is more rested.
    Small effect.
    """
    return float(home_rest_days - away_rest_days)


def last10_edge(home_last10_win_pct: float, away_last10_win_pct: float) -> float:
    """
    Positive means home team has better recent form.
    """
    return home_last10_win_pct - away_last10_win_pct


def home_away_split_edge(home_home_win_pct: float, away_away_win_pct: float) -> float:
    """
    Positive means home team is stronger in its home split
    compared with away team's road split.
    """
    return home_home_win_pct - away_away_win_pct