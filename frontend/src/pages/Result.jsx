import { useNavigate, useLocation } from 'react-router-dom';

// Fallback shown when navigating directly to /result without data (dev only)
const FALLBACK = {
  overall_score: 0,
  sport_type: 'unknown',
  deviation_scores: { deviations: {} },
};

function severityClass(s) {
  if (s < 0.3) return 'border-green-500';
  if (s < 0.6) return 'border-amber-500';
  return 'border-red-500';
}

function severityBadge(s) {
  if (s < 0.3) return 'bg-green-100 text-green-700';
  if (s < 0.6) return 'bg-amber-100 text-amber-700';
  return 'bg-red-100 text-red-700';
}

function severityLabel(s) {
  if (s < 0.3) return 'Good';
  if (s < 0.6) return 'Fair';
  return 'Needs work';
}

function formatJointName(key) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function Result() {
  const navigate = useNavigate();
  const { state } = useLocation();

  const result = state?.result ?? FALLBACK;
  const { overall_score, sport_type, deviation_scores } = result;
  const deviations = deviation_scores?.deviations ?? {};

  const sportLabel = sport_type === 'tennis_serve' ? 'Tennis' : 'Badminton';

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

        {/* Joint breakdown */}
        <div>
          <h2 className="text-sm font-semibold text-gray-900 mb-3">Joint Analysis</h2>
          {Object.keys(deviations).length === 0 ? (
            <p className="text-sm text-gray-400">No joint data available.</p>
          ) : (
            <div className="space-y-2">
              {Object.entries(deviations).map(([joint, d]) => (
                <div key={joint} className={`bg-white rounded-xl p-4 border-l-4 ${severityClass(d.severity_score)} shadow-sm`}>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-900">{formatJointName(joint)}</span>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${severityBadge(d.severity_score)}`}>
                      {severityLabel(d.severity_score)}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-1">
                    {d.angle?.toFixed(1)}° &nbsp;·&nbsp; {d.deviation_deg?.toFixed(1)}° off &nbsp;·&nbsp; {d.direction?.replace('_', ' ')}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>


      </div>
    </div>
  );
}

export default Result;
