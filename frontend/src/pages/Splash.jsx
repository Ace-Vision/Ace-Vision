import { useNavigate } from 'react-router-dom';

function Splash() {
  const navigate = useNavigate();

  return (
    <div
      className="min-h-screen bg-black flex flex-col items-center justify-center overflow-hidden cursor-pointer select-none relative"
      onClick={() => navigate('/home')}
    >
      {/* Animated blobs */}
      <div className="absolute inset-0 overflow-hidden">
        {/* Lime blob */}
        <div
          className="absolute w-[380px] h-[380px] rounded-full opacity-[0.18] blur-[90px] animate-blob-1"
          style={{
            background: 'radial-gradient(circle, #C8FF57 0%, transparent 70%)',
            top: '10%',
            left: '-10%',
          }}
        />
        {/* Warm amber blob */}
        <div
          className="absolute w-[320px] h-[320px] rounded-full opacity-[0.14] blur-[80px] animate-blob-2"
          style={{
            background: 'radial-gradient(circle, #FFB347 0%, transparent 70%)',
            top: '40%',
            right: '-5%',
          }}
        />
        {/* Soft green blob */}
        <div
          className="absolute w-[280px] h-[280px] rounded-full opacity-[0.12] blur-[100px] animate-blob-3"
          style={{
            background: 'radial-gradient(circle, #A8FF6E 0%, transparent 70%)',
            bottom: '5%',
            left: '20%',
          }}
        />
        {/* Subtle white center glow */}
        <div
          className="absolute w-[200px] h-[200px] rounded-full opacity-[0.04] blur-[60px]"
          style={{
            background: 'radial-gradient(circle, #ffffff 0%, transparent 70%)',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
          }}
        />
      </div>

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center">
        {/* Logo */}
        <div className="animate-fade-in" style={{ animationDelay: '0.2s' }}>
          <h1
            className="text-[52px] font-bold tracking-tight text-white leading-none"
            style={{ letterSpacing: '-0.03em' }}
          >
            ACE
          </h1>
          <h1
            className="text-[52px] font-bold tracking-tight leading-none"
            style={{ letterSpacing: '-0.03em', color: '#C8FF57' }}
          >
            VISION
          </h1>
        </div>

        {/* Tap to start */}
        <p
          className="mt-16 text-xs font-medium text-white/30 tracking-widest uppercase animate-fade-in"
          style={{ animationDelay: '1s' }}
        >
          Tap to start
        </p>
      </div>
    </div>
  );
}

export default Splash;
