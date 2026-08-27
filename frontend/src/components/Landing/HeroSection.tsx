import { useState } from 'react';
import { ShieldCheckIcon, SparklesIcon, FileTextIcon } from '../Icons';

interface HeroSectionProps {
  onGoToApp: () => void;
}

interface SimQuery {
  id: string;
  tabTitle: string;
  question: string;
  latency: string;
  candidates: number;
  score: string;
  response: string;
  citations: Array<{
    num: number;
    title: string;
    meta: string;
    quote: string;
  }>;
}

const SIMULATION_SCENARIOS: SimQuery[] = [
  {
    id: 'tutela',
    tabTitle: 'Tutela Providencia Judicial',
    question: '¿Cuáles son los requisitos de procedibilidad de la acción de tutela contra sentencias judiciales en Colombia?',
    latency: '380ms',
    candidates: 28,
    score: '0.96',
    response: `Conforme a la doctrina constitucional reiterada en la Sentencia C-590 de 2005 y SU-573 de 2019, la procedibilidad exige dos niveles concurrentes:\n\n1. **Requisitos Generales:** Relevancia constitucional, agotamiento de recursos ordinarios y extraordinarios (subsidiariedad), inmediatez en la presentación, legitimación y que la irregularidad procesal sea determinante.\n2. **Defectos Específicos:** Defecto orgánico, sustantivo, fáctico, procedimental absoluto, error inducido o desconocimiento del precedente constitucional vinculante.`,
    citations: [
      {
        num: 1,
        title: 'Corte Constitucional · Sentencia C-590 de 2005',
        meta: 'M.P. Jaime Córdoba Triviño · Jurisprudencia Vinculante',
        quote: 'La tutela contra providencias judiciales es excepcional y procede únicamente cuando se acredite el cumplimiento de la totalidad de los requisitos generales y al menos una causal especial o defecto sustantivo.',
      },
      {
        num: 2,
        title: 'Corte Constitucional · Sentencia SU-573 de 2019',
        meta: 'Sala Plena · Unificación Jurisprudencial',
        quote: 'El desconocimiento del precedente judicial de las altas cortes constituye defecto sustantivo violatorio del derecho fundamental al debido proceso (Art. 29 CP).',
      },
    ],
  },
  {
    id: 'cgp',
    tabTitle: 'Términos CGP (Art. 369)',
    question: '¿Cuál es el término legal para contestar la demanda en un proceso declarativo verbal según el CGP?',
    latency: '290ms',
    candidates: 19,
    score: '0.99',
    response: `De acuerdo con el **Artículo 369 del Código General del Proceso (Ley 1564 de 2012)**:\n\n• El término de traslado para contestar la demanda en el proceso declarativo verbal es de **veinte (20) días**, computados a partir del día siguiente a la notificación del auto admisorio.\n• Durante este mismo término procesal, el demandado podrá proponer excepciones previas, excepciones de mérito y formular demanda de reconvención.`,
    citations: [
      {
        num: 1,
        title: 'Código General del Proceso · Artículo 369',
        meta: 'Ley 1564 de 2012 · Régimen Procesal Civil',
        quote: 'Del auto admisorio de la demanda se correrá traslado al demandado por el término de veinte (20) días para que ejerza su derecho de contradicción y aporte las pruebas que pretenda hacer valer.',
      },
    ],
  },
  {
    id: 'laboral',
    tabTitle: 'Indemnización CST (Art. 64)',
    question: '¿Cómo se liquida la indemnización por despido sin justa causa para salarios superiores a 10 SMLMV en contrato indefinido?',
    latency: '310ms',
    candidates: 24,
    score: '0.97',
    response: `Según el **Artículo 64 del Código Sustantivo del Trabajo** (modificado por el Art. 28 de la Ley 789 de 2002), cuando el trabajador devenga diez (10) o más salarios mínimos legales mensuales vigentes:\n\n1. **Primer año de servicio continuo:** Veinte (20) días de salario.\n2. **Años subsiguientes o fracción:** Quince (15) días adicionales de salario por cada año completo de servicio, liquidado proporcionalmente por fracción de año.`,
    citations: [
      {
        num: 1,
        title: 'Código Sustantivo del Trabajo · Artículo 64, Numeral 4, Literal b',
        meta: 'Ley 789 de 2002 · Régimen Laboral Colombiano',
        quote: 'Para trabajadores que devenguen un salario igual o superior a diez (10) salarios mínimos legales mensuales: veinte (20) días de salario si tuvieren un tiempo de servicio no mayor de un (1) año; y quince (15) días adicionales por cada uno de los años de servicio subsiguientes.',
      },
    ],
  },
];

