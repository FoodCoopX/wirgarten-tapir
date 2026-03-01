import React, { useEffect, useState } from 'react';
import { BakeryApi } from '../../../api-client';
import type { PreferenceSatisfactionResponse } from '../../../api-client/models';
import { useApi } from '../../../hooks/useApi';

interface MetricsCardProps {
  year: number;
  week: number;
  deliveryDay: number;
  csrfToken: string;
}

export const MetricsCard: React.FC<MetricsCardProps> = ({ year, week, deliveryDay, csrfToken }) => {
  const [data, setData] = useState<PreferenceSatisfactionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedLocations, setExpandedLocations] = useState<Set<string>>(new Set());
  const bakeryApi = useApi(BakeryApi, csrfToken);

  useEffect(() => {
    loadMetrics();
  }, [year, week, deliveryDay]);

  const loadMetrics = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await bakeryApi.bakeryMetricsSatisfactionRetrieve({
        year,
        deliveryWeek: week,
        deliveryDay,
      });
      
      setData(response);
    } catch (err) {
      console.error('Failed to load metrics:', err);
      setError('Fehler beim Laden der Metriken');
    } finally {
      setLoading(false);
    }
  };

  const toggleLocation = (locationId: string) => {
    setExpandedLocations(prev => {
      const next = new Set(prev);
      if (next.has(locationId)) {
        next.delete(locationId);
      } else {
        next.add(locationId);
      }
      return next;
    });
  };

  if (loading) {
    return (
      <div className="text-center py-3">
        <div className="spinner-border spinner-border-sm text-primary" role="status">
          <span className="visually-hidden">Lädt...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-warning py-2 mb-0" role="alert">
        <small>
          <span className="material-icons" style={{ fontSize: '16px', verticalAlign: 'middle' }}>
            warning
          </span>
          {' '}{error}
        </small>
      </div>
    );
  }

  if (!data || !data.locations || data.locations.length === 0) {
    return (
      <div className="alert alert-info py-2 mb-0" role="alert">
        <small>
          <span className="material-icons" style={{ fontSize: '16px', verticalAlign: 'middle' }}>
            info
          </span>
          {' '}Keine Metriken verfügbar. Bitte erst Backplan erstellen.
        </small>
      </div>
    );
  }

  return (
    <div className="d-flex flex-column gap-2">
      {data.locations.map((metric) => {
        const isExpanded = expandedLocations.has(metric.pickupLocationId);
        const noMatchPercentage = metric.totalDeliveries > 0
          ? ((metric.noMatch / metric.totalDeliveries) * 100).toFixed(0)
          : '0';

        return (
          <div key={metric.pickupLocationId} className="card">
            <div 
              className="card-header py-2" 
              style={{ backgroundColor: '#8B6F47', color: 'white', cursor: 'pointer' }}
              onClick={() => toggleLocation(metric.pickupLocationId)}
            >
              <div className="d-flex justify-content-between align-items-center">
                <small className="fw-bold">{metric.pickupLocationName}</small>
                <div className="d-flex align-items-center gap-2">
                  <span style={{ fontSize: '0.8rem' }}>
                    {metric.satisfied}/{metric.totalDeliveries} zufrieden
                  </span>
                  <span className="material-icons" style={{ fontSize: '18px' }}>
                    {isExpanded ? 'expand_less' : 'expand_more'}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="card-body p-2">
              {/* Progress Bar */}
              <div className="progress mb-2" style={{ height: '20px' }}>
                <div 
                  className="progress-bar" 
                  style={{ 
                    width: `${metric.satisfiedPercentage}%`,
                    backgroundColor: '#28a745',
                    fontSize: '0.7rem',
                    fontWeight: 'bold',
                  }}
                  title={`${metric.satisfied} zufrieden (${metric.satisfiedPercentage}%)`}
                >
                  {metric.satisfiedPercentage > 15 && `${metric.satisfiedPercentage}%`}
                </div>
                <div 
                  className="progress-bar bg-danger" 
                  style={{ 
                    width: `${100 - metric.satisfiedPercentage}%`,
                    fontSize: '0.7rem',
                    fontWeight: 'bold',
                  }}
                  title={`${metric.noMatch} kein Match (${noMatchPercentage}%)`}
                >
                  {Number(noMatchPercentage) > 15 && `${noMatchPercentage}%`}
                </div>
              </div>

              {/* Breakdown Numbers */}
              <div className="d-flex justify-content-between" style={{ fontSize: '0.8rem' }}>
                <div className="text-muted">
                  <span className="material-icons" style={{ fontSize: '14px', verticalAlign: 'middle', color: '#28a745' }}>
                    check_circle
                  </span>
                  {' '}<strong>{metric.directlyChosen}</strong> direkt gewählt
                </div>
                <div className="text-muted">
                  <span className="material-icons" style={{ fontSize: '14px', verticalAlign: 'middle', color: '#28a745' }}>
                    favorite
                  </span>
                  {' '}<strong>{metric.gotFavorite}</strong> Favorit möglich
                </div>
                <div className="text-muted">
                  <span className="material-icons" style={{ fontSize: '14px', verticalAlign: 'middle', color: '#6c757d' }}>
                    sentiment_satisfied
                  </span>
                  {' '}<strong>{metric.noFavorites}</strong> ohne Präf.
                </div>
              </div>

              {metric.noMatch > 0 && (
                <div className="mt-1 text-center" style={{ fontSize: '0.8rem' }}>
                  <span className="text-danger">
                    <span className="material-icons" style={{ fontSize: '14px', verticalAlign: 'middle' }}>
                      warning
                    </span>
                    {' '}<strong>{metric.noMatch}</strong> Lieferungen ohne passendes Favoritenbrot
                  </span>
                </div>
              )}

              {/* Bread Breakdown (Collapsible) */}
              {isExpanded && metric.breadBreakdown && metric.breadBreakdown.length > 0 && (
                <div className="mt-2 pt-2 border-top">
                  <div className="d-flex flex-column gap-1">
                    {metric.breadBreakdown.map((bread) => (
                      <div 
                        key={bread.breadId} 
                        className="d-flex justify-content-between align-items-center py-1 px-2"
                        style={{ 
                          backgroundColor: '#f8f9fa',
                          borderRadius: '4px',
                          fontSize: '0.85rem',
                        }}
                      >
                        <span 
                          className="text-truncate fw-medium" 
                          style={{ maxWidth: '160px' }}
                          title={bread.breadName}
                        >
                          {bread.breadName}
                        </span>
                        
                        <div className="d-flex gap-1 align-items-center">
                          <span 
                            className="badge bg-secondary"
                            title="Gesamt verteilt"
                            style={{ minWidth: '32px' }}
                          >
                            {bread.count}
                          </span>
                          {bread.directlyChosen > 0 && (
                            <span 
                              className="badge" 
                              style={{ 
                                backgroundColor: '#8B6F47',
                                minWidth: '32px',
                              }}
                              title="Direkt gewählt"
                            >
                              ✓{bread.directlyChosen}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};