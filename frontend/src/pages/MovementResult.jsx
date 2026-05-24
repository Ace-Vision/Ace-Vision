import { useNavigate, useLocation } from 'react-router-dom';

const API_BASE = process.env.REACT_APP_API_URL || '';

function MovementResult() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const result       = state?.result ?? {};
  const opponentName = state?.opponentName ?? '';
  const matchComment = state?.matchComment ?? '';
  const sport        = state?.sport ?? 'badminton';

  const { session_id, rallies = [], rally_summary = {}, phase_analysis = null } = result;

  // 最終スコア: ralliesの最後のエントリから取得、なければsummaryのラリー数で代替
  const lastRally = rallies.length > 0 ? rallies[rallies.length - 1] : null;
  const myScore  = lastRally?.my_score  ?? rally_summary.user_wins     ?? 0;
  const oppScore = lastRally?.opponent_score ?? rally_summary.opponent_wins ?? 0;

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
          Movement Analysis
        </span>
      </div>

      <div className="px-5 pt-6 space-y-6">

        {/* Final score */}
        <div className="animate-fade-up flex items-center justify-center gap-8 py-4">
          <div className="text-center">
            <p
              className="font-black text-white tabular-nums"
              style={{ fontSize: '64px', lineHeight: 1, letterSpacing: '-0.04em' }}
            >
              {myScore}
            </p>
            <p className="text-[11px] text-white/25 mt-2 uppercase tracking-widest">You</p>
          </div>
          <p className="text-3xl text-white/15 font-light mb-4">:</p>
          <div className="text-center">
            <p
              className="font-black text-white tabular-nums"
              style={{ fontSize: '64px', lineHeight: 1, letterSpacing: '-0.04em' }}
            >
              {oppScore}
            </p>
            <p className="text-[11px] text-white/25 mt-2 uppercase tracking-widest">{opponentName || 'Opponent'}</p>
          </div>
        </div>

        {/* Heatmaps */}
        {session_id && (
          <div className="animate-fade-up grid grid-cols-2 gap-3" style={{ animationDelay: '0.08s' }}>
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
                Opponent wins
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
        )}

        {/* Phase Analysis */}
        {phase_analysis && session_id && (
          <div className="animate-fade-up space-y-3" style={{ animationDelay: '0.12s' }}>
            <p className="text-[10px] font-bold text-white/25 uppercase tracking-widest">
              Movement by Phase
            </p>

            <div className="grid grid-cols-3 gap-2">
              {phase_analysis.phases.map((phase, i) => {
                const pct = phase.coverage_pct;
                const isLate = i === 2;
                const flagged = isLate && phase_analysis.stamina_flag;
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
                    <div className="rounded-xl overflow-hidden bg-[#111] border"
                      style={{ borderColor: flagged ? 'rgba(255,107,107,0.3)' : 'rgba(255,255,255,0.06)' }}>
                      <img
                        src={`${API_BASE}/phase_heatmap/${session_id}/${phase.phase}`}
                        alt={`Phase ${phase.phase}`}
                        className="w-full block"
                      />
                    </div>
                    {/* Coverage bar */}
                    <div className="mt-1.5 h-0.5 rounded-full bg-white/[0.06] overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${pct}%`,
                          background: flagged ? '#FF6B6B' : i === 0 ? '#C8FF57' : 'rgba(255,255,255,0.25)',
                        }}
                      />
                    </div>
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
                  Your court coverage dropped from {phase_analysis.coverage_trend[0]}% early on to {phase_analysis.coverage_trend[2]}% in the final phase.
                  Fatigue may be limiting your movement — add cardio sessions and footwork endurance drills to your training routine.
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

        {/* Rally Analysis */}
        <button
          onClick={() => navigate('/rally-result', {
            state: {
              result:         { session_id, rallies, summary: rally_summary },
              movementResult: result,
              opponentName,
              matchComment,
              sport,
            }
          })}
          className="w-full py-4 rounded-2xl text-sm font-semibold transition-all animate-fade-up active:scale-95"
          style={{ animationDelay: '0.14s', background: '#C8FF57', color: '#000' }}
        >
          Rally Analysis →
        </button>

        <button
          onClick={() => navigate('/home')}
          className="w-full py-4 rounded-2xl bg-white/[0.04] border border-white/[0.07] text-sm font-semibold text-white/30 hover:bg-white/[0.07] transition-colors animate-fade-up"
          style={{ animationDelay: '0.2s' }}
        >
          Analyze Again
        </button>

      </div>
    </div>
  );
}

export default MovementResult;
