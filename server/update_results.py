import sqlite3
import pandas as pd
import requests
from pathlib import Path

DB_PATH = Path("statified.db")

conn = sqlite3.connect(DB_PATH)

df = pd.read_sql_query("""
    SELECT *
    FROM predictions
""", conn)

df["date"] = pd.to_datetime(df["date"]).dt.date
df["actual_result"] = pd.to_numeric(df["actual_result"], errors="coerce")

missing = df[df["actual_result"].isna()].copy()

print("\nGames missing results:\n")
for i, row in missing.iterrows():
    print(f"{i}: {row['date']} | {row['away_team']} at {row['home_team']}")

choice = input("\nEnter row numbers to update separated by commas, or type ALL: ").strip()

if choice.lower() == "all":
    selected_indexes = missing.index.tolist()
else:
    selected_indexes = [int(x.strip()) for x in choice.split(",")]

updated_count = 0

for index in selected_indexes:
    row = df.loc[index]

    game_date = row["date"]
    home_team = row["home_team"]
    away_team = row["away_team"]
    prediction_id = int(row["id"])

    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={game_date}"
    response = requests.get(url)
    data = response.json()

    games = data.get("dates", [])
    if not games:
        print(f"No API games found for {game_date}")
        continue

    found = False

    for game in games[0].get("games", []):
        api_home = game["teams"]["home"]["team"]["name"]
        api_away = game["teams"]["away"]["team"]["name"]
        status = game["status"]["detailedState"]

        if api_home == home_team and api_away == away_team:
            found = True

            if status != "Final":
                print(f"Not final yet: {away_team} at {home_team} — {status}")
                break

            home_score = game["teams"]["home"]["score"]
            away_score = game["teams"]["away"]["score"]

            actual_result = 1 if home_score > away_score else 0

            conn.execute(
                """
                UPDATE predictions
                SET actual_result = ?
                WHERE id = ?
                """,
                (actual_result, prediction_id)
            )

            updated_count += 1

            print(f"Updated: {away_team} at {home_team} {away_score}-{home_score}")
            break

    if not found:
        print(f"Could not match: {away_team} at {home_team}")

conn.commit()
conn.close()

print(f"\nDone. Updated {updated_count} rows.")