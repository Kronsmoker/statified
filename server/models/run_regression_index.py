from __future__ import annotations

import pandas as pd


def build_run_regression_index(
    df: pd.DataFrame,
    team_col: str = "team",
    date_col: str = "date",
    runs_col: str = "runs_scored",
) -> pd.DataFrame:
    """
    Build rolling scoring features and Run Regression Index (RRI) for each team.

    Required columns:
        - team
        - date
        - runs_scored

    Returns a copy of the dataframe with these added columns:
        - season_avg_runs
        - last_3_avg_runs
        - last_5_avg_runs
        - last_10_avg_runs
        - rri_3
        - rri_5
        - rri_10
        - scoring_form_label

    RRI logic:
        RRI = season_avg_runs - recent_avg_runs

    Interpretation:
        - Positive RRI: team scoring below its season baseline
        - Negative RRI: team scoring above its season baseline
        - Near zero: team scoring around normal
    """

    required_cols = {team_col, date_col, runs_col}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    out = df.copy()

    # Make sure date is a datetime so sorting works correctly
    out[date_col] = pd.to_datetime(out[date_col])

    # Make sure runs are numeric
    out[runs_col] = pd.to_numeric(out[runs_col], errors="coerce")

    # Sort by team and date
    out = out.sort_values([team_col, date_col]).reset_index(drop=True)

    # Group by team
    grouped = out.groupby(team_col, group_keys=False)

    out["games_played_before"] = grouped.cumcount()

    # Use only prior games for prediction features
    out["season_avg_runs"] = grouped[runs_col].transform(
        lambda s: s.shift(1).expanding().mean()
    )

    out["last_3_avg_runs"] = grouped[runs_col].transform(
        lambda s: s.shift(1).rolling(window=3, min_periods=1).mean()
    )

    out["last_5_avg_runs"] = grouped[runs_col].transform(
        lambda s: s.shift(1).rolling(window=5, min_periods=1).mean()
    )

    out["last_10_avg_runs"] = grouped[runs_col].transform(
        lambda s: s.shift(1).rolling(window=10, min_periods=1).mean()
    )
    
    # Run Regression Index values
    out["rri_3"] = out["season_avg_runs"] - out["last_3_avg_runs"]
    out["rri_5"] = out["season_avg_runs"] - out["last_5_avg_runs"]
    out["rri_10"] = out["season_avg_runs"] - out["last_10_avg_runs"]
    out["games_played_before"] = grouped.cumcount()
    
    # Simple label using rri_5 as the main signal
    def classify_rri(value: float, games_played_before: int) -> str:
        if pd.isna(value):
            return "unknown"
        if games_played_before < 5:
            return "small_sample"
        if value >= 1.5:
            return "strong_underperformance"
        if value >= 0.75:
            return "mild_underperformance"
        if value <= -1.5:
            return "strong_overperformance"
        if value <= -0.75:
            return "mild_overperformance"
        return "neutral"

    out["scoring_form_label"] = out.apply(
        lambda row: classify_rri(row["rri_5"], row["games_played_before"]),
        axis=1,
    )

    return out


def get_team_rri_snapshot(
    df: pd.DataFrame,
    team_name: str,
    team_col: str = "team",
    date_col: str = "date",
    runs_col: str = "runs_scored",
) -> dict:
    """
    Return the latest RRI snapshot for one team.
    Good for sending to your frontend/API.
    """

    rri_df = build_run_regression_index(
        df=df,
        team_col=team_col,
        date_col=date_col,
        runs_col=runs_col,
    )

    team_df = rri_df[rri_df[team_col] == team_name].sort_values(date_col)

    if team_df.empty:
        raise ValueError(f"No rows found for team: {team_name}")

    latest = team_df.iloc[-1]

    return {
        "team": latest[team_col],
        "date": str(latest[date_col].date()),
        "runs_scored": float(latest[runs_col]),
        "season_avg_runs": round(float(latest["season_avg_runs"]), 3),
        "last_3_avg_runs": round(float(latest["last_3_avg_runs"]), 3),
        "last_5_avg_runs": round(float(latest["last_5_avg_runs"]), 3),
        "last_10_avg_runs": round(float(latest["last_10_avg_runs"]), 3),
        "rri_3": round(float(latest["rri_3"]), 3),
        "rri_5": round(float(latest["rri_5"]), 3),
        "rri_10": round(float(latest["rri_10"]), 3),
        "scoring_form_label": latest["scoring_form_label"],
    }


if __name__ == "__main__":
    # Example usage with test data
    sample_data = pd.DataFrame(
        {
            "team": [
                "Orioles", "Orioles", "Orioles", "Orioles", "Orioles",
                "Orioles", "Orioles", "Orioles", "Orioles", "Orioles"
            ],
            "date": [
                "2026-03-01", "2026-03-02", "2026-03-03", "2026-03-04", "2026-03-05",
                "2026-03-06", "2026-03-07", "2026-03-08", "2026-03-09", "2026-03-10"
            ],
            "runs_scored": [7, 6, 8, 5, 4, 3, 2, 3, 4, 2],
        }
    )

    result = build_run_regression_index(sample_data)
    print(result)

    snapshot = get_team_rri_snapshot(sample_data, "Orioles")
    print("\nLATEST SNAPSHOT:")
    print(snapshot)