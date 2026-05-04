import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactDOM from 'react-dom';

const API_BASE = process.env.REACT_APP_API_URL || '';

// Camera modal rendered via portal to escape overflow container
function CameraPortal({ videoRef, recording, onClose, onStart, onStop }) {
  return ReactDOM.createPortal(
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 99999,
        background: '#000', display: 'flex', flexDirection: 'column',
      }}
    >
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{ width: '100%', height: 'calc(100dvh - 160px)', objectFit: 'cover', flexShrink: 0 }}
      />
      <div
        style={{
          height: '160px',
          flexShrink: 0,
          background: '#000',
          borderTop: '1px solid #1e1e1e',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '40px',
          paddingBottom: 'env(safe-area-inset-bottom)',
        }}
      >
        {!recording ? (
          <>
            <button
              onClick={onClose}
              style={{
                padding: '10px 24px',
                borderRadius: '999px',
                background: 'rgba(255,255,255,0.08)',
                border: '1px solid rgba(255,255,255,0.12)',
                color: '#fff',
                fontSize: '14px',
                fontWeight: 600,
                fontFamily: 'DM Sans, sans-serif',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              onClick={onStart}
              style={{
                width: 72, height: 72,
                borderRadius: '50%',
                background: '#ef4444',
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <span style={{ width: 20, height: 20, borderRadius: '50%', background: '#fff' }} />
            </button>
          </>
        ) : (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{
                width: 10, height: 10, borderRadius: '50%',
                background: '#ef4444', animation: 'pulse 1s ease-in-out infinite',
              }} />
              <span style={{ color: '#f87171', fontSize: 14, fontWeight: 600, fontFamily: 'DM Sans, sans-serif' }}>
                Recording
              </span>
            </div>
            <button
              onClick={onStop}
              style={{
                width: 72, height: 72,
                borderRadius: '50%',
                background: '#dc2626',
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <span style={{ width: 20, height: 20, borderRadius: 4, background: '#fff' }} />
            </button>
          </>
        )}
      </div>
    </div>,
    document.body
  );
}

function Home() {
  const navigate = useNavigate();
  // step: 'sport' | 'action' | 'loading'
  const [step, setStep] = useState('sport');
  const [sport, setSport] = useState(null);
  const [recording, setRecording] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [error, setError] = useState(null);

  const videoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const uploadInputRef = useRef(null);

  useEffect(() => {
    if (cameraOpen && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [cameraOpen]);

  function selectSport(s) {
    setSport(s);
    setStep('action');
  }

  async function uploadFile(file) {
    setCameraOpen(false);
    setStep('loading');
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('sport_type', sport);
      formData.append('skill_level', 'intermediate');
      const res = await fetch(`${API_BASE}/analyse`, { method: 'POST', body: formData });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `Server error ${res.status}`);
      }
      const result = await res.json();
      navigate('/result', { state: { result, sport } });
    } catch (err) {
      setError(err.message);
      setStep('action');
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
    recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
    recorder.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: mimeType });
      streamRef.current?.getTracks().forEach(t => t.stop());
      streamRef.current = null;
      setCameraOpen(false);
      setRecording(false);
      await uploadFile(new File([blob], `recording.${ext}`, { type: mimeType }));
    };
    recorder.start();
    mediaRecorderRef.current = recorder;
    setRecording(true);
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
  }

  function closeCamera() {
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    setCameraOpen(false);
    setRecording(false);
  }

  // ── Loading screen ──────────────────────────────────────────
  if (step === 'loading') {
    return (
      <div className="min-h-screen bg-black flex flex-col items-center justify-center gap-8">
        <div className="flex flex-col items-center">
          <h1
            className="text-[44px] font-bold text-white leading-none"
            style={{ letterSpacing: '-0.03em' }}
          >
            ACE
          </h1>
          <h1
            className="text-[44px] font-bold leading-none"
            style={{ letterSpacing: '-0.03em', color: '#C8FF57' }}
          >
            VISION
          </h1>
        </div>
        <div className="flex flex-col items-center gap-3">
          <div
            className="w-10 h-10 rounded-full border-2 border-white/10 border-t-[#C8FF57]"
            style={{ animation: 'spin 1s linear infinite' }}
          />
          <p className="text-xs font-medium text-white/30 tracking-widest uppercase">Analyzing</p>
        </div>
        {error && <p className="text-sm text-red-400 px-6 text-center">{error}</p>}
      </div>
    );
  }

  // ── Sport selector ──────────────────────────────────────────
  if (step === 'sport') {
    return (
      <div className="min-h-screen bg-black flex flex-col items-center justify-center px-8">
        {/* Back to splash */}
        <button
          onClick={() => navigate('/')}
          className="absolute top-14 left-5 text-[11px] font-semibold text-white/20 uppercase tracking-widest"
        >
          Ace Vision
        </button>

        <div className="w-full flex flex-col items-center">
          <h2
            className="text-[36px] font-bold text-white text-center leading-tight mb-16 animate-fade-up-slow"
            style={{ letterSpacing: '-0.02em', animationDelay: '0.1s' }}
          >
            Ready to<br />analyze?
          </h2>

          <div className="w-full flex flex-col items-center gap-4">
            <button
              onClick={() => selectSport('badminton')}
              className="w-full max-w-[260px] py-5 rounded-2xl bg-[#111] border border-[#2a2a2a] text-white hover:bg-[#181818] hover:border-white/20 active:scale-95 transition-all animate-fade-up-slow"
              style={{ fontSize: '16px', fontWeight: 500, letterSpacing: '0.04em', animationDelay: '0.5s' }}
            >
              Badminton
            </button>
            <button
              onClick={() => selectSport('tennis_serve')}
              className="w-full max-w-[260px] py-5 rounded-2xl bg-[#111] border border-[#2a2a2a] text-white hover:bg-[#181818] hover:border-white/20 active:scale-95 transition-all animate-fade-up-slow"
              style={{ fontSize: '16px', fontWeight: 500, letterSpacing: '0.04em', animationDelay: '0.7s' }}
            >
              Tennis
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Action screen (upload / record) ────────────────────────
  return (
    <div className="min-h-screen bg-black flex flex-col">
      {/* Header */}
      <div className="px-5 pt-14 pb-6 flex items-center gap-3 animate-fade-up-slow">
        <button onClick={() => setStep('sport')} className="text-white/25 text-2xl leading-none">
          ‹
        </button>
        <span className="text-sm font-medium text-white/30" style={{ letterSpacing: '0.02em' }}>
          {sport === 'badminton' ? 'Badminton' : 'Tennis'}
        </span>
      </div>

      <div className="flex-1 flex flex-col justify-center px-6 gap-3 pb-16">
        {error && <p className="text-sm text-red-400 text-center mb-2">{error}</p>}

        {/* Upload Video */}
        <button
          onClick={() => uploadInputRef.current?.click()}
          className="w-full bg-[#C8FF57] text-black py-[22px] rounded-2xl active:opacity-80 transition-opacity animate-fade-up-slow"
          style={{ fontSize: '16px', fontWeight: 500, letterSpacing: '0.04em', animationDelay: '0.1s' }}
        >
          Upload Video
        </button>
        <input
          ref={uploadInputRef}
          type="file"
          accept="video/mp4,video/quicktime,video/webm"
          className="hidden"
          onChange={e => { const f = e.target.files[0]; if (f) uploadFile(f); }}
        />

        {/* Record Video */}
        <button
          onClick={openCamera}
          className="w-full bg-transparent border border-white/12 text-white py-[22px] rounded-2xl active:opacity-70 transition-opacity animate-fade-up-slow"
          style={{ fontSize: '16px', fontWeight: 500, letterSpacing: '0.04em', animationDelay: '0.3s' }}
        >
          Record Video
        </button>

        <p
          className="text-center text-[11px] text-white/15 mt-1 animate-fade-up-slow"
          style={{ animationDelay: '0.5s' }}
        >
          MP4 · MOV · Max 200MB
        </p>
      </div>

      {/* Camera — rendered via portal to escape overflow */}
      {cameraOpen && (
        <CameraPortal
          videoRef={videoRef}
          recording={recording}
          onClose={closeCamera}
          onStart={startRecording}
          onStop={stopRecording}
        />
      )}
    </div>
  );
}

export default Home;
