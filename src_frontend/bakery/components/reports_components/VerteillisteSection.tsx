import React from 'react';
import { SectionToggle } from './SectionToggle';
import { ActionButtons } from './ActionButtons';
import '../../styles/bakery_styles.css';

interface LocationTotals {
  totalBaked: number;
  totalOrdered: number;
  totalExtra: number;
}

interface VerteillisteSectionProps {
  isOpen: boolean;
  onToggle: () => void;
  isLoading: boolean;
  hasPreview: boolean;
  hasSolverResults: boolean;
  locationBreads: Record<string, Record<string, { baked: number; ordered: number; extra: number }>>;
  locationTotals: Record<string, LocationTotals>;
  distBreadNames: string[];
  pdfUrl: string;
  onEmail: () => void;
}

export const VerteillisteSection: React.FC<VerteillisteSectionProps> = ({
  isOpen, onToggle, isLoading, hasPreview, hasSolverResults,
  locationBreads, locationTotals, distBreadNames, pdfUrl, onEmail,
}) => {
  const subtitle = hasPreview
    ? 'Brote pro Abholstation (Vorschau)'
    : hasSolverResults
      ? 'Brote pro Abholstation (lt. Backplan)'
      : 'Brote pro Abholstation (lt. Mitgliederbestellungen)';

  return (
    <div className="mb-3">
      <SectionToggle isOpen={isOpen} onToggle={onToggle} title="Verteilliste" icon="warehouse" />
      <p className="text-muted small mb-2">{subtitle}</p>

      {isOpen && (
        <>
          {isLoading ? (
            <div className="text-center py-3">
              <div className="spinner-border spinner-border-sm spinner-bakery-primary" />
              <p className="mt-1 text-muted small">Lade Daten...</p>
            </div>
          ) : Object.keys(locationBreads).length > 0 ? (
            <>
              {!hasSolverResults && (
                <div className="alert alert-info alert-sm mb-2" style={{ fontSize: '0.75rem', padding: '0.5rem' }}>
                  <span className="material-icons" style={{ fontSize: '14px', verticalAlign: 'middle' }}>info</span>
                  {' '}Basierend auf Mitgliederbestellungen (noch kein Backplan)
                </div>
              )}
              {hasPreview && (
                <div className="alert alert-warning alert-sm mb-2" style={{ fontSize: '0.75rem', padding: '0.5rem' }}>
                  <span className="material-icons" style={{ fontSize: '14px', verticalAlign: 'middle' }}>preview</span>
                  {' '}Vorschau – noch nicht gespeichert
                </div>
              )}
              <div className="table-responsive mb-3">
                <table className="table table-sm" style={{ fontSize: '0.7rem' }}>
                  <thead>
                    <tr className="total-row-brown">
                      <th rowSpan={2} style={{ verticalAlign: 'bottom' }}>Station</th>
                      {hasSolverResults ? (
                        <>
                          {distBreadNames.map(name => (
                            <th key={name} colSpan={3} className="text-center border-left-bakery" style={{
                              minWidth: '60px', padding: '4px 2px', fontSize: '0.6rem',
                              borderBottom: 'none',
                            }}>{name}</th>
                          ))}
                          <th colSpan={3} className="text-center border-left-bakery" style={{
                            borderBottom: 'none',
                          }}>Gesamt</th>
                        </>
                      ) : (
                        <>
                          {distBreadNames.map(name => (
                            <th key={name} className="text-center border-left-bakery" style={{
                              padding: '4px 2px', fontSize: '0.6rem',
                              borderBottom: 'none',
                            }}>{name}</th>
                          ))}
                          <th colSpan={3} className="text-center border-left-bakery" style={{
                            borderBottom: 'none',
                          }}>Gesamt</th>
                        </>
                      )}
                    </tr>
                    <tr className="total-row-brown">
                      {hasSolverResults ? (
                        <>
                          {distBreadNames.map(name => (
                            <React.Fragment key={`header-${name}`}>
                              <th className="text-center border-left-bakery" style={{ fontSize: '0.55rem', fontWeight: 'normal', padding: '2px' }} title="Bestellt">
                                <span className="material-icons" style={{ fontSize: '10px' }}>shopping_cart</span>
                              </th>
                              <th className="text-center" style={{ fontSize: '0.55rem', fontWeight: 'normal', padding: '2px' }} title="Differenz">+/-</th>
                              <th className="text-center" style={{ fontSize: '0.55rem', fontWeight: 'normal', padding: '2px' }} title="Gesamt">
                                <span className="material-icons" style={{ fontSize: '10px' }}>local_fire_department</span>
                              </th>
                            </React.Fragment>
                          ))}
                          <th className="text-center border-left-bakery" style={{ fontSize: '0.55rem', fontWeight: 'normal', padding: '2px' }} title="Bestellt">
                            <span className="material-icons" style={{ fontSize: '10px' }}>shopping_cart</span>
                          </th>
                          <th className="text-center" style={{ fontSize: '0.55rem', fontWeight: 'normal', padding: '2px' }} title="Differenz">+/-</th>
                          <th className="text-center" style={{ fontSize: '0.55rem', fontWeight: 'normal', padding: '2px' }} title="Gesamt">
                            <span className="material-icons" style={{ fontSize: '10px' }}>local_fire_department</span>
                          </th>
                        </>
                      ) : (
                        <>
                          {distBreadNames.map(name => (
                            <th key={`header-${name}`} className="text-center border-left-bakery" style={{ fontSize: '0.55rem', fontWeight: 'normal', padding: '2px' }} title="Bestellt">Best.</th>
                          ))}
                          <th className="text-center border-left-bakery" style={{ fontSize: '0.55rem', fontWeight: 'normal', padding: '2px' }} title="Bestellt">Best.</th>
                          <th className="text-center" style={{ fontSize: '0.55rem', fontWeight: 'normal', padding: '2px' }} title="Noch offen">offen</th>
                          <th className="text-center" style={{ fontSize: '0.55rem', fontWeight: 'normal', padding: '2px' }} title="Gesamt">Ges.</th>
                        </>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(locationBreads).sort(([a], [b]) => a.localeCompare(b)).map(([loc, breads]) => {
                      const locTots = hasSolverResults
                        ? {
                            totalBaked: Object.values(breads).reduce((s, b) => s + (b.baked || 0), 0),
                            totalOrdered: Object.values(breads).reduce((s, b) => s + (b.ordered || 0), 0),
                            totalExtra: Object.values(breads).reduce((s, b) => s + (b.baked || 0), 0) - Object.values(breads).reduce((s, b) => s + (b.ordered || 0), 0),
                          }
                        : locationTotals[loc] || { totalBaked: 0, totalOrdered: 0, totalExtra: 0 };

                      return (
                        <tr key={loc}>
                          <td style={{ fontSize: '0.7rem' }}>{loc}</td>
                          {hasSolverResults ? (
                            distBreadNames.map(name => {
                              const data = breads[name] || { baked: 0, ordered: 0, extra: 0 };
                              return (
                                <React.Fragment key={`${loc}-${name}`}>
                                  <td className="text-center border-left-bakery">{data.ordered || '—'}</td>
                                  <td className={`text-center ${data.extra > 0 ? 'text-bakery-success' : data.extra < 0 ? 'text-bakery-danger' : 'text-bakery-muted'}`} style={{
                                    fontSize: '0.65rem',
                                  }}>
                                    {data.extra > 0 ? `+${data.extra}` : data.extra === 0 ? '—' : data.extra}
                                  </td>
                                  <td className="text-center text-bakery-primary-darker fw-bold">{data.baked || '—'}</td>
                                </React.Fragment>
                              );
                            })
                          ) : (
                            distBreadNames.map(name => {
                              const data = breads[name] || { ordered: 0 };
                              return (
                                <td key={`${loc}-${name}`} className="text-center border-left-bakery">{data.ordered || '—'}</td>
                              );
                            })
                          )}
                          <td className="text-center border-left-bakery">{locTots.totalOrdered}</td>
                          <td className={`text-center ${locTots.totalExtra > 0 ? 'text-bakery-danger' : 'text-bakery-muted'}`} style={{
                            fontSize: '0.65rem',
                          }}>
                            {hasSolverResults
                              ? (locTots.totalExtra > 0 ? `+${locTots.totalExtra}` : locTots.totalExtra === 0 ? '—' : locTots.totalExtra)
                              : locTots.totalExtra}
                          </td>
                          <td className="text-center text-bakery-primary-darker fw-bold">{locTots.totalBaked}</td>
                        </tr>
                      );
                    })}
                    <tr className="total-row-brown fw-bold">
                      <td>Gesamt</td>
                      {hasSolverResults ? (
                        distBreadNames.map(name => {
                          const totBaked = Object.values(locationBreads).reduce((s, b) => s + (b[name]?.baked || 0), 0);
                          const totOrdered = Object.values(locationBreads).reduce((s, b) => s + (b[name]?.ordered || 0), 0);
                          const totExtra = totBaked - totOrdered;
                          return (
                            <React.Fragment key={`total-${name}`}>
                              <td className="text-center border-left-bakery">{totOrdered}</td>
                              <td className={`text-center ${totExtra > 0 ? 'text-bakery-success' : totExtra < 0 ? 'text-bakery-danger' : 'text-bakery-muted'}`}>
                                {totExtra > 0 ? `+${totExtra}` : totExtra === 0 ? '—' : totExtra}
                              </td>
                              <td className="text-center">{totBaked}</td>
                            </React.Fragment>
                          );
                        })
                      ) : (
                        distBreadNames.map(name => {
                          const totOrdered = Object.values(locationBreads).reduce((s, b) => s + (b[name]?.ordered || 0), 0);
                          return <td key={`total-${name}`} className="text-center border-left-bakery">{totOrdered}</td>;
                        })
                      )}
                      {(() => {
                        const gtBaked = !hasSolverResults && Object.keys(locationTotals).length > 0
                          ? Object.values(locationTotals).reduce((s, t) => s + t.totalBaked, 0)
                          : Object.values(locationBreads).reduce((s, breads) => s + Object.values(breads).reduce((ss, b) => ss + (b.baked || 0), 0), 0);
                        const gtOrdered = !hasSolverResults && Object.keys(locationTotals).length > 0
                          ? Object.values(locationTotals).reduce((s, t) => s + t.totalOrdered, 0)
                          : Object.values(locationBreads).reduce((s, breads) => s + Object.values(breads).reduce((ss, b) => ss + (b.ordered || 0), 0), 0);
                        const gtExtra = gtBaked - gtOrdered;
                        return (
                          <>
                            <td className="text-center border-left-bakery">{gtOrdered}</td>
                            <td className={`text-center ${gtExtra > 0 ? 'text-bakery-danger' : 'text-bakery-muted'}`}>
                              {hasSolverResults ? (gtExtra > 0 ? `+${gtExtra}` : gtExtra === 0 ? '—' : gtExtra) : gtExtra}
                            </td>
                            <td className="text-center">{gtBaked}</td>
                          </>
                        );
                      })()}
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="text-muted small mb-2">
                <p className="mb-0" style={{ fontSize: '0.7rem' }}>
                  {hasSolverResults ? (
                    <>
                      <span className="material-icons" style={{ fontSize: '10px', verticalAlign: 'middle' }}>shopping_cart</span> = Bestellt &nbsp;|&nbsp;
                      <span className="text-bakery-success">+</span>/<span className="text-bakery-danger">-</span> = Differenz &nbsp;|&nbsp;
                      <span className="material-icons" style={{ fontSize: '10px', verticalAlign: 'middle' }}>local_fire_department</span> = Gebacken (lt. Backplan)
                    </>
                  ) : (
                    <>Best. = direkt gewählte Brotsorten &nbsp;|&nbsp; offen = noch nicht gewählt &nbsp;|&nbsp; Ges. = Brotanteile gesamt</>
                  )}
                </p>
              </div>
            </>
          ) : (
            <p className="text-muted small text-center py-2">Keine Daten verfügbar.</p>
          )}
          <ActionButtons pdfUrl={pdfUrl} label="Verteilliste" hasPreview={hasPreview} onEmail={onEmail} />
        </>
      )}
    </div>
  );
};