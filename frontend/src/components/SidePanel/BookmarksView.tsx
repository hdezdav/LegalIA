import { BookmarkIcon } from '../Icons';

export function BookmarksView() {
  return (
    <div className="sidepanel-content">
      <div className="sidepanel-header-row">
        <h3 className="sidepanel-view-title">Marcadores Guardados</h3>
      </div>
      <div className="sidepanel-body-scroll">
        <div className="sidepanel-empty-card">
          <div className="empty-card-icon-circle">
            <BookmarkIcon size={24} />
          </div>
          <h3 className="empty-card-title">Sin marcadores</h3>
          <p className="empty-card-desc">
            Guarda respuestas clave, citas de jurisprudencia o normas importantes para consultarlas rápidamente.
          </p>
        </div>
      </div>
    </div>
  );
}
