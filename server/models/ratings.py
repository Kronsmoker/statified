def team_power_rating(win_pct: float, run_diff_per_game: float) -> float:
    """
    Simple team power rating.

    win_pct: team win percentage, like 0.600
    run_diff_per_game: average runs scored minus average runs allowed per game
    """
    return (win_pct * 2.0) + (run_diff_per_game * 1.5)


def team_rating_diff(home_rating: float, away_rating: float) -> float:
    """
    Positive means home team is stronger.
    """
    return home_rating - away_rating