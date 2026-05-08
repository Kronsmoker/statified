from models.bullpen import calculate_bullpen_breakdown_score


def expected_home_runs(
    base_runs: float,
    rating_diff: float,
    pitcher_edge: float,
    home_field: float,
    rest_edge: float = 0.0,
    form_edge: float = 0.0,
    split_edge: float = 0.0,
    rri_edge: float = 0.0,
    bullpen_edge: float = 0.0,
) -> float:
    """
    Expected runs for home team.
    Positive edges help home team.
    """
    runs = (
        base_runs
        + (rating_diff * 0.50)
        + (pitcher_edge * 0.30)
        + home_field
        + (rest_edge * 0.08)
        + (form_edge * 0.20)
        + (split_edge * 0.25)
        + (rri_edge * 0.15)
        + bullpen_edge
    )
    return max(runs, 0.5)


def expected_away_runs(
    base_runs: float,
    rating_diff: float,
    pitcher_edge: float,
    home_field: float,
    rest_edge: float = 0.0,
    form_edge: float = 0.0,
    split_edge: float = 0.0,
    rri_edge: float = 0.0,
    bullpen_edge: float = 0.0,
) -> float:
    """
    Expected runs for away team.
    Home team positive edges hurt away team.
    But bullpen_edge always BENEFITS the team receiving it.
    """
    runs = (
        base_runs
        - (rating_diff * 0.50)
        - (pitcher_edge * 0.30)
        - home_field
        - (rest_edge * 0.08)
        - (form_edge * 0.20)
        - (split_edge * 0.25)
        - (rri_edge * 0.15)
        + bullpen_edge
    )
    return max(runs, 0.5)