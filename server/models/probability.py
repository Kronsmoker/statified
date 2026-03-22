import math
from models.timezone import timezone_penalty


def logistic_probability(edge: float) -> float:
    """
    Converts a model edge into a probability between 0 and 1.
    """
    return 1 / (1 + math.exp(-edge))


def win_probability_from_expected_runs(home_runs: float, away_runs: float) -> float:
    """
    Converts expected runs into home win probability.
    """
    run_edge = home_runs - away_runs
    return logistic_probability(run_edge)


def win_probability(team_a_score, team_b_score, team_a, team_b, timezone_weight=1.0):
    """
    Legacy score-based probability function.
    Keeps your current app working.
    """
    team_a_tz = timezone_penalty(team_a, team_b) * timezone_weight
    team_b_tz = timezone_penalty(team_b, team_a) * timezone_weight

    team_a_adjusted = team_a_score - team_a_tz
    team_b_adjusted = team_b_score - team_b_tz

    total = team_a_adjusted + team_b_adjusted

    print("----- WIN PROBABILITY DEBUG -----")
    print("team_a:", team_a)
    print("team_b:", team_b)
    print("team_a_score:", team_a_score)
    print("team_b_score:", team_b_score)
    print("team_a_tz_penalty:", team_a_tz)
    print("team_b_tz_penalty:", team_b_tz)
    print("team_a_adjusted:", team_a_adjusted)
    print("team_b_adjusted:", team_b_adjusted)
    print("total:", total)

    if total == 0:
        print("probability: 0.5")
        return 0.5

    prob = team_a_adjusted / total
    print("probability:", prob)
    print("---------------------------------")

    return prob