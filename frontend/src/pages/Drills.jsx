import { useState } from 'react';

const drills = [
  {
    id: 1, sport: 'Badminton', title: 'Elbow Angle Drill',
    desc: 'Shadow swing holding elbow at 118° using a foam roller.',
    duration: '10 min', level: 'Beginner',
  },
  {
    id: 2, sport: 'Badminton', title: 'Wrist Flick Wall Rally',
    desc: 'Flick a shuttlecock against a wall 20 reps focusing on contact point.',
    duration: '5 min', level: 'Beginner',
  },
  {
    id: 3, sport: 'Tennis', title: 'Serve Toss Consistency',
    desc: 'Toss ball to same spot 50 times. Mark target on wall.',
    duration: '15 min', level: 'Intermediate',
  },
  {
    id: 4, sport: 'Tennis', title: 'Hip Rotation Lead',
    desc: 'Practice serve focusing on hip rotation before shoulder rotation.',
    duration: '10 min', level: 'Intermediate',
  },
];

function Drills() {
  const [filter, setFilter] = useState('All');
  const filtered = filter === 'All' ? drills : drills.filter(d => d.sport === filter);

  return (
    <div className="min-h-screen bg-[#0a0a0a] pb-28">

      <div className="px-5 pt-16 pb-7">
        <p className="text-[13px] font-semibold text-[#444] tracking-widest uppercase mb-2">Ace Vision</p>
        <h1 className="text-3xl font-bold text-white">Drills.</h1>
      </div>

      {/* Filter */}
      <div className="px-5 mb-5 flex gap-2">
        {['All', 'Badminton', 'Tennis'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
              filter === f
                ? 'bg-[#C8FF57] text-black'
                : 'bg-[#111] text-[#555] border border-[#1e1e1e]'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      <div className="px-5 space-y-2">
        {filtered.map(d => (
          <div key={d.id} className="card-sm px-4 py-4 hover:bg-[#161616] transition-colors cursor-pointer">
            <div className="flex items-start justify-between gap-3 mb-1.5">
              <p className="text-sm font-bold text-white">{d.title}</p>
              <span className={`text-[12px] font-bold uppercase tracking-wider shrink-0 mt-0.5 ${
                d.level === 'Beginner' ? 'text-[#C8FF57]' : 'text-amber-400'
              }`}>
                {d.level}
              </span>
            </div>
            <p className="text-xs text-[#555] leading-relaxed mb-3">{d.desc}</p>
            <p className="text-[12px] font-semibold text-[#333] uppercase tracking-wider">
              {d.sport} · {d.duration}
            </p>
          </div>
        ))}
      </div>

    </div>
  );
}

export default Drills;
