import { useNavigate } from 'react-router-dom';

const sessions = [
  { id: 1, code: 'BH', color: 'bg-purple-500', title: 'Backhand Drive',  sport: 'Badminton', date: 'Apr 13',  score: 73 },
  { id: 2, code: 'SV', color: 'bg-teal-600',   title: 'Tennis Serve',    sport: 'Tennis',    date: 'Apr 10',  score: 61 },
  { id: 3, code: 'FH', color: 'bg-purple-400', title: 'Forehand Clear',  sport: 'Badminton', date: 'Apr 7',   score: 80 },
  { id: 4, code: 'BL', color: 'bg-teal-500',   title: 'Baseline Rally',  sport: 'Tennis',    date: 'Apr 3',   score: 55 },
];

function scoreBadge(score) {
  if (score >= 75) return 'bg-green-100 text-green-700';
  if (score >= 55) return 'bg-amber-100 text-amber-700';
  return 'bg-red-100 text-red-700';
}

function History() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50 pb-24">

      {/* Header */}
      <div className="bg-white px-6 pt-14 pb-4 border-b border-gray-100">
        <h1 className="text-xl font-semibold text-gray-900">History</h1>
        <p className="text-sm text-gray-400 mt-1">Your past analyses</p>
      </div>

      <div className="px-6 pt-5 space-y-3">
        {sessions.map(s => (
          <button
            key={s.id}
            onClick={() => navigate('/result')}
            className="w-full bg-white rounded-xl p-4 border border-gray-100 flex items-center gap-3 text-left hover:shadow-sm transition-shadow"
          >
            <div className={`w-10 h-10 ${s.color} rounded-lg flex items-center justify-center text-white text-xs font-medium shrink-0`}>
              {s.code}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900">{s.title}</p>
              <p className="text-xs text-gray-400">{s.sport} · {s.date}</p>
            </div>
            <span className={`text-xs font-semibold px-2 py-1 rounded-full ${scoreBadge(s.score)}`}>
              {s.score}
            </span>
            <span className="text-purple-500 text-lg ml-1">›</span>
          </button>
        ))}
      </div>

    </div>
  );
}

export default History;
