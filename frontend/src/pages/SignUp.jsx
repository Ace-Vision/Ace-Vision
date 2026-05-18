import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const SKILL_LEVELS = ['Beginner', 'Intermediate', 'Advanced'];

export default function SignUp() {
  const navigate = useNavigate();

  const [form, setForm] = useState({ name: '', email: '', password: '', skill_level: 'Beginner' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function handleChange(e) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
    setError('');
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.name || !form.email || !form.password) {
      setError('Please fill in all fields.');
      return;
    }
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, skill_level: form.skill_level.toLowerCase() }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'Registration failed.');
        return;
      }
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user', JSON.stringify({ id: data.user_id, name: data.name, email: data.email }));
      navigate('/home');
    } catch {
      setError('Cannot connect to server. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-black flex flex-col overflow-hidden relative">
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
      </div>

      {/* Header */}
      <div className="relative z-10 flex items-center px-6 pt-14 pb-4">
        <button
          onClick={() => navigate('/')}
          className="flex items-center justify-center w-10 h-10 rounded-2xl transition-opacity active:opacity-60"
          style={{ background: '#1a1a1a', border: '1px solid rgba(255,255,255,0.1)' }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 12H5M12 5l-7 7 7 7" />
          </svg>
        </button>
        <div className="ml-4">
          <span className="text-white font-bold text-lg tracking-tight">ACE</span>
          <span className="font-bold text-lg tracking-tight ml-1" style={{ color: '#C8FF57' }}>VISION</span>
        </div>
      </div>

      {/* Form card */}
      <div className="relative z-10 flex-1 flex flex-col justify-center px-6 pb-10">
        <div
          className="rounded-3xl px-6 pt-8 pb-8"
          style={{ background: '#0d0d0d', border: '1px solid rgba(255,255,255,0.08)' }}
        >
          <h2 className="text-2xl font-bold text-white mb-1">Create account</h2>
          <p className="text-sm mb-8" style={{ color: 'rgba(255,255,255,0.4)' }}>
            Join Ace Vision and start improving
          </p>

          <form onSubmit={handleSubmit} noValidate>
            {/* Name */}
            <div className="mb-4">
              <label className="block text-xs font-medium mb-2" style={{ color: 'rgba(255,255,255,0.5)' }}>
                Full name
              </label>
              <input
                name="name"
                type="text"
                placeholder="John Doe"
                value={form.name}
                onChange={handleChange}
                className="w-full rounded-2xl px-4 py-4 text-sm text-white outline-none transition-all duration-200"
                style={{ background: '#1a1a1a', border: '1px solid rgba(255,255,255,0.1)', caretColor: '#C8FF57' }}
                onFocus={e => (e.target.style.borderColor = '#C8FF57')}
                onBlur={e => (e.target.style.borderColor = 'rgba(255,255,255,0.1)')}
              />
            </div>

            {/* Email */}
            <div className="mb-4">
              <label className="block text-xs font-medium mb-2" style={{ color: 'rgba(255,255,255,0.5)' }}>
                Email address
              </label>
              <input
                name="email"
                type="email"
                placeholder="you@example.com"
                value={form.email}
                onChange={handleChange}
                className="w-full rounded-2xl px-4 py-4 text-sm text-white outline-none transition-all duration-200"
                style={{ background: '#1a1a1a', border: '1px solid rgba(255,255,255,0.1)', caretColor: '#C8FF57' }}
                onFocus={e => (e.target.style.borderColor = '#C8FF57')}
                onBlur={e => (e.target.style.borderColor = 'rgba(255,255,255,0.1)')}
              />
            </div>

            {/* Password */}
            <div className="mb-4">
              <label className="block text-xs font-medium mb-2" style={{ color: 'rgba(255,255,255,0.5)' }}>
                Password
              </label>
              <input
                name="password"
                type="password"
                placeholder="Min. 8 characters"
                value={form.password}
                onChange={handleChange}
                className="w-full rounded-2xl px-4 py-4 text-sm text-white outline-none transition-all duration-200"
                style={{ background: '#1a1a1a', border: '1px solid rgba(255,255,255,0.1)', caretColor: '#C8FF57' }}
                onFocus={e => (e.target.style.borderColor = '#C8FF57')}
                onBlur={e => (e.target.style.borderColor = 'rgba(255,255,255,0.1)')}
              />
            </div>

            {/* Skill level */}
            <div className="mb-6">
              <label className="block text-xs font-medium mb-2" style={{ color: 'rgba(255,255,255,0.5)' }}>
                Skill level
              </label>
              <div className="flex gap-2">
                {SKILL_LEVELS.map(level => (
                  <button
                    key={level}
                    type="button"
                    onClick={() => setForm(prev => ({ ...prev, skill_level: level }))}
                    className="flex-1 rounded-2xl py-3 text-xs font-semibold transition-all duration-200"
                    style={
                      form.skill_level === level
                        ? { background: '#C8FF57', color: '#000' }
                        : { background: '#1a1a1a', color: 'rgba(255,255,255,0.5)', border: '1px solid rgba(255,255,255,0.1)' }
                    }
                  >
                    {level}
                  </button>
                ))}
              </div>
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

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-2xl py-4 text-sm font-semibold text-black transition-opacity duration-200 active:opacity-80 disabled:opacity-50"
              style={{ background: '#C8FF57' }}
            >
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          {/* Sign in link */}
          <p className="text-center text-sm mt-6" style={{ color: 'rgba(255,255,255,0.4)' }}>
            Already have an account?{' '}
            <button
              className="font-semibold"
              style={{ color: '#C8FF57' }}
              onClick={() => navigate('/')}
            >
              Sign in
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
