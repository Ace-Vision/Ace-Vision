import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE = process.env.REACT_APP_API_URL || '';

function sportLabel(s) {
  if (s === 'tennis_serve') return 'Tennis';
  return 'Badminton';
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function MatchHistory() {
  const navigate = useNavigate();
  const preferredSport = localStorage.getItem('preferred_sport');
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [opening, setOpening] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { setLoading(false); return; }

    fetch(`${API_BASE}/users/me/match_history`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => {
        const filtered = preferredSport
          ? data.filter(m => m.sport_type === preferredSport)
          : data;
        setMatches(filtered);
        setLoading(false);
      })
      .catch(() => { setError('Failed to load history.'); setLoading(false); });
  }, []);

  async function openMatch(session_id) {
    setOpening(session_id);
    try {
      const r = await fetch(`${API_BASE}/match_sessions/${session_id}`);
      if (!r.ok) throw new Error();
      const detail = await r.json();
      navigate('/movement-result', {
        state: {
          result: {
            session_id:    detail.session_id,
            rallies:       detail.rallies,
            rally_summary: detail.rally_summary,
            phase_analysis: detail.phase_analysis,
          },
          opponentName: detail.opponent_name || '',
          matchComment: detail.match_comment || '',
          sport:        detail.sport_type,
        },
      });
    } catch {
      setOpening(null);
      setError('Could not load match data.');
    }
  }

  return (
    <div className="min-h-screen bg-black pb-16">

      <div className="px-5 pt-14 pb-2 flex items-center gap-3">
        <button
          onClick={() => navigate('/home')}
          className="text-white/30 hover:text-white text-2xl leading-none transition-colors"
        >
          ‹
        </button>
        <span className="text-[11px] font-semibold text-white/25 uppercase tracking-widest">
          {preferredSport === 'tennis_serve' ? 'Tennis' : 'Badminton'} History
        </span>
      </div>

      <div className="px-5 pt-6">
        {loading && (
          <div className="flex justify-center pt-16">
            <div className="w-8 h-8 rounded-full border-2 border-white/10 border-t-[#C8FF57]" style={{ animation: 'spin 1s linear infinite' }} />
          </div>
        )}

        {!loading && error && (
          <p className="text-center text-sm text-white/30 pt-16">{error}</p>
        )}

        {!loading && !error && matches.length === 0 && (
          <div className="flex flex-col items-center gap-3 pt-20">
            <p className="text-white/20 text-sm">No match analyses saved yet.</p>
            <p className="text-white/12 text-xs text-center">
              Run a Match analysis and your results<br />will appear here automatically.
            </p>
          </div>
        )}

        {!loading && !error && matches.length > 0 && (
          <div className="space-y-3">
            {matches.map(m => (
              <button
                key={m.session_id}
                onClick={() => openMatch(m.session_id)}
                disabled={opening === m.session_id}
                className="w-full rounded-2xl px-5 pt-5 pb-4 text-left active:scale-[0.98] transition-all"
                style={{ background: '#111', border: '1px solid rgba(255,255,255,0.07)' }}
              >
                {/* Opponent name */}
                <div className="flex items-baseline gap-2 mb-3">
                  <span className="text-[11px] font-bold text-white/25 uppercase tracking-widest">VS</span>
                  <span
                    className="font-black text-white truncate"
                    style={{ fontSize: '28px', lineHeight: 1, letterSpacing: '-0.03em' }}
                  >
                    {m.opponent_name || 'Unknown'}
                  </span>
                </div>

                {/* Score + meta */}
                <div className="flex items-center justify-between">
                  <p className="text-white/25 text-[11px]">
                    {sportLabel(m.sport_type)} · {formatDate(m.created_at)}
                  </p>
                  <div className="flex items-center gap-2">
                    <span className="font-black tabular-nums text-white" style={{ fontSize: '20px', letterSpacing: '-0.03em' }}>
                      {m.my_score ?? '–'}
                    </span>
                    <span className="text-white/20 font-light">:</span>
                    <span className="font-black tabular-nums text-white/35" style={{ fontSize: '20px', letterSpacing: '-0.03em' }}>
                      {m.opp_score ?? '–'}
                    </span>
                    {opening === m.session_id ? (
                      <div className="w-4 h-4 rounded-full border-2 border-white/10 border-t-white/50 ml-1" style={{ animation: 'spin 1s linear infinite' }} />
                    ) : (
                      <span className="text-white/20 text-lg ml-1">›</span>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default MatchHistory;
