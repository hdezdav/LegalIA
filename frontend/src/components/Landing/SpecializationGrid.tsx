import { SPECIALIZATIONS } from '../../constants';
import { SpecializationIcon } from '../SpecializationMenu';

export function SpecializationGrid() {
  const specDetails: Record<string, { count: string; desc: string }> = {
    general: {
      count: '1.4M+ Docs',
      desc: 'Respuestas transversales, redacción de conceptos y derechos de petición.',
    },
    constitucional: {
      count: '320K+ Sentencias',
      desc: 'Sentencias C, T y SU, tutela contra providencias y control constitucional.',
    },
    laboral: {
      count: '210K+ Providencias',
      desc: 'CST, Ley 789/02, pensiones Ley 100/93 y casación laboral de la CSJ.',
    },
    civil: {
      count: '260K+ Documentos',
      desc: 'Código General del Proceso (Ley 1564/12), contratos y responsabilidad civil.',
    },
    penal: {
      count: '180K+ Autos y Fallos',
      desc: 'Código Penal (Ley 599/00), sistema acusatorio (Ley 906/04) y casación penal.',
    },
    administrativo: {
      count: '190K+ Sentencias',
      desc: 'CPACA (Ley 1437/11), Consejo de Estado y régimen de contratación Ley 80/93.',
    },
    comercial: {
      count: '140K+ Conceptos',
      desc: 'Código de Comercio, régimen de SAS (Ley 1258/08) y Supersociedades.',
    },
    tributario: {
      count: '120K+ Resoluciones',
      desc: 'Estatuto Tributario, conceptos vinculantes DIAN y régimen sancionatorio.',
    },
  };

  return (
    <section className="specs-section" id="especialidades">
      <div className="landing-container">
        <div className="section-header-center" style={{ marginBottom: '3rem' }}>
          <div className="section-tag">Especialidades del Derecho</div>
          <h2 className="section-title">
            Cobertura integral de todas las ramas <br />
            del ordenamiento jurídico colombiano
          </h2>
          <p className="section-description">
            Cada área cuenta con agentes afinados con la doctrina y jurisprudencia especializada de su respectiva sala o tribunal.
          </p>
        </div>

        <div className="specs-grid">
          {SPECIALIZATIONS.map((spec) => {
            const detail = specDetails[spec.id] || {
              count: '100K+ Docs',
              desc: spec.description,
            };

            return (
              <div key={spec.id} className="spec-card-landing">
                <div className="spec-card-top">
                  <div className="spec-icon-round" style={{ color: spec.color }}>
                    <SpecializationIcon id={spec.id} size={18} />
                  </div>
                  <span className="spec-corpus-count">{detail.count}</span>
                </div>
                <h3 className="spec-card-name">{spec.name}</h3>
                <p className="spec-card-desc">{detail.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
