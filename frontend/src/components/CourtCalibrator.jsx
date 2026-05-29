import { useState, useRef, useEffect } from 'react';

// Extra draggable zone beyond the video edge (in % of video dimensions)
const PAD = 80;

export default function CourtCalibrator({ videoFile, onConfirm, onBack }) {
  const wrapperRef = useRef(null);
  const videoRef   = useRef(null);

  const [videoUrl,   setVideoUrl]   = useState(null);
  const [isPortrait, setIsPortrait] = useState(false);
  const [corners,    setCorners]    = useState([
    { x: 15, y: 20 },
    { x: 85, y: 20 },
    { x: 85, y: 80 },
    { x: 15, y: 80 },
  ]);
  const [dragging, setDragging] = useState(null);
  const [ready,    setReady]    = useState(false);

  useEffect(() => {
    const url = URL.createObjectURL(videoFile);
    setVideoUrl(url);
    setReady(false);
    setIsPortrait(false);
    return () => { URL.revokeObjectURL(url); setVideoUrl(null); };
  }, [videoFile]);

  // Global drag/touch handlers — coords relative to wrapperRef (video div)
  useEffect(() => {
    if (dragging === null) return;

    const getPos = (e) => {
      const rect = wrapperRef.current.getBoundingClientRect();
      const cx = e.touches ? e.touches[0].clientX : e.clientX;
      const cy = e.touches ? e.touches[0].clientY : e.clientY;
      // Allow corners to go up to PAD% outside the video frame
      return {
        x: Math.max(-PAD, Math.min(100 + PAD, ((cx - rect.left)  / rect.width)  * 100)),
        y: Math.max(-PAD, Math.min(100 + PAD, ((cy - rect.top)   / rect.height) * 100)),
      };
    };

    const onMove = (e) => { e.preventDefault(); setCorners(prev => prev.map((c, i) => i === dragging ? getPos(e) : c)); };
    const onUp   = () => setDragging(null);

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup',   onUp);
    window.addEventListener('touchmove', onMove, { passive: false });
    window.addEventListener('touchend',  onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup',   onUp);
      window.removeEventListener('touchmove', onMove);
      window.removeEventListener('touchend',  onUp);
    };
  }, [dragging]);

  const onLoadedMetadata = () => {
    const v = videoRef.current;
    if (!v) return;
    setIsPortrait(v.videoHeight > v.videoWidth);
    v.currentTime = 0.1;
  };

  const onVideoReady = () => setReady(true);

  const polyPoints = corners.map(c => `${c.x},${c.y}`).join(' ');

  const videoStyle = isPortrait
    ? { display: 'block', borderRadius: 16, maxHeight: '62dvh', width: 'auto' }
    : { display: 'block', borderRadius: 16, width: '100%' };

  const wrapperStyle = {
    position: 'relative',
    display:  'inline-block',
    width:    isPortrait ? 'auto' : '100%',
    overflow: 'visible',
  };

  // SVG extends PAD% beyond the video in all directions so corner dots
  // remain interactive even when dragged outside the video frame.
  const svgStyle = {
    position: 'absolute',
    left:     `${-PAD}%`,
    top:      `${-PAD}%`,
    width:    `${100 + 2 * PAD}%`,
    height:   `${100 + 2 * PAD}%`,
    overflow: 'visible',
    pointerEvents: 'none', // only the corner <g> elements capture events
  };

  const viewBox = `${-PAD} ${-PAD} ${100 + 2 * PAD} ${100 + 2 * PAD}`;

  return (
    <div className="bg-black" style={{ position: 'fixed', inset: 0, zIndex: 100, paddingTop: 'env(safe-area-inset-top)', paddingBottom: 'env(safe-area-inset-bottom)', display: 'flex', justifyContent: 'center' }}>
      <div className="flex flex-col w-full" style={{ maxWidth: 430 }}>
      <div className="px-5 pt-14 pb-4 flex items-center gap-3 flex-shrink-0">
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

      <p className="px-5 text-sm text-white/40 mb-4 flex-shrink-0">
        Drag the 4 corners to mark <span className="text-white/60">your half</span> of the court — net side at top, baseline at bottom
      </p>

      {/* Centering flex row */}
      <div className="flex justify-center px-5 flex-1 min-h-0" style={{ overflow: 'visible' }}>
        <div ref={wrapperRef} style={wrapperStyle}>
          {videoUrl && (
            <video
              key={videoUrl}
              ref={videoRef}
              src={videoUrl}
              style={videoStyle}
              muted
              playsInline
              preload="auto"
              onLoadedMetadata={onLoadedMetadata}
              onSeeked={onVideoReady}
              onLoadedData={onVideoReady}
              onCanPlay={onVideoReady}
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
              style={svgStyle}
              viewBox={viewBox}
              preserveAspectRatio="none"
            >
              {/* Dashed border showing the extended drag zone */}
              <rect
                x={-PAD + 0.5} y={-PAD + 0.5}
                width={100 + 2 * PAD - 1} height={100 + 2 * PAD - 1}
                fill="transparent"
                stroke="rgba(255,255,255,0.07)"
                strokeWidth="0.6"
                strokeDasharray="2.5 2.5"
              />
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
                  style={{ cursor: dragging === i ? 'grabbing' : 'grab', pointerEvents: 'all' }}
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
      </div>

      <p className="mt-3 text-[11px] text-white/20 text-center flex-shrink-0">
        Corner off-screen? Drag beyond the video edge
      </p>

      <div className="px-5 mt-5 pb-10 flex-shrink-0">
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
    </div>
  );
}
