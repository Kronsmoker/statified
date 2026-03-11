import { useMemo, useState } from "react";

const STAT_OPTIONS = [
  { key: "net_rating_last10", label: "Net Rating (Last 10)" },
  { key: "rest_days", label: "Rest Days" },
  { key: "turnover_diff", label: "Turnover Differential" },
  { key: "pace_diff", label: "Pace Differential" },
  { key: "home_away_split", label: "Home/Away Split" },
];

export default function App() {
  const [homeTeam, setHomeTeam] = useState("Lakers");
  const [awayTeam, setAwayTeam] = useState("Suns");
  const [selected, setSelected] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const selectedKeys = useMemo(() => new Set(selected), [selected]);

  function toggleStat(key) {
    setSelected((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  }

  async function getProbability() {
    setLoading(true);
    setResult(null);

    const payload = {
      sport: "basketball",
      league: "NBA",
      home_team: homeTeam,
      away_team: awayTeam,
      selected_stats: selected.map((k) => ({ stat_key: k, weight: 1.0 })),
    };

    const res = await fetch("http://localhost:8000/probability", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    setResult(data);
    setLoading(false);
  }

  return (
    <div style={{ maxWidth: 900, margin: "40px auto", fontFamily: "system-ui" }}>
      <h1 style={{ marginBottom: 6 }}>Statified</h1>
      <div style={{ opacity: 0.7, marginBottom: 24 }}>
        Build your stat parlay → get a probability.
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
            onClick={getProbability}
            disabled={loading}
            style={{
              marginTop: 18,
              padding: "12px 14px",
              borderRadius: 10,
              border: "1px solid #000",
              background: "#000",
              color: "#fff",
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
    </div>
  );
}


