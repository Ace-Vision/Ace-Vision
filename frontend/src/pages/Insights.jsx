import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE = process.env.REACT_APP_API_URL || '';

function PieChart({ slices }) {
  const active = slices.filter(s => s.count > 0);
  const total  = active.reduce((s, d) => s + d.count, 0);
  if (total === 0) return null;

  const cx = 50, cy = 50, R = 40, ir = 24;
  const isSingle = active.length === 1;
  let paths = [];
  if (!isSingle) {
    let angle = -Math.PI / 2;
    paths = active.map(slice => {
      const startA = angle;
      const sweep  = (slice.count / total) * 2 * Math.PI;
      angle += sweep;
      const endA = angle;
      const large = sweep > Math.PI ? 1 : 0;
      const x1  = cx + R  * Math.cos(startA), y1  = cy + R  * Math.sin(startA);
      const x2  = cx + R  * Math.cos(endA),   y2  = cy + R  * Math.sin(endA);
      const ix1 = cx + ir * Math.cos(startA), iy1 = cy + ir * Math.sin(startA);
      const ix2 = cx + ir * Math.cos(endA),   iy2 = cy + ir * Math.sin(endA);
      const d = `M${x1} ${y1} A${R} ${R} 0 ${large} 1 ${x2} ${y2} L${ix2} ${iy2} A${ir} ${ir} 0 ${large} 0 ${ix1} ${iy1}Z`;
      return { ...slice, d };
    });
  }

  return (
    <div className="flex items-center gap-8">
      <svg viewBox="0 0 100 100" style={{ width: 120, height: 120, flexShrink: 0 }}>
        {isSingle ? (
          <>
            <circle cx={cx} cy={cy} r={R} fill={active[0].color} />
            <circle cx={cx} cy={cy} r={ir} fill="#0d0d0d" />
          </>
        ) : (
          paths.map((p, i) => <path key={i} d={p.d} fill={p.color} />)
        )}
      </svg>
      <div className="space-y-3">
        {active.map((s, i) => (
          <div key={i} className="flex items-center gap-2.5">
            <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: s.color }} />
            <span className="text-xs text-white/50">{s.label}</span>
            <span className="text-xs font-bold text-white ml-2 tabular-nums">{s.count}</span>
            <span className="text-[10px] text-white/20">
              ({Math.round(s.count / total * 100)}%)
            </span>
          </div>
        ))}
        <p className="text-[10px] text-white/20 pt-1">{total} tagged losses total</p>
      </div>
    </div>
  );
}

