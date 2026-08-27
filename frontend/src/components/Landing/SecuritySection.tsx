import { CheckCircleIcon, LockIcon } from '../Icons';

export function SecuritySection() {
  const points = [
    {
      title: 'Privacidad garantizada',
      desc: 'Cumplimiento estricto de la Ley 1581 de 2012. Tus consultas y documentos están protegidos.',
    },
    {
      title: 'Cifrado de extremo a extremo',
      desc: 'Toda comunicación usa cifrado bancario. Tus datos están seguros en tránsito y en reposo.',
    },
    {
      title: 'Tus datos son tuyos',
      desc: 'Garantía contractual: tu información nunca entrena modelos ni se comparte con terceros.',
    },
    {
      title: 'Control total',
      desc: 'Elimina tu historial cuando quieras. Cada usuario opera en un entorno aislado.',
    },
  ];

  return (
    <section className="security-section" id="seguridad">
      <div className="landing-container">
        <div className="security-box">
          {/* Left Column */}
          <div>
            <div className="section-tag">Seguridad y privacidad</div>
            <h2 className="section-title" style={{ fontSize: '2.2rem' }}>
              Tu información <br />
              permanece privada
            </h2>
            <p className="section-description" style={{ marginBottom: '2rem' }}>
              Entendemos la sensibilidad del trabajo legal. Por eso Legalia opera bajo estándares estrictos de confidencialidad.
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#34c759', fontWeight: 600, fontSize: '0.875rem' }}>
              <LockIcon size={18} />
              <span>Infraestructura segura</span>
            </div>
          </div>

          {/* Right Column: Points */}
          <div className="security-points-list">
            {points.map((pt, i) => (
              <div key={i} className="security-point-item">
                <CheckCircleIcon size={20} className="sec-check-icon" />
                <div>
                  <div className="sec-point-title">{pt.title}</div>
                  <div className="sec-point-desc">{pt.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
