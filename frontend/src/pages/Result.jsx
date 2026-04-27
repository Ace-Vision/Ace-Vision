import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';

const API_BASE = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

const FALLBACK = {
  overall_score: 0,
  sport_type: 'unknown',
  deviation_scores: { deviations: {}, checkpoints: {} },
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

function severity(s) {
  if (s < 0.3) return { border: 'border-green-500', badge: 'bg-green-100 text-green-700', label: 'Good' };
  if (s < 0.6) return { border: 'border-amber-500', badge: 'bg-amber-100 text-amber-700', label: 'Fair' };
  return { border: 'border-red-500',  badge: 'bg-red-100 text-red-700',   label: 'Needs work' };
}

function formatJointName(key) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function JointList({ deviations }) {
  if (!deviations || Object.keys(deviations).length === 0) {
    return <p className="text-sm text-gray-400">No data for this checkpoint.</p>;
  }
  return (
    <div className="space-y-2">
      {Object.entries(deviations).map(([joint, d]) => (
        <div key={joint} className={`bg-white rounded-xl p-4 border-l-4 ${severity(d.severity_score).border} shadow-sm`}>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-900">{formatJointName(joint)}</span>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${severity(d.severity_score).badge}`}>
              {severity(d.severity_score).label}
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {d.angle?.toFixed(1)}° &nbsp;·&nbsp; {d.deviation_deg?.toFixed(1)}° off &nbsp;·&nbsp; {d.direction?.replace('_', ' ')}
          </p>
        </div>
      ))}
    </div>
  );
}

function Result() {
  const navigate = useNavigate();
  const { state } = useLocation();

  const result = state?.result ?? FALLBACK;
  const { overall_score, sport_type, deviation_scores, coaching, overlay_path } = result;
  const checkpoints = deviation_scores?.checkpoints ?? {};
  const sportLabel = sport_type === 'tennis_serve' ? 'Tennis' : 'Badminton';
  const CHECKPOINTS = CHECKPOINTS_BY_SPORT[sport_type] ?? CHECKPOINTS_BY_SPORT.tennis_serve;

  const defaultCheckpoint = sport_type === 'badminton' ? 'contact' : 'trophy';
  const [activeCheckpoint, setActiveCheckpoint] = useState(defaultCheckpoint);

  const activeDeviations = checkpoints[activeCheckpoint]?.deviations ?? {};

  return (
    <div className="min-h-screen bg-gray-50 pb-24">

      {/* Header */}
      <div className="bg-white px-6 pt-14 pb-4 border-b border-gray-100 flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="text-gray-400 text-xl">‹</button>
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Analysis Result</h1>
          <p className="text-sm text-gray-400">{sportLabel}</p>
        </div>
      </div>

      <div className="px-6 pt-5 space-y-5">

        {/* Overlay video */}
        {overlay_path && (
          <div className="rounded-2xl overflow-hidden bg-black">
            <video
              src={`${API_BASE}${overlay_path}`}
              controls
              playsInline
              className="w-full"
            />
          </div>
        )}

        {/* Score */}
        <div className="bg-purple-700 rounded-2xl p-5 flex items-center justify-between">
          <div>
            <p className="text-purple-200 text-sm">Overall Score</p>
            <p className="text-white text-5xl font-bold mt-1">{overall_score}</p>
            <p className="text-purple-300 text-xs mt-1">out of 100</p>
          </div>
          <div className="w-20 h-20 rounded-full border-4 border-purple-400 flex items-center justify-center">
            <span className="text-white text-2xl font-bold">{overall_score}</span>
          </div>
        </div>

        {/* Checkpoint tabs */}
        <div>
          <h2 className="text-sm font-semibold text-gray-900 mb-3">Joint Analysis</h2>
          <div className="flex gap-2 mb-4">
            {CHECKPOINTS.map(({ key, label }) => {
              const hasData = checkpoints[key]?.deviations && Object.keys(checkpoints[key].deviations).length > 0;
              return (
                <button
                  key={key}
                  onClick={() => setActiveCheckpoint(key)}
                  className={`flex-1 py-2 rounded-lg text-xs font-medium border transition-colors ${
                    activeCheckpoint === key
                      ? 'border-purple-600 bg-purple-600 text-white'
                      : 'border-gray-200 bg-white text-gray-500'
                  } ${!hasData ? 'opacity-50' : ''}`}
                >
                  {label}
                </button>
              );
            })}
          </div>

          <JointList deviations={activeDeviations} />
        </div>

        {/* Coaching feedback */}
        {coaching?.advice && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <span className="text-lg">🎾</span>
              <h2 className="text-sm font-semibold text-gray-900">Coaching Advice</h2>
            </div>
            <div className="bg-gradient-to-br from-purple-50 to-white rounded-2xl p-5 shadow-sm border border-purple-100 space-y-3">
              <ReactMarkdown
                components={{
                  p: ({ children }) => (
                    <p className="text-sm text-gray-700 leading-relaxed">{children}</p>
                  ),
                  strong: ({ children }) => (
                    <span className="font-semibold text-gray-900">{children}</span>
                  ),
                  ul: ({ children }) => (
                    <ul className="space-y-1.5 pl-1">{children}</ul>
                  ),
                  li: ({ children }) => (
                    <li className="flex gap-2 text-sm text-gray-700 leading-relaxed">
                      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-purple-400 shrink-0" />
                      <span>{children}</span>
                    </li>
                  ),
                  h1: ({ children }) => (
                    <h3 className="text-sm font-bold text-purple-800 mt-4 first:mt-0">{children}</h3>
                  ),
                  h2: ({ children }) => (
                    <h3 className="text-sm font-bold text-purple-800 mt-4 first:mt-0">{children}</h3>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-sm font-bold text-purple-800 mt-4 first:mt-0">{children}</h3>
                  ),
                }}
              >
                {coaching.advice}
              </ReactMarkdown>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

export default Result;
