import React, { useState, useEffect } from 'react';
import { EggFried } from 'react-bootstrap-icons';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import type { BreadList, BreadContent } from '../../../api-client/models';

interface BreadSelectionModalProps {
  breads: BreadList[];
  contentsMap: { [breadId: string]: BreadContent[] };
  pickupLocationId: string;
  pickupLocationName: string;
  selectedWeek: number;
  selectedYear: number;
  onSelect: (breadId: string) => void;
  onClose: () => void;
  csrfToken: string;
}

export const BreadSelectionModal: React.FC<BreadSelectionModalProps> = ({
  breads: initialBreads,
  contentsMap,
  pickupLocationId,
  pickupLocationName,
  selectedWeek,
  selectedYear,
  onSelect,
  onClose,
  csrfToken,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);
  const [availableBreads, setAvailableBreads] = useState<BreadList[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAvailableBreads();
    // eslint-disable-next-line
  }, [pickupLocationId, selectedWeek, selectedYear]);

  const loadAvailableBreads = async () => {
    setLoading(true);
    try {
      // Fetch breads with capacity filtering
      const breadsWithCapacity = await bakeryApi.bakeryBreadsListList({
        isActive: true,
        pickupLocationId,
        year: selectedYear,
        week: selectedWeek,
      });
      
      setAvailableBreads(breadsWithCapacity);
    } catch (error) {
      console.error('Failed to load available breads:', error);
      setAvailableBreads([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Modal Backdrop */}
      <div 
        className="modal-backdrop fade show" 
        onClick={onClose}
        style={{ zIndex: 1050 }}
      />

      {/* Modal */}
      <div 
        className="modal fade show d-block" 
        tabIndex={-1}
        style={{ zIndex: 1055 }}
      >
        <div className="modal-dialog modal-xl modal-dialog-scrollable">
          <div className="modal-content">
            <div 
              className="modal-header" 
              style={{ backgroundColor: '#D4A574', color: 'white' }}
            >
              <h5 className="modal-title">
                <span className="material-icons align-middle me-2">bakery_dining</span>
                Brot auswählen für {pickupLocationName}
              </h5>
              <button 
                type="button" 
                className="btn-close btn-close-white" 
                onClick={onClose}
              />
            </div>

            <div className="modal-body" style={{ backgroundColor: '#FAF8F5' }}>
              {loading ? (
                <div className="text-center py-5">
                  <div className="spinner-border" style={{ color: '#D4A574' }} />
                  <p className="mt-2 text-muted">Lade verfügbare Brote...</p>
                </div>
              ) : (
                <>
                  <div className="alert alert-info mb-4">
                    <strong>KW {selectedWeek}/{selectedYear}</strong> - Station: {pickupLocationName}
                    <br />
                    <small>{availableBreads.length} Brotsorte{availableBreads.length !== 1 ? 'n' : ''} verfügbar</small>
                  </div>

                  {availableBreads.length === 0 ? (
                    <div className="alert alert-warning">
                      <strong>Keine Brote verfügbar</strong>
                      <p className="mb-0">
                        Für diese Abholstation und Woche sind keine Brote mit verfügbarer Kapazität vorhanden.
                      </p>
                    </div>
                  ) : (
                    <div className="d-flex flex-wrap gap-3">
                      {availableBreads.map(bread => {
                        const contents = contentsMap[bread.id!] || [];

                        return (
                          <div key={bread.id} style={{ width: '280px', flex: '0 0 280px' }}>
                            <div
                              className="card h-100 shadow-sm"
                              style={{
                                border: '1px solid #dee2e6',
                                cursor: 'pointer',
                              }}
                              onClick={() => onSelect(bread.id!)}
                            >
                              {bread.picture ? (
                                <img
                                  src={bread.picture}
                                  alt={bread.name}
                                  className="card-img-top"
                                  style={{ height: '180px', objectFit: 'cover' }}
                                />
                              ) : (
                                <div
                                  className="d-flex align-items-center justify-content-center"
                                  style={{ height: '180px', backgroundColor: '#F5E6D3' }}
                                >
                                  <EggFried size={48} style={{ color: '#D4A574' }} />
                                </div>
                              )}

                              <div className="card-body d-flex flex-column">
                                <h6 className="card-title mb-0" style={{ color: '#8B4513' }}>
                                  {bread.name}
                                </h6>

                                {bread.weight && (
                                  <small className="text-muted mb-2">{Number(bread.weight).toFixed(0)}g</small>
                                )}

                                {bread.labels && bread.labels.length > 0 && (
                                  <div className="mb-2">
                                    {bread.labels.map(label => (
                                      <span
                                        key={label.id}
                                        className="badge me-1"
                                        style={{ backgroundColor: '#F5E6D3', color: '#8B4513', fontSize: '0.7rem' }}
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

                                {bread.availableCapacity !== undefined && bread.availableCapacity !== null && (
                                  <div className="mb-2">
                                    <small className="text-muted">
                                      Verfügbar: {bread.availableCapacity}
                                    </small>
                                  </div>
                                )}
                              </div>

                              <div className="card-footer text-center py-2" style={{ backgroundColor: '#8B4513', color: 'white' }}>
                                Auswählen
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};