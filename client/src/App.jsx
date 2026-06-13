import { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [games, setGames] = useState([]);
  const [selectedGame, setSelectedGame] = useState(null);
  const [selectedStats, setSelectedStats] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

  const [isUnlocked, setIsUnlocked] = useState(
    localStorage.getItem("statified_unlocked") === "true"
  );
  const [passwordInput, setPasswordInput] = useState("");

  const [selectedDate, setSelectedDate] = useState(
  new Date().toISOString().split("T")[0]);

  const APP_PASSWORD = "statified2026";

  const statOptions = [
    { key: "last10", label: "Last 10 Performance", defaultWeight: 50 },
    { key: "rest_days", label: "Rest Days", defaultWeight: 50 },
    { key: "home_away_split", label: "Home/Away Split", defaultWeight: 50 },
    { key: "timezone", label: "Travel / Timezone", defaultWeight: 50 },
    { key: "pitcher_stats", label: "Pitcher Stats", defaultWeight: 50 },
    {
      key: "bullpen_breakdown_score",
      label: "Bullpen Breakdown Score",
      defaultWeight: 50,
    },
  ];

  useEffect(() => {
    setSelectedGame(null);
    setResult(null);
    fetch(`${API_BASE_URL}/mlb-games?game_date=${selectedDate}`)
      .then((res) => res.json())
      .then((data) => {
        console.log("MLB games data:", data);
        setGames(Array.isArray(data) ? data : data.games || []);
      })
      .catch((err) => console.error(err));
  }, [selectedDate, API_BASE_URL]);

  function handleUnlock(e) {
    e.preventDefault();

    if (passwordInput === APP_PASSWORD) {
      localStorage.setItem("statified_unlocked", "true");
      setIsUnlocked(true);
    } else {
      alert("Wrong password");
    }
  }

  function toggleStat(stat) {
    setSelectedStats((prev) => {
      const exists = prev.find((s) => s.stat_key === stat.key);

      if (exists) {
        return prev.filter((s) => s.stat_key !== stat.key);
      }

      return [
        ...prev,
        {
          stat_key: stat.key,
          weight: stat.defaultWeight,
          locked: false,
        },
      ];
    });
  }

  function updateWeight(statKey, newPercent) {
  setSelectedStats((prev) => {
    const target = prev.find((s) => s.stat_key === statKey);

    if (!target || target.locked) return prev;

    const lockedStats = prev.filter((s) => s.locked);
    const unlockedStats = prev.filter((s) => !s.locked);

    const lockedTotal = lockedStats.reduce((sum, s) => sum + s.weight, 0);

    const maxAllowed = 100 - lockedTotal;

    const updatedWeight = Math.min(Number(newPercent), maxAllowed);

    const otherUnlocked = unlockedStats.filter(
      (s) => s.stat_key !== statKey
    );

    const remaining = maxAllowed - updatedWeight;

    const otherTotal = otherUnlocked.reduce((sum, s) => sum + s.weight, 0);

    return prev.map((s) => {
      if (s.stat_key === statKey) {
        return { ...s, weight: updatedWeight };
      }

      if (s.locked) {
        return s;
      }

      if (otherUnlocked.length === 0) {
        return s;
      }

      if (otherTotal === 0) {
        return {
          ...s,
          weight: remaining / otherUnlocked.length,
        };
      }

      return {
        ...s,
        weight: (s.weight / otherTotal) * remaining,
      };
    });
  });
}

  function toggleLock(statKey) {
    setSelectedStats((prev) =>
      prev.map((s) =>
        s.stat_key === statKey ? { ...s, locked: !s.locked } : s
      )
    );
  }

  function getPercent(stat) {
    const totalWeight = selectedStats.reduce((sum, s) => sum + s.weight, 0);

    if (totalWeight === 0) return 0;

    return Math.round((stat.weight / totalWeight) * 100);
  }

  const generateProbability = async () => {
    if (!selectedGame) return;

    setLoading(true);
    setResult(null);

    if (selectedStats.length === 0) {
      alert("Select at least one stat");
      setLoading(false);
      return;
    }

    const totalWeight = selectedStats.reduce(
      (sum, stat) => sum + stat.weight,
      0
    );

    if (totalWeight === 0) {
      alert("At least one selected stat needs weight above 0");
      setLoading(false);
      return;
    }

    const normalizedStats = selectedStats.map((stat) => ({
      ...stat,
      weight: stat.weight / totalWeight,
    }));

    try {
      const res = await fetch(`${API_BASE_URL}/probability`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          sport: "baseball",
          league: "mlb",
          home_team: selectedGame.home_team,
          away_team: selectedGame.away_team,
          selected_stats: normalizedStats,
        }),
      });

      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error(err);
    }

    setLoading(false);
  };

  if (!isUnlocked) {
    return (
      <div className="login-screen">
        <form className="login-card" onSubmit={handleUnlock}>
          <h1>Statified</h1>
          <p>Enter password to continue</p>

          <input
            type="password"
            value={passwordInput}
            onChange={(e) => setPasswordInput(e.target.value)}
            placeholder="Password"
          />

          <button type="submit">Unlock</button>
        </form>
      </div>
    );
  }

  return (
    <div className="container">
      <h1>Statified MLB</h1>
      <p>Today's MLB games, live scores, and win probabilities.</p>

      <div className="app-layout">
        <div className="games-column">
          <h2>MLB Games</h2>

<div style={{
  display: "flex",
  gap: "10px",
  alignItems: "center",
  marginBottom: "15px"
}}>
  <button
    onClick={() => {
      const d = new Date(selectedDate);
      d.setDate(d.getDate() - 1);
      setSelectedDate(d.toISOString().split("T")[0]);
    }}
  >
    ◀
  </button>

  <input
    type="date"
    value={selectedDate}
    onChange={(e) => setSelectedDate(e.target.value)}
  />

  <button
    onClick={() => {
      const d = new Date(selectedDate);
      d.setDate(d.getDate() + 1);
      setSelectedDate(d.toISOString().split("T")[0]);
    }}
  >
    ▶
  </button>
</div>
          <p>Games loaded: {games.length}</p>

          <div className="games-list">
            {games.map((game, i) => (
              <div
                key={i}
                className="game-card"
                onClick={() => {
                  setSelectedGame(game);
                  setResult(null);
                }}
                style={{
                  cursor: "pointer",
                  border:
                    selectedGame?.home_team === game.home_team &&
                    selectedGame?.away_team === game.away_team
                      ? "2px solid #22c55e"
                      : "1px solid #ccc",
                }}
              >
                <h3>
                  {game.away_team} at {game.home_team}
                </h3>
                <p>Status: {game.status}</p>

                {game.away_score !== null && game.home_score !== null && (
                  <p>
                    Score: {game.away_score} - {game.home_score}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="side-panel">
          <div className="main-grid">
            <div className="card">
              <h2>Game</h2>

              {!selectedGame && (
                <p style={{ opacity: 0.7 }}>Select a game below</p>
              )}

              {selectedGame && (
                <>
                  <div>
                    <strong>Home:</strong> {selectedGame.home_team}
                  </div>
                  <div>
                    <strong>Away:</strong> {selectedGame.away_team}
                  </div>
                </>
              )}

              <h3 style={{ marginTop: 20 }}>Stat Packs (MVP)</h3>

              {statOptions.map((stat) => {
                const selected = selectedStats.find(
                  (s) => s.stat_key === stat.key
                );

                return (
                  <div key={stat.key} className="stat-card">
                    <label>
                      <input
                        type="checkbox"
                        checked={!!selected}
                        onChange={() => toggleStat(stat)}
                      />{" "}
                      {stat.label}
                    </label>

                    {selected && (
                      <div style={{ marginTop: 8 }}>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="1"
                          value={selected.weight}
                          disabled={selected.locked}
                          onChange={(e) =>
                            updateWeight(stat.key, e.target.value)
                          }
                        />

                        <span style={{ marginLeft: 10 }}>
                          {Math.round(selected.weight)}%
                        </span>

                        <button
                          type="button"
                          onClick={() => toggleLock(stat.key)}
                          style={{
                            marginLeft: 10,
                            border: "none",
                            background: "transparent",
                            cursor: "pointer",
                            fontSize: "18px",
                          }}
                        >
                          {selected.locked ? "🔒" : "🔓"}
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}

              <button
                onClick={generateProbability}
                disabled={!selectedGame || loading}
                style={{
                  marginTop: "16px",
                  padding: "12px 18px",
                  backgroundColor:
                    !selectedGame || loading ? "#999" : "#22c55e",
                  color: "white",
                  border: "none",
                  borderRadius: "8px",
                  cursor: !selectedGame || loading ? "not-allowed" : "pointer",
                  fontWeight: "bold",
                  width: "100%",
                }}
              >
                {loading ? "Calculating..." : "Generate Probability"}
              </button>
            </div>

            <div className="card">
              <h2>Result</h2>

              {!result && !loading && (
                <p style={{ opacity: 0.7 }}>
                  Select a game and generate probability.
                </p>
              )}

              {loading && <p>Calculating...</p>}

              {result && (
                <>
                  <h2>
                    {Math.round(result.p_home_win * 100)}% {result.home_team}{" "}
                    win
                  </h2>

                  <p>
                    {Math.round(result.p_away_win * 100)}% {result.away_team}{" "}
                    win
                  </p>

                  <div style={{ marginTop: 12, color: "#00bfff" }}>
                    You've been Statified
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;