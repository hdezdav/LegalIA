import { useState } from 'react';
import { ChevronDownIcon } from '../Icons';

export function FAQSection() {
  const [openIdx, setOpenIdx] = useState<number | null>(0);

  const faqs = [
    {
      q: '¿Por qué Legalia no inventa jurisprudencia?',
      a: 'Legalia solo responde con información extraída del corpus legal colombiano. Si no hay evidencia en las fuentes oficiales, no hay respuesta.',
    },
    {
      q: '¿El corpus está actualizado?',
      a: 'Sí. Incluye sentencias y normativa de la Corte Constitucional, Corte Suprema, Consejo de Estado, DIAN y otras fuentes oficiales.',
    },
    {
      q: '¿Quién es el dueño de los documentos que genero?',
      a: 'Tú. Retienes el 100% de los derechos sobre cualquier documento creado en la plataforma.',
    },
    {
      q: '¿Usan mis consultas para entrenar modelos?',
      a: 'No. Tu información nunca se usa para entrenar modelos ni se comparte con terceros. Cumplimos con la Ley 1581 de 2012.',
    },
    {
      q: '¿Emiten factura electrónica?',
      a: 'Sí. Todos los pagos generan factura electrónica válida ante la DIAN con IVA discriminado.',
    },
  ];

  const toggle = (idx: number) => {
    setOpenIdx(openIdx === idx ? null : idx);
  };

  return (
    <section className="faq-section" id="faq">
      <div className="landing-container">
        <div className="section-header-center">
          <div className="section-tag">Preguntas frecuentes</div>
          <h2 className="section-title">
            Lo que necesitas saber
          </h2>
        </div>

        <div className="faq-accordion-list">
          {faqs.map((faq, i) => {
            const isOpen = openIdx === i;
            return (
              <div key={i} className={`faq-item ${isOpen ? 'open' : ''}`}>
                <button className="faq-trigger-btn" onClick={() => toggle(i)}>
                  <span>{faq.q}</span>
                  <ChevronDownIcon size={18} className="faq-chevron" />
                </button>
                {isOpen && <div className="faq-answer-text">{faq.a}</div>}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
