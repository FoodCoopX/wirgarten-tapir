import React, { useState, useEffect } from 'react';
import { InfoCircle, ExclamationTriangle, ArrowRepeat } from 'react-bootstrap-icons';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import type { 
  BreadList, 
  PickupLocationsByDeliveryDayResponse 
} from '../../../api-client/models';
import '../../styles/bakery_styles.css';

interface AllocationModalProps {
  isOpen: boolean;
  onClose: () => void;
  year: number;
  week: number;
  day: number;
  dayLabel: string;
  activeBreads: BreadList[];
  csrfToken: string;
}

interface AllocationData {
  [stationId: string]: {
    [breadId: string]: string;
  };
}

export const AllocationModal: React.FC<AllocationModalProps> = ({
  isOpen,
  onClose,
  year,
  week,
  day,
  dayLabel,
  activeBreads,
  csrfToken,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);

  const [pickupLocations, setPickupLocations] = useState<PickupLocationsByDeliveryDayResponse['pickupLocations']>([]);
  const [loading, setLoading] = useState(true);
  const [allocations, setAllocations] = useState<AllocationData>({});
  const [saving, setSaving] = useState(false);
  const [initialAllocations, setInitialAllocations] = useState<AllocationData>({});

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen, year, week, day]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && !saving) {
        e.preventDefault();
        handleSaveAndClose();
      }
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, saving, allocations, initialAllocations]);

  const loadData = () => {
    setLoading(true);
   

    bakeryApi.pickupLocationsApiPickupLocationsByDeliveryDayRetrieve({ dayOfWeek : day })
      .then((locationsResponse) => {
        setPickupLocations(locationsResponse.pickupLocations);

        // Load existing capacities for these pickup locations
        const locationIds = locationsResponse.pickupLocations.map(s => s.id);
        
        if (locationIds.length === 0) {
          const initial: AllocationData = {};
          setAllocations(initial);
          setInitialAllocations(JSON.parse(JSON.stringify(initial)));
          return;
        }

        return bakeryApi.bakeryBreadCapacityPickupLocationList({
          year,
          week,
          pickupLocationIds: locationIds,
        }).then((capacities) => {
          // Initialize allocations (locations × breads)
          const initial: AllocationData = {};
          locationsResponse.pickupLocations.forEach(location => {
            initial[location.id] = {};
            activeBreads.forEach(bread => {
              const existingCapacity = capacities.find(
                (c) => c.pickupLocation === location.id && c.bread === bread.id
              );
              initial[location.id][bread.id!] =
                existingCapacity ? String(existingCapacity.capacity) : '';
            });
          });

          setAllocations(initial);
          setInitialAllocations(JSON.parse(JSON.stringify(initial)));
        });
      })
      .catch((error) => {
        console.error('Failed to load data:', error);
        alert('Fehler beim Laden der Daten');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const handleCellChange = (stationId: string, breadId: string, value: string) => {
    const sanitized = value.trim().toLowerCase();
    // Allow empty, 'x', or numeric values only
    if (sanitized !== '' && sanitized !== 'x' && isNaN(Number(sanitized))) {
      return;
    }

    setAllocations(prev => ({
      ...prev,
      [stationId]: {
        ...prev[stationId],
        [breadId]: sanitized,
      },
    }));
  };

  const handleSaveAndClose = () => {
    setSaving(true);

    const updates: Array<{
      pickupLocation: string;  
      bread: string;
      capacity: number | null;
    }> = [];

    // Compare current allocations with initial allocations
    Object.entries(allocations).forEach(([stationId, breadAllocs]) => {
      Object.entries(breadAllocs).forEach(([breadId, value]) => {
        const initialValue = initialAllocations[stationId]?.[breadId] || '';

        // Only save if value changed
        if (value !== initialValue) {
          const capacityValue = value === '' || value === 'x' ? null : Number(value);
          
          updates.push({
            pickupLocation: stationId,  
            bread: breadId,
            capacity: capacityValue,
          });
        }
      });
    });

    if (updates.length === 0) {
      onClose();
      setSaving(false);
      return;
    }

    bakeryApi.bakeryBreadCapacityPickupLocationBulkUpdateCreate({
      breadCapacityBulkUpdateRequest: {
        year,
        deliveryWeek: week,
        updates,
      },
    })
      .then(() => {
        onClose();
      })
      .catch((error) => {
        console.error('Failed to save capacities:', error);
        alert('Fehler beim Speichern der Mengen');
      })
      .finally(() => {
        setSaving(false);
      });
  };

  if (!isOpen) return null;

  const sumValues = (values: string[]): number => {
    return values.reduce((sum, val) => {
      if (val === 'x') return Infinity;
      if (val === '' || isNaN(Number(val))) return sum;
      return sum + Number(val);
    }, 0);
  };

  const getRowSum = (locationId: string): number => {
    return sumValues(activeBreads.map(bread => allocations[locationId]?.[bread.id!] || ''));
  };

  const getColSum = (breadId: string): number => {
    return sumValues(pickupLocations.map(location => allocations[location.id]?.[breadId] || ''));
  };

  const getTotalSum = (): number => {
    return pickupLocations.reduce((total, location) => {
      const locationSum = sumValues(activeBreads.map(bread => allocations[location.id]?.[bread.id!] || ''));
      if (locationSum === Infinity) return Infinity;
      return total + locationSum;
    }, 0);
  };

  const formatSum = (sum: number): string => {
    if (sum === Infinity) return '∞';
    if (sum === 0) return '-';
    return String(sum);
  };

  const getModalClass = () => {
    const count = activeBreads.length;
    if (count <= 2) return 'modal-lg';      
    if (count <= 4) return 'modal-xl';      
    return '';                               
  };

  const getModalStyle = () => {
    if (activeBreads.length > 4) {
      return { maxWidth: '95vw' };          
    }
    return {};
  };

  return (
    <>
      <div
        className="modal-backdrop fade show"
        onClick={onClose}
        style={{ zIndex: 1040 }}
      />
      <div
        className="modal fade show d-block"
        tabIndex={-1}
        style={{ zIndex: 1050 }}
      >
        <div 
          className={`modal-dialog ${getModalClass()} modal-dialog-centered modal-dialog-scrollable`}
          style={getModalStyle()}
        >
          <div className="modal-content">
            <div
              className="modal-header header-white-on-middle-brown"
            >
              <h5 className="modal-title">
                Mengen zuweisen - {dayLabel}, KW {week}/{year}
              </h5>
              {saving && (
                <span className="badge bg-warning ms-2">
                  <ArrowRepeat size={14} className="me-1 spinner-grow-sm" />
                  Speichert...
                </span>
              )}
              <button
                type="button"
                className="btn-close btn-close-white"
                onClick={onClose}
              />
            </div>

            <div className="modal-body p-3">
              {loading ? (
                <div className="text-center py-5">
                  <div className="spinner-border spinner-bakery-primary" />
                  <p className="mt-2 text-muted">Lade Daten...</p>
                </div>
              ) : (
                <>
                  {activeBreads.length === 0 ? (
                    <div className="alert alert-info d-flex align-items-center" role="alert">
                      <InfoCircle size={20} className="me-2" />
                      Keine Brote für diesen Tag verfügbar. Aktiviere zuerst Brote im Wochenplan.
                    </div>
                  ) : pickupLocations.length === 0 ? (
                    <div className="alert alert-warning d-flex align-items-center" role="alert">
                      <ExclamationTriangle size={20} className="me-2" />
                      Keine Abholorte für {dayLabel} konfiguriert.
                    </div>
                  ) : (
                    <div className="card">
                      <div className="card-body p-0">
                        <div className="table-responsive">
                          <table className="table table-bordered table-hover mb-0">
                            <thead className="table-header-bakery" style={{ position: 'sticky', top: 0, zIndex: 10 }}>
                              <tr>
                                <th style={{ minWidth: '150px' }}>Abholort</th>
                                {activeBreads.map(bread => (
                                  <th key={bread.id} className="text-center" style={{ minWidth: '120px' }}>
                                    {bread.name}
                                  </th>
                                ))}
                                <th className="text-center bg-bakery-cream" style={{ minWidth: '80px' }}>
                                  Σ
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              {pickupLocations.map(location => {
                                const rowSum = getRowSum(location.id);

                                return (
                                  <tr key={location.id}>
                                    <td className="fw-bold align-middle">
                                      {location.name}
                                    </td>
                                    {activeBreads.map(bread => (
                                      <td key={bread.id} className="p-1">
                                        <input
                                          type="text"
                                          className="form-control form-control-sm text-center"
                                          value={allocations[location.id]?.[bread.id!] || ''}
                                          onChange={(e) => handleCellChange(location.id, bread.id!, e.target.value)}
                                          placeholder="-"
                                          style={{
                                            minWidth: '60px',
                                            fontSize: '14px',
                                          }}
                                        />
                                      </td>
                                    ))}
                                    <td
                                      className="text-center align-middle fw-bold bg-bakery-cream"
                                      style={{ fontSize: '14px' }}
                                    >
                                      {formatSum(rowSum)}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                            <tfoot>
                              <tr className="bg-bakery-cream">
                                <td className="fw-bold bg-bakery-cream">Σ Gesamt</td>
                                {activeBreads.map(bread => (
                                    <td
                                      key={bread.id}
                                      className="text-center fw-bold align-middle bg-bakery-cream"
                                      style={{  fontSize: '14px' }}
                                    >
                                      {formatSum(getColSum(bread.id!))}
                                    </td>
                                ))}
                                <td
                                  className="text-center fw-bold align-middle bg-bakery-primary text-white"
                                  style={{ fontSize: '14px' }}
                                >
                                  {formatSum(getTotalSum())}
                                </td>
                              </tr>
                            </tfoot>
                          </table>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary d-inline-flex align-items-center gap-1"
                onClick={onClose}
                disabled={saving}
              >
                Abbrechen
              </button>
              <button
                type="button"
                className="btn d-inline-flex align-items-center gap-1 dark-brown-button"
                onClick={handleSaveAndClose}
                disabled={saving}
              >
                {saving ? (
                  <>
                    <span className="spinner-border spinner-border-sm" />
                    Speichert...
                  </>
                ) : (
                  <>
                    Speichern & Schließen
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};