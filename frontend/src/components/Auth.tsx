import { useState, FormEvent } from 'react';
import { api } from '../api';
import { ScalesIcon } from './Icons';
import './Auth.css';

interface AuthProps {
  onLogin: () => void;
  onBackToLanding?: () => void;
}

export function Auth({ onLogin, onBackToLanding }: AuthProps) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        await api.login(email, password);
      } else {
        await api.register(email, password, fullName);
        await api.login(email, password);
      }
      onLogin();
    } catch (err: any) {
      setError(err.message || 'Ocurrió un error al procesar la solicitud');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleMode = () => {
    setIsLogin(!isLogin);
    setError('');
  };

  return (
    <div className="auth-viewport">
      <div className={`auth-card ${isLogin ? 'mode-login' : 'mode-register'}`}>
        
        {/* SVG Background Wave (Blue to White) */}
        <div className="auth-curve-bg" aria-hidden="true">
          <svg viewBox="0 0 1000 600" preserveAspectRatio="none" className="auth-wave-svg">
            <defs>
              <linearGradient id="authBlueGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#3b82f6" />
                <stop offset="50%" stopColor="#2563eb" />
                <stop offset="100%" stopColor="#1d4ed8" />
              </linearGradient>
            </defs>
            <path
              d="M 0,0 L 515,0 C 485,140 375,250 425,385 C 455,470 365,545 295,600 L 0,600 Z"
              fill="url(#authBlueGradient)"
            />
          </svg>
        </div>

        {/* Left Side: Welcome & Toggle Action Panel */}
        <div className="auth-side-panel">
          <div className="auth-brand-badge">
            <ScalesIcon size={22} className="auth-badge-icon" />
            <span className="auth-badge-name">Legalia</span>
          </div>

          <div className="auth-panel-content" key={`side-content-${isLogin ? 'login' : 'signup'}`}>
            <h2 className="auth-panel-title">
              {isLogin ? '¿Eres nuevo aquí?' : '¿Ya tienes cuenta?'}
            </h2>
            <p className="auth-panel-desc">
              {isLogin
                ? 'Únete a LegalIA y consulta jurisprudencia y normativa colombiana con inteligencia artificial certificada.'
                : '¡Bienvenido de nuevo! Inicia sesión para continuar consultando fuentes jurídicas oficiales y minutas.'}
            </p>
            <button
              type="button"
              onClick={handleToggleMode}
              className="btn-auth-outline"
              disabled={loading}
            >
              {isLogin ? 'CREAR CUENTA' : 'INICIAR SESIÓN'}
            </button>
          </div>

          <div className="auth-panel-footer">
            <span>Inteligencia Artificial Jurídica · Colombia</span>
          </div>
        </div>

        {/* Right Side: Form Panel */}
        <div className="auth-main-panel">
          <div className="auth-form-container">
            <h1 className="auth-title" key={`title-${isLogin ? 'login' : 'signup'}`}>
              {isLogin ? 'Iniciar sesión' : 'Crear cuenta'}
            </h1>

            <form onSubmit={handleSubmit} className="auth-form-body">
              {!isLogin && (
                <div className="pill-input-group field-animated">
                  <span className="pill-input-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" strokeLinecap="round" strokeLinejoin="round" />
                      <circle cx="12" cy="7" r="4" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </span>
                  <input
                    id="fullName"
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                    disabled={loading}
                    placeholder="Nombre completo"
                    autoComplete="name"
                  />
                </div>
              )}

              <div className="pill-input-group">
                <span className="pill-input-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" strokeLinecap="round" strokeLinejoin="round" />
                    <polyline points="22,6 12,13 2,6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={loading}
                  placeholder="Correo electrónico"
                  autoComplete="email"
                />
              </div>

              <div className="pill-input-group">
                <span className="pill-input-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={loading}
                  placeholder="Contraseña"
                  autoComplete={isLogin ? 'current-password' : 'new-password'}
                  minLength={8}
                />
              </div>

              {error && (
                <div className="auth-error-pill" role="alert">
                  <svg viewBox="0 0 20 20" fill="currentColor" className="error-icon">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  <span>{error}</span>
                </div>
              )}

              <div className="auth-action-row">
                <button
                  type="submit"
                  className="btn-auth-solid"
                  disabled={loading}
                >
                  {loading ? (
                    <span className="btn-spinner" />
                  ) : (
                    <span key={`btn-${isLogin ? 'login' : 'signup'}`} className="btn-text-animated">
                      {isLogin ? 'INICIAR SESIÓN' : 'CREAR CUENTA'}
                    </span>
                  )}
                </button>
              </div>
            </form>

            <div className="auth-social-section">
              <p className="auth-social-label">O continúa con tus cuentas profesionales</p>
              <div className="auth-social-buttons">
                {/* Google */}
                <button
                  type="button"
                  className="btn-social"
                  aria-label="Acceder con Google"
                  title="Google"
                  onClick={() => setError('Autenticación con Google disponible próximamente')}
                >
                  <svg viewBox="0 0 24 24" width="18" height="18">
                    <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z"/>
                    <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.26v3.15C3.25 21.37 7.33 24 12 24z"/>
                    <path fill="#FBBC05" d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.26C.46 8.16 0 9.97 0 12s.46 3.84 1.26 5.42l4.02-3.15z"/>
                    <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.25 2.63 1.26 6.58l4.02 3.15c.95-2.83 3.6-4.98 6.72-4.98z"/>
                  </svg>
                </button>

                {/* Facebook */}
                <button
                  type="button"
                  className="btn-social"
                  aria-label="Acceder con Facebook"
                  title="Facebook"
                  onClick={() => setError('Autenticación con Facebook disponible próximamente')}
                >
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="#1877F2">
                    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                  </svg>
                </button>

                {/* Twitter / X */}
                <button
                  type="button"
                  className="btn-social"
                  aria-label="Acceder con Twitter"
                  title="Twitter"
                  onClick={() => setError('Autenticación con Twitter disponible próximamente')}
                >
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="#1DA1F2">
                    <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.936 9.936 0 0024 4.59z"/>
                  </svg>
                </button>

                {/* LinkedIn */}
                <button
                  type="button"
                  className="btn-social"
                  aria-label="Acceder con LinkedIn"
                  title="LinkedIn"
                  onClick={() => setError('Autenticación con LinkedIn disponible próximamente')}
                >
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="#0A66C2">
                    <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 10.9v8.37H9.25V10.9H6.46M7.86 6.3a1.65 1.65 0 1 0 0 3.3 1.65 1.65 0 0 0 0-3.3z"/>
                  </svg>
                </button>
              </div>
            </div>

            {/* Mobile switch helper */}
            <div className="auth-mobile-switch">
              <span>{isLogin ? "¿No tienes una cuenta?" : '¿Ya tienes una cuenta?'}</span>
              <button
                type="button"
                onClick={handleToggleMode}
                className="btn-mobile-toggle"
              >
                {isLogin ? 'Crear cuenta' : 'Iniciar sesión'}
              </button>
            </div>

            {onBackToLanding && (
              <button
                type="button"
                onClick={onBackToLanding}
                className="btn-back-landing"
              >
                ← Volver a la página principal
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
