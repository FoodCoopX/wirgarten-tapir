import React from 'react';
import { EggFried } from 'react-bootstrap-icons';
import type { BreadList, BreadContent, BreadLabel } from '../../../api-client/models';
import '../../styles/bakery_styles.css';

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
    <div className="card w-100 card-bakery-border-left">
      <div className="card-body p-3">
        <div className="row g-2">
          {/* Image column */}
          <div className="col-auto">
            {bread.picture ? (
              <img
                src={bread.picture}
                alt={bread.name}
                className="compact-card-image"
              />
            ) : (
              <div className="compact-card-placeholder">
                <EggFried size={24} className="icon-bakery-primary" />
              </div>
            )}
          </div>

          {/* Details column */}
          <div className="col">
            <div className="d-flex flex-column h-100">
              <div className="d-flex justify-content-between align-items-start mb-1">
                <h6 className="mb-0 text-bakery-primary-darker">
                  {bread.name}
                </h6>
                {showActions && (
                  <div className="d-flex gap-1">
                    {onEdit && (
                      <button
                        className="btn btn-sm dark-brown-button btn-compact-action"
                        onClick={onEdit}
                        disabled={disabled}
                      >
                        Ändern
                      </button>
                    )}
                    {onRemove && (
                      <button
                        className="btn btn-sm btn-outline-danger btn-compact-action"
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
                      className={`badge me-1 ${label.isActive ? 'badge-bakery-success' : 'badge-bakery-muted'}`}
                      style={{ fontSize: '0.65rem' }}
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
                  <small className="fw-bold content-ingredients-label">
                    ZUTATEN:
                  </small>
                  <br />
                  <small className="content-ingredients-text">
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