import { useState } from 'react';
import { useNavigate } from 'react-router-dom';


export default function Splash() {
  const navigate = useNavigate();

  const [tapped, setTapped] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function handleTap() {
    if (!tapped) setTapped(true);
  }

  async function handleSignIn(e) {
    e.preventDefault();
    if (!email || !password) {
      setError('Please enter your email and password.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${process.env.REACT_APP_API_URL || ''}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'Invalid email or password.');
        return;
      }
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user', JSON.stringify({ id: data.user_id, name: data.name, email: data.email }));
      localStorage.removeItem('guest');
      navigate('/home');
    } catch {
      setError('Cannot connect to server. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="min-h-screen bg-black flex flex-col items-center justify-center overflow-hidden relative select-none"
      onClick={!tapped ? handleTap : undefined}
      style={{ cursor: tapped ? 'default' : 'pointer' }}
    >
      {/* Background blobs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div
          className="absolute w-[380px] h-[380px] rounded-full opacity-[0.18] blur-[90px] animate-blob-1"
          style={{ background: 'radial-gradient(circle, #C8FF57 0%, transparent 70%)', top: '10%', left: '-10%' }}
        />
        <div
          className="absolute w-[320px] h-[320px] rounded-full opacity-[0.14] blur-[80px] animate-blob-2"
          style={{ background: 'radial-gradient(circle, #FFB347 0%, transparent 70%)', top: '40%', right: '-5%' }}
        />
        <div
          className="absolute w-[280px] h-[280px] rounded-full opacity-[0.12] blur-[100px] animate-blob-3"
          style={{ background: 'radial-gradient(circle, #A8FF6E 0%, transparent 70%)', bottom: '5%', left: '20%' }}
        />
        <div
          className="absolute w-[200px] h-[200px] rounded-full opacity-[0.04] blur-[60px]"
          style={{ background: 'radial-gradient(circle, #ffffff 0%, transparent 70%)', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }}
        />
      </div>

      {/* Logo */}
      <div
        className="relative z-10 flex flex-col items-center transition-all duration-700 ease-in-out"
        style={{ transform: tapped ? 'translateY(-160px)' : 'translateY(0px)' }}
      >
        <div className="animate-fade-in" style={{ animationDelay: '0.2s' }}>
          <h1 className="text-[52px] font-bold tracking-tight text-white leading-none" style={{ letterSpacing: '-0.03em' }}>
            ACE
          </h1>
          <h1 className="text-[52px] font-bold tracking-tight leading-none" style={{ letterSpacing: '-0.03em', color: '#C8FF57' }}>
            VISION
          </h1>
        </div>

        <p
          className="mt-16 text-xs font-medium tracking-widest uppercase animate-fade-in transition-opacity duration-300"
          style={{ animationDelay: '1s', color: 'rgba(255,255,255,0.3)', opacity: tapped ? 0 : 1 }}
        >
          Tap to start
        </p>
      </div>

      {/* Login sheet */}
      <div
        className="absolute inset-0 z-20 transition-transform duration-700 ease-in-out overflow-y-auto"
        style={{ transform: tapped ? 'translateY(0%)' : 'translateY(105%)' }}
      >
        <div
          className="min-h-full rounded-t-[32px] px-6 pt-8 pb-12 flex flex-col justify-center"
          style={{ background: '#0d0d0d', borderTop: '1px solid rgba(255,255,255,0.08)' }}
        >
          {/* Drag handle */}
          <div className="w-10 h-1 rounded-full mx-auto mb-10" style={{ background: 'rgba(255,255,255,0.15)' }} />

          {/* Heading */}
          <h2 className="text-2xl font-bold text-white mb-1">Sign in</h2>
          <p className="text-sm mb-8" style={{ color: 'rgba(255,255,255,0.4)' }}>
            Welcome back to Ace Vision
          </p>

          <form onSubmit={handleSignIn} noValidate>
            {/* Email */}
            <div className="mb-4">
              <label className="block text-xs font-medium mb-2" style={{ color: 'rgba(255,255,255,0.5)' }}>
                Email address
              </label>
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={e => { setEmail(e.target.value); setError(''); }}
                className="w-full rounded-2xl px-4 py-4 text-sm text-white outline-none transition-all duration-200"
                style={{ background: '#1a1a1a', border: '1px solid rgba(255,255,255,0.1)', caretColor: '#C8FF57' }}
                onFocus={e => (e.target.style.borderColor = '#C8FF57')}
                onBlur={e => (e.target.style.borderColor = 'rgba(255,255,255,0.1)')}
              />
            </div>

            {/* Password */}
            <div className="mb-2">
              <label className="block text-xs font-medium mb-2" style={{ color: 'rgba(255,255,255,0.5)' }}>
                Password
              </label>
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={e => { setPassword(e.target.value); setError(''); }}
                className="w-full rounded-2xl px-4 py-4 text-sm text-white outline-none transition-all duration-200"
                style={{ background: '#1a1a1a', border: '1px solid rgba(255,255,255,0.1)', caretColor: '#C8FF57' }}
                onFocus={e => (e.target.style.borderColor = '#C8FF57')}
                onBlur={e => (e.target.style.borderColor = 'rgba(255,255,255,0.1)')}
              />
            </div>

            {/* Forgot password */}
            <div className="flex justify-end mb-4">
              <button type="button" className="text-xs font-medium" style={{ color: '#C8FF57' }}>
                Forgot password?
              </button>
            </div>

            {/* Error */}
            {error && (
              <div
                className="rounded-2xl px-4 py-3 mb-4 text-xs font-medium"
                style={{ background: 'rgba(255,80,80,0.12)', border: '1px solid rgba(255,80,80,0.25)', color: '#ff6b6b' }}
              >
                {error}
              </div>
            )}

            {/* Sign in button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-2xl py-4 text-sm font-semibold text-black transition-opacity duration-200 active:opacity-80 disabled:opacity-50 mb-6"
              style={{ background: '#C8FF57' }}
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          {/* Sign up link */}
          <p className="text-center text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
            Don't have an account?{' '}
            <button
              className="font-semibold"
              style={{ color: '#C8FF57' }}
              onClick={() => navigate('/signup')}
            >
              Sign up
            </button>
          </p>

          {/* Guest */}
          <button
            onClick={() => { localStorage.setItem('guest', 'true'); navigate('/home'); }}
            className="w-full mt-5 text-xs font-medium transition-opacity active:opacity-50"
            style={{ color: 'rgba(255,255,255,0.2)' }}
          >
            Continue without signing in
          </button>
        </div>
      </div>
    </div>
  );
}
