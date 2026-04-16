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

function levelColor(lvl) {
  return lvl === 'Beginner' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700';
}

function Drills() {
  return (
    <div className="min-h-screen bg-gray-50 pb-24">

      {/* Header */}
      <div className="bg-white px-6 pt-14 pb-4 border-b border-gray-100">
        <h1 className="text-xl font-semibold text-gray-900">Drills</h1>
        <p className="text-sm text-gray-400 mt-1">Practice exercises for improvement</p>
      </div>

      <div className="px-6 pt-5 space-y-3">
        {drills.map(d => (
          <div key={d.id} className="bg-white rounded-xl p-4 border border-gray-100">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm">{d.sport === 'Badminton' ? '🏸' : '🎾'}</span>
              <span className="text-sm font-medium text-gray-900 flex-1">{d.title}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${levelColor(d.level)}`}>
                {d.level}
              </span>
            </div>
            <p className="text-xs text-gray-500 mb-2">{d.desc}</p>
            <p className="text-xs text-gray-400">⏱ {d.duration}</p>
          </div>
        ))}
      </div>

    </div>
  );
}

export default Drills;
