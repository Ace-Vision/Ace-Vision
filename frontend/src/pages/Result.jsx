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
  const { overall_score, sport_type, deviation_scores, coaching, overlay_path } = result;
  const checkpoints = deviation_scores?.checkpoints ?? {};
  const CHECKPOINTS = CHECKPOINTS_BY_SPORT[sport_type] ?? CHECKPOINTS_BY_SPORT.tennis_serve;


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
        <span className="text-[11px] font-semibold text-white/25 uppercase tracking-widest">Results</span>
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
            <p className="text-[11px] font-semibold text-white/25 uppercase tracking-widest mb-1">Overall Score</p>
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
          <p className="text-[11px] font-semibold text-white/25 uppercase tracking-widest mb-3">Breakdown</p>
          <div className="space-y-2">
            {CHECKPOINTS.map(({ key, label }) => {
              const score = checkpointScore(checkpoints[key]);

              return (
                <div key={key}>
                  <div className="w-full card-sm px-4 py-4 flex items-center justify-between">
                    <span className="text-sm font-semibold text-white">{label}</span>
                    <span className={`text-xl font-black tabular-nums ${scoreColor(score)}`}>
                      {score ?? '—'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* AI Coach */}
        {coaching?.advice && (
          <div className="card-sm px-4 py-4 animate-fade-up" style={{ animationDelay: '0.3s' }}>
            <p className="text-[10px] font-bold text-[#C8FF57] uppercase tracking-widest mb-3">AI Coach</p>
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

        {/* Analyze Again */}
        <button
          onClick={() => navigate('/home')}
          className="w-full py-4 rounded-2xl bg-white/[0.04] border border-white/[0.07] text-sm font-semibold text-white/30 transition-colors hover:bg-white/[0.07] animate-fade-up"
          style={{ animationDelay: '0.3s' }}
        >
          Analyze Again
        </button>

      </div>
    </div>
  );
}

export default Result;
