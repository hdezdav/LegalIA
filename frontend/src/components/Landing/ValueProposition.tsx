import { ZapIcon, ShieldCheckIcon, FileTextIcon } from '../Icons';

export function ValueProposition() {
  const pillars = [
    {
      icon: ZapIcon,
      title: 'Búsqueda precisa',
      desc: 'Encuentra artículos, sentencias y jurisprudencia clave en segundos. Búsqueda semántica que entiende el contexto de tu pregunta.',
    },
    {
      icon: FileTextIcon,
      title: 'Fuentes verificables',
      desc: 'Cada respuesta incluye las fuentes exactas: número de providencia, artículo de ley, y enlace directo al documento oficial.',
    },
    {
      icon: ShieldCheckIcon,
      title: 'Sin invenciones',
      desc: 'Si no hay evidencia en el corpus legal, no hay respuesta. Legalia no inventa jurisprudencia ni confunde artículos.',
    },
  ];

  return (
    <section className="value-prop-section" id="metodologia">
      <div className="landing-container">
        <div className="section-header-center">
          <div className="section-tag">Cómo funciona</div>
          <h2 className="section-title">
            Construido para <br />
            trabajo legal profesional
          </h2>
          <p className="section-description">
            Cada respuesta está respaldada por fuentes reales del derecho colombiano. Sin especulación, sin invenciones.
          </p>
        </div>

        <div className="pillars-grid">
          {pillars.map((pillar, i) => {
            const Icon = pillar.icon;
            return (
              <div key={i} className="pillar-card">
                <div className="pillar-icon-box">
                  <Icon size={22} />
                </div>
                <h3 className="pillar-title">{pillar.title}</h3>
                <p className="pillar-desc">{pillar.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
