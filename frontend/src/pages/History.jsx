import { useNavigate } from 'react-router-dom';

const sessions = [
  { id: 1, code: 'BH', title: 'Backhand Drive',  sport: 'Badminton', date: 'Apr 13', score: 73 },
  { id: 2, code: 'SV', title: 'Tennis Serve',    sport: 'Tennis',    date: 'Apr 10', score: 61 },
  { id: 3, code: 'FH', title: 'Forehand Clear',  sport: 'Badminton', date: 'Apr 7',  score: 80 },
  { id: 4, code: 'BL', title: 'Baseline Rally',  sport: 'Tennis',    date: 'Apr 3',  score: 55 },
];

function scoreColor(s) {
  if (s >= 75) return 'text-[#C8FF57]';
  if (s >= 55) return 'text-amber-400';
  return 'text-red-400';
}

function History() {
  const navigate = useNavigate();
  const avg = Math.round(sessions.reduce((a, s) => a + s.score, 0) / sessions.length);
  const best = Math.max(...sessions.map(s => s.score));

  return (
    <div className="min-h-screen bg-[#0a0a0a] pb-28">

      <div className="px-5 pt-16 pb-7">
        <p className="text-[13px] font-semibold text-[#444] tracking-widest uppercase mb-2">Ace Vision</p>
        <h1 className="text-3xl font-bold text-white">History.</h1>
      </div>

      {/* Stats row */}
      <div className="px-5 mb-5 grid grid-cols-3 gap-3">
        {[
          { label: 'Sessions', value: sessions.length },
          { label: 'Avg',      value: avg },
          { label: 'Best',     value: best },
        ].map(s => (
          <div key={s.label} className="card p-4 text-center">
            <p className="text-2xl font-black text-white tabular-nums">{s.value}</p>
            <p className="text-[12px] text-[#444] mt-1 font-semibold uppercase tracking-wider">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="px-5 space-y-2">
        {sessions.map(s => (
          <button
            key={s.id}
            onClick={() => navigate('/result')}
            className="w-full card-sm px-4 py-4 flex items-center gap-4 text-left hover:bg-[#161616] transition-colors"
          >
            <div className="w-9 h-9 rounded-lg bg-[#1e1e1e] flex items-center justify-center text-[#555] text-xs font-bold shrink-0">
              {s.code}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white">{s.title}</p>
              <p className="text-xs text-[#444] mt-0.5">{s.sport} · {s.date}</p>
            </div>
            <span className={`text-sm font-black tabular-nums ${scoreColor(s.score)}`}>{s.score}</span>
          </button>
        ))}
      </div>

    </div>
  );
}

export default History;
