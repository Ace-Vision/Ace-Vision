import { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

// SVG donut pie chart (same as RallyResult summary page)
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
    <div className="flex items-center gap-6">
      <svg viewBox="0 0 100 100" style={{ width: 110, height: 110, flexShrink: 0 }}>
        {isSingle ? (
          <>
            <circle cx={cx} cy={cy} r={R} fill={active[0].color} />
            <circle cx={cx} cy={cy} r={ir} fill="#111" />
          </>
        ) : (
          paths.map((p, i) => <path key={i} d={p.d} fill={p.color} />)
        )}
      </svg>
      <div className="space-y-2.5">
        {active.map((s, i) => (
          <div key={i} className="flex items-center gap-2.5">
            <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: s.color }} />
            <span className="text-xs text-white/50">{s.label}</span>
            <span className="text-xs font-bold text-white ml-3">{s.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const API_BASE = process.env.REACT_APP_API_URL || '';

const COURT_W = 400;
const COURT_H = 440;

// ── Finalization helpers (shared with RallyResult) ─────────────────────────────
const FINALIZED_KEY = 'avFinalized';
function isFinalized(sessionId) {
  if (!sessionId) return false;
  try { return JSON.parse(localStorage.getItem(FINALIZED_KEY) || '[]').includes(sessionId); }
  catch { return false; }
}

// ── Heatmap zone analysis ──────────────────────────────────────────────────────

function computeHeatmapInsight(positions, rallies) {
  const userWinRallies = rallies.filter(r => r.rally_winner === 'user');
  const oppWinRallies  = rallies.filter(r => r.rally_winner === 'opponent');
  if (!userWinRallies.length || !oppWinRallies.length) return null;

  const getPts = rallySet => {
    const pts = [];
    for (const rally of rallySet) {
      const s = rally.start_s ?? 0;
      const e = rally.end_s   ?? rally.timestamp ?? 0;
      for (const pos of positions) {
        if (pos.time_s >= s && pos.time_s <= e) pts.push(pos);
      }
    }
    return pts;
  };

  const winPts  = getPts(userWinRallies);
  const lossPts = getPts(oppWinRallies);
  if (winPts.length < 5 || lossPts.length < 5) return null;

  const centroid = pts => ({
    x: pts.reduce((s, p) => s + p.cx, 0) / pts.length,
    y: pts.reduce((s, p) => s + p.cy, 0) / pts.length,
  });

  const spread = pts => {
    const xs = pts.map(p => p.cx);
    const ys = pts.map(p => p.cy);
    return (Math.max(...xs) - Math.min(...xs)) * (Math.max(...ys) - Math.min(...ys))
      / (COURT_W * COURT_H);
  };

  const wc = centroid(winPts);
  const lc = centroid(lossPts);
  const ws = spread(winPts);
  const ls = spread(lossPts);

  const centroidDist = Math.sqrt((wc.x - lc.x) ** 2 + (wc.y - lc.y) ** 2)
    / Math.sqrt(COURT_W ** 2 + COURT_H ** 2);
  const spreadRatio = ls / Math.max(ws, 0.001);

  if (spreadRatio <= 1.3 && centroidDist <= 0.12) {
    return { type: 'good', spreadRatio, centroidDist };
  }

  // Determine dominant direction of displacement
  const dx = lc.x - wc.x;
  const dy = lc.y - wc.y; // positive = deeper (away from net), negative = toward net

  let direction;
  if (Math.abs(dx) >= Math.abs(dy)) {
    direction = dx > 0 ? 'right side' : 'left side';
  } else {
    // net is at y=0 in court coords; smaller cy = closer to net
    direction = dy < 0 ? 'forecourt (net area)' : 'back court';
  }

  return { type: 'warning', direction, spreadRatio, centroidDist };
}

// ── Component ──────────────────────────────────────────────────────────────────

function MovementResult() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const result       = state?.result ?? {};
  const sport        = state?.sport ?? 'badminton';

  const { session_id, rallies = [], rally_summary = {}, phase_analysis = null } = result;

  const lastRally = rallies.length > 0 ? rallies[rallies.length - 1] : null;
  const myScore   = lastRally?.my_score        ?? rally_summary.user_wins     ?? 0;
  const oppScore  = lastRally?.opponent_score  ?? rally_summary.opponent_wins ?? 0;
  const won    = myScore > oppScore;
  const tied   = myScore === oppScore;
  const locked = isFinalized(session_id);

  // ── Editable fields ──────────────────────────────────────────────────────────

  const [opponentName,   setOpponentName]   = useState(state?.opponentName ?? '');
  const [matchComment,   setMatchComment]   = useState(state?.matchComment ?? '');
  const [editingName,    setEditingName]    = useState(false);
  const [editingComment, setEditingComment] = useState(false);
  const nameRef    = useRef(null);
  const commentRef = useRef(null);

  useEffect(() => { if (editingName)    nameRef.current?.focus();    }, [editingName]);
  useEffect(() => { if (editingComment) commentRef.current?.focus(); }, [editingComment]);

  const saveEdit = useCallback(async (field, value) => {
    if (!session_id) return;
    try {
      const token = localStorage.getItem('token');
      await fetch(`${API_BASE}/match_sessions/${session_id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ [field]: value }),
      });
    } catch {}
  }, [session_id]);

  // ── Page / swipe state ───────────────────────────────────────────────────────

  // locked (history view): 3 pages — Overview / Heatmaps / Final Analysis
  // fresh flow:            2 pages — Overview / Heatmaps  (rally starts via button)
  const PAGE_COUNT = locked ? 3 : 2;
  const [page, setPage] = useState(0);
  const touchStartX = useRef(null);

  function handleTouchStart(e) {
    touchStartX.current = e.touches[0].clientX;
  }
  function handleTouchEnd(e) {
    if (touchStartX.current === null) return;
    const dx = e.changedTouches[0].clientX - touchStartX.current;
    if (Math.abs(dx) > 50)
      setPage(p => dx < 0 ? Math.min(PAGE_COUNT - 1, p + 1) : Math.max(0, p - 1));
    touchStartX.current = null;
  }

  // ── Heatmap insight ──────────────────────────────────────────────────────────

  const [insight, setInsight] = useState(null);

  useEffect(() => {
    if (!session_id || !rallies.length) return;
    fetch(`${API_BASE}/court_positions/${session_id}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setInsight(computeHeatmapInsight(data, rallies)); })
      .catch(() => {});
  }, [session_id]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Coaching (page 2) ────────────────────────────────────────────────────────

  const [coachingText, setCoachingText] = useState(null);
  const [coachingLoading, setCoachingLoading] = useState(false);
  const [coachingError, setCoachingError] = useState(null);
  const coachingFetched = useRef(false);

  // ── Rally labels (for pie chart on page 2) ───────────────────────────────────
  const [rallyLabels, setRallyLabels] = useState({});
  const labelsFetched = useRef(false);

  useEffect(() => {
    if (page !== 2 || !locked || labelsFetched.current || !session_id) return;
    labelsFetched.current = true;
    fetch(`${API_BASE}/rally_labels/${session_id}`)
      .then(r => r.json())
      .then(data => setRallyLabels(data.labels || {}))
      .catch(() => {});
  }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (page !== 2 || !locked || coachingFetched.current || !session_id) return;
    coachingFetched.current = true;
    setCoachingLoading(true);
    fetch(`${API_BASE}/rally_coaching`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id,
        sport_type:    sport,
        user_wins:     rally_summary.user_wins     ?? 0,
        opponent_wins: rally_summary.opponent_wins ?? 0,
        total_rallies: rally_summary.total_rallies ?? 0,
        opponent_name: opponentName,
        match_comment: matchComment,
        loss_tags:  {},
        rally_notes: {},
      }),
    })
      .then(async r => {
        if (r.status === 429) { setCoachingError('quota'); return; }
        if (!r.ok)            { setCoachingError('error'); return; }
        const data = await r.json();
        setCoachingText(data?.feedback ?? null);
        if (!data?.feedback) setCoachingError('error');
      })
      .catch(() => setCoachingError('error'))
      .finally(() => setCoachingLoading(false));
  }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Pie chart data (page 2) ──────────────────────────────────────────────────
  const totalLossSlots = rallies.reduce((sum, r) => {
    const pOpp = r.prev_opp != null ? r.prev_opp : (r.rally_winner === 'user' ? r.opponent_score : r.opponent_score - 1);
    return sum + Math.max(0, r.opponent_score - pOpp);
  }, 0);
  const lossCounts = { swing_miss: 0, bad_footwork: 0, other: 0 };
  Object.values(rallyLabels).forEach(l => { if (l in lossCounts) lossCounts[l]++; });
  const unlabeled = Math.max(0, totalLossSlots - Object.keys(rallyLabels).length);
  const pieSlices = [
    { label: 'Swing Miss',   count: lossCounts.swing_miss,   color: '#FF6B6B' },
    { label: 'Bad Footwork', count: lossCounts.bad_footwork, color: '#FF9F43' },
    { label: 'Other',        count: lossCounts.other,        color: '#636e72' },
    { label: 'Unlabeled',    count: unlabeled,               color: 'rgba(255,255,255,0.10)' },
  ];

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div
      className="min-h-screen bg-black pb-20"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {/* Header */}
      <div className="px-5 pt-14 pb-2 flex items-center gap-3">
        <button
          onClick={() => navigate('/home')}
          className="text-white/30 hover:text-white text-2xl leading-none transition-colors"
        >
          ‹
        </button>
        <span className="text-[11px] font-semibold text-white/25 uppercase tracking-widest">
          Movement Analysis
        </span>
      </div>

      {/* Tab bar */}
      <div className="px-5 pt-3 pb-0 flex gap-6 border-b border-white/[0.06]">
        {(locked ? ['Overview', 'Heatmaps', 'Analysis'] : ['Overview', 'Heatmaps']).map((label, i) => (
          <button
            key={i}
            onClick={() => setPage(i)}
            className="pb-3 text-[11px] font-bold uppercase tracking-widest transition-colors"
            style={{
              color: page === i ? '#C8FF57' : 'rgba(255,255,255,0.2)',
              borderBottom: page === i ? '2px solid #C8FF57' : '2px solid transparent',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ── Page 0: Overview ──────────────────────────────────────────────────── */}
      {page === 0 && (
        <div className="px-5 pt-8 space-y-7">

          {/* Score + player names */}
          <div className="animate-fade-up flex items-center justify-center gap-10 py-2">

            {/* You */}
            <div className="text-center">
              <p
                className="font-black text-white tabular-nums"
                style={{ fontSize: '72px', lineHeight: 1, letterSpacing: '-0.04em' }}
              >
                {myScore}
              </p>
              <p className="text-base font-semibold text-white mt-2">You</p>
            </div>

            <p className="text-3xl text-white/15 font-light mb-8">:</p>

            {/* Opponent */}
            <div className="text-center">
              <p
                className="font-black text-white tabular-nums"
                style={{ fontSize: '72px', lineHeight: 1, letterSpacing: '-0.04em' }}
              >
                {oppScore}
              </p>

              {locked ? (
                <p className="mt-2 text-base font-semibold text-white/70">
                  {opponentName || 'Opponent'}
                </p>
              ) : editingName ? (
                <input
                  ref={nameRef}
                  value={opponentName}
                  onChange={e => setOpponentName(e.target.value)}
                  onBlur={() => { setEditingName(false); saveEdit('opponent_name', opponentName); }}
                  onKeyDown={e => {
                    if (e.key === 'Enter') { setEditingName(false); saveEdit('opponent_name', opponentName); }
                  }}
                  placeholder="Opponent"
                  className="mt-2 text-base font-semibold text-white bg-transparent border-b border-white/30 outline-none text-center w-28"
                  style={{ caretColor: '#C8FF57' }}
                />
              ) : (
                <button
                  onClick={() => setEditingName(true)}
                  className="mt-2 flex items-center gap-1 justify-center"
                >
                  <span className="text-base font-semibold text-white">
                    {opponentName || 'Opponent'}
                  </span>
                  <span className="text-[11px] text-white/30">✎</span>
                </button>
              )}
            </div>
          </div>

          {/* Win / loss message */}
          <div className="animate-fade-up text-center" style={{ animationDelay: '0.05s' }}>
            <p
              className="text-lg font-bold"
              style={{ color: tied ? 'rgba(255,255,255,0.7)' : won ? '#C8FF57' : 'rgba(255,255,255,0.85)' }}
            >
              {tied
                ? 'Close match!'
                : won
                ? 'Congrats on the win! 🏆'
                : 'Great effort out there! 💪'}
            </p>
          </div>

          {/* Comment */}
          <div className="animate-fade-up" style={{ animationDelay: '0.09s' }}>
            {locked ? (
              <div
                className="w-full px-4 py-4 rounded-2xl"
                style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}
              >
                {matchComment ? (
                  <p className="text-sm text-white/50 leading-relaxed whitespace-pre-wrap">{matchComment}</p>
                ) : (
                  <p className="text-sm text-white/15 italic">No comment added.</p>
                )}
                <p className="text-[10px] text-white/15 mt-2 uppercase tracking-widest">🔒 Locked</p>
              </div>
            ) : editingComment ? (
              <textarea
                ref={commentRef}
                value={matchComment}
                onChange={e => setMatchComment(e.target.value)}
                onBlur={() => { setEditingComment(false); saveEdit('match_comment', matchComment); }}
                rows={4}
                placeholder="How did the match feel? Any thoughts…"
                className="w-full px-4 py-3 rounded-2xl text-sm text-white placeholder:text-white/20 outline-none resize-none"
                style={{
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.15)',
                  caretColor: '#C8FF57',
                }}
              />
            ) : (
              <button
                onClick={() => setEditingComment(true)}
                className="w-full text-left px-4 py-4 rounded-2xl transition-colors active:opacity-70"
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.07)',
                }}
              >
                {matchComment ? (
                  <p className="text-sm text-white/70 leading-relaxed whitespace-pre-wrap">{matchComment}</p>
                ) : (
                  <p className="text-sm text-white/20 italic">Tap to add a note about the match…</p>
                )}
                <p className="text-[10px] text-white/20 mt-2 uppercase tracking-widest">Tap to edit  ✎</p>
              </button>
            )}
          </div>

        </div>
      )}

      {/* ── Page 1: Heatmaps ──────────────────────────────────────────────────── */}
      {page === 1 && session_id && (
        <div className="px-5 pt-6 space-y-8">

          {/* Win / Loss heatmaps */}
          <div className="animate-fade-up space-y-3">
            <div>
              <p className="text-[10px] font-bold text-white/25 uppercase tracking-widest mb-1">
                Zone Comparison
              </p>
              <p className="text-xs text-white/45 leading-relaxed">
                Areas you covered in rallies you won vs. rallies you lost.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-[10px] font-bold text-[#C8FF57] uppercase tracking-widest mb-2 px-1">
                  Your wins
                </p>
                <div className="rounded-xl overflow-hidden bg-[#111] border border-white/[0.06]">
                  <img
                    src={`${API_BASE}/heatmap/${session_id}/win`}
                    alt="Win heatmap"
                    className="w-full block"
                  />
                </div>
              </div>
              <div>
                <p className="text-[10px] font-bold text-white/30 uppercase tracking-widest mb-2 px-1">
                  Opp. wins
                </p>
                <div className="rounded-xl overflow-hidden bg-[#111] border border-white/[0.06]">
                  <img
                    src={`${API_BASE}/heatmap/${session_id}/loss`}
                    alt="Loss heatmap"
                    className="w-full block"
                  />
                </div>
              </div>
            </div>

            {/* Rule-based insight */}
            {insight === null ? (
              <p className="text-[11px] text-white/20 text-center py-1">
                Not enough rally data for zone analysis.
              </p>
            ) : insight.type === 'good' ? (
              <div
                className="rounded-2xl p-4 space-y-1"
                style={{ background: 'rgba(200,255,87,0.07)', border: '1px solid rgba(200,255,87,0.2)' }}
              >
                <p className="text-[11px] font-black uppercase tracking-widest" style={{ color: '#C8FF57' }}>
                  ✓ Balanced Coverage
                </p>
                <p className="text-xs leading-relaxed" style={{ color: 'rgba(200,255,87,0.72)' }}>
                  No strong correlation between movement area and point outcomes. You had no extreme weak zones this match — footwork was well-balanced.
                </p>
              </div>
            ) : (
              <div
                className="rounded-2xl p-4 space-y-1"
                style={{ background: 'rgba(255,140,0,0.08)', border: '1px solid rgba(255,140,0,0.25)' }}
              >
                <p className="text-[11px] font-black uppercase tracking-widest" style={{ color: '#FFA040' }}>
                  ⚠ Weak Zone Detected
                </p>
                <p className="text-xs leading-relaxed" style={{ color: 'rgba(255,160,64,0.88)' }}>
                  During losing rallies you were pushed further into the{' '}
                  <strong style={{ color: '#FFB060' }}>{insight.direction}</strong>{' '}
                  compared to winning rallies. Focus footwork drills on recovering quickly from that area.
                </p>
              </div>
            )}
          </div>

          {/* Phase heatmaps */}
          {phase_analysis && (
            <div className="animate-fade-up space-y-3" style={{ animationDelay: '0.06s' }}>
              <div>
                <p className="text-[10px] font-bold text-white/25 uppercase tracking-widest mb-1">
                  Movement by Phase
                </p>
                <p className="text-xs text-white/45 leading-relaxed">
                  The match is split into three equal thirds. Early sets your baseline range; Mid shows if you maintained it; Late reveals endurance — a drop here signals fatigue.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-2">
                {phase_analysis.phases.map((phase, i) => {
                  const pct     = phase.coverage_pct;
                  const flagged = i === 2 && phase_analysis.stamina_flag;
                  const captions = ['Starting range', 'Consistency', 'Endurance'];
                  return (
                    <div key={i}>
                      <div className="flex items-center justify-between px-0.5 mb-1.5">
                        <span className="text-[9px] text-white/25 uppercase tracking-wider">
                          {i === 0 ? 'Early' : i === 1 ? 'Mid' : 'Late'}
                        </span>
                        <span
                          className="text-[10px] font-bold tabular-nums"
                          style={{ color: flagged ? '#FF6B6B' : 'rgba(255,255,255,0.35)' }}
                        >
                          {pct}%
                        </span>
                      </div>
                      <div
                        className="rounded-xl overflow-hidden bg-[#111] border"
                        style={{ borderColor: flagged ? 'rgba(255,107,107,0.3)' : 'rgba(255,255,255,0.06)' }}
                      >
                        <img
                          src={`${API_BASE}/phase_heatmap/${session_id}/${phase.phase}`}
                          alt={`Phase ${phase.phase}`}
                          className="w-full block"
                        />
                      </div>
                      <div className="mt-1.5 h-0.5 rounded-full bg-white/[0.06] overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${pct}%`,
                            background: flagged
                              ? '#FF6B6B'
                              : i === 0 ? '#C8FF57' : 'rgba(255,255,255,0.25)',
                          }}
                        />
                      </div>
                      <p className="mt-1 text-[9px] text-white/20 text-center leading-tight">
                        {captions[i]}
                      </p>
                    </div>
                  );
                })}
              </div>

              {phase_analysis.stamina_flag ? (
                <div
                  className="rounded-2xl p-4 space-y-2"
                  style={{ background: 'rgba(255,60,60,0.10)', border: '1px solid rgba(255,60,60,0.45)' }}
                >
                  <p className="text-[11px] font-black uppercase tracking-widest" style={{ color: '#FF3C3C' }}>
                    ⚠ Stamina Alert
                  </p>
                  <p className="text-xs font-semibold leading-relaxed" style={{ color: 'rgba(255,100,100,0.85)' }}>
                    Coverage dropped from {phase_analysis.coverage_trend[0]}% early on to{' '}
                    {phase_analysis.coverage_trend[2]}% in the final phase. Add cardio and footwork endurance to your training routine.
                  </p>
                </div>
              ) : (
                <div
                  className="rounded-2xl p-4 space-y-2"
                  style={{ background: 'rgba(200,255,87,0.07)', border: '1px solid rgba(200,255,87,0.25)' }}
                >
                  <p className="text-[11px] font-black uppercase tracking-widest" style={{ color: '#C8FF57' }}>
                    ✓ Stamina Good
                  </p>
                  <p className="text-xs font-semibold leading-relaxed" style={{ color: 'rgba(200,255,87,0.70)' }}>
                    Court coverage remained consistent across all three phases — no signs of stamina decline detected.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Fresh flow: start rally analysis from heatmaps page */}
          {!locked && (
            <button
              onClick={() => navigate('/rally-result', {
                state: {
                  result:         { session_id, rallies, summary: rally_summary },
                  movementResult: result,
                  opponentName,
                  matchComment,
                  sport,
                },
              })}
              className="w-full py-4 rounded-2xl text-sm font-semibold transition-all active:scale-95"
              style={{ background: '#C8FF57', color: '#000' }}
            >
              Start Rally Analysis →
            </button>
          )}
        </div>
      )}

      {/* ── Page 2: Final Analysis (history / locked only) ────────────────────── */}
      {page === 2 && (
        <div className="px-5 pt-6 space-y-6">

          {/* Loss breakdown pie chart */}
          {totalLossSlots > 0 && (
            <div>
              <p className="text-[10px] font-bold text-white/25 uppercase tracking-widest mb-4">
                Loss Breakdown
              </p>
              <PieChart slices={pieSlices} />
            </div>
          )}

          <div>
            <p className="text-[10px] font-bold text-white/25 uppercase tracking-widest mb-1">
              AI Coaching
            </p>
            <p className="text-xs text-white/40 leading-relaxed">
              Personalized feedback based on your match result and movement data.
            </p>
          </div>

          <div
            className="rounded-2xl p-4"
            style={{ background: '#0d0d0d', border: '1px solid rgba(255,255,255,0.06)' }}
          >
            {coachingLoading ? (
              <div className="space-y-2">
                {[1, 0.8, 0.6].map((w, i) => (
                  <div
                    key={i}
                    className="h-2 rounded-full bg-white/[0.05]"
                    style={{ width: `${w * 100}%`, animation: `pulse 1.5s ease-in-out ${i * 0.15}s infinite` }}
                  />
                ))}
              </div>
            ) : coachingText ? (
              <p className="text-sm text-white/60 leading-relaxed">{coachingText}</p>
            ) : coachingError === 'quota' ? (
              <p className="text-xs text-white/30 leading-relaxed">
                API quota exceeded — coaching will be available again tomorrow.
              </p>
            ) : (
              <p className="text-xs text-white/20">Coaching unavailable.</p>
            )}
          </div>

          {/* View individual rallies */}
          <button
            onClick={() => navigate('/rally-result', {
              state: {
                result:         { session_id, rallies, summary: rally_summary },
                movementResult: result,
                opponentName,
                matchComment,
                sport,
                fromHistory: true,
              },
            })}
            className="w-full py-4 rounded-2xl text-sm font-semibold transition-all active:scale-95"
            style={{ background: '#C8FF57', color: '#000' }}
          >
            View Each Rally →
          </button>

          <button
            onClick={() => navigate('/match-history')}
            className="w-full py-4 rounded-2xl bg-white/[0.04] border border-white/[0.07] text-sm font-semibold text-white/30 hover:bg-white/[0.07] transition-colors"
          >
            View Other Matches
          </button>

        </div>
      )}

      {/* Page indicator dots */}
      <div className="fixed bottom-7 left-0 right-0 flex justify-center gap-2 pointer-events-none">
        {Array.from({ length: PAGE_COUNT }).map((_, i) => (
          <div
            key={i}
            className="rounded-full transition-all"
            style={{
              width:      page === i ? 20 : 6,
              height:     6,
              background: page === i ? '#C8FF57' : 'rgba(255,255,255,0.2)',
            }}
          />
        ))}
      </div>
    </div>
  );
}

export default MovementResult;
