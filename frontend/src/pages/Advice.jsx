import { useNavigate, useLocation } from 'react-router-dom';

const API_BASE = process.env.REACT_APP_API_URL || '';

const PATTERNS = {
  1: {
    name: 'Late Positioning',
    icon: '⏱',
    short: 'Getting into position too late',
    detail: 'You may be arriving at the shuttle too late, forcing you to hit from a low or cramped position. Focus on early footwork — move into position before the shuttle reaches you.',
  },
  2: {
    name: 'Wrist-only Swing',
    icon: '🤚',
    short: 'Not using the full kinetic chain',
    detail: 'You\'re relying too much on wrist snap rather than driving through with shoulder and elbow first. Let the larger muscles lead and the wrist follow through naturally at the end.',
  },
  3: {
    name: 'Backswing Issue',
    icon: '↩',
    short: 'Backswing preparation is off',
    detail: 'Your arm loading before the swing is either too large or too compact compared to the ideal. Aim for a controlled, full draw before swinging forward to build proper momentum.',
  },
  4: {
    name: 'No Body Rotation',
    icon: '🔄',
    short: 'Body is facing the net too early',
    detail: 'Turn sideways first and use hip-to-shoulder rotation to generate power. If your chest faces the net throughout the swing, you\'re losing most of your power before the racket even moves.',
  },
  5: {
    name: 'No Follow-through',
    icon: '🛑',
    short: 'Swing stopped at impact',
    detail: 'You\'re decelerating at the point of contact instead of committing to a full swing. Let the racket follow through completely — stopping early costs you both power and accuracy.',
  },
};

const JOINT_TO_METRIC = {
  right_elbow:   'right_elbow_flexion',
  left_elbow:    'left_elbow_flexion',
  right_shoulder: 'right_shoulder_abduction',
  left_shoulder:  'left_shoulder_abduction',
  right_wrist:   'wrist_extension',
  left_wrist:    'wrist_extension',
  right_knee:    'right_knee_flexion',
  left_knee:     'left_knee_flexion',
  right_hip:     'hip_shoulder_separation',
  left_hip:      'hip_shoulder_separation',
  nose:          'trunk_lateral_tilt',
};

function severityLabel(s) {
  if (s >= 0.7) return { text: 'High', color: '#f87171' };
  if (s >= 0.4) return { text: 'Medium', color: '#fb923c' };
  return { text: 'Low', color: '#C8FF57' };
}

function findJointDeviation(checkpoints, highlightJoint) {
  if (!checkpoints || !highlightJoint) return null;
  const metricKey = JOINT_TO_METRIC[highlightJoint];
  if (!metricKey) return null;

  let worst = null;
  for (const [cpName, cpData] of Object.entries(checkpoints)) {
    if (!cpData?.deviations) continue;
    const dev = cpData.deviations[metricKey];
    if (dev && (!worst || dev.severity_score > worst.severity_score)) {
      worst = { ...dev, checkpoint: cpName, metric: metricKey };
    }
  }
  return worst;
}

