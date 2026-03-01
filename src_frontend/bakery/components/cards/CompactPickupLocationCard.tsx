import React from 'react';
import { GeoAlt, Calendar } from 'react-bootstrap-icons';

interface CompactPickupLocationCardProps {
  name: string;
  address?: string;
  deliveryDay?: number;
  onEdit?: () => void;
  disabled?: boolean;
}

const DAY_LABELS: Record<number, string> = {
  0: 'Montag',
  1: 'Dienstag',
  2: 'Mittwoch',
  3: 'Donnerstag',
  4: 'Freitag',
  5: 'Samstag',
  6: 'Sonntag',
};

export const CompactPickupLocationCard: React.FC<CompactPickupLocationCardProps> = ({
  name,
  address,
  deliveryDay,
  onEdit,
  disabled = false,
}) => {
  return (
    <div 
      className="card w-100" 
      style={{ 
        borderLeft: '4px solid #8B4513',
        backgroundColor: '#FAF8F5' 
      }}
    >
      <div className="card-body p-3">
        <div className="d-flex justify-content-between align-items-start">
          <div className="flex-grow-1">
            <div className="d-flex align-items-center mb-2">
              <GeoAlt size={18} className="me-2" style={{ color: '#8B4513' }} />
              <h6 className="mb-0" style={{ color: '#8B4513' }}>
                {name}
              </h6>
            </div>

            {address && (
              <p className="text-muted small mb-1" style={{ fontSize: '0.85rem', marginLeft: '26px' }}>
                {address}
              </p>
            )}

            {deliveryDay !== undefined && deliveryDay !== null && (
              <div className="d-flex align-items-center text-muted small" style={{ marginLeft: '26px' }}>
                <Calendar size={14} className="me-1" />
                <span style={{ fontSize: '0.85rem' }}>
                  Lieferung: {DAY_LABELS[deliveryDay] || `Tag ${deliveryDay}`}
                </span>
              </div>
            )}
          </div>

          {onEdit && (
            <button
              className="btn btn-sm"
              style={{ 
                backgroundColor: '#8B4513', 
                color: 'white',
                fontSize: '0.75rem',
                padding: '0.25rem 0.5rem'
              }}
              onClick={onEdit}
              disabled={disabled}
            >
              Ändern
            </button>
          )}
        </div>
      </div>
    </div>
  );
};