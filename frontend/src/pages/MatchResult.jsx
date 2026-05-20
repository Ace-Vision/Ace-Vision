import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';

const API_BASE = process.env.REACT_APP_API_URL || '';
const CLIPS_INITIAL = 3;

function MatchResult() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const result = state?.result ?? {};

  const { session_id, shot_count = 0, shots = [], clip_filenames = [], coaching } = result;
  const [showAll, setShowAll] = useState(false);

  const visible = showAll ? clip_filenames : clip_filenames.slice(0, CLIPS_INITIAL);

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
        <span className="text-[11px] font-semibold text-white/25 uppercase tracking-widest">Match Analysis</span>
      </div>

      <div className="px-5 pt-4 space-y-8">

        {/* Shot count */}
        <div className="animate-fade-up">
          <p
            className="font-black text-white tabular-nums"
            style={{ fontSize: '64px', lineHeight: 1, letterSpacing: '-0.04em' }}
          >
            {shot_count}
          </p>
          <p className="text-sm text-white/25 mt-1">overhead shots detected</p>
        </div>

        {/* Key Focus */}
        {coaching?.advice && (
          <div
            className="rounded-2xl px-4 py-4 animate-fade-up"
            style={{ background: '#111', border: '1px solid rgba(200,255,87,0.15)', animationDelay: '0.1s' }}
          >
            <p className="text-[10px] font-bold text-[#C8FF57] uppercase tracking-widest mb-3">Key Focus</p>
            <ReactMarkdown
              components={{
                p: ({ children }) => (
                  <p className="text-sm text-white/55 leading-relaxed mb-2 last:mb-0">{children}</p>
                ),
                strong: ({ children }) => (
                  <span className="font-semibold text-white">{children}</span>
                ),
              }}
            >
              {coaching.advice}
            </ReactMarkdown>
          </div>
        )}

        {/* Clips */}
        {clip_filenames.length > 0 && (
          <div className="animate-fade-up" style={{ animationDelay: '0.2s' }}>
            <p className="text-[11px] font-semibold text-white/25 uppercase tracking-widest mb-3">
              Overhead Shots
            </p>
            <div className="space-y-2">
              {visible.map((filename, i) => (
                <div key={filename} className="rounded-2xl overflow-hidden bg-[#111] border border-white/[0.06]">
                  <video
                    src={`${API_BASE}/clips/${session_id}/${filename}`}
                    controls
                    playsInline
                    className="w-full"
                    onLoadedMetadata={e => { e.target.playbackRate = 0.5; }}
                  />
                  <p className="text-[10px] text-white/20 px-3 py-2">
                    {shots[i] ? `Peak at ${shots[i].peak_time_s.toFixed(1)}s` : `Shot ${i + 1}`}
                  </p>
                </div>
              ))}
            </div>

            {clip_filenames.length > CLIPS_INITIAL && (
              <button
                onClick={() => setShowAll(v => !v)}
                className="mt-2 w-full py-3 rounded-xl text-xs font-semibold text-white/30 bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.06] transition-colors"
              >
                {showAll
                  ? 'Show less ▲'
                  : `Show ${clip_filenames.length - CLIPS_INITIAL} more ▼`}
              </button>
            )}
          </div>
        )}

        {/* Analyze Again */}
        <button
          onClick={() => navigate('/home')}
          className="w-full py-4 rounded-2xl bg-white/[0.04] border border-white/[0.07] text-sm font-semibold text-white/30 hover:bg-white/[0.07] transition-colors animate-fade-up"
          style={{ animationDelay: '0.3s' }}
        >
          Analyze Again
        </button>

      </div>
    </div>
  );
}

export default MatchResult;
