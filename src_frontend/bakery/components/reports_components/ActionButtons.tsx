import React from 'react';
import TapirButton from '../../../components/TapirButton';

interface ActionButtonsProps {
  pdfUrl: string | null;
  label: string;
  hasPreview: boolean;
  onEmail?: () => void;
}

export const ActionButtons: React.FC<ActionButtonsProps> = ({ pdfUrl, label, hasPreview, onEmail }) => (
  <div className="d-grid gap-2">
    {hasPreview && (
      <div className="alert alert-warning py-1 px-2 mb-1" style={{ fontSize: '0.75rem' }}>
        <span className="material-icons me-1" style={{ fontSize: '12px', verticalAlign: 'middle' }}>warning</span>
        Vorschau aktiv — PDF wird aus gespeicherten Daten erstellt.
        Erst „Anwenden", dann PDF herunterladen.
      </div>
    )}
    {pdfUrl ? (
      <a
        href={pdfUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="btn btn-sm dark-brown-button text-decoration-none"
      >
        <span className="material-icons me-2" style={{ fontSize: '16px', verticalAlign: 'middle' }}>download</span>
        {label} als PDF herunterladen
      </a>
    ) : (
      <TapirButton variant="" className="dark-brown-button" size="sm" icon="download" text={`${label} als PDF herunterladen`} disabled />
    )}
    <TapirButton variant="outline-secondary" size="sm" icon="email" text={`${label} per email senden`} onClick={onEmail} disabled />
  </div>
);