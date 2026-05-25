import { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const API_BASE = process.env.REACT_APP_API_URL || '';

// ── Finalization helpers ───────────────────────────────────────────────────────
const FINALIZED_KEY = 'avFinalized';
function isFinalized(sessionId) {
  if (!sessionId) return false;
  try { return JSON.parse(localStorage.getItem(FINALIZED_KEY) || '[]').includes(sessionId); }
  catch { return false; }
}
function finalizeSession(sessionId) {
  if (!sessionId) return;
  try {
    const list = JSON.parse(localStorage.getItem(FINALIZED_KEY) || '[]');
    if (!list.includes(sessionId)) { list.push(sessionId); localStorage.setItem(FINALIZED_KEY, JSON.stringify(list)); }
  } catch {}
}

const LABEL_OPTIONS = [
  { value: 'swing_miss',   label: 'Swing Miss' },
  { value: 'bad_footwork', label: 'Bad Footwork' },
  { value: 'other',        label: 'Other' },
];

// ── Court minimap ─────────────────────────────────────────────────────────────

const COURT_BW = 400; // backend court width
const COURT_BH = 440; // backend court height
const TRAIL_LEN = 18; // number of past positions to show

function drawMinimap(canvas, positions, absoluteTime, startS, endS) {
  const ctx = canvas.getContext('2d');
  const W = canvas.width;
  const H = canvas.height;

  ctx.fillStyle = '#0a0a0a';
  ctx.fillRect(0, 0, W, H);

  const pad = Math.round(W * 0.08);
  const cw  = W - 2 * pad;
  const ch  = H - 2 * pad;

  // Outer court
  ctx.strokeStyle = 'rgba(255,255,255,0.18)';
  ctx.lineWidth = 1.5;
  ctx.strokeRect(pad, pad, cw, ch);

  // Net (top edge, thicker)
  ctx.strokeStyle = 'rgba(255,255,255,0.40)';
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.moveTo(pad, pad);
  ctx.lineTo(pad + cw, pad);
  ctx.stroke();

  // Service line
  const svcY = pad + Math.round(ch / 3);
  ctx.strokeStyle = 'rgba(255,255,255,0.09)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad, svcY);
  ctx.lineTo(pad + cw, svcY);
  ctx.stroke();

  // Center line (service box divider)
  ctx.beginPath();
  ctx.moveTo(pad + cw / 2, svcY);
  ctx.lineTo(pad + cw / 2, pad + ch);
  ctx.stroke();

  // Filter to this rally's time window
  const pts = positions.filter(p => p.time_s >= startS && p.time_s <= endS);
  if (!pts.length) return;

  // Find index of closest position to absoluteTime
  let curIdx = 0;
  let minDiff = Infinity;
  for (let i = 0; i < pts.length; i++) {
    const d = Math.abs(pts[i].time_s - absoluteTime);
    if (d < minDiff) { minDiff = d; curIdx = i; }
  }

  // Trail
  const trailStart = Math.max(0, curIdx - TRAIL_LEN);
  for (let i = trailStart; i < curIdx; i++) {
    const alpha = (i - trailStart + 1) / (curIdx - trailStart + 1);
    const p = pts[i];
    const x = pad + (p.cx / COURT_BW) * cw;
    const y = pad + (p.cy / COURT_BH) * ch;
    ctx.fillStyle = `rgba(200,255,87,${alpha * 0.35})`;
    ctx.beginPath();
    ctx.arc(x, y, Math.max(1.5, 3 * alpha), 0, Math.PI * 2);
    ctx.fill();
  }

  // Current dot
  const cur = pts[curIdx];
  const dx = pad + (cur.cx / COURT_BW) * cw;
  const dy = pad + (cur.cy / COURT_BH) * ch;

  ctx.fillStyle = 'rgba(200,255,87,0.18)';
  ctx.beginPath();
  ctx.arc(dx, dy, 9, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = '#C8FF57';
  ctx.beginPath();
  ctx.arc(dx, dy, 5, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = 'rgba(255,255,255,0.55)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(dx, dy, 5, 0, Math.PI * 2);
  ctx.stroke();
}

function CourtMinimap({ positions, startS, endS, videoRef }) {
  const canvasRef = useRef(null);

  // Draw initial frame once positions/rally change
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !positions.length) return;
    drawMinimap(canvas, positions, startS, startS, endS);
  }, [positions, startS, endS]);

  // Wire up to video timeupdate
  useEffect(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !positions.length) return;
    const handler = () =>
      drawMinimap(canvas, positions, startS + video.currentTime, startS, endS);
    video.addEventListener('timeupdate', handler);
    return () => video.removeEventListener('timeupdate', handler);
  }, [positions, startS, endS, videoRef]);

  return (
    <canvas
      ref={canvasRef}
      width={160}
      height={176}
      style={{ display: 'block', margin: '0 auto', borderRadius: 12 }}
    />
  );
}

