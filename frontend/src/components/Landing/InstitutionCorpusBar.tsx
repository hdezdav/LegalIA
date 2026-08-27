import { LandmarkIcon, ScalesIcon, ScrollIcon, BuildingIcon, CoinsIcon, BriefcaseIcon } from '../Icons';

export function InstitutionCorpusBar() {
  const institutions = [
    { name: 'Corte Constitucional', icon: ScalesIcon },
    { name: 'Corte Suprema de Justicia', icon: LandmarkIcon },
    { name: 'Consejo de Estado', icon: ScrollIcon },
    { name: 'Rama Judicial', icon: BuildingIcon },
    { name: 'DIAN', icon: CoinsIcon },
    { name: 'Superintendencias', icon: BriefcaseIcon },
  ];

  return (
    <section className="corpus-section">
      <div className="landing-container">
        <div className="corpus-subtitle">
          Fuentes oficiales de Colombia
        </div>
        <div className="corpus-badges-grid">
          {institutions.map((inst, i) => {
            const Icon = inst.icon;
            return (
              <div key={i} className="corpus-badge-item">
                <Icon size={20} className="court-svg-icon" />
                <div>{inst.name}</div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
