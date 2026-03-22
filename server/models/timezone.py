# simple timezone mapping
team_timezones = {
    "Lakers": 0,      # Pacific
    "Warriors": 0,
    "Nuggets": 1,     # Mountain
    "Bulls": 2,       # Central
    "Celtics": 3,     # Eastern
    "Knicks": 3
}

# get timezone difference
def get_timezone_traveled(team_from, team_to):
    if team_from not in team_timezones or team_to not in team_timezones:
        return 0
    
    from_tz = team_timezones[team_from]
    to_tz = team_timezones[team_to]
    return abs(to_tz - from_tz)

# simple fatigue penalty
def timezone_penalty(team_from, team_to):
    tz_diff = get_timezone_traveled(team_from, team_to)
    return tz_diff * 0.1


# test it
if __name__ == "__main__":
    print(get_timezone_traveled("Lakers", "Celtics"))  # 3
    print(timezone_penalty("Lakers", "Celtics"))       # 0.3