import React from 'react';
import { EggFried, CheckCircleFill, StarFill } from 'react-bootstrap-icons';
import type { BreadList, BreadContent, BreadLabel } from '../../../api-client/models';

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
}) => {
  return (
    <div style={{ width, flex: `0 0 ${width}` }}>
      <div
        className="card h-100 shadow-sm position-relative"
        style={{
          border: isSelected ? '3px solid #2E7D32' : isPreferred ? '2px solid #FFD700' : '1px solid #dee2e6',
          cursor: onClick ? 'pointer' : 'default',
          transform: isSelected ? 'scale(1.02)' : 'scale(1)',
          transition: 'all 0.2s ease',
          backgroundColor: isSelected ? '#d4edda' : 'white',
        }}
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
                style={{ 
                  color: '#2E7D32',
                  filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))'
                }} 
              />
            ) : isPreferred ? (
              <div
                style={{
                  backgroundColor: 'rgba(255, 215, 0, 0.95)',
                  borderRadius: '50%',
                  padding: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
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
            style={{ 
              height: '180px', 
              objectFit: 'cover',
              opacity: isSelected ? 1 : 0.95
            }}
          />
        ) : (
          <div
            className="d-flex align-items-center justify-content-center"
            style={{ height: '180px', backgroundColor: '#F5E6D3' }}
          >
            <EggFried size={48} style={{ color: '#D4A574' }} />
          </div>
        )}

        {/* Card Body */}
        <div className="card-body d-flex flex-column">
          <h6 className="card-title mb-0" style={{ color: '#8B4513' }}>
            {bread.name}
          </h6>

          {bread.weight && (
            <small className="text-muted mb-2">{Number(bread.weight).toFixed(0)}g</small>
          )}

          {labels.length > 0 && (
            <div className="mb-2">
              {labels.map(label => (
                <span
                  key={label.id}
                  className="badge me-1"
                  style={{ 
                    backgroundColor: label.isActive ? '#2E7D32' : '#9E9E9E',
                    color: 'white',
                    fontSize: '0.7rem'
                  }}
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
              <small className="fw-bold" style={{ color: '#C4A882', fontSize: '0.7rem' }}>
                ZUTATEN:
              </small>
              <br />
              <small style={{ color: '#B8A99A', fontSize: '0.75rem' }}>
                {contents.map(c => c.ingredientName).join(', ')}
              </small>
            </div>
          )}
        </div>

        {/* Footer */}
        {showFooter && (
          <div 
            className="card-footer text-center py-2" 
            style={{ 
              backgroundColor: isSelected ? '#2E7D32' : isPreferred ? '#FFD700' : '#8B4513', 
              color: 'white' 
            }}
          >
            {footerText || (isSelected ? 'Ist ausgewählt' : isPreferred ? 'Lieblingsbrot' : 'Auswählen')}
          </div>
        )}
      </div>
    </div>
  );
};