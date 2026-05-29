import pandas as pd

df = pd.read_csv("predictions.csv")

df["date"] = pd.to_datetime(df["date"]).dt.date

print("\n1 = Analyze ALL Dates")
print("2 = Analyze SINGLE Date")
print("3 = Analyze DATE RANGE")

choice = input("\nChoose option: ")

#ALL DATA
if choice == "1":
    filtered_df = df

#SINGLE DATE
elif choice == "2":
    selected_date = input("Enter date (YYYY-MM-DD): ")

    selected_date = pd.to_datetime(selected_date).date()

    filtered_df = df[
        df["date"] == selected_date
    ]

# DATE RANGE
elif choice == "3":
    start_date = input("Enter START date (YYYY-MM-DD): ")
    end_date = input("Enter END date (YYYY-MM-DD): ")

    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()

    filtered_df = df[
        (df["date"] >= start_date) &
        (df["date"] <= end_date)
    ]

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
filtered_df = filtered_df.drop_duplicates(
    subset=["date", "home_team", "away_team", "selected_stats"],
    keep="last"
)

# overall accuracy
correct = ((filtered_df["p_home_win"] > 0.5) & (filtered_df["actual_result"] == 1)) | \
          ((filtered_df["p_home_win"] < 0.5) & (filtered_df["actual_result"] == 0))

accuracy = correct.mean()

print("Total predictions:", len(filtered_df))
print("Accuracy:", round(accuracy, 3))

# high confidence
high_conf = filtered_df[filtered_df["p_home_win"] >= 0.7]

high_correct = ((high_conf["p_home_win"] > 0.5) & (high_conf["actual_result"] == 1)) | \
               ((high_conf["p_home_win"] < 0.5) & (high_conf["actual_result"] == 0))

if len(high_conf) > 0:
    print("\nHigh confidence picks:", len(high_conf))
    print("High confidence accuracy:", round(high_correct.mean(), 3))

# calibration
print("\nAverage predicted probability:", round(filtered_df["p_home_win"].mean(), 3))
print("Actual home win rate:", round(filtered_df["actual_result"].mean(), 3))