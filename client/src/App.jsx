import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API_FALLBACK = "http://127.0.0.1:8000";

const statOptions = [
  { key: "last10", label: "Recent Form", description: "Last 10 games", defaultWeight: 50, icon: "↗" },
  { key: "rest_days", label: "Rest Advantage", description: "Days since last game", defaultWeight: 50, icon: "◷" },
  { key: "home_away_split", label: "Venue Splits", description: "Home and road performance", defaultWeight: 50, icon: "⌂" },
  { key: "timezone", label: "Travel Impact", description: "Travel and time zones", defaultWeight: 50, icon: "✦" },
  { key: "pitcher_stats", label: "Starting Pitching", description: "Starter matchup", defaultWeight: 50, icon: "P" },
  { key: "bullpen_breakdown_score", label: "Bullpen Readiness", description: "Relief usage and fatigue", defaultWeight: 50, icon: "B" },
];

const teamAbbreviations = {
  "Arizona Diamondbacks": "ARI", "Atlanta Braves": "ATL", "Baltimore Orioles": "BAL",
  "Boston Red Sox": "BOS", "Chicago Cubs": "CHC", "Chicago White Sox": "CWS",
  "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE", "Colorado Rockies": "COL",
  "Detroit Tigers": "DET", "Houston Astros": "HOU", "Kansas City Royals": "KC",
  "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD", "Miami Marlins": "MIA",
  "Milwaukee Brewers": "MIL", "Minnesota Twins": "MIN", "New York Mets": "NYM",
  "New York Yankees": "NYY", "Athletics": "ATH", "Philadelphia Phillies": "PHI",
  "Pittsburgh Pirates": "PIT", "San Diego Padres": "SD", "San Francisco Giants": "SF",
  "Seattle Mariners": "SEA", "St. Louis Cardinals": "STL", "Tampa Bay Rays": "TB",
  "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH",
};

