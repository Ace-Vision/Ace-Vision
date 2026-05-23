import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const API_BASE = process.env.REACT_APP_API_URL || '';

const LABEL_OPTIONS = [
  { value: 'swing_miss',   label: 'Swing Miss' },
  { value: 'bad_footwork', label: 'Bad Footwork' },
  { value: 'other',        label: 'Other' },
];

function ScoreChip({ my, opp, winner }) {
  const color = winner === 'user' ? '#C8FF57' : '#FF6B6B';
  return (
    <span
      className="text-xs font-bold px-2 py-1 rounded-lg"
      style={{ background: `${color}18`, color }}
    >
      {my} – {opp}
    </span>
  );
}

function RallyCard({ rally, label, onLabel }) {
  const isWin = rally.rally_winner === 'user';
  const accentColor = isWin ? '#C8FF57' : '#FF6B6B';

  const prevMy  = isWin ? rally.my_score - 1 : rally.my_score;
  const prevOpp = isWin ? rally.opponent_score : rally.opponent_score - 1;

  return (
    <div
      className="rounded-2xl overflow-hidden border"
      style={{ background: '#111', borderColor: 'rgba(255,255,255,0.06)' }}
    >
      {/* Score transition header */}
      <div className="px-4 pt-3 pb-2 flex items-center gap-2">
        <ScoreChip my={prevMy} opp={prevOpp} winner={rally.rally_winner} />
        <span className="text-white/25 text-xs">→</span>
        <ScoreChip my={rally.my_score} opp={rally.opponent_score} winner={rally.rally_winner} />
        <span className="ml-auto text-[10px] text-white/20">
          {Math.round(rally.end_s - rally.start_s)}s
        </span>
      </div>

      {/* Clip video */}
      <video
        src={`${API_BASE}/rally_clip/${rally.session_id}/${rally.clip_filename}`}
        controls
        playsInline
        muted
        className="w-full block"
      />

      {/* Label buttons — losing rallies only */}
      {!isWin && (
        <div className="px-3 py-3 flex gap-2 flex-wrap">
          {LABEL_OPTIONS.map(opt => {
            const selected = label === opt.value;
            return (
              <button
                key={opt.value}
                onClick={() => onLabel(rally.index, selected ? null : opt.value)}
                className="px-3 py-1.5 rounded-xl text-xs font-semibold transition-all active:scale-95"
                style={
                  selected
                    ? { background: '#FF6B6B', color: '#000' }
                    : { background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.35)',
                        border: '1px solid rgba(255,255,255,0.08)' }
                }
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function RallyResult() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const result         = state?.result ?? {};
  const movementResult = state?.movementResult ?? null;
  const { session_id, rallies = [], summary = {} } = result;

  function goBack() {
    if (movementResult) {
      // MovementResult の状態を明示的に渡して遷移 (navigate(-1) は state が失われる場合がある)
      navigate('/movement-result', { state: { result: movementResult } });
    } else {
      navigate(-1);
    }
  }

  const [labels, setLabels] = useState({});

  // Fetch saved labels on mount
  useEffect(() => {
    if (!session_id) return;
    fetch(`${API_BASE}/rally_labels/${session_id}`)
      .then(r => r.json())
      .then(data => {
        const parsed = {};
        for (const [k, v] of Object.entries(data.labels || {})) {
          parsed[parseInt(k)] = v;
        }
        setLabels(parsed);
      })
      .catch(() => {});
  }, [session_id]);

  async function handleLabel(rallyIndex, label) {
    setLabels(prev => ({ ...prev, [rallyIndex]: label ?? undefined }));
    await fetch(`${API_BASE}/rally_label`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ session_id, rally_index: rallyIndex, label }),
    }).catch(() => {});
  }

  // Attach session_id to each rally for the card
  const enriched = rallies.map(r => ({ ...r, session_id }));
  const wins   = enriched.filter(r => r.rally_winner === 'user');
  const losses = enriched.filter(r => r.rally_winner === 'opponent');

  return (
    <div className="min-h-screen bg-black pb-16">

      {/* Header */}
      <div className="px-5 pt-14 pb-2 flex items-center gap-3">
        <button
          onClick={goBack}
          className="text-white/30 hover:text-white text-2xl leading-none transition-colors"
        >
          ‹
        </button>
        <span className="text-[11px] font-semibold text-white/25 uppercase tracking-widest">
          Score Analysis
        </span>
      </div>

      <div className="px-5 pt-4 space-y-6">

        {/* Heatmaps */}
        {session_id && (
          <div className="animate-fade-up" style={{ animationDelay: '0s' }}>
            <p className="text-[10px] font-bold uppercase tracking-widest text-white/30 mb-3">
              Position Heatmap
            </p>
            <div className="grid grid-cols-2 gap-3">
              {[
                { which: 'win',  label: 'Winning',  color: '#C8FF57' },
                { which: 'loss', label: 'Losing',   color: '#FF6B6B' },
              ].map(({ which, label, color }) => (
                <div key={which}
                  className="rounded-2xl overflow-hidden bg-[#111] border border-white/[0.06]">
                  <p className="text-[10px] font-bold uppercase tracking-widest px-3 pt-2 pb-1"
                    style={{ color }}>
                    {label}
                  </p>
                  <img
                    src={`${API_BASE}/heatmap/${session_id}/${which}`}
                    alt={`${label} heatmap`}
                    className="w-full block"
                    onError={e => { e.currentTarget.style.display = 'none'; }}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Summary */}
        <div className="animate-fade-up flex items-end gap-4">
          <div>
            <p
              className="font-black tabular-nums"
              style={{ fontSize: '48px', lineHeight: 1, letterSpacing: '-0.04em', color: '#C8FF57' }}
            >
              {summary.user_wins ?? 0}
              <span className="text-white/20 text-2xl ml-1">W</span>
            </p>
          </div>
          <div className="pb-1">
            <p
              className="font-black tabular-nums"
              style={{ fontSize: '36px', lineHeight: 1, letterSpacing: '-0.03em', color: '#FF6B6B' }}
            >
              {summary.opponent_wins ?? 0}
              <span className="text-white/20 text-xl ml-1">L</span>
            </p>
          </div>
          <p className="text-xs text-white/25 pb-1 ml-auto">
            {summary.total_rallies ?? 0} rallies
          </p>
        </div>

        {/* Winning rallies */}
        {wins.length > 0 && (
          <div className="animate-fade-up space-y-3" style={{ animationDelay: '0.05s' }}>
            <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: '#C8FF57' }}>
              Winning Rallies · {wins.length}
            </p>
            {wins.map(r => (
              <RallyCard
                key={r.index}
                rally={r}
                label={labels[r.index]}
                onLabel={handleLabel}
              />
            ))}
          </div>
        )}

        {/* Losing rallies */}
        {losses.length > 0 && (
          <div className="animate-fade-up space-y-3" style={{ animationDelay: '0.1s' }}>
            <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: '#FF6B6B' }}>
              Losing Rallies · {losses.length}
            </p>
            {losses.map(r => (
              <RallyCard
                key={r.index}
                rally={r}
                label={labels[r.index]}
                onLabel={handleLabel}
              />
            ))}
          </div>
        )}

        {rallies.length === 0 && (
          <div className="animate-fade-up py-16 text-center">
            <p className="text-white/25 text-sm">No scores detected in this video.</p>
            <p className="text-white/15 text-xs mt-1">Make sure you clearly announce scores during the match.</p>
          </div>
        )}

        <button
          onClick={() => navigate('/home')}
          className="w-full py-4 rounded-2xl bg-white/[0.04] border border-white/[0.07] text-sm font-semibold text-white/30 hover:bg-white/[0.07] transition-colors animate-fade-up"
          style={{ animationDelay: '0.15s' }}
        >
          Analyze Again
        </button>

      </div>
    </div>
  );
}

export default RallyResult;
