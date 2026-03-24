import React from 'react';
import { SectionToggle } from './SectionToggle';
import { ActionButtons } from './ActionButtons';
import '../../styles/bakery_styles.css';

interface BacklisteSectionProps {
  isOpen: boolean;
  onToggle: () => void;
  allBreadNames: string[];
  breadDeliveries: Record<string, number>;
  breadBaked: Record<string, number>;
  totalDeliveries: number;
  totalBaked: number;
  totalExtra: number;
  pdfUrl: string;
  hasPreview: boolean;
  onEmail: () => void;
}

export const BacklisteSection: React.FC<BacklisteSectionProps> = ({
  isOpen, onToggle, allBreadNames, breadDeliveries, breadBaked,
  totalDeliveries, totalBaked, totalExtra, pdfUrl, hasPreview, onEmail,
}) => (
  <div className="mb-3">
    <SectionToggle isOpen={isOpen} onToggle={onToggle} title="Backliste" icon="bakery_dining" />

    {isOpen && (
      <>
        {allBreadNames.length > 0 ? (
          <>
            <div className="table-responsive mb-3">
              <table className="table table-sm" style={{ fontSize: '0.8rem' }}>
                <thead className="table-header-bakery" style={{ fontSize: '0.8rem' }}>
                  <tr className="total-row-brown">
                    <th>Brotsorte</th>
                    <th className="text-end" title="Zuweisung zu Verteilstationen">
                      <span className="material-icons" style={{ fontSize: '14px', verticalAlign: 'middle' }}>local_shipping</span>
                    </th>
                    <th className="text-end" title="Extra (Reserve/Verkauf)">
                      <span className="material-icons" style={{ fontSize: '14px', verticalAlign: 'middle' }}>add_circle</span>
                    </th>
                    <th className="text-end" title="Gesamt im Ofen gebacken">
                      <span className="material-icons" style={{ fontSize: '14px', verticalAlign: 'middle' }}>local_fire_department</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {allBreadNames.map((name) => {
                    const deliveries = breadDeliveries[name] || 0;
                    const baked = breadBaked[name] || 0;
                    const extra = baked - deliveries;
                    return (
                      <tr key={name}>
                        <td>{name}</td>
                        <td className="text-end">{deliveries}</td>
                        <td className={`text-end ${extra > 0 ? 'text-bakery-success' : 'text-bakery-muted'}`}>
                          {extra > 0 ? `+${extra}` : extra}
                        </td>
                        <td className="text-end">
                          <strong className="text-bakery-primary-darker">{baked}</strong>
                        </td>
                      </tr>
                    );
                  })}
                  <tr className="total-row-brown fw-bold">
                    <td>Gesamt</td>
                    <td className="text-end">{totalDeliveries}</td>
                    <td className={`text-end ${totalExtra > 0 ? 'text-bakery-success' : 'text-bakery-muted'}`}>
                      {totalExtra > 0 ? `+${totalExtra}` : totalExtra}
                    </td>
                    <td className="text-end">{totalBaked}</td>
                  </tr>
                </tbody>
              </table>
              <div className="text-muted small">
                <p className="mb-1">
                  <span className="material-icons" style={{ fontSize: '12px', verticalAlign: 'middle' }}>local_shipping</span> = Zuweisung zu Verteilstationen
                </p>
                <p className="mb-1">
                  <span className="material-icons" style={{ fontSize: '12px', verticalAlign: 'middle' }}>add_circle</span> = Extra (Reserve/Verkauf)
                </p>
                <p className="mb-0">
                  <span className="material-icons" style={{ fontSize: '12px', verticalAlign: 'middle' }}>local_fire_department</span> = Gesamt im Ofen gebacken
                </p>
              </div>
            </div>
            <ActionButtons pdfUrl={pdfUrl} label="Backliste" hasPreview={hasPreview} onEmail={onEmail} />
          </>
        ) : (
          <p className="text-muted small text-center py-2">Noch kein Backplan berechnet.</p>
        )}
      </>
    )}
  </div>
);