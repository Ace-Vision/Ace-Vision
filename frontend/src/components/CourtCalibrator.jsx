import { useState, useRef, useEffect } from 'react';

export default function CourtCalibrator({ videoFile, onConfirm, onBack }) {
  const containerRef = useRef(null);
  const videoRef = useRef(null);

  const [videoUrl, setVideoUrl] = useState(null);
  const [corners, setCorners] = useState([
    { x: 15, y: 20 },
    { x: 85, y: 20 },
    { x: 85, y: 80 },
    { x: 15, y: 80 },
  ]);
  const [dragging, setDragging] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const url = URL.createObjectURL(videoFile);
    setVideoUrl(url);
    setReady(false);
    return () => {
      URL.revokeObjectURL(url);
      setVideoUrl(null);
    };
  }, [videoFile]);

  // Global drag handlers so movement works outside the container
  useEffect(() => {
    if (dragging === null) return;

    const getPos = (e) => {
      const rect = containerRef.current.getBoundingClientRect();
      const cx = e.touches ? e.touches[0].clientX : e.clientX;
      const cy = e.touches ? e.touches[0].clientY : e.clientY;
      return {
        x: ((cx - rect.left) / rect.width) * 100,
        y: ((cy - rect.top) / rect.height) * 100,
      };
    };

    const onMove = (e) => {
      e.preventDefault();
      const pos = getPos(e);
      setCorners(prev => prev.map((c, i) => (i === dragging ? pos : c)));
    };

    const onUp = () => setDragging(null);

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    window.addEventListener('touchmove', onMove, { passive: false });
    window.addEventListener('touchend', onUp);

    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      window.removeEventListener('touchmove', onMove);
      window.removeEventListener('touchend', onUp);
    };
  }, [dragging]);

  const polyPoints = corners.map(c => `${c.x},${c.y}`).join(' ');

  return (
    <div className="min-h-screen bg-black flex flex-col">
      <div className="px-5 pt-14 pb-4 flex items-center gap-3">
        <button
          onClick={onBack}
          className="text-white/30 hover:text-white text-2xl leading-none transition-colors"
        >
          ‹
        </button>
        <span className="text-[11px] font-semibold text-white/25 uppercase tracking-widest">
          Court Setup
        </span>
      </div>

      <p className="px-5 text-sm text-white/40 mb-4">
        Drag the 4 corners to mark <span className="text-white/60">your half</span> of the court — net side at top, baseline at bottom
      </p>

      {/* overflow visible so corners can extend beyond the video edge */}
      <div
        ref={containerRef}
        className="relative mx-5"
        style={{ minHeight: 180 }}
      >
        {videoUrl && (
          <video
            key={videoUrl}
            ref={videoRef}
            src={videoUrl}
            className="w-full block rounded-2xl"
            muted
            playsInline
            preload="auto"
            onLoadedMetadata={() => {
              if (videoRef.current) videoRef.current.currentTime = 0.1;
            }}
            onSeeked={() => setReady(true)}
            onLoadedData={() => setReady(true)}
            onCanPlay={() => setReady(true)}
          />
        )}

        {!ready && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#111] rounded-2xl">
            <div
              className="w-6 h-6 rounded-full border-2 border-white/10 border-t-white/40"
              style={{ animation: 'spin 1s linear infinite' }}
            />
          </div>
        )}

        {ready && (
          <svg
            className="absolute inset-0 w-full h-full"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            style={{ overflow: 'visible' }}
          >
            <polygon
              points={polyPoints}
              fill="rgba(200,255,87,0.07)"
              stroke="rgba(200,255,87,0.5)"
              strokeWidth="0.5"
            />
            {corners.map((c, i) => (
              <g
                key={i}
                onMouseDown={(e) => { e.stopPropagation(); setDragging(i); }}
                onTouchStart={(e) => { e.stopPropagation(); setDragging(i); }}
                style={{ cursor: dragging === i ? 'grabbing' : 'grab' }}
              >
                <circle cx={c.x} cy={c.y} r={6} fill="transparent" />
                <circle
                  cx={c.x} cy={c.y} r={2.2}
                  fill="rgba(200,255,87,0.9)"
                  stroke="white"
                  strokeWidth="0.4"
                />
              </g>
            ))}
          </svg>
        )}
      </div>

      <p className="mt-3 text-[11px] text-white/20 text-center">
        Tap and drag each corner
      </p>

      <div className="px-5 mt-5 pb-10">
        <button
          onClick={() => onConfirm(corners)}
          disabled={!ready}
          className="w-full py-4 rounded-2xl text-sm font-semibold transition-all disabled:opacity-30"
          style={{ background: '#C8FF57', color: '#000' }}
        >
          Start Analysis
        </button>
      </div>
    </div>
  );
}
