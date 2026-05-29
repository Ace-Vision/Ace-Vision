import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactDOM from 'react-dom';
import CourtCalibrator from '../components/CourtCalibrator';

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
  const preferredSport = localStorage.getItem('preferred_sport');
  const isLoggedIn = !!(localStorage.getItem('token')) && localStorage.getItem('guest') !== 'true';
  // step: 'sport' | 'mode' | 'action' | 'calibrate' | 'loading'
  const [step, setStep] = useState(preferredSport ? 'mode' : 'sport');
  const [sport, setSport] = useState(preferredSport || null);
  const [mode, setMode] = useState(null); // 'form' | 'match'
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [recording, setRecording] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [error, setError] = useState(null);
  const [pendingFile, setPendingFile] = useState(null);
  const [, setCourtCorners] = useState(null);
  const [opponentName, setOpponentName] = useState('');
  const [matchComment, setMatchComment] = useState('');
  const [finalMyScore,  setFinalMyScore]  = useState('');
  const [finalOppScore, setFinalOppScore] = useState('');
  const [progressInfo, setProgressInfo] = useState({ pct: 0, step: 'Preparing…' });
  const [elapsedSec, setElapsedSec] = useState(0);

  const videoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const uploadInputRef = useRef(null);
  const jobIdRef = useRef(null);
  const pollRef = useRef(null);
  const tickRef = useRef(null);
  const startTimeRef = useRef(null);

  // Refs so async uploadFile always reads the latest values (state would be stale in the closure)
  const opponentNameRef = useRef('');
  const matchCommentRef = useRef('');
  useEffect(() => { opponentNameRef.current = opponentName; }, [opponentName]);
  useEffect(() => { matchCommentRef.current = matchComment; }, [matchComment]);

  useEffect(() => {
    if (cameraOpen && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [cameraOpen]);

  function selectSport(s) {
    setSport(s);
    if (isLoggedIn) localStorage.setItem('preferred_sport', s);
    setStep('mode');
  }

  function changeSport(s) {
    setSport(s);
    localStorage.setItem('preferred_sport', s);
    setSettingsOpen(false);
  }

  function selectMode(m) {
    setMode(m);
    setStep('action');
  }

  function handleFileSelected(file) {
    if (mode === 'match') {
      setPendingFile(file);
      setStep('calibrate');
    } else {
      uploadFile(file);
    }
  }

  async function uploadFile(file, corners = null) {
    setCameraOpen(false);
    setStep('loading');
    setError(null);
    setProgressInfo({ pct: 0, step: 'Preparing…' });
    setElapsedSec(0);

    const jobId = `job_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    jobIdRef.current = jobId;
    startTimeRef.current = Date.now();

    if (mode === 'match') {
      pollRef.current = setInterval(async () => {
        try {
          const r = await fetch(`${API_BASE}/progress/${jobId}`);
          if (r.ok) setProgressInfo(await r.json());
        } catch {}
      }, 700);
      tickRef.current = setInterval(() => {
        setElapsedSec(Math.floor((Date.now() - startTimeRef.current) / 1000));
      }, 1000);
    }

    try {
      const formData = new FormData();
      formData.append('file', file);

      let endpoint, dest;
      if (mode === 'match') {
        endpoint = '/analyse_movement';
        dest     = '/movement-result';
        formData.append('sport_type', sport);
        formData.append('job_id', jobId);
        if (corners) formData.append('court_corners', JSON.stringify(corners));
        if (finalMyScore !== '' && finalOppScore !== '') {
          formData.append('final_my_score',  finalMyScore);
          formData.append('final_opp_score', finalOppScore);
        }
      } else {
        endpoint = '/analyse';
        dest     = '/result';
        formData.append('sport_type', sport);
        formData.append('skill_level', 'intermediate');
      }

      const res = await fetch(`${API_BASE}${endpoint}`, { method: 'POST', body: formData });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `Server error ${res.status}`);
      }
      const result = await res.json();

      if (mode === 'match') {
        const token = localStorage.getItem('token');
        if (token) {
          fetch(`${API_BASE}/match_sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({
              session_id:    result.session_id,
              sport_type:    sport,
              opponent_name: opponentNameRef.current || null,
              match_comment: matchCommentRef.current || null,
              rallies:       result.rallies || [],
              rally_summary: result.rally_summary || {},
              phase_analysis: result.phase_analysis || null,
            }),
          }).then(r => { if (!r.ok) console.warn('[AceVision] match save failed', r.status); })
            .catch(e => console.warn('[AceVision] match save error', e));
        }
      }

      navigate(dest, { state: { result, sport, mode, file, opponentName: opponentNameRef.current, matchComment: matchCommentRef.current } });
    } catch (err) {
      setError(err.message);
      setStep('action');
    } finally {
      clearInterval(pollRef.current);
      clearInterval(tickRef.current);
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
      handleFileSelected(new File([blob], `recording.${ext}`, { type: mimeType }));
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

  // ── Court calibration ───────────────────────────────────────
  if (step === 'calibrate' && pendingFile) {
    return (
      <CourtCalibrator
        videoFile={pendingFile}
        onConfirm={(corners) => {
          setCourtCorners(corners);
          uploadFile(pendingFile, corners);
        }}
        onBack={() => { setPendingFile(null); setStep('action'); }}
      />
    );
  }

  // ── Loading screen ──────────────────────────────────────────
  if (step === 'loading') {
    return (
      <div className="min-h-screen bg-black flex flex-col items-center justify-center gap-8 px-6">
        <div className="flex flex-col items-center">
          <h1 className="text-[44px] font-bold text-white leading-none" style={{ letterSpacing: '-0.03em' }}>ACE</h1>
          <h1 className="text-[44px] font-bold leading-none" style={{ letterSpacing: '-0.03em', color: '#C8FF57' }}>VISION</h1>
        </div>

        {mode === 'match' && (
          <div className="w-full max-w-sm space-y-3">
            <p className="text-[10px] font-semibold text-white/20 uppercase tracking-widest text-center">
              While we analyze · fill these in
            </p>
            <input
              type="text"
              placeholder="Opponent's name (optional)"
              value={opponentName}
              onChange={e => setOpponentName(e.target.value)}
              className="w-full px-4 py-3 rounded-2xl text-sm text-white placeholder:text-white/20 outline-none"
              style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}
            />
            <textarea
              placeholder="How did the match feel? Any thoughts… (optional)"
              value={matchComment}
              onChange={e => setMatchComment(e.target.value)}
              rows={3}
              className="w-full px-4 py-3 rounded-2xl text-sm text-white placeholder:text-white/20 outline-none resize-none"
              style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}
            />
            <div>
              <p className="text-[10px] font-semibold text-white/20 uppercase tracking-widest mb-2 px-1">
                Final score (optional — improves rally detection)
              </p>
              <div className="flex items-center gap-3">
                <input
                  type="number" min="0" max="30"
                  placeholder="You"
                  value={finalMyScore}
                  onChange={e => setFinalMyScore(e.target.value)}
                  className="flex-1 px-4 py-3 rounded-2xl text-sm text-white placeholder:text-white/20 outline-none text-center tabular-nums"
                  style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}
                />
                <span className="text-white/20 text-lg font-light">—</span>
                <input
                  type="number" min="0" max="30"
                  placeholder="Them"
                  value={finalOppScore}
                  onChange={e => setFinalOppScore(e.target.value)}
                  className="flex-1 px-4 py-3 rounded-2xl text-sm text-white placeholder:text-white/20 outline-none text-center tabular-nums"
                  style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}
                />
              </div>
            </div>
          </div>
        )}

        {mode === 'match' && (
          <div className="w-full max-w-sm space-y-2">
            <div className="flex justify-between items-center gap-2">
              <span className="text-xs text-white/40 truncate">{progressInfo.step}</span>
              <span className="text-xs font-mono text-white/60 shrink-0 tabular-nums">{progressInfo.pct}%</span>
            </div>
            <div className="w-full h-[3px] bg-white/10 rounded-full overflow-hidden">
              <div
                className="h-full bg-[#C8FF57] rounded-full"
                style={{ width: `${progressInfo.pct}%`, transition: 'width 0.5s ease-out' }}
              />
            </div>
            <p className="text-right text-[11px] text-white/20 font-mono tabular-nums">{elapsedSec}s</p>
          </div>
        )}

        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-full border-2 border-white/10 border-t-[#C8FF57]" style={{ animation: 'spin 1s linear infinite' }} />
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

  // ── Mode selector ───────────────────────────────────────────
  if (step === 'mode') {
    const isGuest = localStorage.getItem('guest') === 'true';
    return (
      <div className="min-h-screen bg-black flex flex-col items-center justify-center px-8">
        <div className="px-5 pt-14 pb-6 flex items-center justify-between absolute top-0 left-0 right-0 animate-fade-up-slow">
          <div className="flex items-center gap-3">
            {!isLoggedIn && (
              <button onClick={() => setStep('sport')} className="text-white/25 text-2xl leading-none">
                ‹
              </button>
            )}
            <span className="text-sm font-medium text-white/30" style={{ letterSpacing: '0.02em' }}>
              {sport === 'badminton' ? 'Badminton' : 'Tennis'}
            </span>
          </div>
          {isLoggedIn && (
            <button
              onClick={() => setSettingsOpen(true)}
              className="text-white/25 hover:text-white/50 transition-colors p-1"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3"/>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
              </svg>
            </button>
          )}
        </div>

        <div className="w-full flex flex-col items-center">
          <h2
            className="text-[36px] font-bold text-white text-center leading-tight mb-4 animate-fade-up-slow"
            style={{ letterSpacing: '-0.02em', animationDelay: '0.1s' }}
          >
            What are<br />you filming?
          </h2>
          <p className="text-sm text-white/25 text-center mb-14 animate-fade-up-slow" style={{ animationDelay: '0.2s' }}>
            Choose how you want to analyze
          </p>

          <div className="w-full flex flex-col items-center gap-4">
            {/* Form check */}
            <button
              onClick={() => selectMode('form')}
              className="w-full max-w-[300px] py-6 px-6 rounded-2xl bg-[#111] border border-[#2a2a2a] text-left hover:bg-[#181818] hover:border-white/20 active:scale-95 transition-all animate-fade-up-slow"
              style={{ animationDelay: '0.4s' }}
            >
              <div className="text-white font-semibold mb-1" style={{ fontSize: '16px', letterSpacing: '0.02em' }}>
                Solo Swing
              </div>
              <div className="text-white/30 text-xs leading-relaxed">
                Shadow swing or practice drill.<br />Analyzes your form in detail.
              </div>
            </button>

            {/* Match analysis */}
            <button
              onClick={() => selectMode('match')}
              className="w-full max-w-[300px] py-6 px-6 rounded-2xl bg-[#111] border border-[#2a2a2a] text-left hover:bg-[#181818] hover:border-white/20 active:scale-95 transition-all animate-fade-up-slow"
              style={{ animationDelay: '0.6s' }}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="text-white font-semibold" style={{ fontSize: '16px', letterSpacing: '0.02em' }}>
                  Match
                </span>
                <span
                  className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                  style={{ background: 'rgba(200,255,87,0.12)', color: '#C8FF57', letterSpacing: '0.06em' }}
                >
                  BETA
                </span>
              </div>
              <div className="text-white/30 text-xs leading-relaxed">
                Up to 5 min match footage.<br />Detects shots and finds trends.
              </div>
            </button>

            {/* Training — only for logged-in users */}
            {!isGuest && (
              <button
                onClick={() => navigate('/insights')}
                className="w-full max-w-[300px] py-6 px-6 rounded-2xl bg-[#111] border border-[#2a2a2a] text-left hover:bg-[#181818] hover:border-white/20 active:scale-95 transition-all animate-fade-up-slow"
                style={{ animationDelay: '0.75s' }}
              >
                <div className="text-white font-semibold mb-1" style={{ fontSize: '16px', letterSpacing: '0.02em' }}>
                  Insights
                </div>
                <div className="text-white/30 text-xs leading-relaxed">
                  Trends, history and opponent notes.
                </div>
              </button>
            )}

          </div>
        </div>

        {/* Settings sheet */}
        {settingsOpen && (
          <div
            className="fixed inset-0 z-50 flex flex-col justify-end"
            style={{ background: 'rgba(0,0,0,0.65)' }}
            onClick={() => setSettingsOpen(false)}
          >
            <div
              className="rounded-t-3xl px-6 pt-5 pb-12"
              style={{ background: '#111', border: '1px solid rgba(255,255,255,0.08)' }}
              onClick={e => e.stopPropagation()}
            >
              <div className="w-10 h-1 rounded-full bg-white/20 mx-auto mb-6" />
              <p className="text-[10px] font-bold text-white/25 uppercase tracking-widest mb-4">
                Your sport
              </p>
              <div className="flex gap-3">
                {[{ value: 'badminton', label: 'Badminton' }, { value: 'tennis_serve', label: 'Tennis' }].map(({ value, label }) => (
                  <button
                    key={value}
                    onClick={() => changeSport(value)}
                    className="flex-1 py-4 rounded-2xl text-sm font-semibold transition-all active:scale-95"
                    style={
                      sport === value
                        ? { background: '#C8FF57', color: '#000' }
                        : { background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.4)', border: '1px solid rgba(255,255,255,0.08)' }
                    }
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

      </div>
    );
  }

  // ── Action screen (upload / record) ────────────────────────
  return (
    <div className="min-h-screen bg-black flex flex-col">
      {/* Header */}
      <div className="px-5 pt-14 pb-6 flex items-center gap-3 animate-fade-up-slow">
        <button onClick={() => setStep('mode')} className="text-white/25 text-2xl leading-none">
          ‹
        </button>
        {mode !== 'score' && (
          <>
            <span className="text-sm font-medium text-white/30" style={{ letterSpacing: '0.02em' }}>
              {sport === 'badminton' ? 'Badminton' : 'Tennis'}
            </span>
            <span className="text-white/15 text-sm">·</span>
          </>
        )}
        <span className="text-sm font-medium text-white/20" style={{ letterSpacing: '0.02em' }}>
          {mode === 'form' ? 'Solo Swing' : 'Match'}
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
          onChange={e => { const f = e.target.files[0]; if (f) handleFileSelected(f); }}
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
