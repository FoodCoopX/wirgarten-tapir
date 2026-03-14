import React from 'react';

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
      <button className="btn btn-sm dark-brown-button" disabled>
        <span className="material-icons me-2" style={{ fontSize: '16px', verticalAlign: 'middle' }}>download</span>
        {label} als PDF herunterladen
      </button>
    )}
    <button
      className="btn btn-sm btn-outline-secondary"
      onClick={onEmail}
      disabled={true}
    >
      <span className="material-icons me-2" style={{ fontSize: '16px', verticalAlign: 'middle' }}>email</span>
      {label} per email senden
    </button>
  </div>
);