import { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const API_BASE = process.env.REACT_APP_API_URL || '';

// ナビゲーションをまたいで File を保持するモジュールレベルキャッシュ
let _cachedFile = null;

function MovementResult() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const result = state?.result ?? {};

  const { session_id, total_positions = 0, duration_s = 0,
          rallies = [], rally_summary = {} } = result;

  // state に file があればキャッシュを更新、なければキャッシュから取得
  const fileFromState = state?.file ?? null;
  if (fileFromState) _cachedFile = fileFromState;
  const originalFile = fileFromState ?? _cachedFile;

  const originalRef = useRef(null);
  const movementRef = useRef(null);

  const [originalUrl, setOriginalUrl] = useState(null);
  useEffect(() => {
    if (!originalFile) return;
    const url = URL.createObjectURL(originalFile);
    setOriginalUrl(url);
    return () => {
      URL.revokeObjectURL(url);
      setOriginalUrl(null);
    };
  }, [originalFile]);

  // Original (master) → Court movement (slave)
  useEffect(() => {
    const master = originalRef.current;
    const slave  = movementRef.current;
    if (!master || !slave) return;

    const onPlay   = () => slave.play().catch(() => {});
    const onPause  = () => slave.pause();
    const onSeeked = () => { slave.currentTime = master.currentTime; };

    master.addEventListener('play',   onPlay);
    master.addEventListener('pause',  onPause);
    master.addEventListener('seeked', onSeeked);

    return () => {
      master.removeEventListener('play',   onPlay);
      master.removeEventListener('pause',  onPause);
      master.removeEventListener('seeked', onSeeked);
    };
  }, [originalUrl, session_id]);

  const minutes = Math.floor(duration_s / 60);
  const seconds = Math.round(duration_s % 60);

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

      <div className="px-5 pt-4 space-y-4">

        {/* Stats */}
        <div className="animate-fade-up">
          <p
            className="font-black text-white tabular-nums"
            style={{ fontSize: '48px', lineHeight: 1, letterSpacing: '-0.04em' }}
          >
            {total_positions}
          </p>
          <p className="text-xs text-white/25 mt-1">
            positions tracked · {minutes}m {seconds}s
          </p>
        </div>

        {/* Original video — master */}
        {originalUrl && (
          <div className="animate-fade-up rounded-2xl overflow-hidden bg-[#111] border border-white/[0.06]"
            style={{ animationDelay: '0.05s' }}>
            <p className="text-[10px] font-bold text-white/30 uppercase tracking-widest px-4 pt-3 pb-2">
              Original
            </p>
            <video
              key={originalUrl}
              ref={originalRef}
              src={originalUrl}
              controls
              playsInline
              muted
              className="w-full block"
            />
          </div>
        )}

        {/* Court movement — synced slave */}
        {session_id && (
          <div className="animate-fade-up rounded-2xl overflow-hidden bg-[#111] border border-white/[0.06]"
            style={{ animationDelay: '0.1s' }}>
            <p className="text-[10px] font-bold text-[#C8FF57] uppercase tracking-widest px-4 pt-3 pb-2">
              Court Movement
            </p>
            <video
              ref={movementRef}
              src={`${API_BASE}/movement/${session_id}`}
              playsInline
              muted
              className="w-full block"
            />
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
          style={{ animationDelay: '0.15s', background: '#C8FF57', color: '#000' }}
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