function Insights() {
  const navigate = useNavigate();
  const preferredSport = localStorage.getItem('preferred_sport');
  const sportLabel = preferredSport === 'tennis_serve' ? 'Tennis' : 'Badminton';

  const [loading, setLoading] = useState(true);
  const [pieSlices, setPieSlices] = useState([]);
  const [totalLabeled, setTotalLabeled] = useState(0);
  const [matchCount, setMatchCount] = useState(0);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { setLoading(false); return; }

    const twoWeeksAgo = new Date();
    twoWeeksAgo.setDate(twoWeeksAgo.getDate() - 14);

    fetch(`${API_BASE}/users/me/match_history`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then(async matches => {
        const recent = matches.filter(m => {
          const rightSport = preferredSport ? m.sport_type === preferredSport : true;
          const recentEnough = new Date(m.created_at) >= twoWeeksAgo;
          return rightSport && recentEnough;
        });

        setMatchCount(recent.length);

        if (recent.length === 0) { setLoading(false); return; }

        const labelResults = await Promise.all(
          recent.map(m =>
            fetch(`${API_BASE}/rally_labels/${m.session_id}`)
              .then(r => r.json())
              .then(data => data.labels || {})
              .catch(() => ({}))
          )
        );

        const counts = { swing_miss: 0, bad_footwork: 0, other: 0 };
        for (const labels of labelResults) {
          for (const label of Object.values(labels)) {
            if (label in counts) counts[label]++;
          }
        }

        const total = counts.swing_miss + counts.bad_footwork + counts.other;
        setTotalLabeled(total);
        setPieSlices([
          { label: 'Swing Miss',   count: counts.swing_miss,   color: '#FF6B6B' },
          { label: 'Bad Footwork', count: counts.bad_footwork, color: '#FF9F43' },
          { label: 'Other',        count: counts.other,        color: '#636e72' },
        ]);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="min-h-screen bg-black pb-16">

      {/* Header */}
      <div className="px-5 pt-14 pb-2 flex items-center gap-3">
        <button
          onClick={() => navigate('/home')}
          className="text-white/30 hover:text-white text-2xl leading-none transition-colors"
        >
          ‹
        </button>
        <span className="text-[11px] font-semibold text-white/25 uppercase tracking-widest">
          Insights
        </span>
      </div>

      <div className="px-5 pt-6 space-y-5">

        {/* 2-week loss breakdown */}
        <div
          className="rounded-2xl p-5 animate-fade-up"
          style={{ background: '#0d0d0d', border: '1px solid rgba(255,255,255,0.06)' }}
        >
          <div className="mb-4">
            <p className="text-[10px] font-bold text-white/25 uppercase tracking-widest mb-1">
              Last 2 Weeks · {sportLabel}
            </p>
            <p className="text-xs text-white/35">
              Mistake breakdown across all recent matches
            </p>
          </div>

          {loading ? (
            <div className="space-y-2 py-2">
              {[1, 0.75, 0.5].map((w, i) => (
                <div
                  key={i}
                  className="h-2 rounded-full bg-white/[0.05]"
                  style={{ width: `${w * 100}%`, animation: `pulse 1.5s ease-in-out ${i * 0.15}s infinite` }}
                />
              ))}
            </div>
          ) : matchCount === 0 ? (
            <div className="py-4">
              <p className="text-sm text-white/20">No matches in the last 2 weeks.</p>
              <p className="text-xs text-white/12 mt-1">
                Run a match analysis and your data will appear here.
              </p>
            </div>
          ) : totalLabeled === 0 ? (
            <div className="py-4">
              <p className="text-sm text-white/20">No tagged losses yet.</p>
              <p className="text-xs text-white/12 mt-1">
                Tag each loss point in Rally Analysis to see trends here.
              </p>
            </div>
          ) : (
            <PieChart slices={pieSlices} />
          )}
        </div>

        {/* Match History */}
        <button
          onClick={() => navigate('/match-history')}
          className="w-full rounded-2xl px-5 py-5 text-left active:scale-[0.98] transition-all animate-fade-up"
          style={{ background: '#111', border: '1px solid rgba(255,255,255,0.07)', animationDelay: '0.05s' }}
        >
          <div className="text-white font-semibold mb-1" style={{ fontSize: '16px', letterSpacing: '0.02em' }}>
            Match History
          </div>
          <div className="text-white/30 text-xs">
            Review past match analyses
          </div>
        </button>

        {/* Opponent Book (dummy) */}
        <button
          onClick={() => navigate('/opponent-book')}
          className="w-full rounded-2xl px-5 py-5 text-left active:scale-[0.98] transition-all animate-fade-up"
          style={{ background: '#111', border: '1px solid rgba(255,255,255,0.07)', animationDelay: '0.1s' }}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-white font-semibold" style={{ fontSize: '16px', letterSpacing: '0.02em' }}>
              Opponent Book
            </span>
            <span
              className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
              style={{ background: 'rgba(255,255,255,0.07)', color: 'rgba(255,255,255,0.3)', letterSpacing: '0.06em' }}
            >
              SOON
            </span>
          </div>
          <div className="text-white/30 text-xs">
            Tendencies and trends of past opponents
          </div>
        </button>

      </div>
    </div>
  );
}

export default Insights;
