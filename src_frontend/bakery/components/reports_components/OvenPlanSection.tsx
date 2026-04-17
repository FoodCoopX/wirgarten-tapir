import React from 'react';
import { SectionToggle } from './SectionToggle';
import '../../styles/bakery_styles.css';

interface StoveSessionGrouped {
  session: number;
  layers: { layer: number; breadName: string | null; quantity: number }[];
}

interface OvenPlanSectionProps {
  isOpen: boolean;
  onToggle: () => void;
  displaySessions: StoveSessionGrouped[];
}

export const OvenPlanSection: React.FC<OvenPlanSectionProps> = ({ isOpen, onToggle, displaySessions }) => (
  <div className="mb-3">
    <SectionToggle isOpen={isOpen} onToggle={onToggle} title="Ofenplan" icon="local_fire_department" />
    <p className="text-muted small mb-2">Belegung der Ofengänge</p>

    {isOpen && (
      <>
        {displaySessions.length > 0 ? (
          <div className="d-flex flex-column gap-2 mb-3">
            {displaySessions.map((session) => (
              <div key={session.session} className="card">
                <div className="card-header py-1 header-white-on-middle-brown">
                  <small className="fw-bold">Ofengang {session.session}</small>
                </div>
                <ul className="list-group list-group-flush">
                  {session.layers.map((layer) => (
                    <li key={layer.layer} className="list-group-item py-1 small">
                      <span className="text-muted">Etage {layer.layer}:</span>{' '}
                      {layer.breadName ? (
                        <span>
                          {layer.breadName}{' '}
                          <span className="badge bg-secondary">×{layer.quantity}</span>
                        </span>
                      ) : (
                        <span className="text-muted fst-italic">leer</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-muted small text-center py-2">Noch kein Ofenplan berechnet.</p>
        )}
      </>
    )}
  </div>
);