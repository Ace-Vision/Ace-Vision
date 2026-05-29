import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';


const API_BASE = process.env.REACT_APP_API_URL || '';

const FALLBACK = {
  overall_score: 0,
  sport_type: 'unknown',
  deviation_scores: { checkpoints: {} },
};

const CHECKPOINTS_BY_SPORT = {
  badminton: [
    { key: 'backswing',      label: 'Backswing' },
    { key: 'contact',        label: 'Contact' },
    { key: 'follow_through', label: 'Follow Through' },
  ],
  tennis_serve: [
    { key: 'trophy',      label: 'Trophy' },
    { key: 'racket_drop', label: 'Racket Drop' },
    { key: 'contact',     label: 'Contact' },
  ],
};

function checkpointScore(cpData) {
  const devs = cpData?.deviations ? Object.values(cpData.deviations) : [];
  if (!devs.length) return null;
  const avg = devs.reduce((s, d) => s + (d.severity_score ?? 0), 0) / devs.length;
  return Math.round((1 - avg) * 100);
}

function scoreColor(s) {
  if (s === null) return 'text-white/20';
  if (s >= 75) return 'text-[#C8FF57]';
  if (s >= 55) return 'text-amber-400';
  return 'text-red-400';
}

function ScoreRing({ score }) {
  const r = 52;
  const circ = 2 * Math.PI * r;
  const offset = circ - ((score ?? 0) / 100) * circ;
  return (
    <svg width="128" height="128" viewBox="0 0 128 128">
      <circle cx="64" cy="64" r={r} fill="none" stroke="#1a1a1a" strokeWidth="6" />
      <circle
        cx="64" cy="64" r={r}
        fill="none" stroke="#C8FF57" strokeWidth="6"
        strokeDasharray={circ} strokeDashoffset={offset}
        strokeLinecap="round" transform="rotate(-90 64 64)"
        style={{ transition: 'stroke-dashoffset 1s ease-out' }}
      />
    </svg>
  );
}

