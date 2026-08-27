import { ScalesIcon } from '../Icons';

interface LandingNavbarProps {
  onGoToApp: () => void;
  onLogin: () => void;
}

export function LandingNavbar({ onGoToApp, onLogin }: LandingNavbarProps) {
  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <header className="landing-navbar">
      <div className="landing-container navbar-inner">
        {/* Brand */}
        <div className="navbar-brand" onClick={onGoToApp}>
          <div className="brand-icon-box">
            <ScalesIcon size={18} />
          </div>
          <span className="brand-title">
            Legal<span>IA</span>
          </span>
          <span className="brand-colombia-tag">Colombia</span>
        </div>

        {/* Center Links */}
        <nav className="navbar-links">
          <a href="#producto" onClick={(e) => { e.preventDefault(); scrollTo('producto'); }} className="navbar-link">
            Producto
          </a>
          <a href="#especialidades" onClick={(e) => { e.preventDefault(); scrollTo('especialidades'); }} className="navbar-link">
            Especialidades
          </a>
          <a href="#seguridad" onClick={(e) => { e.preventDefault(); scrollTo('seguridad'); }} className="navbar-link">
            Seguridad
          </a>
          <a href="#precios" onClick={(e) => { e.preventDefault(); scrollTo('precios'); }} className="navbar-link">
            Precios
          </a>
          <a href="#faq" onClick={(e) => { e.preventDefault(); scrollTo('faq'); }} className="navbar-link">
            Preguntas
          </a>
        </nav>

        {/* Right CTA Actions */}
        <div className="navbar-actions">
          <button className="btn-nav-login" onClick={onLogin}>
            Iniciar Sesión
          </button>
          <button className="btn-nav-cta" onClick={onGoToApp}>
            <span>Probar Gratis</span>
            <span aria-hidden="true">→</span>
          </button>
        </div>
      </div>
    </header>
  );
}
