import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE = process.env.REACT_APP_API_URL || '';

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function OpponentBook() {
  const navigate = useNavigate();
  const preferredSport = localStorage.getItem('preferred_sport');

  const [opponents, setOpponents] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { setLoading(false); return; }

    fetch(`${API_BASE}/users/me/match_history`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(matches => {
        const filtered = preferredSport
          ? matches.filter(m => m.sport_type === preferredSport)
          : matches;

        // Group by opponent_name (ignore null / empty)
        const map = new Map();
        for (const m of filtered) {
          const name = (m.opponent_name || '').trim();
          if (!name) continue;
          if (!map.has(name)) {
            map.set(name, { name, wins: 0, losses: 0, sessions: [], lastDate: m.created_at });
          }
          const opp = map.get(name);
          if ((m.my_score ?? 0) > (m.opp_score ?? 0)) opp.wins++;
          else opp.losses++;
          opp.sessions.push(m);
          if (m.created_at > opp.lastDate) opp.lastDate = m.created_at;
        }

        setOpponents([...map.values()].sort((a, b) => b.lastDate.localeCompare(a.lastDate)));
        setLoading(false);
      })
      .catch(() => { setError('Failed to load history.'); setLoading(false); });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="min-h-screen bg-black pb-16">

      <div className="px-5 pt-14 pb-2 flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="text-white/30 hover:text-white text-2xl leading-none transition-colors"
        >
          ‹
        </button>
        <span className="text-[11px] font-semibold text-white/25 uppercase tracking-widest">
          Opponent Book
        </span>
      </div>

      <div className="px-5 pt-6">
        {loading && (
          <div className="flex justify-center pt-16">
            <div className="w-8 h-8 rounded-full border-2 border-white/10 border-t-[#C8FF57]"
              style={{ animation: 'spin 1s linear infinite' }} />
          </div>
        )}

        {!loading && error && (
          <p className="text-center text-sm text-white/30 pt-16">{error}</p>
        )}

        {!loading && !error && opponents.length === 0 && (
          <div className="flex flex-col items-center gap-3 pt-20">
            <p className="text-white/20 text-sm">No named opponents yet.</p>
            <p className="text-white/12 text-xs text-center leading-relaxed">
              When you enter an opponent's name during<br />match analysis, they'll appear here.
            </p>
          </div>
        )}

        {!loading && !error && opponents.length > 0 && (
          <div className="space-y-3">
            {opponents.map(opp => (
              <button
                key={opp.name}
                onClick={() => navigate('/opponent-detail', { state: { opponent: opp } })}
                className="w-full rounded-2xl px-5 pt-5 pb-4 text-left active:scale-[0.98] transition-all"
                style={{ background: '#111', border: '1px solid rgba(255,255,255,0.07)' }}
              >
                <div className="flex items-baseline gap-2 mb-3">
                  <span className="text-[11px] font-bold text-white/25 uppercase tracking-widest">VS</span>
                  <span
                    className="font-black text-white truncate"
                    style={{ fontSize: '28px', lineHeight: 1, letterSpacing: '-0.03em' }}
                  >
                    {opp.name}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <p className="text-white/25 text-[11px]">
                    {opp.sessions.length} {opp.sessions.length === 1 ? 'match' : 'matches'} · Last {formatDate(opp.lastDate)}
                  </p>
                  <div className="flex items-center gap-2">
                    <span className="font-black tabular-nums text-[#C8FF57]"
                      style={{ fontSize: '18px', letterSpacing: '-0.03em' }}>{opp.wins}W</span>
                    <span className="text-white/20 font-light text-sm">–</span>
                    <span className="font-black tabular-nums text-white/35"
                      style={{ fontSize: '18px', letterSpacing: '-0.03em' }}>{opp.losses}L</span>
                    <span className="text-white/20 text-lg ml-1">›</span>
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

export default OpponentBook;
