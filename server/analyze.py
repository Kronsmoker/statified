import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)

df = pd.read_csv("predictions.csv", on_bad_lines="skip")

df["date"] = pd.to_datetime(df["date"]).dt.date

print("\n1 = Analyze ALL Dates")
print("2 = Analyze SINGLE Date")
print("3 = Analyze DATE RANGE")

choice = input("\nChoose option: ")

#ALL DATA
if choice == "1":
    filtered_df = df.copy()

#SINGLE DATE
elif choice == "2":
    selected_date = input("Enter date (YYYY-MM-DD): ")

    selected_date = pd.to_datetime(selected_date).date()

    filtered_df = df[
        df["date"] == selected_date
    ].copy()

# DATE RANGE
elif choice == "3":
    start_date = input("Enter START date (YYYY-MM-DD): ")
    end_date = input("Enter END date (YYYY-MM-DD): ")

    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()

    filtered_df = df[
        (df["date"] >= start_date) &
        (df["date"] <= end_date)
    ].copy()

else:
    print("Invalid option")
    exit()

print(filtered_df[["date", "home_team", "away_team"]])

print("Total predictions:", len(filtered_df))

# clean data
filtered_df["actual_result"] = pd.to_numeric(filtered_df["actual_result"], errors="coerce")
filtered_df = filtered_df.dropna(subset=["actual_result"])
filtered_df["actual_result"] = filtered_df["actual_result"].astype(int)

# remove duplicates
before = len(filtered_df)

filtered_df = filtered_df.drop_duplicates(
    subset=["date", "home_team", "away_team", "selected_stats"],
    keep="last"
)

after = len(filtered_df)

print("Removed duplicates:", before - after)
print("Remaining rows:", after)

# overall accuracy
correct = ((filtered_df["p_home_win"] > 0.5) & (filtered_df["actual_result"] == 1)) | \
          ((filtered_df["p_home_win"] < 0.5) & (filtered_df["actual_result"] == 0))

accuracy = correct.mean()

print("Total predictions:", len(filtered_df))
print("Accuracy:", round(accuracy, 3))

# high confidence both home and away
high_conf = filtered_df[
    (filtered_df["p_home_win"] >= 0.7) |
    (filtered_df["p_home_win"] <= 0.3)
]

high_correct = (
    ((high_conf["p_home_win"] > 0.5) & (high_conf["actual_result"] == 1)) |
    ((high_conf["p_home_win"] < 0.5) & (high_conf["actual_result"] == 0))
)

if len(high_conf) > 0:
    print("\nHigh confidence picks:", len(high_conf))
    print("High confidence accuracy:", round(high_correct.mean(), 3))
else:
    print("\nHigh confidence picks: 0")

filtered_df["prob_bucket"] = pd.cut(
    filtered_df["p_home_win"],
    bins=[0, .3, .4, .5, .6, .7, 1],
    labels=["0-.30", ".30-.40", ".40-.50", ".50-.60", ".60-.70", ".70-1"]
)

bucket_report = filtered_df.groupby("prob_bucket").agg(
    games=("actual_result", "count"),
    avg_predicted=("p_home_win", "mean"),
    actual_home_win_rate=("actual_result", "mean")
)

print(
    high_conf.groupby("selected_stats")
    .size()
    .sort_values(ascending=False)
)

print(
    high_conf[
        [
            "date",
            "home_team",
            "away_team",
            "p_home_win",
            "actual_result",
            "selected_stats"
        ]
    ].sort_values("p_home_win", ascending=False)
)

print(
    filtered_df.groupby("selected_stats")["p_home_win"]
    .mean()
    .sort_values(ascending=False)
)

print(bucket_report)


filtered_df["correct"] = (
    ((filtered_df["p_home_win"] > 0.5) & (filtered_df["actual_result"] == 1)) |
    ((filtered_df["p_home_win"] < 0.5) & (filtered_df["actual_result"] == 0))
)

stat_report = filtered_df.groupby("selected_stats").agg(
    games=("correct", "count"),
    accuracy=("correct", "mean")
)

print(stat_report.sort_values("games", ascending=False))

# calibration
print("\nAverage predicted probability:", round(filtered_df["p_home_win"].mean(), 3))
print("Actual home win rate:", round(filtered_df["actual_result"].mean(), 3))