import { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [games, setGames] = useState([]);
  const [selectedGame, setSelectedGame] = useState(null);
  const [selectedStats, setSelectedStats] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  

  // ✅ CLEAN STAT PACK (baseball only)
  const statOptions = [
    { key: "last10", label: "Last 10 Performance" },
    { key: "rest_days", label: "Rest Days" },
    { key: "home_away_split", label: "Home/Away Split" },
    { key: "timezone", label: "Travel / Timezone" },
    { key: "pitcher_stats", label: "Pitcher Stats" },
  ];

  useEffect(() => {
    fetch("http://127.0.0.1:8000/mlb-games")
      .then((res) => res.json())
      .then((data) => setGames(data.games || []))
      .catch((err) => console.error(err));
  }, []);

  const toggleStat = (statKey) => {
    setSelectedStats((prev) =>
      prev.includes(statKey)
        ? prev.filter((s) => s !== statKey)
        : [...prev, statKey]
    );
  };

  const generateProbability = async () => {
    if (!selectedGame) return;

    setLoading(true);
    setResult(null);

    try {
      const res = await fetch("http://127.0.0.1:8000/probability", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          sport: "baseball",
          league: "mlb",
          home_team: selectedGame.home_team,
          away_team: selectedGame.away_team,
          selected_stats: selectedStats.map((s) => ({
            stat_key: s,
            weight: 1.0,
          })),
        }),
      });

      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error(err);
    }

    setLoading(false);
  };

  return (
    <div className="container">
      <h1>Statified MLB</h1>
      <p>Today's MLB games, live scores, and win probabilities.</p>

      <div className="main-grid">
        {/* LEFT PANEL */}
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

          {statOptions.map((stat) => (
            <div key={stat.key}>
              <label>
                <input
                  type="checkbox"
                  checked={selectedStats.includes(stat.key)}
                  onChange={() => toggleStat(stat.key)}
                />
                {" "}{stat.label}
              </label>
            </div>
          ))}

          <button onClick={generateProbability}>
            Generate Probability
          </button>
        </div>

        {/* RIGHT PANEL */}
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
                {Math.round(result.p_home_win * 100)}%{" "}
                {result.home_team} win
              </h2>
              <p>
                {Math.round(result.p_away_win * 100)}%{" "}
                {result.away_team} win
              </p>

              <div style={{ marginTop: 12 }}>
                You've been Statified
              </div>
            </>
          )}
        </div>
      </div>

      {/* GAME LIST */}
      <h2 style={{ marginTop: 40 }}>Today's MLB Games</h2>
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
  );
}

export default App;