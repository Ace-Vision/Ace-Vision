import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function Record() {
  const navigate = useNavigate();
  const [sport, setSport] = useState('badminton');
  const [skill, setSkill] = useState('intermediate');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);

  function handleFile(e) {
    const f = e.target.files[0];
    if (f) setFile(f);
  }

  async function handleAnalyse() {
    if (!file) return;
    setLoading(true);
    // TODO: POST /analyse with file + skill_level
    await new Promise(r => setTimeout(r, 1500)); // mock delay
    setLoading(false);
    navigate('/result');
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-24">

      {/* Header */}
      <div className="bg-white px-6 pt-14 pb-4 border-b border-gray-100">
        <h1 className="text-xl font-semibold text-gray-900">New Analysis</h1>
        <p className="text-sm text-gray-400 mt-1">Upload a video to get started</p>
      </div>

      <div className="px-6 pt-6 space-y-5">

        {/* Sport */}
        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">Choose sport</p>
          <div className="flex gap-3">
            {[['badminton', '🏸 Badminton'], ['tennis', '🎾 Tennis']].map(([val, label]) => (
              <button
                key={val}
                onClick={() => setSport(val)}
                className={`flex-1 py-3 rounded-xl text-sm font-medium border-2 transition-colors ${
                  sport === val
                    ? 'border-purple-600 bg-purple-50 text-purple-700'
                    : 'border-gray-200 bg-white text-gray-500'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Skill level */}
        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">Skill level</p>
          <div className="flex gap-2">
            {['beginner', 'intermediate', 'advanced'].map(lvl => (
              <button
                key={lvl}
                onClick={() => setSkill(lvl)}
                className={`flex-1 py-2 rounded-lg text-xs font-medium border transition-colors capitalize ${
                  skill === lvl
                    ? 'border-purple-600 bg-purple-600 text-white'
                    : 'border-gray-200 bg-white text-gray-500'
                }`}
              >
                {lvl}
              </button>
            ))}
          </div>
        </div>

        {/* Upload */}
        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">Your video</p>
          <label className={`flex flex-col items-center justify-center w-full h-40 border-2 border-dashed rounded-xl cursor-pointer transition-colors ${
            file ? 'border-purple-500 bg-purple-50' : 'border-gray-300 bg-white hover:border-purple-400'
          }`}>
            {file ? (
              <>
                <span className="text-3xl mb-2">✅</span>
                <span className="text-sm font-medium text-purple-700">{file.name}</span>
                <span className="text-xs text-gray-400 mt-1">Tap to change</span>
              </>
            ) : (
              <>
                <span className="text-3xl mb-2">📹</span>
                <span className="text-sm font-medium text-gray-600">Tap to upload</span>
                <span className="text-xs text-gray-400 mt-1">MP4 · MOV · Max 200MB</span>
              </>
            )}
            <input type="file" accept="video/mp4,video/quicktime" className="hidden" onChange={handleFile} />
          </label>
        </div>

        {/* Analyse button */}
        <button
          onClick={handleAnalyse}
          disabled={!file || loading}
          className={`w-full py-4 rounded-xl text-sm font-semibold transition-colors ${
            file && !loading
              ? 'bg-purple-700 text-white hover:bg-purple-800'
              : 'bg-gray-200 text-gray-400 cursor-not-allowed'
          }`}
        >
          {loading ? 'Analysing...' : 'Analyse My Swing'}
        </button>

      </div>
    </div>
  );
}

export default Record;
