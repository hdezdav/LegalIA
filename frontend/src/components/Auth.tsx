import { useState, FormEvent } from 'react';
import { api } from '../api';
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
      setError(err.message || 'Ocurrió un error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-wrapper">
      <div className="auth-container">
        <div className="auth-logo">
          <svg className="auth-logo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2L2 7v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <h1>Legalia</h1>
        </div>

        <p className="auth-subtitle">
          Asistente jurídico basado en fuentes verificables del derecho colombiano
        </p>

        <form onSubmit={handleSubmit} className="auth-form">
          {!isLogin && (
            <div className="form-field">
              <label htmlFor="fullName">Nombre completo</label>
              <input
                id="fullName"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                disabled={loading}
                placeholder="Juan Pérez"
              />
            </div>
          )}

          <div className="form-field">
            <label htmlFor="email">Correo electrónico</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
              placeholder="correo@ejemplo.com"
              autoComplete="email"
            />
          </div>

          <div className="form-field">
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
              placeholder="Mínimo 8 caracteres"
              autoComplete={isLogin ? 'current-password' : 'new-password'}
              minLength={8}
            />
          </div>

          {error && <div className="error-banner">{error}</div>}

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Procesando...' : isLogin ? 'Iniciar sesión' : 'Crear cuenta'}
          </button>
        </form>

        <div className="auth-divider">
          <span>o</span>
        </div>

        <button
          type="button"
          onClick={() => {
            setIsLogin(!isLogin);
            setError('');
          }}
          className="btn-secondary"
          disabled={loading}
        >
          {isLogin ? '¿No tienes cuenta? Regístrate' : '¿Ya tienes cuenta? Inicia sesión'}
        </button>

        {onBackToLanding && (
          <button
            type="button"
            onClick={onBackToLanding}
            className="btn-text-back"
            style={{
              marginTop: '0.85rem',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-dim)',
              fontSize: '0.82rem',
              cursor: 'pointer',
              textDecoration: 'underline',
            }}
          >
            ← Volver a la página principal
          </button>
        )}

        <div className="auth-footer">
          Principio: NO EVIDENCE → NO ANSWER
        </div>
      </div>
    </div>
  );
}
