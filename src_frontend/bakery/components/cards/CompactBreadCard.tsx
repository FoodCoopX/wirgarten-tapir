import React from 'react';
import { EggFried } from 'react-bootstrap-icons';
import type { BreadList, BreadContent, BreadLabel } from '../../../api-client/models';

interface CompactBreadCardProps {
  bread: BreadList;
  contents?: BreadContent[];
  labels?: BreadLabel[];
  onEdit?: () => void;
  onRemove?: () => void;
  showActions?: boolean;
  disabled?: boolean;
}

export const CompactBreadCard: React.FC<CompactBreadCardProps> = ({
  bread,
  contents = [],
  labels = [],
  onEdit,
  onRemove,
  showActions = true,
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
        <div className="row g-2">
          {/* Image column */}
          <div className="col-auto">
            {bread.picture ? (
              <img
                src={bread.picture}
                alt={bread.name}
                style={{ 
                  width: '80px', 
                  height: '80px', 
                  objectFit: 'cover',
                  borderRadius: '4px'
                }}
              />
            ) : (
              <div
                className="d-flex align-items-center justify-content-center"
                style={{ 
                  width: '80px', 
                  height: '80px', 
                  backgroundColor: '#F5E6D3',
                  borderRadius: '4px'
                }}
              >
                <EggFried size={24} style={{ color: '#D4A574' }} />
              </div>
            )}
          </div>

          {/* Details column */}
          <div className="col">
            <div className="d-flex flex-column h-100">
              <div className="d-flex justify-content-between align-items-start mb-1">
                <h6 className="mb-0" style={{ color: '#8B4513' }}>
                  {bread.name}
                </h6>
                {showActions && (
                  <div className="d-flex gap-1">
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
                    {onRemove && (
                      <button
                        className="btn btn-sm btn-outline-danger"
                        style={{ 
                          fontSize: '0.75rem',
                          padding: '0.25rem 0.5rem'
                        }}
                        onClick={onRemove}
                        disabled={disabled}
                      >
                        Entfernen
                      </button>
                    )}
                  </div>
                )}
              </div>
              
              {bread.weight && (
                <small className="text-muted mb-1">
                  {Number(bread.weight).toFixed(0)}g
                </small>
              )}

              {labels.length > 0 && (
                <div className="mb-1">
                  {labels.map(label => (
                    <span
                      key={label.id}
                      className="badge me-1"
                      style={{ 
                        backgroundColor: label.isActive ? '#2E7D32' : '#9E9E9E',
                        color: 'white',
                        fontSize: '0.65rem'
                      }}
                    >
                      {label.name}
                    </span>
                  ))}
                </div>
              )}

              {bread.description && (
                <p className="mb-1 small text-muted" style={{ fontSize: '0.8rem' }}>
                  {bread.description}
                </p>
              )}

              {contents.length > 0 && (
                <div className="mt-auto">
                  <small className="fw-bold" style={{ color: '#C4A882', fontSize: '0.65rem' }}>
                    ZUTATEN:
                  </small>
                  <br />
                  <small style={{ color: '#B8A99A', fontSize: '0.7rem' }}>
                    {contents.map(c => c.ingredientName).join(', ')}
                  </small>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};