export function HeroSection({ onGoToApp }: HeroSectionProps) {
  const [activeScenarioId, setActiveScenarioId] = useState('tutela');
  const [activeCitationIdx, setActiveCitationIdx] = useState(0);

  const scenario =
    SIMULATION_SCENARIOS.find((s) => s.id === activeScenarioId) ||
    SIMULATION_SCENARIOS[0];

  const activeCitation = scenario.citations[activeCitationIdx] || scenario.citations[0];

  return (
    <section className="landing-hero" id="producto">
      <div className="landing-container">
        {/* Verification Pill Badge */}
        <div className="hero-trust-badge">
          <span className="badge-dot" />
          <span>Respaldado por fuentes oficiales · Sin invenciones</span>
        </div>

        {/* Headline */}
        <h1 className="hero-headline">
          Respuestas jurídicas <br />
          en las que <span className="hero-headline-gradient">puedes confiar</span>
        </h1>

        {/* Subtitle */}
        <p className="hero-subheadline">
          Análisis legal respaldado por fuentes verificables del derecho colombiano. Cada respuesta cita exactamente de dónde viene.
        </p>

        {/* Action Buttons */}
        <div className="hero-cta-group">
          <button className="btn-hero-primary" onClick={onGoToApp}>
            <SparklesIcon size={18} />
            <span>Probar Legalia Gratis</span>
          </button>
          <a
            href="#metodologia"
            onClick={(e) => {
              e.preventDefault();
              document.getElementById('metodologia')?.scrollIntoView({ behavior: 'smooth' });
            }}
            className="btn-hero-secondary"
          >
            <span>Ver cómo funciona</span>
          </a>
        </div>

        {/* Interactive Legal Workspace Simulator */}
        <div className="simulator-window">
          {/* Window Top Bar */}
          <div className="simulator-titlebar">
            <div className="window-dots">
              <div className="window-dot red" />
              <div className="window-dot yellow" />
              <div className="window-dot green" />
            </div>
            <div className="simulator-status-badge">
              <ShieldCheckIcon size={14} />
              <span>Verificado · Sin evidencia, sin respuesta</span>
            </div>
          </div>

          {/* Scenario Tab Selector */}
          <div className="simulator-tabs-bar">
            {SIMULATION_SCENARIOS.map((sim) => (
              <button
                key={sim.id}
                className={`sim-tab-btn ${sim.id === activeScenarioId ? 'active' : ''}`}
                onClick={() => {
                  setActiveScenarioId(sim.id);
                  setActiveCitationIdx(0);
                }}
              >
                {sim.tabTitle}
              </button>
            ))}
          </div>

          {/* Body: Chat Response + Real-time Citation Drawer */}
          <div className="simulator-body">
            {/* Left: Chat Simulation */}
            <div className="simulator-chat-pane">
              <div className="sim-query-box">
                <div className="sim-query-label">Consulta jurídica</div>
                <div className="sim-query-text">{scenario.question}</div>
              </div>

              <div className="sim-response-box">
                <div className="sim-telemetry-row">
                  <span className="sim-telemetry-tag">⚡ Latencia: {scenario.latency}</span>
                  <span className="sim-telemetry-tag">🔍 RAG: {scenario.candidates} fragmentos</span>
                  <span className="sim-telemetry-tag">🎯 Relevancia: {scenario.score}</span>
                </div>
                <div className="sim-response-text">
                  {scenario.response.split('\n\n').map((para, i) => (
                    <p key={i} style={{ marginBottom: '0.75rem' }}>
                      {para}
                      {i === 0 && (
                        <button
                          className="citation-pill-btn"
                          onClick={() => setActiveCitationIdx(0)}
                          title="Ver fuente 1"
                        >
                          [1]
                        </button>
                      )}
                      {i === 1 && scenario.citations.length > 1 && (
                        <button
                          className="citation-pill-btn"
                          onClick={() => setActiveCitationIdx(1)}
                          title="Ver fuente 2"
                        >
                          [2]
                        </button>
                      )}
                    </p>
                  ))}
                </div>
              </div>
            </div>

            {/* Right: Live Source Evidence Drawer */}
            <div className="simulator-citation-drawer">
              <div className="citation-drawer-header">
                <FileTextIcon size={14} />
                <span>Fuente Extraída [{activeCitation.num}]</span>
              </div>
              <div className="citation-source-card">
                <div className="source-court-title">{activeCitation.title}</div>
                <div className="source-meta-tag">{activeCitation.meta}</div>
                <div className="source-verbatim-quote">
                  "{activeCitation.quote}"
                </div>
              </div>
              <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: 'auto' }}>
                ✓ Fragmento cotejado contra la publicación oficial de la Rama Judicial.
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
