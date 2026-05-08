def calculate_bullpen_breakdown_score(
    bullpen_innings_yesterday: float = 0,
    back_to_back_relievers: int = 0,
    closer_used_yesterday: bool = False,
    setup_used_yesterday: bool = False,
    bullpen_era_penalty: float = 0,
):
    bbs = (
        (2 * bullpen_innings_yesterday)
        + (2 * back_to_back_relievers)
        + (1.5 if closer_used_yesterday else 0)
        + (1 if setup_used_yesterday else 0)
        + bullpen_era_penalty
    )

    if bbs >= 10:
        risk_level = "Blow-up risk"
        run_boost = 0.75
    elif bbs >= 7:
        risk_level = "Attackable bullpen"
        run_boost = 0.45
    elif bbs >= 4:
        risk_level = "Mild danger"
        run_boost = 0.25
    else:
        risk_level = "Fresh / safe bullpen"
        run_boost = 0.0

    return {
        "bbs": round(bbs, 2),
        "risk_level": risk_level,
        "opponent_expected_run_boost": run_boost,
    }