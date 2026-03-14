import React from 'react';
import { SectionToggle } from './SectionToggle';
import { ActionButtons } from './ActionButtons';
import type { AbhollisteResponse, PickupLocation } from '../../../api-client/models';

interface AbhollisteSectionProps {
  isOpen: boolean;
  onToggle: () => void;
  isLoading: boolean;
  hasPreview: boolean;
  dayPickupLocations: PickupLocation[];
  selectedLocation: string;
  onPickupLocationChange: (id: string) => void;
  abhollisteData: AbhollisteResponse | null;
  checkedMembers: Record<string, boolean>;
  onCheckToggle: (memberId: string) => void;
  pdfUrl: string | null;
  allPdfUrl: string;
  onEmail: () => void;
}

export const AbhollisteSection: React.FC<AbhollisteSectionProps> = ({
  isOpen, onToggle, isLoading, hasPreview, dayPickupLocations,
  selectedLocation, onPickupLocationChange, abhollisteData,
  checkedMembers, onCheckToggle, pdfUrl, allPdfUrl, onEmail,
}) => (
  <div>
    <SectionToggle isOpen={isOpen} onToggle={onToggle} title="Abholliste" icon="local_shipping" />
    <p className="text-muted small mb-2">Brote pro Mitglied am Abholort</p>

    {isOpen && (
      <>
        <div className="mb-3">
          <select
            className="form-select form-select-sm"
            value={selectedLocation}
            onChange={(e) => onPickupLocationChange(e.target.value)}
          >
            <option value="">Abholort auswählen...</option>
         {dayPickupLocations.map(pl => (
  <option key={pl.id ?? ''} value={pl.id ?? ''}>{pl.name}</option>
))}
          </select>
        </div>
        <ActionButtons pdfUrl={pdfUrl} label="Abholliste" hasPreview={hasPreview} onEmail={onEmail} />
        <div className="mt-2">
          <a
            href={allPdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-sm dark-brown-button w-100 text-decoration-none"
          >
            <span className="material-icons me-2" style={{ fontSize: '16px', verticalAlign: 'middle' }}>picture_as_pdf</span>
            Alle Abhollisten als ein PDF
          </a>
        </div>

        {isLoading ? (
          <div className="text-center py-3">
            <div className="spinner-border spinner-border-sm" style={{ color: '#D4A574' }} />
            <p className="mt-1 text-muted small">Lade Abholliste...</p>
          </div>
        ) : selectedLocation && abhollisteData?.entries?.length ? (
          <>
            <div className="table-responsive mb-3 mt-3">
              <table className="table table-sm table-bordered" style={{ fontSize: '0.8rem' }}>
                <thead style={{ backgroundColor: '#F5E6D3' }}>
                  <tr>
                    <th className="text-center" style={{ width: '30px' }}>#</th>
                    <th>Name</th>
                    <th className="text-center" style={{ width: '40px' }}>Σ</th>
                    <th className="text-center" style={{ width: '30px' }}>
                      <span className="material-icons" style={{ fontSize: '14px' }}>check</span>
                    </th>
                    {abhollisteData.breadNames.map(name => (
                      <th key={name} className="text-center" style={{
                        writingMode: 'vertical-rl', transform: 'rotate(180deg)',
                        minWidth: '28px', maxWidth: '28px', padding: '8px 2px', fontSize: '0.7rem',
                      }}>{name}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {abhollisteData.entries.map((entry: any, index: number) => {
                    const memberId = entry.memberId || entry.member_id;
                    const displayName = entry.displayName || entry.display_name;
                    const totalBreads = entry.totalBreads || entry.total_breads || 0;
                    const breadCounts: Record<string, number> = entry.breadCounts || entry.bread_counts || {};
                    const breadPreferred: Record<string, boolean> = entry.breadPreferred || entry.bread_preferred || {};
                    const isChecked = checkedMembers[memberId] || false;

                    return (
                      <tr key={memberId} style={{
                        backgroundColor: isChecked ? '#d4edda' : undefined,
                        textDecoration: isChecked ? 'line-through' : undefined,
                        opacity: isChecked ? 0.7 : 1,
                      }}>
                        <td className="text-center text-muted">{index + 1}</td>
                        <td style={{ fontSize: '0.8rem', whiteSpace: 'nowrap' }}>{displayName}</td>
                        <td className="text-center">
                          <strong style={{ color: '#8B4513' }}>{totalBreads}</strong>
                        </td>
                        <td className="text-center">
                          <input
                            type="checkbox" className="form-check-input"
                            checked={isChecked}
                           onChange={() => onCheckToggle(String(memberId))}
                            style={{ cursor: 'pointer' }}
                          />
                        </td>
                        {abhollisteData.breadNames.map(name => {
                          const count = breadCounts[name] || 0;
                          const preferred = breadPreferred[name] || false;
                          return (
                            <td key={name} className="text-center" style={{
                              backgroundColor: preferred ? '#d4edda' : undefined,
                              color: count > 0 ? '#212529' : '#ccc',
                            }}>
                              {count > 0 ? count : preferred ? '' : '—'}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                  <tr style={{ backgroundColor: '#F5E6D3', fontWeight: 'bold' }}>
                    <td />
                    <td>Gesamt</td>
                    <td className="text-center">{abhollisteData.grandTotal}</td>
                    <td />
                    {abhollisteData.breadNames.map(name => (
                      <td key={name} className="text-center">
                        {(abhollisteData.breadTotals as unknown as Record<string, number>)[name] || 0}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="d-flex align-items-center gap-2 mb-2" style={{ fontSize: '0.75rem' }}>
              <span style={{
                display: 'inline-block', width: '14px', height: '14px',
                backgroundColor: '#d4edda', border: '1px solid #c3e6cb',
              }} />
              <span className="text-muted">= als Lieblingsbrot angegeben</span>
            </div>
          </>
        ) : selectedLocation ? (
          <p className="text-muted small text-center py-2">Keine Brotbestellungen für diesen Abholort.</p>
        ) : null}
      </>
    )}
  </div>
);