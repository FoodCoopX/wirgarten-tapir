import React from 'react';
import { EggFried, CheckCircleFill, StarFill } from 'react-bootstrap-icons';
import type { BreadList, BreadContent, BreadLabel } from '../../../api-client/models';
import '../../styles/bakery_styles.css';

interface SingleBreadCardProps {
  bread: BreadList;
  contents?: BreadContent[];
  labels?: BreadLabel[];
  isSelected?: boolean;
  isPreferred?: boolean;
  onClick?: () => void;
  width?: string;
  showFooter?: boolean;
  footerText?: string;
  showAvailability?: boolean;
}

export const SingleBreadCard: React.FC<SingleBreadCardProps> = ({
  bread,
  contents = [],
  labels = [],
  isSelected = false,
  isPreferred = false,
  onClick,
  width = '280px',
  showFooter = true,
  footerText,
  showAvailability = false,
}) => {
  const availableCapacity = bread.availableCapacity;
  const hasLimitedCapacity = showAvailability && availableCapacity !== undefined && availableCapacity <= 5;
  return (
    <div style={{ width, flex: `0 0 ${width}` }}>
      <div
        className={`card h-100 shadow-sm position-relative ${isSelected ? 'bread-selected' : isPreferred ? 'bread-preferred' : ''}`}
        style={{ cursor: onClick ? 'pointer' : 'default' }}
        onClick={onClick}
      >
        {/* Selected/Preferred Badge */}
        {(isSelected || isPreferred) && (
          <div 
            className="position-absolute top-0 end-0 m-2"
            style={{ zIndex: 10 }}
          >
            {isSelected ? (
              <CheckCircleFill 
                size={32} 
                className="text-bakery-success-dark"
                style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))' }} 
              />
            ) : isPreferred ? (
              <div
                className="bg-bakery-gold d-flex align-items-center justify-content-center"
                style={{
                  borderRadius: '50%',
                  padding: '8px',
                  filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))'
                }}
              >
                <StarFill size={16} style={{ color: 'white' }} />
              </div>
            ) : null}
          </div>
        )}

        {/* Image */}
        {bread.picture ? (
          <img
            src={bread.picture}
            alt={bread.name}
            className="card-img-top"
            style={{ height: '180px', objectFit: 'cover' }}
          />
        ) : (
          <div
            className="d-flex align-items-center justify-content-center bg-bakery-cream"
            style={{ height: '180px' }}
          >
            <EggFried size={48} className="icon-bakery-primary" />
          </div>
        )}

        {/* Card Body */}
        <div className="card-body d-flex flex-column">
          <h6 className="card-title mb-0 text-bakery-primary-darker">
            {bread.name}
          </h6>

          {bread.weight && (
            <small className="text-muted mb-2">{Number(bread.weight).toFixed(0)}g</small>
          )}

          {/* Availability Badge */}
          {showAvailability && availableCapacity !== undefined && (
            <div className="mb-2">
              <span 
                className={`badge ${hasLimitedCapacity ? 'bg-warning text-dark' : 'badge-bakery-success'}`}
                style={{ fontSize: '0.7rem' }}
              >
                {availableCapacity} verfügbar
              </span>
            </div>
          )}

          {labels.length > 0 && (
            <div className="mb-2">
              {labels.map(label => (
                <span
                  key={label.id}
                  className={`badge me-1 ${label.isActive ? 'badge-bakery-success' : 'badge-bakery-muted'}`}
                  style={{ fontSize: '0.7rem' }}
                >
                  {label.name}
                </span>
              ))}
            </div>
          )}

          {bread.description && (
            <p className="card-text text-muted small mb-2">{bread.description}</p>
          )}

          {contents.length > 0 && (
            <div className="mb-2" style={{ flex: 1 }}>
              <small className="fw-bold content-ingredients-label" style={{ fontSize: '0.7rem' }}>
                ZUTATEN:
              </small>
              <br />
              <small className="content-ingredients-text" style={{ fontSize: '0.75rem' }}>
                {contents.map(c => c.ingredientName).join(', ')}
              </small>
            </div>
          )}
        </div>

        {/* Footer */}
        {showFooter && (
          <div 
            className={`card-footer text-center py-2 ${isSelected ? 'bread-card-footer-selected' : isPreferred ? 'bread-card-footer-preferred' : 'bread-card-footer-default'}`}
          >
            {footerText || (isSelected ? 'Ist ausgewählt' : isPreferred ? 'Lieblingsbrot' : 'Auswählen')}
          </div>
        )}
      </div>
    </div>
  );
};