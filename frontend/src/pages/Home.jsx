import { useNavigate } from 'react-router-dom';

const recentItems = [
  { id: 1, code: 'BH', color: 'bg-purple-500', title: 'Backhand Drive',  sub: '2 days ago · Score 73', sport: 'badminton' },
  { id: 2, code: 'SV', color: 'bg-teal-600',   title: 'Tennis Serve',    sub: '5 days ago · Score 61', sport: 'tennis'    },
];

function Home() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50 pb-24">

      {/* Header */}
      <div className="bg-white px-6 pt-14 pb-4 border-b border-gray-100">
        <h1 className="text-2xl font-semibold text-gray-900">Ace Vision</h1>
        <p className="text-sm text-gray-400 mt-1">Badminton · Tennis</p>
      </div>

      {/* Sport Selector */}
      <div className="flex gap-2 px-6 py-4">
        <button className="bg-purple-100 text-purple-800 text-sm font-medium px-4 py-1.5 rounded-full">
          🏸 Badminton
        </button>
        <button className="bg-gray-100 text-gray-500 text-sm font-medium px-4 py-1.5 rounded-full">
          🎾 Tennis
        </button>
      </div>

      {/* Upload Card */}
      <div className="px-6">
        <div className="bg-purple-700 rounded-2xl p-5">
          <h2 className="text-white font-medium text-base">Analyze My Swing</h2>
          <p className="text-purple-200 text-sm mt-1">
            Upload your video and AI will compare it with pros
          </p>
          <label className="mt-4 border-2 border-dashed border-purple-400 rounded-xl p-6 flex flex-col items-center cursor-pointer hover:border-purple-200 transition-colors">
            <span className="text-3xl mb-2">⬆️</span>
            <span className="text-white text-sm font-medium">Upload Video</span>
            <span className="text-purple-300 text-xs mt-1">MP4 · MOV · Max 200MB</span>
            <input type="file" accept="video/mp4,video/quicktime" className="hidden" onChange={() => navigate('/record')} />
          </label>
        </div>
      </div>

      {/* Recent Analysis */}
      <div className="px-6 mt-6">
        <h3 className="text-sm font-medium text-gray-900 mb-3">Recent Analysis</h3>
        {recentItems.map(item => (
          <button
            key={item.id}
            onClick={() => navigate('/history')}
            className="w-full bg-white rounded-xl p-4 mb-3 border border-gray-100 flex items-center gap-3 text-left hover:shadow-sm transition-shadow"
          >
            <div className={`w-10 h-10 ${item.color} rounded-lg flex items-center justify-center text-white text-xs font-medium shrink-0`}>
              {item.code}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900">{item.title}</p>
              <p className="text-xs text-gray-400">{item.sub}</p>
            </div>
            <span className="text-purple-500 text-lg">›</span>
          </button>
        ))}
      </div>

    </div>
  );
}

export default Home;
