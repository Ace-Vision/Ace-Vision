import { useNavigate, useLocation } from 'react-router-dom';

const API_BASE = process.env.REACT_APP_API_URL || '';

function MovementResult() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const result = state?.result ?? {};

  const { session_id, rallies = [], rally_summary = {} } = result;

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
            <p className="text-[11px] text-white/25 mt-2 uppercase tracking-widest">Opponent</p>
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

        {/* Rally Analysis */}
        <button
          onClick={() => navigate('/rally-result', {
            state: {
              result:         { session_id, rallies, summary: rally_summary },
              movementResult: result,
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
