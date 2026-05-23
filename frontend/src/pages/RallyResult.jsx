import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const API_BASE = process.env.REACT_APP_API_URL || '';

const LABEL_OPTIONS = [
  { value: 'swing_miss',   label: 'Swing Miss' },
  { value: 'bad_footwork', label: 'Bad Footwork' },
  { value: 'other',        label: 'Other' },
];

// SVG donut pie chart
function PieChart({ slices }) {
  const active = slices.filter(s => s.count > 0);
  const total  = active.reduce((s, d) => s + d.count, 0);
  if (total === 0) return null;

  const cx = 50, cy = 50, R = 40, ir = 24;
  let angle = -Math.PI / 2;

  const paths = active.map(slice => {
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

  return (
    <div className="flex items-center gap-6">
      <svg viewBox="0 0 100 100" style={{ width: 110, height: 110, flexShrink: 0 }}>
        {paths.map((p, i) => <path key={i} d={p.d} fill={p.color} />)}
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
function RallyPage({ rally, label, onLabel, sessionId, onNext, isLast }) {
  const isWin    = rally.rally_winner === 'user';
  const accent   = isWin ? '#C8FF57' : '#FF6B6B';
  const prevMy   = isWin ? rally.my_score - 1 : rally.my_score;
  const prevOpp  = isWin ? rally.opponent_score : rally.opponent_score - 1;
  const duration = Math.round(rally.end_s - rally.start_s);

  return (
    <div className="px-5 pt-3 pb-6 space-y-4">

      {/* Win / Loss label */}
      <div className="flex items-center justify-between">
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', color: accent, textTransform: 'uppercase' }}>
          {isWin ? 'Point Won' : 'Point Lost'}
        </span>
        <span className="text-[11px] text-white/20">{duration}s</span>
      </div>

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
          src={`${API_BASE}/rally_clip/${sessionId}/${rally.clip_filename}`}
          controls
          playsInline
          muted
          style={{ display: 'inline-block', maxHeight: '50dvh', maxWidth: '100%', borderRadius: 16 }}
        />
      </div>

      {/* Tag buttons — losses only */}
      {!isWin && (
        <div>
          <p className="text-[10px] font-semibold text-white/20 uppercase tracking-widest mb-2">
            Tag this loss
          </p>
          <div className="flex gap-2 flex-wrap">
            {LABEL_OPTIONS.map(opt => {
              const sel = label === opt.value;
              return (
                <button
                  key={opt.value}
                  onClick={() => onLabel(rally.index, sel ? null : opt.value)}
                  className="px-3 py-1.5 rounded-xl text-xs font-semibold transition-all active:scale-95"
                  style={sel
                    ? { background: '#FF6B6B', color: '#000' }
                    : { background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.35)', border: '1px solid rgba(255,255,255,0.08)' }
                  }
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>
      )}

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
function SummaryPage({ summary, losses, labels, onHome }) {
  const counts = { swing_miss: 0, bad_footwork: 0, other: 0, unlabeled: 0 };
  losses.forEach(r => {
    const l = labels[r.index];
    if (l === 'swing_miss')        counts.swing_miss++;
    else if (l === 'bad_footwork') counts.bad_footwork++;
    else if (l === 'other')        counts.other++;
    else                           counts.unlabeled++;
  });

  const pieSlices = [
    { label: 'Swing Miss',   count: counts.swing_miss,   color: '#FF6B6B' },
    { label: 'Bad Footwork', count: counts.bad_footwork, color: '#FF9F43' },
    { label: 'Other',        count: counts.other,        color: '#636e72' },
    { label: 'Unlabeled',    count: counts.unlabeled,    color: 'rgba(255,255,255,0.10)' },
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
      {losses.length > 0 && (
        <div>
          <p className="text-[10px] font-bold text-white/25 uppercase tracking-widest mb-4">
            Loss Breakdown
          </p>
          <PieChart slices={pieSlices} />
        </div>
      )}

      {/* AI Feedback placeholder */}
      <div className="rounded-2xl border border-white/[0.06] bg-[#0d0d0d] p-4 space-y-2">
        <p className="text-[10px] font-bold text-white/25 uppercase tracking-widest">
          AI Coaching
        </p>
        <div className="space-y-1.5">
          <div className="h-2 rounded-full bg-white/[0.05] w-full" />
          <div className="h-2 rounded-full bg-white/[0.05] w-4/5" />
          <div className="h-2 rounded-full bg-white/[0.05] w-3/5" />
        </div>
      </div>

      <button
        onClick={onHome}
        className="w-full py-4 rounded-2xl bg-white/[0.04] border border-white/[0.07] text-sm font-semibold text-white/30 hover:bg-white/[0.07] transition-colors"
      >
        Analyze Again
      </button>

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

  const [page, setPage] = useState(0);
  const [labels, setLabels] = useState({});

  // Fetch persisted labels
  useEffect(() => {
    if (!session_id) return;
    fetch(`${API_BASE}/rally_labels/${session_id}`)
      .then(r => r.json())
      .then(data => {
        const parsed = {};
        for (const [k, v] of Object.entries(data.labels || {})) parsed[parseInt(k)] = v;
        setLabels(parsed);
      })
      .catch(() => {});
  }, [session_id]);

  async function handleLabel(rallyIndex, label) {
    setLabels(prev => {
      const next = { ...prev };
      if (label == null) delete next[rallyIndex]; else next[rallyIndex] = label;
      return next;
    });
    await fetch(`${API_BASE}/rally_label`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id, rally_index: rallyIndex, label }),
    }).catch(() => {});
  }

  const enriched   = rallies.map(r => ({ ...r, session_id }));
  const losses     = enriched.filter(r => r.rally_winner === 'opponent');
  const totalPages = enriched.length + 1;
  const isSummary  = page >= enriched.length;

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
        {isSummary ? (
          <SummaryPage
            summary={summary}
            losses={losses}
            labels={labels}
            onHome={() => navigate('/home')}
          />
        ) : enriched.length === 0 ? (
          <SummaryPage
            summary={summary}
            losses={losses}
            labels={labels}
            onHome={() => navigate('/home')}
          />
        ) : (
          <RallyPage
            key={page}
            rally={enriched[page]}
            label={labels[enriched[page].index]}
            onLabel={handleLabel}
            sessionId={session_id}
            onNext={() => setPage(p => p + 1)}
            isLast={page === enriched.length - 1}
          />
        )}
      </div>

    </div>
  );
}

export default RallyResult;
