import pandas as pd

df = pd.read_csv("predictions.csv")

# clean data
df["actual_result"] = pd.to_numeric(df["actual_result"], errors="coerce")
df = df.dropna(subset=["actual_result"])
df["actual_result"] = df["actual_result"].astype(int)

# 🔥 ADD THIS PART

# overall accuracy
correct = ((df["p_home_win"] > 0.5) & (df["actual_result"] == 1)) | \
          ((df["p_home_win"] < 0.5) & (df["actual_result"] == 0))

accuracy = correct.mean()

print("Total predictions:", len(df))
print("Accuracy:", round(accuracy, 3))


# high confidence (70%+)
high_conf = df[df["p_home_win"] >= 0.7]

high_correct = ((high_conf["p_home_win"] > 0.5) & (high_conf["actual_result"] == 1)) | \
               ((high_conf["p_home_win"] < 0.5) & (high_conf["actual_result"] == 0))

if len(high_conf) > 0:
    print("\nHigh confidence picks:", len(high_conf))
    print("High confidence accuracy:", round(high_correct.mean(), 3))


# calibration
print("\nAverage predicted probability:", round(df["p_home_win"].mean(), 3))
print("Actual home win rate:", round(df["actual_result"].mean(), 3))
