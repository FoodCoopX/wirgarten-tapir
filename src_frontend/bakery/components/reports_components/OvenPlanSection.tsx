import React from "react";
import "../../styles/bakery_styles.css";
import { SectionToggle } from "./SectionToggle";

interface StoveLayer {
  layer: number;
  breadName: string | null;
  quantity: number;
}

interface StoveSessionGrouped {
  session: number;
  layers: StoveLayer[];
}

// Breads of a group can share a layer, which then has an entry per bread.
const byLayerNumber = (layers: StoveLayer[]): [number, StoveLayer[]][] => {
  const grouped = new Map<number, StoveLayer[]>();
  for (const layer of layers) {
    if (!grouped.has(layer.layer)) grouped.set(layer.layer, []);
    grouped.get(layer.layer)!.push(layer);
  }
  return [...grouped.entries()];
};

interface OvenPlanSectionProps {
  isOpen: boolean;
  onToggle: () => void;
  displaySessions: StoveSessionGrouped[];
}

export const OvenPlanSection: React.FC<OvenPlanSectionProps> = ({
  isOpen,
  onToggle,
  displaySessions,
}) => (
  <div className="mb-3">
    <SectionToggle
      isOpen={isOpen}
      onToggle={onToggle}
      title="Ofenplan"
      icon="local_fire_department"
    />
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
                  {byLayerNumber(session.layers).map(([number, breads]) => (
                    <li key={number} className="list-group-item py-1 small">
                      <span className="text-muted">Etage {number}:</span>{" "}
                      {breads.some((layer) => layer.breadName) ? (
                        breads.map((layer, index) => (
                          <span key={index}>
                            {index > 0 && " + "}
                            {layer.breadName}{" "}
                            <span className="badge bg-secondary">
                              ×{layer.quantity}
                            </span>
                          </span>
                        ))
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
          <p className="text-muted small text-center py-2">
            Noch kein Ofenplan berechnet.
          </p>
        )}
      </>
    )}
  </div>
);
