import { ScalesIcon } from '../Icons';

interface LandingFooterProps {
  onGoToApp: () => void;
}

export function LandingFooter({ onGoToApp }: LandingFooterProps) {
  return (
    <>
      {/* Final CTA Banner */}
      <section className="cta-banner-section">
        <div className="landing-container">
          <div className="cta-banner-card">
            <h2 className="cta-banner-title">
              Respuestas jurídicas <br />
              en las que puedes confiar
            </h2>
            <p className="cta-banner-subtitle">
              Únete a los abogados que ya usan Legalia para consultas legales verificables.
            </p>
            <button className="btn-cta-banner" style={{ margin: '0 auto' }} onClick={onGoToApp}>
              <span>Comenzar gratis</span>
              <span aria-hidden="true">→</span>
            </button>
          </div>
        </div>
      </section>

      {/* Footer Bottom */}
      <footer className="landing-footer">
        <div className="landing-container">
          <div className="footer-top-row">
            <div className="navbar-brand" onClick={onGoToApp}>
              <div className="brand-icon-box">
                <ScalesIcon size={18} />
              </div>
              <span className="brand-title">
                Legal<span>ia</span>
              </span>
              <span className="brand-colombia-tag">Colombia</span>
            </div>

            <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
              <a href="#producto" className="navbar-link">Producto</a>
              <a href="#especialidades" className="navbar-link">Especialidades</a>
              <a href="#seguridad" className="navbar-link">Seguridad</a>
              <a href="#precios" className="navbar-link">Precios</a>
              <a href="#faq" className="navbar-link">FAQ</a>
            </div>
          </div>

          <div className="footer-bottom-row">
            <div>
              © 2026 Legalia. Todos los derechos reservados.
            </div>
            <div style={{ display: 'flex', gap: '1.25rem' }}>
              <span style={{ color: '#86868b' }}>Privacidad</span>
              <span style={{ color: '#86868b' }}>Términos</span>
            </div>
          </div>
        </div>
      </footer>
    </>
  );
}