export default function Advice() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const result = state?.result;
  const sport  = state?.sport ?? 'badminton';

  if (!result) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <button onClick={() => navigate('/home')} className="text-white/40 text-sm">
          ← Back to home
        </button>
      </div>
    );
  }

  const { overlay_path, coaching, deviation_scores } = result;
  const highlightJoint = coaching?.highlight_joint;
  const patternId      = coaching?.pattern_id;
  const pattern        = PATTERNS[patternId] ?? null;
  const checkpoints    = deviation_scores?.checkpoints ?? {};
  const jointDev       = findJointDeviation(checkpoints, highlightJoint);
  const sev            = jointDev ? severityLabel(jointDev.severity_score) : null;

  const jointLabel = highlightJoint
    ? highlightJoint.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    : null;
  const metricLabel = jointDev?.metric
    ? jointDev.metric.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    : null;
  const cpLabel = jointDev?.checkpoint
    ? jointDev.checkpoint.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    : null;

  return (
    <div className="min-h-screen bg-black pb-12">

      {/* Header */}
      <div className="px-5 pt-14 pb-4 flex items-center gap-3">
        <button
          onClick={() => navigate('/result', { state })}
          className="text-white/30 hover:text-white text-2xl leading-none transition-colors"
        >
          ‹
        </button>
        <span className="text-[13px] font-semibold text-white/25 uppercase tracking-widest">
          Advice
        </span>
      </div>

      <div className="px-5 space-y-4">

        {/* User video */}
        <div>
          <p className="text-[12px] font-semibold text-white/25 uppercase tracking-widest mb-2">
            Your Motion
          </p>
          <div className="rounded-2xl overflow-hidden bg-[#111]">
            <video
              src={`${API_BASE}${overlay_path}`}
              controls playsInline
              className="w-full"
              onLoadedMetadata={e => { e.target.playbackRate = 0.25; }}
            />
          </div>
        </div>

        {/* Pattern card */}
        {pattern && (
          <div
            className="rounded-2xl p-4 space-y-3"
            style={{ background: '#0f0f0f', border: '1px solid rgba(255,255,255,0.07)' }}
          >
            <div className="flex items-center gap-2">
              <span className="text-xl">{pattern.icon}</span>
              <div>
                <p className="text-[12px] font-semibold text-white/30 uppercase tracking-widest">
                  Pattern {patternId} of 5
                </p>
                <p className="text-base font-bold text-white leading-tight">
                  {pattern.name}
                </p>
              </div>
            </div>
            <p className="text-sm text-white/50 leading-relaxed">
              {pattern.detail}
            </p>
          </div>
        )}

        {/* Joint deviation card */}
        {jointDev && sev && (
          <div
            className="rounded-2xl p-4 space-y-2"
            style={{ background: '#0f0f0f', border: '1px solid rgba(255,255,255,0.07)' }}
          >
            <p className="text-[12px] font-semibold text-white/30 uppercase tracking-widest mb-1">
              Where it shows up
            </p>

            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-white">{jointLabel}</p>
                <p className="text-xs text-white/35 mt-0.5">
                  {metricLabel} · at {cpLabel}
                </p>
              </div>
              <span
                className="text-xs font-bold px-3 py-1 rounded-full"
                style={{ background: sev.color + '22', color: sev.color }}
              >
                {sev.text}
              </span>
            </div>

            {/* Deviation bar */}
            <div className="mt-2">
              <div className="flex justify-between text-[12px] text-white/25 mb-1">
                <span>Deviation</span>
                <span>{jointDev.deviation_deg?.toFixed(1)}° off</span>
              </div>
              <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${Math.min(jointDev.severity_score * 100, 100)}%`,
                    background: sev.color,
                  }}
                />
              </div>
            </div>

            <p className="text-xs text-white/30 pt-1">
              Direction: {jointDev.direction?.replace(/_/g, ' ')} ·{' '}
              Your angle: {jointDev.angle?.toFixed(1)}°
            </p>
          </div>
        )}

        {/* Pro reference video */}
        <div>
          <p className="text-[12px] font-semibold text-white/25 uppercase tracking-widest mb-2">
            Pro Reference
          </p>
          <div className="rounded-2xl overflow-hidden bg-[#111]">
            <video
              src={`${API_BASE}/reference/${sport}`}
              controls playsInline
              className="w-full"
            />
          </div>
          <p className="text-[12px] text-white/20 mt-2 text-center">
            Compare your motion above to the reference below
          </p>
        </div>

        {/* AI advice */}
        {coaching?.advice && (
          <div
            className="rounded-2xl p-4"
            style={{ background: '#0f0f0f', border: '1px solid rgba(255,255,255,0.07)' }}
          >
            <p className="text-[12px] font-bold text-[#C8FF57] uppercase tracking-widest mb-2">
              AI Coach
            </p>
            <p className="text-sm text-white/50 leading-relaxed">{coaching.advice}</p>
          </div>
        )}

      </div>
    </div>
  );
}
