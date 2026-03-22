import { useMemo, useState, useEffect } from "react";

const STAT_OPTIONS = [
  { key: "net_rating_last10", label: "Net Rating (Last 10)" },
  { key: "rest_days", label: "Rest Days" },
  { key: "turnover_diff", label: "Turnover Differential" },
  { key: "pace_diff", label: "Pace Differential" },
  { key: "home_away_split", label: "Home/Away Split" },
  { key: "timezone", label: "Timezone Travel" }
  
];

export default function App() {
  const [homeTeam, setHomeTeam] = useState("Dodgers");
  const [awayTeam, setAwayTeam] = useState("Giants");
  const [selected, setSelected] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [games, setGames] = useState([]);
  const [gamesLoading, setGamesLoading] = useState(false);
  const [gamesError, setGamesError] = useState("");

  useEffect(() => {
    async function fetchGames() {
      setGamesLoading(true);
      try {
        const res = await fetch("http://127.0.0.1:8000/mlb-games-with-probabilities");
        const data = await res.json();
        setGames(data.games || []);
      } catch (err) {
        console.error("Failed to fetch MLB games:", err);
        setGamesError("Failed to load MLB games");
      } finally {
        setGamesLoading(false);
      }
    }

  fetchGames();
}, []);
  
  const selectedKeys = useMemo(() => new Set(selected), [selected]);

  function toggleStat(key) {
    setSelected((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  }

  async function getProbability() {
    setLoading(true);
    setResult(null);
  
    try {
      const payload = {
        sport: "baseball",
        league: "MLB",
        home_team: homeTeam,
        away_team: awayTeam,
        selected_stats: selected.map((k) => ({ stat_key: k, weight: 1.0 })),
      };
  
      const res = await fetch("http://127.0.0.1:8000/probability", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
  
      if (!res.ok) {
        throw new Error(`HTTP error ${res.status}`);
      }
  
      const data = await res.json();
      console.log("backend response:", data);
      setResult(data);
    } catch (error) {
      console.error("Probability request failed:", error);
      setResult({
        home_team: homeTeam,
        away_team: awayTeam,
        p_home_win: 0,
        p_away_win: 0,
        message: "Request failed. Check backend terminal.",
        selected_stats_count: selected.length,
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: "40px auto", fontFamily: "system-ui" }}>
      <h1 style={{ marginBottom: 6 }}>Statified MLB</h1>
      <div style={{ opacity: 0.7, marginBottom: 24 }}>
        Today's MLB games, live scores, and win probabilities.
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        <div style={{ border: "1px solid #ddd", borderRadius: 12, padding: 16 }}>
          <h2 style={{ marginTop: 0 }}>Game</h2>

          <div style={{ display: "grid", gap: 10 }}>
            <label>
              Home Team
              <input
                value={homeTeam}
                onChange={(e) => setHomeTeam(e.target.value)}
                style={{ width: "100%", padding: 10, marginTop: 6 }}
              />
            </label>

            <label>
              Away Team
              <input
                value={awayTeam}
                onChange={(e) => setAwayTeam(e.target.value)}
                style={{ width: "100%", padding: 10, marginTop: 6 }}
              />
            </label>
          </div>

          <h2 style={{ marginTop: 18 }}>Stat Packs (MVP)</h2>

          <div style={{ display: "grid", gap: 10 }}>
            {STAT_OPTIONS.map((s) => (
              <label key={s.key} style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <input
                  type="checkbox"
                  checked={selectedKeys.has(s.key)}
                  onChange={() => toggleStat(s.key)}
                />
                {s.label}
              </label>
            ))}
          </div>

          <button
            className="statified-button"
            onClick={getProbability}
            disabled={loading}
            style={{
              marginTop: 18,
              padding: "12px 14px",
              borderRadius: 10,
              cursor: "pointer",
            }}
          >

            {loading ? "Statifying..." : "Generate Probability"}
          </button>
        </div>

        <div style={{ border: "1px solid #ddd", borderRadius: 12, padding: 16 }}>
          <h2 style={{ marginTop: 0 }}>Result</h2>

          <div style={{ marginBottom: 12, opacity: 0.8 }}>
            Your Stat Parlay:{" "}
            {selected.length === 0 ? <span>(none)</span> : <span>{selected.join(", ")}</span>}
          </div>

          {!result && !loading && (
            <div style={{ opacity: 0.7 }}>
              Select a few stats and click <b>Generate Probability</b>.
            </div>
          )}

          {loading && <div>Calculating...</div>}

          {result && (
            <div>
              <div style={{ fontSize: 28, fontWeight: 700 }}>
                {Math.round(result.p_home_win * 100)}% {result.home_team} win
              </div>

              <div style={{ marginTop: 6, opacity: 0.8 }}>
                {Math.round(result.p_away_win * 100)}% {result.away_team} win
              </div>

              <div style={{ marginTop: 14, padding: 12, borderRadius: 10, background: "#f6f6f6" }}>
                <b>{result.message}</b>
              </div>

              <div style={{ marginTop: 10, opacity: 0.7 }}>
                Stats selected: {result.selected_stats_count}
              </div>
            </div>
          )}
        </div>
      </div>
      <div style={{ marginTop: 40 }}>
  <h2>Today's MLB Games</h2>

  {gamesLoading && <div>Loading games...</div>}
  {gamesError && <div>{gamesError}</div>}

  {games.map((game, index) => (
  <div
    key={index}
    style={{
      border: "1px solid #ddd",
      borderRadius: 12,
      padding: 12,
      marginBottom: 10,
    }}
  >
    <div style={{ fontWeight: 600 }}>
      {game.away_team} at {game.home_team}
    </div>

    <div style={{ opacity: 0.8 }}>
      Status: {game.status}
    </div>

    <div>
      {game.away_score == null || game.home_score == null
        ? "Score: Not started"
        : `Score: ${game.away_score} - ${game.home_score}`}
    </div>

    <div>
      Expected Runs: {game.away_team} {game.expected_away_runs} - {game.home_team} {game.expected_home_runs}
    </div>

    <div style={{ marginTop: 8 }}>
      Home Win: {Math.round(game.p_home_win * 100)}%
    </div>

    <div>
      Away Win: {Math.round(game.p_away_win * 100)}%
    </div>
  </div>
))}
</div>
    </div>
  );
}


