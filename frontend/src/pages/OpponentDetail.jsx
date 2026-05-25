import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const API_BASE = process.env.REACT_APP_API_URL || '';
const COURT_W  = 400;
const COURT_H  = 440;

// ── Pie chart ────────────────────────────────────────────────────────────────
function PieChart({ slices }) {
  const active = slices.filter(s => s.count > 0);
  const total  = active.reduce((s, d) => s + d.count, 0);
  if (total === 0) return null;

  const cx = 50, cy = 50, R = 40, ir = 24;

  // Single slice: SVG arc can't draw a full circle, use circles instead
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

// ── Main component ────────────────────────────────────────────────────────────
function OpponentDetail() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const opponent = state?.opponent;

  const preferredSport = localStorage.getItem('preferred_sport') || 'badminton';

  // Derived data from sessions
  const sessions = opponent?.sessions ?? [];
  const sessionIds = sessions.map(s => s.session_id);

  // Pie chart state
  const [pieSlices, setPieSlices]   = useState([]);
  const [totalLabeled, setTotalLabeled] = useState(0);
  const [labelsLoading, setLabelsLoading] = useState(true);

  // Combined heatmap
  const heatmapSrc = sessionIds.length > 0
    ? `${API_BASE}/combined_heatmap?sessions=${sessionIds.join(',')}`
    : null;

  // Court positions (for zone analysis → AI prompt)
  const [allPositions, setAllPositions] = useState([]);
  const positionsFetched = useRef(false);

  // AI coaching
  const [coaching, setCoaching]     = useState(null);
  const [coachingLoading, setCoachingLoading] = useState(false);
  const [coachingError, setCoachingError]     = useState(null);
  const coachingFetched = useRef(false);

  // 1. Fetch all rally labels in parallel and aggregate
  useEffect(() => {
    if (!sessionIds.length) { setLabelsLoading(false); return; }

    Promise.all(
      sessionIds.map(sid =>
        fetch(`${API_BASE}/rally_labels/${sid}`)
          .then(r => r.json())
          .then(d => d.labels || {})
          .catch(() => ({}))
      )
    ).then(results => {
      const counts = { swing_miss: 0, bad_footwork: 0, other: 0 };
      for (const labels of results) {
        for (const v of Object.values(labels)) {
          if (v in counts) counts[v]++;
        }
      }
      const total = counts.swing_miss + counts.bad_footwork + counts.other;
      setTotalLabeled(total);
      setPieSlices([
        { label: 'Swing Miss',   count: counts.swing_miss,   color: '#FF6B6B' },
        { label: 'Bad Footwork', count: counts.bad_footwork, color: '#FF9F43' },
        { label: 'Other',        count: counts.other,        color: '#636e72' },
      ]);
      setLabelsLoading(false);
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 2. Fetch court positions for zone description (used in AI prompt)
  useEffect(() => {
    if (!sessionIds.length || positionsFetched.current) return;
    positionsFetched.current = true;

    Promise.all(
      sessionIds.map(sid =>
        fetch(`${API_BASE}/court_positions/${sid}`)
          .then(r => r.ok ? r.json() : [])
          .catch(() => [])
      )
    ).then(results => {
      setAllPositions(results.flat());
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 3. Fetch AI coaching once labels + positions are ready
  useEffect(() => {
    if (labelsLoading || coachingFetched.current || !opponent) return;
    coachingFetched.current = true;

    // Build zone description from positions
    let zoneDescription = '';
    if (allPositions.length >= 5) {
      const avgX = allPositions.reduce((s, p) => s + p.cx, 0) / allPositions.length;
      const avgY = allPositions.reduce((s, p) => s + p.cy, 0) / allPositions.length;
      const yZone = avgY < COURT_H * 0.33 ? 'forecourt (near the net)'
                  : avgY < COURT_H * 0.66 ? 'mid-court'
                  : 'back court';
      const xZone = avgX < COURT_W * 0.33 ? 'left side'
                  : avgX > COURT_W * 0.66 ? 'right side'
                  : 'center';
      zoneDescription = `${opponent.name} tends to push you into the ${yZone}, ${xZone} of the court.`;
    }

    const comments = sessions
      .map(s => s.match_comment)
      .filter(c => c && c.trim());

    const mistakeCounts = {};
    pieSlices.forEach(s => { mistakeCounts[s.label.toLowerCase().replace(' ', '_')] = s.count; });

    setCoachingLoading(true);
    fetch(`${API_BASE}/opponent_coaching`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        opponent_name:  opponent.name,
        sport_type:     preferredSport,
        total_matches:  sessions.length,
        total_wins:     opponent.wins,
        total_losses:   opponent.losses,
        mistake_counts: {
          swing_miss:   pieSlices.find(s => s.label === 'Swing Miss')?.count   ?? 0,
          bad_footwork: pieSlices.find(s => s.label === 'Bad Footwork')?.count ?? 0,
          other:        pieSlices.find(s => s.label === 'Other')?.count        ?? 0,
        },
        zone_description: zoneDescription,
        comments,
      }),
    })
      .then(async r => {
        if (r.status === 429) { setCoachingError('quota'); return; }
        if (!r.ok) { setCoachingError('error'); return; }
        const data = await r.json();
        setCoaching(data?.feedback ?? null);
        if (!data?.feedback) setCoachingError('error');
      })
      .catch(() => setCoachingError('error'))
      .finally(() => setCoachingLoading(false));
  }, [labelsLoading, allPositions]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!opponent) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <p className="text-white/30 text-sm">No opponent data.</p>
      </div>
    );
  }

  const comments = sessions.map(s => s.match_comment).filter(c => c && c.trim());

  return (
    <div className="min-h-screen bg-black pb-16">

      {/* Header */}
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

      <div className="px-5 pt-4 space-y-6">

        {/* Opponent name + W-L */}
        <div className="animate-fade-up">
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-[11px] font-bold text-white/25 uppercase tracking-widest">VS</span>
            <h1 className="font-black text-white" style={{ fontSize: '40px', lineHeight: 1, letterSpacing: '-0.03em' }}>
              {opponent.name}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-black text-[#C8FF57] tabular-nums" style={{ fontSize: '22px', letterSpacing: '-0.03em' }}>
              {opponent.wins}W
            </span>
            <span className="text-white/20 font-light">–</span>
            <span className="font-black text-white/35 tabular-nums" style={{ fontSize: '22px', letterSpacing: '-0.03em' }}>
              {opponent.losses}L
            </span>
            <span className="text-white/20 text-xs ml-1">
              {sessions.length} {sessions.length === 1 ? 'match' : 'matches'}
            </span>
          </div>
        </div>

        {/* Loss breakdown pie */}
        <div
          className="rounded-2xl p-5 animate-fade-up"
          style={{ background: '#0d0d0d', border: '1px solid rgba(255,255,255,0.06)', animationDelay: '0.05s' }}
        >
          <p className="text-[10px] font-bold text-white/25 uppercase tracking-widest mb-4">
            Loss Breakdown vs {opponent.name}
          </p>
          {labelsLoading ? (
            <div className="space-y-2 py-2">
              {[1, 0.75, 0.5].map((w, i) => (
                <div key={i} className="h-2 rounded-full bg-white/[0.05]"
                  style={{ width: `${w * 100}%`, animation: `pulse 1.5s ease-in-out ${i * 0.15}s infinite` }} />
              ))}
            </div>
          ) : totalLabeled === 0 ? (
            <p className="text-sm text-white/20 py-2">No tagged losses yet for these matches.</p>
          ) : (
            <PieChart slices={pieSlices} />
          )}
        </div>

        {/* Combined heatmap */}
        {heatmapSrc && (
          <div
            className="rounded-2xl overflow-hidden animate-fade-up"
            style={{ background: '#0d0d0d', border: '1px solid rgba(255,255,255,0.06)', animationDelay: '0.1s' }}
          >
            <div className="px-5 pt-4 pb-3">
              <p className="text-[10px] font-bold text-white/25 uppercase tracking-widest mb-1">
                Shot Placement Heatmap
              </p>
              <p className="text-xs text-white/35">
                Where {opponent.name} tends to push you on the court
              </p>
            </div>
            <img
              src={heatmapSrc}
              alt="Combined heatmap"
              className="w-full block"
              onError={e => { e.target.style.display = 'none'; }}
            />
          </div>
        )}

        {/* Match comments */}
        {comments.length > 0 && (
          <div
            className="rounded-2xl p-5 animate-fade-up"
            style={{ background: '#0d0d0d', border: '1px solid rgba(255,255,255,0.06)', animationDelay: '0.15s' }}
          >
            <p className="text-[10px] font-bold text-white/25 uppercase tracking-widest mb-3">
              Your Match Notes
            </p>
            <div className="space-y-3">
              {comments.map((c, i) => (
                <p key={i} className="text-sm text-white/50 leading-relaxed border-l-2 border-white/10 pl-3">
                  {c}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* AI coaching */}
        <div
          className="rounded-2xl p-5 animate-fade-up"
          style={{ background: '#0d0d0d', border: '1px solid rgba(200,255,87,0.12)', animationDelay: '0.2s' }}
        >
          <p className="text-[10px] font-bold text-[#C8FF57] uppercase tracking-widest mb-3">
            AI Scouting Advice
          </p>
          {coachingLoading ? (
            <div className="space-y-2">
              {[1, 0.8, 0.6].map((w, i) => (
                <div key={i} className="h-2 rounded-full bg-white/[0.05]"
                  style={{ width: `${w * 100}%`, animation: `pulse 1.5s ease-in-out ${i * 0.15}s infinite` }} />
              ))}
            </div>
          ) : coaching ? (
            <p className="text-sm text-white/60 leading-relaxed">{coaching}</p>
          ) : coachingError === 'quota' ? (
            <p className="text-xs text-white/30">API quota exceeded — try again tomorrow.</p>
          ) : (
            <p className="text-xs text-white/20">Coaching unavailable.</p>
          )}
        </div>

      </div>
    </div>
  );
}

export default OpponentDetail;
