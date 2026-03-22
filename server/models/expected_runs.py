def expected_home_runs(
    base_runs: float,
    rating_diff: float,
    pitcher_edge: float,
    home_field: float,
    rest_edge: float = 0.0,
    form_edge: float = 0.0,
    split_edge: float = 0.0,
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
) -> float:
    """
    Expected runs for away team.
    Home team positive edges hurt away team.
    """
    runs = (
        base_runs
        - (rating_diff * 0.50)
        - (pitcher_edge * 0.30)
        - home_field
        - (rest_edge * 0.08)
        - (form_edge * 0.20)
        - (split_edge * 0.25)
    )
    return max(runs, 0.5)