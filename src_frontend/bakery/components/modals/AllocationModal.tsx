import React, { useState, useEffect } from 'react';
import { Modal } from 'react-bootstrap';
import { InfoCircle, ExclamationTriangle } from 'react-bootstrap-icons';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import { handleRequestError } from '../../../utils/handleRequestError';
import TapirButton from '../../../components/TapirButton';
import type { 
  BreadList, 
  PickupLocationDeliveryDay,
} from '../../../api-client/models';
import '../../styles/bakery_styles.css';

interface AllocationTableProps {
  activeBreads: BreadList[];
  pickupLocations: PickupLocationDeliveryDay[];
  allocations: AllocationData;
  onCellChange: (pickupLocationId: string, breadId: string, value: string) => void;
}

const AllocationTable: React.FC<AllocationTableProps> = ({
  activeBreads,
  pickupLocations,
  allocations,
  onCellChange,
}) => {
  const sumValues = (values: string[]): number => {
    return values.reduce((sum, val) => {
      if (val === '' || Number.isNaN(Number(val))) return sum;
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
      return total + sumValues(activeBreads.map(bread => allocations[location.id]?.[bread.id!] || ''));
    }, 0);
  };

  const formatSum = (sum: number): string => {
    if (sum === 0) return '-';
    return String(sum);
  };

  return (
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
                          onChange={(e) => onCellChange(location.id, bread.id!, e.target.value)}
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
  );
};

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
  [pickupLocationId: string]: {
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

  const [pickupLocations, setPickupLocations] = useState<PickupLocationDeliveryDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [allocations, setAllocations] = useState<AllocationData>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen, year, week, day]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !saving) {
      e.preventDefault();
      handleSaveAndClose();
    }
  };

  const loadData = () => {
    setLoading(true);
   

    bakeryApi.pickupLocationsApiPickupLocationsByDeliveryDayRetrieve({ dayOfWeek : day })
      .then((locationsResponse) => {
        setPickupLocations(locationsResponse.pickupLocations);

        const locationIds = locationsResponse.pickupLocations.map(s => s.id);

        return bakeryApi.bakeryBreadCapacityPickupLocationList({
          year,
          week,
          pickupLocationIds: locationIds,
        }).then((capacities) => {
          const initial: AllocationData = {};
          locationsResponse.pickupLocations.forEach(location => {
            initial[location.id] = {};
          });
          capacities.forEach((capacity) => {
            initial[capacity.pickupLocation][capacity.bread] = String(capacity.capacity);
          });

          setAllocations(initial);
        });
      })
      .catch((error) => {
        handleRequestError(error, 'Fehler beim Laden der Daten');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const handleCellChange = (pickupLocationId: string, breadId: string, value: string) => {
    const sanitized = value.trim();
    if (sanitized !== '' && Number.isNaN(Number(sanitized))) {
      return;
    }

    setAllocations(prev => ({
      ...prev,
      [pickupLocationId]: {
        ...prev[pickupLocationId],
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

    Object.entries(allocations).forEach(([pickupLocationId, breadAllocs]) => {
      Object.entries(breadAllocs).forEach(([breadId, value]) => {
        updates.push({
          pickupLocation: pickupLocationId,
          bread: breadId,
          capacity: value === '' ? null : Number(value),
        });
      });
    });

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
        handleRequestError(error, 'Fehler beim Speichern der Mengen');
      })
      .finally(() => {
        setSaving(false);
      });
  };

  const getModalSize = (): 'lg' | 'xl' | undefined => {
    const count = activeBreads.length;
    if (count <= 2) return 'lg';
    if (count <= 4) return 'xl';
    return undefined;
  };

  const renderModalBodyContent = () => {
    if (loading) {
      return (
        <div className="text-center py-5">
          <div className="spinner-border spinner-bakery-primary" />
          <p className="mt-2 text-muted">Lade Daten...</p>
        </div>
      );
    }

    if (activeBreads.length === 0) {
      return (
        <div className="alert alert-info d-flex align-items-center" role="alert">
          <InfoCircle size={20} className="me-2" />
          Keine Brote für diesen Tag verfügbar. Aktiviere zuerst Brote im Wochenplan.
        </div>
      );
    }

    if (pickupLocations.length === 0) {
      return (
        <div className="alert alert-warning d-flex align-items-center" role="alert">
          <ExclamationTriangle size={20} className="me-2" />
          Keine Abholorte für {dayLabel} konfiguriert.
        </div>
      );
    }

    return (
      <AllocationTable
        activeBreads={activeBreads}
        pickupLocations={pickupLocations}
        allocations={allocations}
        onCellChange={handleCellChange}
      />
    );
  };

  return (
    <Modal
      show={isOpen}
      onHide={onClose}
      size={activeBreads.length > 4 ? undefined : getModalSize()}
      fullscreen={activeBreads.length > 4 || undefined}
      centered
      scrollable
      onKeyDown={handleKeyDown}
    >
      <Modal.Header closeButton className="header-white-on-middle-brown">
        <Modal.Title>
          <h5 className="mb-0">Mengen zuweisen - {dayLabel}, KW {week}/{year}</h5>
        </Modal.Title>
      </Modal.Header>

      <Modal.Body className="p-3">
        {renderModalBodyContent()}
      </Modal.Body>

      <Modal.Footer>
        <TapirButton
          variant="secondary"
          text="Abbrechen"
          icon="close"
          onClick={onClose}
          disabled={saving}
          size="sm"
        />
        <TapirButton
          variant=""
          className="dark-brown-button"
          text="Speichern & Schließen"
          icon="save"
          onClick={handleSaveAndClose}
          disabled={saving}
          loading={saving}
          size="sm"
        />
      </Modal.Footer>
    </Modal>
  );
};