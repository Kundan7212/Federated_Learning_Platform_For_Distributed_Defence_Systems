import { useState, FormEvent } from 'react';
import { Navigate } from 'react-router-dom';
import { Shield, Eye, EyeOff, Cpu, Lock, Mail, User } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

export default function Login() {
  const { isAuth, login, demoLogin, register } = useAuth();
  const [mode, setMode]         = useState<'login' | 'register'>('login');
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [recruiterLoading, setRecruiterLoading] = useState(false);
  const [username, setUsername] = useState('');
  const [showPw, setShowPw]     = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState('');

  if (isAuth) return <Navigate to="/dashboard" replace />;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        await register(email, username, password);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleRecruiterAccess() {
    setError('');
    setRecruiterLoading(true);
    try {
      await demoLogin();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Recruiter access failed');
    } finally {
      setRecruiterLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#030712] flex items-center justify-center relative overflow-hidden">

      {/* Animated background grid */}
      <div className="absolute inset-0 hex-bg opacity-40" />

      {/* Glow orb */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full bg-cyan-500/5 blur-[80px] pointer-events-none" />

      {/* Slow rotating radar sweep behind the card */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[640px] h-[640px] rounded-full radar-sweep pointer-events-none" />

      {/* Dual scanning beams with glow trail, offset for depth */}
      <div
        className="absolute left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-400/70 to-transparent pointer-events-none"
        style={{ animation: 'scan-line 5s ease-in-out infinite', boxShadow: '0 0 14px 2px rgba(34,211,238,0.45)' }}
      />
      <div
        className="absolute left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-500/30 to-transparent pointer-events-none"
        style={{ animation: 'scan-line 5s ease-in-out infinite', animationDelay: '1.4s' }}
      />

      {/* Drifting data particles */}
      {[...Array(6)].map((_, i) => (
        <div
          key={i}
          className="particle-drift absolute w-1 h-1 rounded-full bg-cyan-400/70 pointer-events-none"
          style={{
            left: `${12 + i * 14}%`,
            bottom: '8%',
            animationDelay: `${i * 0.9}s`,
            animationDuration: `${4.5 + (i % 3)}s`,
          }}
        />
      ))}

      <div className="relative z-10 w-full max-w-3xl px-4">
        {/* Header */}
        <div className="text-center mb-8 animate-fade-in">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 mb-4 glow-pulse">
            <Cpu size={32} className="text-cyan-400" />
          </div>
          <h1 className="text-lg sm:text-xl md:text-2xl font-bold text-slate-100">Federated Learning Platform for Distributed Defence Systems</h1>
          <p className="text-slate-500 text-sm mt-1 font-mono tracking-wider">PRIVACY-PRESERVING AND SECURE INTELLIGENCE</p>
        </div>

        {/* Card */}
        <div className="bg-[#0f172a] border border-[#1e293b] rounded-2xl p-8 shadow-2xl"
          style={{ boxShadow: '0 0 40px rgba(6,182,212,0.05), 0 25px 50px rgba(0,0,0,0.5)' }}
        >
          {/* Mode toggle */}
          <div className="flex rounded-lg bg-[#1e293b] p-1 mb-6">
            {(['login', 'register'] as const).map(m => (
              <button
                key={m}
                onClick={() => { setMode(m); setError(''); }}
                className={`flex-1 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
                  mode === m
                    ? 'bg-cyan-600 text-white shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {m === 'login' ? 'Sign In' : 'Register'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email */}
            <div>
              <label className="label">Email Address</label>
              <div className="relative">
                <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="email" required value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="input pl-9"
                  placeholder="you@organisation.com"
                />
              </div>
            </div>

            {/* Username (register only) */}
            {mode === 'register' && (
              <div>
                <label className="label">Username</label>
                <div className="relative">
                  <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    type="text" required value={username}
                    onChange={e => setUsername(e.target.value)}
                    className="input pl-9"
                    placeholder="Your name"
                  />
                </div>
              </div>
            )}

            {/* Password */}
            <div>
              <label className="label">Password</label>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type={showPw ? 'text' : 'password'} required value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="input pl-9 pr-10"
                  placeholder="••••••••"
                />
                <button type="button" onClick={() => setShowPw(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg px-4 py-3 text-sm">
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? (
                <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> AUTHENTICATING...</>
              ) : (
                <><Shield size={16} /> {mode === 'login' ? 'ACCESS SYSTEM' : 'CREATE ACCOUNT'}</>
              )}
            </button>
          </form>

          {/* Recruiter one-click demo access — no real credentials required */}
          {mode === 'login' && (
            <>
              <div className="flex items-center gap-3 mt-5">
                <div className="h-px flex-1 bg-[#1e293b]" />
                <span className="text-[10px] uppercase tracking-wider text-slate-600">or</span>
                <div className="h-px flex-1 bg-[#1e293b]" />
              </div>
              <button
                type="button"
                onClick={handleRecruiterAccess}
                disabled={recruiterLoading || loading}
                className="btn-secondary w-full flex items-center justify-center gap-2 mt-4 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {recruiterLoading ? (
                  <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> LOADING DEMO...</>
                ) : (
                  <><User size={16} /> Recruiter — View Live Demo</>
                )}
              </button>
              <p className="text-center text-xs text-slate-600 mt-3">
                Instant read-only-style access to the platform — no sign-up needed.
              </p>
            </>
          )}
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-slate-700 mt-4">
          Kundan Patidar · IIIT Nagpur · FL Research Platform
        </p>
      </div>
    </div>
  );
}
