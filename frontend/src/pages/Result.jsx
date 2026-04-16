import { useNavigate } from 'react-router-dom';

// Mock data — replace with real API response later
const mockResult = {
  sport: 'Badminton',
  stroke: 'Backhand Drive',
  score: 73,
  deviations: [
    { joint: 'Right Elbow Flexion',      angle: 102, deviation: 16, direction: 'too low',  severity: 0.7 },
    { joint: 'Wrist Extension',          angle: 28,  deviation: 12, direction: 'too low',  severity: 0.55 },
    { joint: 'Trunk Lateral Tilt',       angle: 18,  deviation: 3,  direction: 'too high', severity: 0.2 },
    { joint: 'Right Shoulder Abduction', angle: 88,  deviation: 2,  direction: 'too low',  severity: 0.1 },
  ],
  coaching: {
    corrections: [
      {
        joint: 'Right Elbow Flexion',
        deviation_deg: 16,
        impact: 'Reduces power transfer and increases injury risk at contact.',
        drill: 'Shadow swing with elbow at 118° — hold a foam roller under your arm to keep angle consistent.',
      },
      {
        joint: 'Wrist Extension',
        deviation_deg: 12,
        impact: 'Late wrist snap causes loss of shuttle speed and direction control.',
        drill: 'Wrist flick drill — flick a shuttlecock against a wall 20 reps focusing on contact point.',
      },
    ],
    summary: 'Good base form. Primary issue is elbow angle at contact — fixing this will noticeably improve power and consistency.',
  },
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

function Result() {
  const navigate = useNavigate();
  const { sport, stroke, score, deviations, coaching } = mockResult;

  return (
    <div className="min-h-screen bg-gray-50 pb-24">

      {/* Header */}
      <div className="bg-white px-6 pt-14 pb-4 border-b border-gray-100 flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="text-gray-400 text-xl">‹</button>
        <div>
          <h1 className="text-xl font-semibold text-gray-900">{stroke}</h1>
          <p className="text-sm text-gray-400">{sport}</p>
        </div>
      </div>

      <div className="px-6 pt-5 space-y-5">

        {/* Score */}
        <div className="bg-purple-700 rounded-2xl p-5 flex items-center justify-between">
          <div>
            <p className="text-purple-200 text-sm">Overall Score</p>
            <p className="text-white text-5xl font-bold mt-1">{score}</p>
            <p className="text-purple-300 text-xs mt-1">out of 100</p>
          </div>
          <div className="w-20 h-20 rounded-full border-4 border-purple-400 flex items-center justify-center">
            <span className="text-white text-2xl font-bold">{score}</span>
          </div>
        </div>

        {/* Joint breakdown */}
        <div>
          <h2 className="text-sm font-semibold text-gray-900 mb-3">Joint Analysis</h2>
          <div className="space-y-2">
            {deviations.map(d => (
              <div key={d.joint} className={`bg-white rounded-xl p-4 border-l-4 ${severityClass(d.severity)} shadow-sm`}>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900">{d.joint}</span>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${severityBadge(d.severity)}`}>
                    {severityLabel(d.severity)}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  {d.angle}° &nbsp;·&nbsp; {d.deviation}° off &nbsp;·&nbsp; {d.direction}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* AI Coaching */}
        <div>
          <h2 className="text-sm font-semibold text-gray-900 mb-3">AI Coaching</h2>

          <div className="bg-white rounded-xl p-4 border border-gray-100 mb-3">
            <p className="text-xs text-gray-500 italic">{coaching.summary}</p>
          </div>

          {coaching.corrections.map((c, i) => (
            <div key={i} className="bg-white rounded-xl p-4 border border-gray-100 mb-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="w-5 h-5 rounded-full bg-purple-600 text-white text-xs flex items-center justify-center font-bold shrink-0">
                  {i + 1}
                </span>
                <span className="text-sm font-medium text-gray-900">{c.joint}</span>
                <span className="text-xs text-red-500 ml-auto">{c.deviation_deg}° off</span>
              </div>
              <p className="text-xs text-gray-600 mb-2">{c.impact}</p>
              <div className="bg-purple-50 rounded-lg p-3">
                <p className="text-xs font-medium text-purple-700 mb-1">Drill</p>
                <p className="text-xs text-purple-600">{c.drill}</p>
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}

export default Result;