function Icon({ name, size = 20 }) {
  const paths = {
    home: <><path d="m3 11 9-8 9 8"/><path d="M5 10v10h14V10"/><path d="M9 20v-6h6v6"/></>,
    chart: <><path d="M4 19V9"/><path d="M10 19V5"/><path d="M16 19v-8"/><path d="M22 19H2"/></>,
    models: <><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></>,
    user: <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/></>,
    chevron: <path d="m9 18 6-6-6-6"/>,
    spark: <path d="m12 2 1.7 5.1L19 9l-5.3 1.9L12 16l-1.7-5.1L5 9l5.3-1.9L12 2Z"/>,
    lock: <><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></>,
  };
  return <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

function formatDate(dateString) {
  return new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric" })
    .format(new Date(`${dateString}T12:00:00`));
}

function shiftDate(dateString, amount) {
  const date = new Date(`${dateString}T12:00:00`);
  date.setDate(date.getDate() + amount);
  return date.toISOString().slice(0, 10);
}

function initials(team) {
  return teamAbbreviations[team] || team.split(" ").map((part) => part[0]).join("").slice(0, 3).toUpperCase();
}

function TeamBadge({ team, large = false }) {
  return <span className={`team-badge ${large ? "team-badge--large" : ""}`}>{initials(team)}</span>;
}

function App() {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || API_FALLBACK;
  const [games, setGames] = useState([]);
  const [selectedGame, setSelectedGame] = useState(null);
  const [selectedStats, setSelectedStats] = useState([
    { stat_key: "pitcher_stats", weight: 34, locked: false },
    { stat_key: "bullpen_breakdown_score", weight: 33, locked: false },
    { stat_key: "last10", weight: 33, locked: false },
  ]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [gamesLoading, setGamesLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("Games");
  const [modelOpen, setModelOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().slice(0, 10));
  const [isUnlocked, setIsUnlocked] = useState(localStorage.getItem("statified_unlocked") === "true");
  const [passwordInput, setPasswordInput] = useState("");
  const APP_PASSWORD = "statified2026";

  useEffect(() => {
    let cancelled = false;
    setGamesLoading(true);
    setError("");
    setSelectedGame(null);
    setResult(null);

    fetch(`${API_BASE_URL}/mlb-games?game_date=${selectedDate}`)
      .then((response) => {
        if (!response.ok) throw new Error("Could not load today’s games.");
        return response.json();
      })
      .then((data) => {
        if (cancelled) return;
        const loadedGames = Array.isArray(data) ? data : data.games || [];
        setGames(loadedGames);
        if (loadedGames.length) setSelectedGame(loadedGames[0]);
      })
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setGamesLoading(false));

    return () => { cancelled = true; };
  }, [selectedDate, API_BASE_URL]);

  const totalWeight = useMemo(() => selectedStats.reduce((sum, stat) => sum + stat.weight, 0), [selectedStats]);

  function handleUnlock(event) {
    event.preventDefault();
    if (passwordInput === APP_PASSWORD) {
      localStorage.setItem("statified_unlocked", "true");
      setIsUnlocked(true);
    } else {
      setError("That password is not correct.");
    }
  }

  function toggleStat(stat) {
    setSelectedStats((current) => {
      const exists = current.some((item) => item.stat_key === stat.key);
      if (exists) return current.filter((item) => item.stat_key !== stat.key);
      return [...current, { stat_key: stat.key, weight: stat.defaultWeight, locked: false }];
    });
  }

  function updateWeight(statKey, newPercent) {
    setSelectedStats((current) => {
      const target = current.find((item) => item.stat_key === statKey);
      if (!target || target.locked) return current;
      const locked = current.filter((item) => item.locked);
      const unlockedOthers = current.filter((item) => !item.locked && item.stat_key !== statKey);
      const lockedTotal = locked.reduce((sum, item) => sum + item.weight, 0);
      const maxAllowed = Math.max(0, 100 - lockedTotal);
      const updatedWeight = Math.min(Number(newPercent), maxAllowed);
      const remaining = maxAllowed - updatedWeight;
      const otherTotal = unlockedOthers.reduce((sum, item) => sum + item.weight, 0);

      return current.map((item) => {
        if (item.stat_key === statKey) return { ...item, weight: updatedWeight };
        if (item.locked || !unlockedOthers.length) return item;
        return { ...item, weight: otherTotal === 0 ? remaining / unlockedOthers.length : (item.weight / otherTotal) * remaining };
      });
    });
  }

  function toggleLock(statKey) {
    setSelectedStats((current) => current.map((item) => item.stat_key === statKey ? { ...item, locked: !item.locked } : item));
  }

  async function generateProbability() {
    if (!selectedGame || selectedStats.length === 0 || totalWeight === 0) return;
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(`${API_BASE_URL}/probability`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sport: "baseball",
          league: "mlb",
          home_team: selectedGame.home_team,
          away_team: selectedGame.away_team,
          selected_stats: selectedStats.map((stat) => ({ stat_key: stat.stat_key, weight: stat.weight / totalWeight })),
          model_name: "custom_ui",
        }),
      });
      if (!response.ok) throw new Error("Prediction request failed.");
      setResult(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const homeProbability = result ? Math.round(result.p_home_win * 100) : 50;
  const awayProbability = result ? Math.round(result.p_away_win * 100) : 50;
  const confidence = result ? Math.max(homeProbability, awayProbability) : null;
  const winningTeam = result ? (homeProbability >= awayProbability ? result.home_team : result.away_team) : null;
  const confidenceLabel = confidence >= 65 ? "Strong edge" : confidence >= 58 ? "Moderate edge" : "Lean";

  if (!isUnlocked) {
    return (
      <main className="login-screen">
        <div className="login-glow" />
        <form className="login-card" onSubmit={handleUnlock}>
          <div className="brand-mark"><Icon name="spark" size={26} /></div>
          <p className="eyebrow">SPORTS INTELLIGENCE</p>
          <h1>Welcome to <span>Statified</span></h1>
          <p className="login-copy">Professional matchup analysis, powered by your model.</p>
          <label className="field-label" htmlFor="password">Access password</label>
          <div className="password-field"><Icon name="lock" size={18}/><input id="password" type="password" value={passwordInput} onChange={(event) => setPasswordInput(event.target.value)} placeholder="Enter password" /></div>
          {error && <p className="form-error">{error}</p>}
          <button className="primary-button" type="submit">Enter Statified <Icon name="chevron" size={18}/></button>
        </form>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><div className="brand-mark"><Icon name="spark" size={22}/></div><div><strong>STATIFIED</strong><span>SPORTS INTELLIGENCE</span></div></div>
        <nav className="desktop-nav">
          {["Games", "Predictions", "Performance", "Models"].map((tab) => <button key={tab} className={activeTab === tab ? "active" : ""} onClick={() => { setActiveTab(tab); if (tab === "Models") setModelOpen(true); }}>{tab}</button>)}
        </nav>
        <button className="profile-button"><span>CG</span><div><strong>Pro Access</strong><small>Account</small></div></button>
      </header>

      <div className="league-strip">
        <div className="league-tabs"><button className="active"><span>MLB</span></button><button disabled>NFL</button><button disabled>NBA</button><button disabled>NHL</button></div>
        <div className="live-pill"><span></span> Live data</div>
      </div>

      <main className="dashboard-wrap">
        <section className="page-heading">
          <div><p className="eyebrow">TODAY’S BOARD</p><h1>MLB Matchups</h1><p>Model-driven probabilities and matchup intelligence.</p></div>
          <div className="date-control"><button aria-label="Previous day" onClick={() => setSelectedDate(shiftDate(selectedDate, -1))}>‹</button><label><Icon name="calendar" size={18}/><span>{formatDate(selectedDate)}</span><input type="date" value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)} /></label><button aria-label="Next day" onClick={() => setSelectedDate(shiftDate(selectedDate, 1))}>›</button></div>
        </section>

        {error && <div className="alert-banner">{error}</div>}

        <div className="dashboard-grid">
          <section className="games-panel">
            <div className="section-header"><div><h2>Game lines</h2><span>{games.length} games scheduled</span></div><button className="model-chip" onClick={() => setModelOpen(true)}><Icon name="models" size={17}/> Custom model</button></div>

            <div className="games-list">
              {gamesLoading && Array.from({ length: 5 }).map((_, index) => <div className="game-row skeleton" key={index}/>) }
              {!gamesLoading && games.length === 0 && <div className="empty-state"><div>⚾</div><h3>No games scheduled</h3><p>Choose another date to view MLB matchups.</p></div>}
              {!gamesLoading && games.map((game) => {
                const selected = selectedGame?.game_pk === game.game_pk || (selectedGame?.home_team === game.home_team && selectedGame?.away_team === game.away_team);
                return (
                  <button className={`game-row ${selected ? "selected" : ""}`} key={game.game_pk || `${game.away_team}-${game.home_team}`} onClick={() => { setSelectedGame(game); setResult(null); }}>
                    <div className="game-status"><span className="league-label">MLB</span><small>{game.status || "Scheduled"}</small></div>
                    <div className="teams-stack">
                      <div><TeamBadge team={game.away_team}/><strong>{game.away_team}</strong>{game.away_score != null && <b>{game.away_score}</b>}</div>
                      <div><TeamBadge team={game.home_team}/><strong>{game.home_team}</strong>{game.home_score != null && <b>{game.home_score}</b>}</div>
                    </div>
                    <div className="row-action"><span>{selected ? "Selected" : "Analyze"}</span><Icon name="chevron" size={18}/></div>
                  </button>
                );
              })}
            </div>
          </section>

          <aside className="analysis-panel">
            {!selectedGame ? (
              <div className="analysis-empty"><div className="analysis-icon"><Icon name="chart" size={30}/></div><h2>Select a matchup</h2><p>Choose a game to generate a Statified win probability.</p></div>
            ) : (
              <>
                <div className="analysis-head"><div><span className="league-label">MATCHUP ANALYSIS</span><small>{selectedGame.status || "Scheduled"}</small></div><button className="icon-button" onClick={() => setModelOpen(true)}><Icon name="models" size={19}/></button></div>

                <div className="matchup-hero">
                  <div className="hero-team"><TeamBadge team={selectedGame.away_team} large/><strong>{initials(selectedGame.away_team)}</strong><span>Away</span></div>
                  <div className="matchup-center"><span>AT</span><small>{formatDate(selectedDate)}</small></div>
                  <div className="hero-team"><TeamBadge team={selectedGame.home_team} large/><strong>{initials(selectedGame.home_team)}</strong><span>Home</span></div>
                </div>

                {!result && !loading && (
                  <div className="pre-prediction">
                    <div className="model-summary"><div><span>Active model</span><strong>Custom Intelligence</strong></div><span>{selectedStats.length} factors</span></div>
                    <div className="factor-pills">{selectedStats.slice(0, 4).map((item) => <span key={item.stat_key}>{statOptions.find((option) => option.key === item.stat_key)?.label}</span>)}</div>
                    <button className="primary-button generate-button" onClick={generateProbability} disabled={!selectedStats.length}>Statify this game <Icon name="spark" size={18}/></button>
                  </div>
                )}

                {loading && <div className="loading-analysis"><div className="spinner"/><h3>Running matchup model</h3><p>Comparing selected performance factors...</p></div>}

                {result && (
                  <div className="prediction-result">
                    <div className="pick-banner"><p>STATIFIED PICK</p><h2>{winningTeam}</h2><span className={`confidence-badge ${confidence >= 65 ? "high" : ""}`}>{confidenceLabel}</span></div>
                    <div className="probability-head"><span>Win probability</span><strong>{confidence}%</strong></div>
                    <div className="probability-track"><div className="away-fill" style={{ width: `${awayProbability}%` }}/><div className="home-fill" style={{ width: `${homeProbability}%` }}/></div>
                    <div className="probability-labels"><div><TeamBadge team={result.away_team}/><span>{initials(result.away_team)}</span><strong>{awayProbability}%</strong></div><div><strong>{homeProbability}%</strong><span>{initials(result.home_team)}</span><TeamBadge team={result.home_team}/></div></div>
                    <div className="score-projection"><div><span>Projected score</span><strong>{result.away_team} {result.expected_away_runs ?? "—"}</strong></div><b>–</b><div><span>Home</span><strong>{result.home_team} {result.expected_home_runs ?? "—"}</strong></div></div>
                    <div className="insight-card"><div className="insight-icon"><Icon name="spark" size={18}/></div><div><span>Top model edge</span><strong>{String(result.biggest_edge?.name || "Model consensus").replaceAll("_", " ")}</strong></div></div>
                    <button className="secondary-button" onClick={generateProbability}>Recalculate matchup</button>
                  </div>
                )}
              </>
            )}
          </aside>
        </div>
      </main>

      <nav className="mobile-nav">{[["Games","home"],["Picks","spark"],["Stats","chart"],["Models","models"],["Account","user"]].map(([label, icon]) => <button key={label} className={label === "Games" ? "active" : ""} onClick={() => label === "Models" && setModelOpen(true)}><Icon name={icon} size={20}/><span>{label}</span></button>)}</nav>

      {modelOpen && <div className="drawer-backdrop" onClick={() => setModelOpen(false)}><aside className="model-drawer" onClick={(event) => event.stopPropagation()}><div className="drawer-head"><div><p className="eyebrow">CUSTOM MODEL</p><h2>Intelligence factors</h2></div><button onClick={() => setModelOpen(false)}>×</button></div><p className="drawer-copy">Select the inputs your prediction should weigh. Active weights automatically rebalance to 100%.</p><div className="model-total"><span>Model allocation</span><strong>{Math.round(totalWeight)}%</strong></div><div className="factor-list">{statOptions.map((stat) => { const selected = selectedStats.find((item) => item.stat_key === stat.key); return <div className={`factor-card ${selected ? "active" : ""}`} key={stat.key}><button className="factor-toggle" onClick={() => toggleStat(stat)}><span className="factor-icon">{stat.icon}</span><span><strong>{stat.label}</strong><small>{stat.description}</small></span><i>{selected ? "✓" : "+"}</i></button>{selected && <div className="factor-controls"><input type="range" min="0" max="100" value={Math.round(selected.weight)} disabled={selected.locked} onChange={(event) => updateWeight(stat.key, event.target.value)}/><strong>{Math.round(selected.weight)}%</strong><button className={selected.locked ? "locked" : ""} onClick={() => toggleLock(stat.key)}><Icon name="lock" size={16}/></button></div>}</div>; })}</div><button className="primary-button drawer-save" onClick={() => setModelOpen(false)}>Apply model</button></aside></div>}
    </div>
  );
}

export default App;
