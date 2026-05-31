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

const PATTERNS = {
  1: { name: 'Late Positioning',   detail: 'You may be arriving at the shuttle too late, forcing you to hit from a low or cramped position. Focus on early footwork — move into position before the shuttle reaches you.' },
  2: { name: 'Wrist-only Swing',   detail: 'You\'re relying too much on wrist snap rather than driving through with shoulder and elbow first. Let the larger muscles lead and the wrist follow through naturally at the end.' },
  3: { name: 'Backswing Issue',     detail: 'Your arm loading before the swing is either too large or too compact compared to the ideal. Aim for a controlled, full draw before swinging forward to build proper momentum.' },
  4: { name: 'No Body Rotation',   detail: 'Turn sideways first and use hip-to-shoulder rotation to generate power. If your chest faces the net throughout the swing, you\'re losing most of your power before the racket even moves.' },
  5: { name: 'No Follow-through',  detail: 'You\'re decelerating at the point of contact instead of committing to a full swing. Let the racket follow through completely — stopping early costs you both power and accuracy.' },
};

const JOINT_TO_METRIC = {
  right_elbow:    'right_elbow_flexion',
  left_elbow:     'left_elbow_flexion',
  right_shoulder: 'right_shoulder_abduction',
  left_shoulder:  'left_shoulder_abduction',
  right_wrist:    'wrist_extension',
  left_wrist:     'wrist_extension',
  right_knee:     'right_knee_flexion',
  left_knee:      'left_knee_flexion',
  right_hip:      'hip_shoulder_separation',
  left_hip:       'hip_shoulder_separation',
  nose:           'trunk_lateral_tilt',
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

function severityLabel(s) {
  if (s >= 0.7) return { text: 'High',   color: '#f87171' };
  if (s >= 0.4) return { text: 'Medium', color: '#fb923c' };
  return                { text: 'Low',   color: '#C8FF57' };
}

function findJointDeviation(checkpoints, highlightJoint) {
  if (!checkpoints || !highlightJoint) return null;
  const metricKey = JOINT_TO_METRIC[highlightJoint];
  if (!metricKey) return null;
  let worst = null;
  for (const cpData of Object.values(checkpoints)) {
    if (!cpData?.deviations) continue;
    const dev = cpData.deviations[metricKey];
    if (dev && (!worst || dev.severity_score > worst.severity_score)) {
      worst = { ...dev, metric: metricKey };
    }
  }
  return worst;
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

  const highlightJoint = coaching?.highlight_joint;
  const patternId      = coaching?.pattern_id;
  const pattern        = PATTERNS[patternId] ?? null;
  const jointDev       = findJointDeviation(checkpoints, highlightJoint);
  const sev            = jointDev ? severityLabel(jointDev.severity_score) : null;
  const jointLabel     = highlightJoint
    ? highlightJoint.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    : null;

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

        {/* AI Coach */}
        {coaching?.advice && (
          <div
            className="rounded-2xl p-4 space-y-3 animate-fade-up"
            style={{ animationDelay: '0.3s', background: '#0f0f0f', border: '1px solid rgba(255,255,255,0.07)' }}
          >
            <p className="text-[12px] font-bold text-[#C8FF57] uppercase tracking-widest">AI Coach</p>

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

            {/* Pattern */}
            {pattern && (
              <div className="pt-2 border-t border-white/[0.06]">
                <p className="text-[11px] font-semibold text-white/25 uppercase tracking-widest mb-1">
                  Pattern Detected
                </p>
                <p className="text-sm font-semibold text-white mb-1">{pattern.name}</p>
                <p className="text-xs text-white/40 leading-relaxed">{pattern.detail}</p>
              </div>
            )}

            {/* Worst joint */}
            {jointDev && sev && (
              <div className="pt-2 border-t border-white/[0.06]">
                <p className="text-[11px] font-semibold text-white/25 uppercase tracking-widest mb-2">
                  Focus Joint
                </p>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-semibold text-white">{jointLabel}</p>
                  <span
                    className="text-xs font-bold px-3 py-1 rounded-full"
                    style={{ background: sev.color + '22', color: sev.color }}
                  >
                    {sev.text}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.min(jointDev.severity_score * 100, 100)}%`,
                      background: sev.color,
                      transition: 'width 0.7s ease-out',
                    }}
                  />
                </div>
                <p className="text-xs text-white/25 mt-1.5">
                  {jointDev.deviation_deg?.toFixed(1)}° off · {jointDev.direction?.replace(/_/g, ' ')}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Analyze Again */}
        <button
          onClick={() => navigate('/home')}
          className="w-full py-4 rounded-2xl bg-white/[0.04] border border-white/[0.07] text-sm font-semibold text-white/30 transition-colors hover:bg-white/[0.07] animate-fade-up"
          style={{ animationDelay: '0.35s' }}
        >
          Analyze Again
        </button>

      </div>
    </div>
  );
}

export default Result;
