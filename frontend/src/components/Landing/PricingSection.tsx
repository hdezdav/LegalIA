import { useState } from 'react';
import { CheckCircleIcon } from '../Icons';

interface PricingSectionProps {
  onGoToApp: () => void;
}

export function PricingSection({ onGoToApp }: PricingSectionProps) {
  const [annual, setAnnual] = useState(true);

  return (
    <section className="pricing-section" id="precios">
      <div className="landing-container">
        <div className="section-header-center">
          <div className="section-tag">Planes</div>
          <h2 className="section-title">
            Diseñado para abogados <br />
            y despachos jurídicos
          </h2>
          <p className="section-description">
            Comienza gratis y escala cuando lo necesites.
          </p>

          {/* Monthly / Annual Toggle */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.75rem', marginTop: '1.5rem' }}>
            <span style={{ fontSize: '0.875rem', color: !annual ? '#1d1d1f' : '#86868b', fontWeight: 400 }}>
              Mensual
            </span>
            <button
              style={{
                width: '44px',
                height: '24px',
                borderRadius: '9999px',
                backgroundColor: annual ? '#06c' : '#d2d2d7',
                position: 'relative',
                transition: 'background-color 0.2s',
                padding: '2px',
              }}
              onClick={() => setAnnual(!annual)}
            >
              <div
                style={{
                  width: '20px',
                  height: '20px',
                  borderRadius: '50%',
                  backgroundColor: '#ffffff',
                  transform: annual ? 'translateX(20px)' : 'translateX(0)',
                  transition: 'transform 0.2s',
                }}
              />
            </button>
            <span style={{ fontSize: '0.875rem', color: annual ? '#1d1d1f' : '#86868b', fontWeight: 400 }}>
              Anual <span style={{ color: '#34c759', fontSize: '0.75rem', fontWeight: 600 }}>(-20%)</span>
            </span>
          </div>
        </div>

        <div className="pricing-grid">
          {/* Plan 1: Gratuito */}
          <div className="pricing-card">
            <div>
              <div className="price-tier-name">Gratuito</div>
              <p className="price-tier-desc">Para estudiantes y pruebas iniciales.</p>
              <div className="price-amount-box">
                <span className="price-currency">$</span>
                <span className="price-number">0</span>
                <span className="price-period">COP / mes</span>
              </div>
              <div className="pricing-features-list">
                <div className="feature-item">
                  <CheckCircleIcon size={16} className="feature-check" />
                  <span>10 consultas diarias</span>
                </div>
                <div className="feature-item">
                  <CheckCircleIcon size={16} className="feature-check" />
                  <span>Corte Constitucional</span>
                </div>
                <div className="feature-item">
                  <CheckCircleIcon size={16} className="feature-check" />
                  <span>8 especialidades básicas</span>
                </div>
                <div className="feature-item">
                  <CheckCircleIcon size={16} className="feature-check" />
                  <span>Historial 7 días</span>
                </div>
              </div>
            </div>
            <button className="btn-pricing-cta secondary" onClick={onGoToApp}>
              Comenzar gratis
            </button>
          </div>

          {/* Plan 2: Litigante Pro (Destacado) */}
          <div className="pricing-card featured">
            <div className="featured-badge">Más popular</div>
            <div>
              <div className="price-tier-name">Profesional</div>
              <p className="price-tier-desc">Para abogados independientes en ejercicio.</p>
              <div className="price-amount-box">
                <span className="price-currency">$</span>
                <span className="price-number">{annual ? '71.000' : '89.000'}</span>
                <span className="price-period">COP / mes</span>
              </div>
              <div className="pricing-features-list">
                <div className="feature-item">
                  <CheckCircleIcon size={16} className="feature-check" />
                  <span><strong>Consultas ilimitadas</strong></span>
                </div>
                <div className="feature-item">
                  <CheckCircleIcon size={16} className="feature-check" />
                  <span>Corpus completo</span>
                </div>
                <div className="feature-item">
                  <CheckCircleIcon size={16} className="feature-check" />
                  <span>Asistentes personalizados</span>
                </div>
                <div className="feature-item">
                  <CheckCircleIcon size={16} className="feature-check" />
                  <span>Memoria de contexto</span>
                </div>
                <div className="feature-item">
                  <CheckCircleIcon size={16} className="feature-check" />
                  <span>Plantillas de documentos</span>
                </div>
                <div className="feature-item">
                  <CheckCircleIcon size={16} className="feature-check" />
                  <span>Exportar Word / PDF</span>
                </div>
              </div>
            </div>
            <button className="btn-pricing-cta primary" onClick={onGoToApp}>
              Probar 14 días gratis
            </button>
          </div>

          {/* Plan 3: Despachos & Firmas */}
          <div className="pricing-card">
            <div>
              <div className="price-tier-name">Despachos</div>
              <p className="price-tier-desc">Para firmas y departamentos legales.</p>
              <div className="price-amount-box">
                <span className="price-currency">$</span>
                <span className="price-number">{annual ? '199.000' : '249.000'}</span>
                <span className="price-period">COP / mes</span>
              </div>
              <div className="pricing-features-list">
                <div className="feature-item">
                  <CheckCircleIcon size={16} className="feature-check" />
                  <span>Hasta 5 licencias</span>
                </div>
                <div className="feature-item">
                  <CheckCircleIcon size={16} className="feature-check" />
                  <span>Expedientes privados</span>
                </div>
                <div className="feature-item">
                  <CheckCircleIcon size={16} className="feature-check" />
                  <span>Gestión de equipos</span>
                </div>
                <div className="feature-item">
                  <CheckCircleIcon size={16} className="feature-check" />
                  <span>Facturación DIAN</span>
                </div>
                <div className="feature-item">
                  <CheckCircleIcon size={16} className="feature-check" />
                  <span>Soporte prioritario</span>
                </div>
              </div>
            </div>
            <button className="btn-pricing-cta secondary" onClick={onGoToApp}>
              Contactar
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