function Result() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const result = state?.result ?? FALLBACK;
  const { overall_score, sport_type, deviation_scores, coaching, overlay_path, session_id } = result;
  const checkpoints = deviation_scores?.checkpoints ?? {};
  const CHECKPOINTS = CHECKPOINTS_BY_SPORT[sport_type] ?? CHECKPOINTS_BY_SPORT.tennis_serve;
  const [openCheckpoint, setOpenCheckpoint] = useState(null);

  function toggleCheckpoint(key) {
    setOpenCheckpoint(prev => prev === key ? null : key);
  }

  return (
    <div className="min-h-screen bg-black pb-12">

      {/* Header */}
      <div className="px-5 pt-14 pb-2 flex items-center gap-3">
        <button
          onClick={() => navigate('/home')}
          className="text-white/30 hover:text-white text-2xl leading-none transition-colors"
        >
          ‹
        </button>
        <span className="text-[13px] font-semibold text-white/25 uppercase tracking-widest">Results</span>
      </div>

      <div className="px-5 pt-2 space-y-5">

        {/* Video */}
        {overlay_path && (
          <div className="rounded-2xl overflow-hidden bg-[#111] animate-fade-up">
            <video
              src={`${API_BASE}${overlay_path}`}
              controls
              playsInline
              className="w-full"
              onLoadedMetadata={e => { e.target.playbackRate = 0.25; }}
            />
          </div>
        )}

        {/* Overall Score */}
        <div
          className="flex items-center justify-between animate-fade-up"
          style={{ animationDelay: '0.1s' }}
        >
          <div>
            <p className="text-[13px] font-semibold text-white/25 uppercase tracking-widest mb-1">Overall Score</p>
            <p
              className="font-black text-white tabular-nums"
              style={{ fontSize: '76px', lineHeight: 1, letterSpacing: '-0.04em' }}
            >
              {overall_score}
            </p>
            <p className="text-xs text-white/25 mt-1">out of 100</p>
          </div>
          <div className="relative flex items-center justify-center">
            <ScoreRing score={overall_score} />
            <span
              className="absolute font-black text-[#C8FF57] tabular-nums"
              style={{ fontSize: '22px', letterSpacing: '-0.03em' }}
            >
              {overall_score}
            </span>
          </div>
        </div>

        {/* Breakdown */}
        <div className="animate-fade-up" style={{ animationDelay: '0.2s' }}>
          <p className="text-[13px] font-semibold text-white/25 uppercase tracking-widest mb-3">Breakdown</p>
          <div className="space-y-2">
            {CHECKPOINTS.map(({ key, label }) => {
              const score = checkpointScore(checkpoints[key]);
              const isOpen = openCheckpoint === key;
              const hasFrame = !!checkpoints[key];
              const frameUrl = `${API_BASE}/frame/${session_id}/${key}`;

              return (
                <div key={key} className="overflow-hidden rounded-2xl bg-[#111] border border-white/[0.06]">
                  <button
                    onClick={() => hasFrame && toggleCheckpoint(key)}
                    className="w-full px-4 py-4 flex items-center justify-between"
                    style={{ cursor: hasFrame ? 'pointer' : 'default' }}
                  >
                    <span className="text-sm font-semibold text-white">{label}</span>
                    <div className="flex items-center gap-3">
                      <span className={`text-xl font-black tabular-nums ${scoreColor(score)}`}>
                        {score ?? '—'}
                      </span>
                      {hasFrame && (
                        <span
                          className="text-white/25 text-sm transition-transform duration-300"
                          style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)', display: 'inline-block' }}
                        >
                          ▾
                        </span>
                      )}
                    </div>
                  </button>

                  {/* Frame image — accordion */}
                  <div
                    style={{
                      maxHeight: isOpen ? '320px' : '0px',
                      transition: 'max-height 0.35s ease',
                      overflow: 'hidden',
                    }}
                  >
                    <div className="px-3 pb-3">
                      <img
                        src={frameUrl}
                        alt={label}
                        className="w-full rounded-xl object-cover"
                        style={{ display: 'block' }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Recurring issues badge */}
        {coaching?.recurring_issues?.length > 0 && (
          <div
            className="card-sm px-4 py-3 border border-amber-400/20 animate-fade-up"
            style={{ animationDelay: '0.25s' }}
          >
            <p className="text-[10px] font-bold text-amber-400 uppercase tracking-widest mb-1">Pattern Detected</p>
            <p className="text-xs text-white/40 leading-relaxed">
              Still showing up across sessions:{' '}
              <span className="text-amber-300 font-semibold">
                {coaching.recurring_issues.map(j => j.replace(/_/g, ' ')).join(', ')}
              </span>
              . Coaching has been escalated for these joints.
            </p>
          </div>
        )}

        {/* AI Coach */}
        {coaching?.advice && (
          <div className="card-sm px-4 py-4 animate-fade-up" style={{ animationDelay: '0.3s' }}>
            <p className="text-[12px] font-bold text-[#C8FF57] uppercase tracking-widest mb-3">AI Coach</p>
            <ReactMarkdown
              components={{
                p: ({ children }) => <p className="text-sm text-white/55 leading-relaxed mb-2 last:mb-0">{children}</p>,
                strong: ({ children }) => <span className="font-semibold text-white">{children}</span>,
                ul: ({ children }) => <ul className="space-y-2 mt-1">{children}</ul>,
                li: ({ children }) => (
                  <li className="flex gap-2.5 text-sm text-white/55 leading-relaxed">
                    <span className="mt-[7px] w-1 h-1 rounded-full bg-[#C8FF57] shrink-0" />
                    <span>{children}</span>
                  </li>
                ),
              }}
            >
              {coaching.advice}
            </ReactMarkdown>
          </div>
        )}

        {/* Full Advice */}
        <button
          onClick={() => navigate('/advice', { state: { result, sport: sport_type } })}
          className="w-full py-4 rounded-2xl text-sm font-semibold text-black transition-opacity active:opacity-80 animate-fade-up"
          style={{ background: '#C8FF57', animationDelay: '0.35s' }}
        >
          Full Advice →
        </button>

        {/* Analyze Again */}
        <button
          onClick={() => navigate('/home')}
          className="w-full py-4 rounded-2xl bg-white/[0.04] border border-white/[0.07] text-sm font-semibold text-white/30 transition-colors hover:bg-white/[0.07] animate-fade-up"
          style={{ animationDelay: '0.4s' }}
        >
          Analyze Again
        </button>

      </div>
    </div>
  );
}

export default Result;
