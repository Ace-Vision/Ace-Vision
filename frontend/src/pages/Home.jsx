import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const recentItems = [
  { id: 1, code: 'BH', color: 'bg-purple-500', title: 'Backhand Drive',  sub: '2 days ago · Score 73', sport: 'badminton' },
  { id: 2, code: 'SV', color: 'bg-teal-600',   title: 'Tennis Serve',    sub: '5 days ago · Score 61', sport: 'tennis'    },
];

function Home() {
  const navigate = useNavigate();
  const [sport, setSport] = useState('badminton');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [recording, setRecording] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);

  const videoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  // stream을 video 엘리먼트에 연결 — cameraOpen 후 DOM이 마운트된 뒤 실행
  useEffect(() => {
    if (cameraOpen && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [cameraOpen]);

  async function handleFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    await uploadFile(file);
  }

  async function uploadFile(file) {
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('sport_type', sport);
      formData.append('skill_level', 'intermediate');

      const res = await fetch(`${API_BASE}/analyse`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `Server error ${res.status}`);
      }

      const result = await res.json();
      navigate('/result', { state: { result, sport, skill: 'intermediate' } });
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  async function openCamera() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false });
      streamRef.current = stream;
      setCameraOpen(true);
    } catch (err) {
      setError('카메라 접근 오류: ' + err.message);
    }
  }

  function startRecording() {
    chunksRef.current = [];
    const mimeType = MediaRecorder.isTypeSupported('video/mp4')
      ? 'video/mp4'
      : MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
      ? 'video/webm;codecs=vp9'
      : 'video/webm';
    const ext = mimeType.includes('mp4') ? 'mp4' : 'webm';
    const recorder = new MediaRecorder(streamRef.current, { mimeType });
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };
    recorder.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: mimeType });
      const file = new File([blob], `recording.${ext}`, { type: mimeType });
      closeCamera();
      await uploadFile(file);
    };
    recorder.start();
    mediaRecorderRef.current = recorder;
    setRecording(true);
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  }

  function closeCamera() {
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    setCameraOpen(false);
    setRecording(false);
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-24">

      {/* Header */}
      <div className="bg-white px-6 pt-14 pb-4 border-b border-gray-100 text-center">
        <h1 className="text-2xl font-semibold text-gray-900">Ace Vision</h1>
        <p className="text-sm text-gray-400 mt-1">Badminton · Tennis</p>
      </div>

      {/* Sport Selector */}
      <div className="flex justify-center gap-4 px-6 py-4">
        <button
          onClick={() => setSport('badminton')}
          className={`text-sm font-medium px-4 py-1.5 rounded-full transition-colors ${
            sport === 'badminton'
              ? 'bg-purple-600 text-white'
              : 'bg-gray-100 text-gray-500 hover:bg-purple-100 hover:text-purple-700'
          }`}
        >
          🏸 Badminton
        </button>
        <button
          onClick={() => setSport('tennis_serve')}
          className={`text-sm font-medium px-4 py-1.5 rounded-full transition-colors ${
            sport === 'tennis_serve'
              ? 'bg-purple-600 text-white'
              : 'bg-gray-100 text-gray-500 hover:bg-purple-100 hover:text-purple-700'
          }`}
        >
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

          {/* Upload Button */}
          <label className={`mt-4 border-2 border-dashed border-purple-400 rounded-xl p-6 flex flex-col items-center transition-colors ${
            loading ? 'cursor-not-allowed opacity-60' : 'cursor-pointer hover:border-purple-200'
          }`}>
            {loading ? (
              <>
                <span className="text-3xl mb-2">⏳</span>
                <span className="text-white text-sm font-medium">Analysing...</span>
                <span className="text-purple-300 text-xs mt-1">This may take a moment</span>
              </>
            ) : (
              <>
                <span className="text-3xl mb-2">⬆️</span>
                <span className="text-white text-sm font-medium">Upload Video</span>
                <span className="text-purple-300 text-xs mt-1">MP4 · MOV · Max 200MB</span>
              </>
            )}
            <input
              type="file"
              accept="video/mp4,video/quicktime,video/webm"
              className="hidden"
              disabled={loading}
              onChange={handleFile}
            />
          </label>

          {/* Record Button */}
          {!loading && (
            <button
              onClick={openCamera}
              className="mt-3 w-full bg-purple-500 hover:bg-purple-400 text-white text-sm font-medium py-3 rounded-xl flex items-center justify-center gap-2 transition-colors"
            >
              <span>🎥</span> Record Video
            </button>
          )}
        </div>

        {error && (
          <div className="mt-3 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}
      </div>

      {/* Camera Modal */}
      {cameraOpen && (
        <div className="fixed inset-0 bg-black z-[100] flex flex-col">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="flex-1 w-full object-cover"
          />
          <div className="bg-black px-6 pt-6 pb-12 flex items-center justify-center gap-6">
            {!recording ? (
              <>
                <button
                  onClick={closeCamera}
                  className="px-5 py-2.5 rounded-full bg-gray-700 text-white text-sm"
                >
                  Cancel
                </button>
                <button
                  onClick={startRecording}
                  className="w-20 h-20 rounded-full bg-red-500 hover:bg-red-400 flex items-center justify-center shadow-lg"
                >
                  <span className="w-6 h-6 rounded-full bg-white" />
                </button>
              </>
            ) : (
              <>
                <span className="text-red-400 text-sm animate-pulse">● Recording...</span>
                <button
                  onClick={stopRecording}
                  className="w-20 h-20 rounded-full bg-red-600 hover:bg-red-500 flex items-center justify-center shadow-lg"
                >
                  <span className="w-6 h-6 rounded bg-white" />
                </button>
              </>
            )}
          </div>
        </div>
      )}

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
