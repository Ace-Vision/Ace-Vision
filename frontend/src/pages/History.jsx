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

function History() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const token = localStorage.getItem('token');
    if (!user.id) { setLoading(false); return; }

    fetch(`${API_BASE}/users/${user.id}/history`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(r => r.json())
      .then(data => {
        setSessions(Array.isArray(data) ? data : []);
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
        <p className="text-[11px] font-semibold text-[#444] tracking-widest uppercase mb-2">Ace Vision</p>
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
            <p className="text-[10px] text-[#444] mt-1 font-semibold uppercase tracking-wider">{s.label}</p>
          </div>
        ))}
      </div>

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
