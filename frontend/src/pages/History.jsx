import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE = process.env.REACT_APP_API_URL || '';

function scoreColor(s) {
  if (s >= 75) return 'text-[#C8FF57]';
  if (s >= 55) return 'text-amber-400';
  return 'text-red-400';
}

function sportLabel(sport) {
  return sport === 'badminton' ? 'Badminton' : 'Tennis';
}

function sportCode(sport) {
  return sport === 'badminton' ? 'BD' : 'TN';
}

function sessionToResult(s) {
  const deviations = {};
  (s.deviations || []).forEach(d => {
    deviations[d.joint_name] = {
      angle: d.player_angle,
      deviation_deg: d.deviation_deg,
      severity_score: d.severity_score,
    };
  });
  return {
    session_id: s.id,
    overall_score: s.overall_score,
    sport_type: s.sport_type,
    overlay_path: `/overlay/${s.id}`,
    deviation_scores: { deviations, checkpoints: {} },
    coaching: s.coaching_feedback,
  };
}

function dotColor(s) {
  if (s >= 75) return '#C8FF57';
  if (s >= 55) return '#f59e0b';
  return '#f87171';
}

function ProgressChart({ data }) {
  if (!data || data.length < 2) return null;

  const W = 300, H = 90;
  const pad = { t: 12, b: 12, l: 12, r: 12 };
  const plotW = W - pad.l - pad.r;
  const plotH = H - pad.t - pad.b;
  const n = data.length;
  const xOf = i => pad.l + (n === 1 ? plotW / 2 : (i * plotW) / (n - 1));
  const yOf = score => pad.t + plotH - (score / 100) * plotH;
  const points = data.map((d, i) => `${xOf(i)},${yOf(d.overall_score)}`).join(' ');

  return (
    <div className="card px-4 pt-3 pb-2 mb-5">
      <p className="text-[10px] font-semibold text-[#444] uppercase tracking-widest mb-2">Score Trend</p>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 90 }}>
        {/* midline at 50 */}
        <line
          x1={pad.l} y1={yOf(50)} x2={W - pad.r} y2={yOf(50)}
          stroke="#1e1e1e" strokeWidth="1" strokeDasharray="4 3"
        />
        {/* score line */}
        <polyline
          points={points}
          fill="none" stroke="#C8FF57" strokeWidth="1.5"
          strokeLinecap="round" strokeLinejoin="round" opacity="0.45"
        />
        {/* dots */}
        {data.map((d, i) => (
          <circle key={i} cx={xOf(i)} cy={yOf(d.overall_score)} r="4" fill={dotColor(d.overall_score)} />
        ))}
      </svg>
      <div className="flex justify-between mt-1">
        <span className="text-[9px] text-[#333]">
          {data.length > 0 && new Date(data[0].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
        </span>
        <span className="text-[9px] text-[#333]">
          {data.length > 1 && new Date(data[data.length - 1].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
        </span>
      </div>
    </div>
  );
}

function History() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const token = localStorage.getItem('token');
    if (!user.id) { setLoading(false); return; }

    const headers = token ? { Authorization: `Bearer ${token}` } : {};

    Promise.all([
      fetch(`${API_BASE}/users/${user.id}/history`, { headers }).then(r => r.json()),
      fetch(`${API_BASE}/users/${user.id}/progress/chart`, { headers }).then(r => r.json()),
    ])
      .then(([history, chart]) => {
        setSessions(Array.isArray(history) ? history : []);
        setChartData(Array.isArray(chart) ? chart : []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const avg = sessions.length
    ? Math.round(sessions.reduce((a, s) => a + s.overall_score, 0) / sessions.length)
    : 0;
  const best = sessions.length ? Math.max(...sessions.map(s => s.overall_score)) : 0;

  return (
    <div className="min-h-screen bg-[#0a0a0a] pb-28">

      <div className="px-5 pt-16 pb-7">
        <p className="text-[13px] font-semibold text-[#444] tracking-widest uppercase mb-2">Ace Vision</p>
        <h1 className="text-3xl font-bold text-white">History.</h1>
      </div>

      {/* Stats row */}
      <div className="px-5 mb-5 grid grid-cols-3 gap-3">
        {[
          { label: 'Sessions', value: loading ? '—' : sessions.length },
          { label: 'Avg',      value: loading || !sessions.length ? '—' : avg },
          { label: 'Best',     value: loading || !sessions.length ? '—' : best },
        ].map(s => (
          <div key={s.label} className="card p-4 text-center">
            <p className="text-2xl font-black text-white tabular-nums">{s.value}</p>
            <p className="text-[12px] text-[#444] mt-1 font-semibold uppercase tracking-wider">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Progress chart */}
      {!loading && chartData.length >= 2 && (
        <div className="px-5">
          <ProgressChart data={chartData} />
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-10">
          <div
            className="w-6 h-6 rounded-full border-2 border-white/10 border-t-[#C8FF57]"
            style={{ animation: 'spin 1s linear infinite' }}
          />
        </div>
      ) : sessions.length === 0 ? (
        <p className="px-5 text-sm text-[#444] text-center py-10">
          No sessions yet. Analyze a video to get started.
        </p>
      ) : (
        <div className="px-5 space-y-2">
          {sessions.slice().reverse().map(s => (
            <button
              key={s.id}
              onClick={() => navigate('/result', { state: { result: sessionToResult(s) } })}
              className="w-full card-sm px-4 py-4 flex items-center gap-4 text-left hover:bg-[#161616] transition-colors"
            >
              <div className="w-9 h-9 rounded-lg bg-[#1e1e1e] flex items-center justify-center text-[#555] text-xs font-bold shrink-0">
                {sportCode(s.sport_type)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-white">{sportLabel(s.sport_type)}</p>
                <p className="text-xs text-[#444] mt-0.5">
                  {new Date(s.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </p>
              </div>
              <span className={`text-sm font-black tabular-nums ${scoreColor(s.overall_score)}`}>
                {s.overall_score}
              </span>
            </button>
          ))}
        </div>
      )}

    </div>
  );
}

export default History;