// SVG donut pie chart
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
            <circle cx={cx} cy={cy} r={ir} fill="#0d0d0d" />
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

// Single rally page
function RallyPage({ rally, labels, onLabel, note, onNote, sessionId, onNext, isLast, courtPositions, isLocked }) {
  const isBoth = rally.rally_winner === 'both';
  const isWin  = rally.rally_winner === 'user';

  // prev_my / prev_opp はバックエンドが付与。なければ旧来の ±1 推定にフォールバック
  const prevMy  = rally.prev_my  ?? (isWin ? rally.my_score - 1 : rally.my_score);
  const prevOpp = rally.prev_opp ?? (isWin ? rally.opponent_score : rally.opponent_score - 1);

  // このクリップに含まれる失点数（タグスロット数）
  const oppDiff = Math.max(0, rally.opponent_score - prevOpp);

  // どちらかが2点以上動いていたら「複数ラリー」
  const isMulti = (rally.my_score - prevMy) + (rally.opponent_score - prevOpp) > 1;

  const accent = isBoth
    ? '#F0C040'
    : isWin ? '#C8FF57' : '#FF6B6B';

  const duration = Math.round(rally.end_s - rally.start_s);
  const videoRef = useRef(null);
  const hasPositions = courtPositions.length > 0
    && rally.start_s != null && rally.end_s != null;

  return (
    <div className="px-5 pt-3 pb-6 space-y-4">

      {/* Win / Loss / Both label */}
      <div className="flex items-center justify-between">
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', color: accent, textTransform: 'uppercase' }}>
          {isBoth ? 'Multiple Rallies' : isWin ? 'Point Won' : 'Point Lost'}
        </span>
        <span className="text-[11px] text-white/20">{duration}s</span>
      </div>

      {/* Multi-rally notice */}
      {isMulti && (
        <div className="rounded-xl px-3 py-2.5"
          style={{
            background: isBoth ? 'rgba(240,192,64,0.07)' : 'rgba(255,255,255,0.04)',
            border: `1px solid ${isBoth ? 'rgba(240,192,64,0.20)' : 'rgba(255,255,255,0.08)'}`,
          }}>
          <p className="text-xs leading-relaxed"
            style={{ color: isBoth ? 'rgba(240,192,64,0.65)' : 'rgba(255,255,255,0.30)' }}>
            {isBoth
              ? 'Multiple rallies are contained in this clip — individual winners could not be determined.'
              : `This clip covers ${(rally.my_score - prevMy) + (rally.opponent_score - prevOpp)} consecutive rallies that were grouped together.`}
          </p>
        </div>
      )}

      {/* Score transition */}
      <div className="flex items-center gap-4">
        <p className="font-black tabular-nums text-white/30" style={{ fontSize: 36, lineHeight: 1, letterSpacing: '-0.04em' }}>
          {prevMy}<span className="text-white/15 text-2xl"> : </span>{prevOpp}
        </p>
        <span className="text-white/20 text-xl">→</span>
        <p className="font-black tabular-nums" style={{ fontSize: 36, lineHeight: 1, letterSpacing: '-0.04em', color: accent }}>
          {rally.my_score}<span className="text-white/20 text-2xl"> : </span>{rally.opponent_score}
        </p>
      </div>

      {/* Clip video */}
      <div style={{ textAlign: 'center' }}>
        <video
          ref={videoRef}
          src={`${API_BASE}/rally_clip/${sessionId}/${rally.clip_filename}`}
          controls
          playsInline
          muted
          style={{ display: 'inline-block', maxHeight: '45dvh', maxWidth: '100%', borderRadius: 16 }}
        />
      </div>

      {/* Court minimap — synced to video */}
      {hasPositions && (
        <CourtMinimap
          positions={courtPositions}
          startS={rally.start_s}
          endS={rally.end_s}
          videoRef={videoRef}
        />
      )}

      {/* Tag buttons — one slot per opponent point in this clip */}
      {oppDiff > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <p className="text-[10px] font-semibold text-white/20 uppercase tracking-widest">
              {oppDiff > 1 ? `Tag losses (${oppDiff})` : 'Tag this loss'}
            </p>
            {isLocked && <span className="text-[10px] text-white/20">🔒</span>}
          </div>
          {Array.from({ length: oppDiff }).map((_, lossIdx) => {
            const key = `${rally.index}_${lossIdx}`;
            const sel = labels[key];
            return (
              <div key={lossIdx}>
                {oppDiff > 1 && (
                  <p className="text-[9px] text-white/15 uppercase tracking-widest mb-1.5">
                    Loss {lossIdx + 1}
                  </p>
                )}
                <div className="flex gap-2 flex-wrap">
                  {LABEL_OPTIONS.map(opt => (
                    <button
                      key={opt.value}
                      onClick={() => !isLocked && onLabel(key, sel === opt.value ? null : opt.value)}
                      disabled={isLocked}
                      className="px-3 py-1.5 rounded-xl text-xs font-semibold transition-all active:scale-95"
                      style={sel === opt.value
                        ? { background: isLocked ? 'rgba(255,107,107,0.4)' : '#FF6B6B', color: isLocked ? 'rgba(0,0,0,0.5)' : '#000' }
                        : { background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.25)', border: '1px solid rgba(255,255,255,0.08)', opacity: isLocked ? 0.5 : 1 }
                      }
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Rally note */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <p className="text-[10px] font-semibold text-white/20 uppercase tracking-widest">Note</p>
          {isLocked && <span className="text-[10px] text-white/20">🔒</span>}
        </div>
        <textarea
          value={note || ''}
          onChange={e => !isLocked && onNote(rally.index, e.target.value)}
          readOnly={isLocked}
          placeholder={isLocked ? '' : 'Add a note about this rally…'}
          rows={2}
          className="w-full px-3 py-2.5 rounded-xl text-xs text-white placeholder:text-white/15 outline-none resize-none"
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.07)',
            opacity: isLocked ? 0.5 : 1,
          }}
        />
      </div>

      {/* Next button */}
      <button
        onClick={onNext}
        className="w-full py-4 rounded-2xl text-sm font-semibold transition-all active:scale-95"
        style={{ background: '#C8FF57', color: '#000' }}
      >
        {isLast ? 'See Summary →' : 'Next Rally →'}
      </button>

    </div>
  );
}

// Final summary page
function SummaryPage({ summary, totalLossSlots, labels, onHome, onHistory, fromHistory, feedback, feedbackLoading, feedbackError, opponentName, sessionId }) {
  // Lock the session the moment the user sees the summary
  useEffect(() => { finalizeSession(sessionId); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const counts = { swing_miss: 0, bad_footwork: 0, other: 0 };
  Object.values(labels).forEach(l => {
    if (l in counts) counts[l]++;
  });
  const unlabeled = Math.max(0, totalLossSlots - Object.keys(labels).length);

  const pieSlices = [
    { label: 'Swing Miss',   count: counts.swing_miss,   color: '#FF6B6B' },
    { label: 'Bad Footwork', count: counts.bad_footwork, color: '#FF9F43' },
    { label: 'Other',        count: counts.other,        color: '#636e72' },
    { label: 'Unlabeled',    count: unlabeled,            color: 'rgba(255,255,255,0.10)' },
  ];

  return (
    <div className="px-5 pt-3 pb-10 space-y-6">

      {/* Score */}
      <div>
        <p className="text-[10px] font-semibold text-white/25 uppercase tracking-widest mb-3">
          Match Summary
        </p>
        <div className="flex items-baseline gap-3">
          <p className="font-black text-white tabular-nums" style={{ fontSize: 60, lineHeight: 1, letterSpacing: '-0.04em' }}>
            {summary.user_wins ?? 0}
          </p>
          <p className="text-white/15 text-4xl font-light">:</p>
          <p className="font-black text-white/35 tabular-nums" style={{ fontSize: 60, lineHeight: 1, letterSpacing: '-0.04em' }}>
            {summary.opponent_wins ?? 0}
          </p>
        </div>
        <p className="text-xs text-white/20 mt-2">{summary.total_rallies ?? 0} rallies analyzed</p>
      </div>

      {/* Pie chart — only if there were losses */}
      {totalLossSlots > 0 && (
        <div>
          <p className="text-[10px] font-bold text-white/25 uppercase tracking-widest mb-4">
            Loss Breakdown
          </p>
          <PieChart slices={pieSlices} />
        </div>
      )}

      {/* AI Coaching */}
      <div className="rounded-2xl border border-white/[0.06] bg-[#0d0d0d] p-4 space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-[10px] font-bold text-white/25 uppercase tracking-widest">AI Coaching</p>
          {opponentName ? (
            <span className="text-[10px] text-white/20">vs {opponentName}</span>
          ) : null}
        </div>
        {feedbackLoading ? (
          <div className="space-y-1.5">
            <div className="h-2 rounded-full bg-white/[0.05] w-full" style={{ animation: 'pulse 1.5s ease-in-out infinite' }} />
            <div className="h-2 rounded-full bg-white/[0.05] w-4/5" style={{ animation: 'pulse 1.5s ease-in-out infinite 0.15s' }} />
            <div className="h-2 rounded-full bg-white/[0.05] w-3/5" style={{ animation: 'pulse 1.5s ease-in-out infinite 0.3s' }} />
          </div>
        ) : feedback ? (
          <p className="text-sm text-white/60 leading-relaxed">{feedback}</p>
        ) : feedbackError === 'quota' ? (
          <p className="text-xs text-white/30 leading-relaxed">
            API quota exceeded — feedback will be available again tomorrow.
          </p>
        ) : feedbackError === 'error' ? (
          <p className="text-xs text-white/20">Feedback unavailable</p>
        ) : null}
      </div>

      {fromHistory ? (
        <button
          onClick={onHistory}
          className="w-full py-4 rounded-2xl bg-white/[0.04] border border-white/[0.07] text-sm font-semibold text-white/30 hover:bg-white/[0.07] transition-colors"
        >
          View Other Matches
        </button>
      ) : (
        <button
          onClick={onHome}
          className="w-full py-4 rounded-2xl bg-white/[0.04] border border-white/[0.07] text-sm font-semibold text-white/30 hover:bg-white/[0.07] transition-colors"
        >
          Analyze Again
        </button>
      )}

    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

function RallyResult() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const result         = state?.result ?? {};
  const movementResult = state?.movementResult ?? null;
  const { session_id, rallies = [], summary = {} } = result;

  const opponentName = state?.opponentName ?? '';
  const matchComment = state?.matchComment ?? '';
  const sport        = state?.sport ?? 'badminton';
  const fromHistory  = state?.fromHistory ?? false;

  const [page, setPage] = useState(0);
  const [labels, setLabels] = useState({});
  const [courtPositions, setCourtPositions] = useState([]);
  const [rallyNotes, setRallyNotes] = useState({});
  const [feedback, setFeedback] = useState(null);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [feedbackError, setFeedbackError] = useState(null); // 'quota' | 'error' | null

  const locked = isFinalized(session_id);

  // Fetch persisted labels — keys are strings like "5_0", "5_1"
  useEffect(() => {
    if (!session_id) return;
    fetch(`${API_BASE}/rally_labels/${session_id}`)
      .then(r => r.json())
      .then(data => setLabels(data.labels || {}))
      .catch(() => {});
  }, [session_id]);

  // Fetch court positions for minimap
  useEffect(() => {
    if (!session_id) return;
    fetch(`${API_BASE}/court_positions/${session_id}`)
      .then(r => r.ok ? r.json() : [])
      .then(data => setCourtPositions(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, [session_id]);

  function handleNote(rallyIndex, note) {
    setRallyNotes(prev => ({ ...prev, [rallyIndex]: note }));
  }

  const enriched = rallies.map(r => ({ ...r, session_id }));

  // 失点スロット数: 各クリップの相手得点数を合計
  const totalLossSlots = enriched.reduce((sum, r) => {
    const pOpp = r.prev_opp != null ? r.prev_opp : (r.rally_winner === 'user' ? r.opponent_score : r.opponent_score - 1);
    return sum + Math.max(0, r.opponent_score - pOpp);
  }, 0);

  const totalPages = enriched.length + 1;
  const isSummary  = page >= enriched.length;

  // Trigger LLM feedback when summary page first appears
  useEffect(() => {
    if (!isSummary || !session_id || feedback !== null || feedbackLoading) return;
    setFeedbackLoading(true);
    const lossTagsObj = { ...labels };
    fetch(`${API_BASE}/rally_coaching`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id,
        sport_type: sport,
        user_wins:     summary.user_wins     ?? 0,
        opponent_wins: summary.opponent_wins ?? 0,
        total_rallies: summary.total_rallies ?? 0,
        opponent_name: opponentName,
        match_comment: matchComment,
        loss_tags:     lossTagsObj,
        rally_notes:   rallyNotes,
      }),
    })
      .then(async r => {
        if (r.status === 429) { setFeedbackError('quota'); return; }
        if (!r.ok) { setFeedbackError('error'); return; }
        const data = await r.json();
        setFeedback(data?.feedback ?? null);
        if (!data?.feedback) setFeedbackError('error');
      })
      .catch(() => setFeedbackError('error'))
      .finally(() => setFeedbackLoading(false));
  }, [isSummary]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleLabel(key, label) {
    setLabels(prev => {
      const next = { ...prev };
      if (label == null) delete next[key]; else next[key] = label;
      return next;
    });
    await fetch(`${API_BASE}/rally_label`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id, rally_index: key, label }),
    }).catch(() => {});
  }

  const goBack = () => {
    if (page > 0) setPage(p => p - 1);
    else if (movementResult) navigate('/movement-result', { state: { result: movementResult } });
    else navigate(-1);
  };

  return (
    <div className="bg-black" style={{ height: '100dvh', display: 'flex', flexDirection: 'column' }}>

      {/* Header */}
      <div className="px-5 pt-14 pb-2 flex-shrink-0 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={goBack}
            className="text-white/30 hover:text-white text-2xl leading-none transition-colors"
          >
            ‹
          </button>
          <span className="text-[11px] font-semibold text-white/25 uppercase tracking-widest">
            Rally Analysis
          </span>
        </div>
        <span className="text-[11px] text-white/20 tabular-nums">
          {page + 1} / {totalPages}
        </span>
      </div>

      {/* Progress bar */}
      <div className="px-5 pb-3 flex-shrink-0 flex gap-1">
        {Array.from({ length: totalPages }).map((_, i) => (
          <div
            key={i}
            className="rounded-full transition-all duration-200"
            style={{
              height: 3,
              flex: i === page ? 2 : 1,
              background: i === page ? '#C8FF57' : 'rgba(255,255,255,0.10)',
            }}
          />
        ))}
      </div>

      {/* Page content */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {isSummary || enriched.length === 0 ? (
          <SummaryPage
            summary={summary}
            totalLossSlots={totalLossSlots}
            labels={labels}
            onHome={() => navigate('/home')}
            onHistory={() => navigate('/match-history')}
            fromHistory={fromHistory}
            feedback={feedback}
            feedbackLoading={feedbackLoading}
            feedbackError={feedbackError}
            opponentName={opponentName}
            sessionId={session_id}
          />
        ) : (
          <RallyPage
            key={page}
            rally={enriched[page]}
            labels={labels}
            onLabel={handleLabel}
            note={rallyNotes[enriched[page].index] ?? ''}
            onNote={handleNote}
            sessionId={session_id}
            onNext={() => setPage(p => p + 1)}
            isLast={page === enriched.length - 1}
            courtPositions={courtPositions}
            isLocked={locked}
          />
        )}
      </div>

    </div>
  );
}

export default RallyResult;
