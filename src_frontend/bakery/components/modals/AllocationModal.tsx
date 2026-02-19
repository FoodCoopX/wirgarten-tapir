import React, { useState, useEffect } from 'react';
import { InfoCircle, ExclamationTriangle, Save, XLg, ArrowRepeat } from 'react-bootstrap-icons';
import { BakeryApi, PickupLocationsApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import type { BreadList, BreadCapacityPickupStation } from '../../../api-client/models';

interface AllocationModalProps {
  isOpen: boolean;
  onClose: () => void;
  year: number;
  week: number;
  day: number;
  dayLabel: string;
  csrfToken: string;
}

interface PickupStation {
  id: number;
  name: string;
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
  csrfToken,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);
  const pickupLocationsApi = useApi(PickupLocationsApi, csrfToken);

  const [breads, setBreads] = useState<BreadList[]>([]);
  const [pickupStations, setPickupStations] = useState<PickupStation[]>([]);
  const [loading, setLoading] = useState(true);
  const [allocations, setAllocations] = useState<AllocationData>({});
  const [saving, setSaving] = useState(false);
  const [initialAllocations, setInitialAllocations] = useState<AllocationData>({});

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen, year, week, day]);

  const loadData = async () => {
    setLoading(true);
    try {
      const dayOfWeek = day + 1;

      const [breadsResponse, stationsResponse] = await Promise.all([
        bakeryApi.bakeryBreadsListList({ isActive: true }),
        pickupLocationsApi.pickupLocationsOpeningTimesList({}),
      ]);

      // Filter stations by day
      const filteredStations: PickupStation[] = (stationsResponse as any[])
        .filter((s: any) => s.day === dayOfWeek)
        .map((s: any) => ({ id: s.id, name: s.pickupLocationName || s.name }));

      setBreads(breadsResponse);
      setPickupStations(filteredStations);

      // Load existing capacities
      const stationIds = filteredStations.map(s => s.id);
      let capacities: BreadCapacityPickupStation[] = [];
      if (stationIds.length > 0) {
        capacities = await bakeryApi.bakeryBreadCapacityPickupStationList({
          year,
          week,
          pickupStationIds: stationIds,
        });
      }

      // Initialize allocations (stations × breads)
      const initial: AllocationData = {};
      filteredStations.forEach(station => {
        initial[station.id] = {};
        breadsResponse.forEach(bread => {
          const existingCapacity = (capacities as any[]).find(
            (c: any) => c.pickupStationDay === station.id && c.bread === bread.id
          );
          initial[station.id][bread.id!] =
            existingCapacity ? existingCapacity.capacity.toString() : '';
        });
      });

      setAllocations(initial);
      setInitialAllocations(JSON.parse(JSON.stringify(initial)));
    } catch (error) {
      console.error('Failed to load data:', error);
      alert('Fehler beim Laden der Daten');
    } finally {
      setLoading(false);
    }
  };

  const handleCellChange = (stationId: string, breadId: string, value: string) => {
    const sanitized = value.trim().toLowerCase();
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

  const handleSaveAndClose = async () => {
    setSaving(true);
    try {
      const updates: Array<{
        pickup_station_day: number;
        bread: string;
        capacity: number | null;
      }> = [];

      Object.entries(allocations).forEach(([stationId, breadAllocs]) => {
        Object.entries(breadAllocs).forEach(([breadId, value]) => {
          const initialValue = initialAllocations[stationId]?.[breadId] || '';

          if (value !== initialValue) {
            if (value === '' || value === 'x') {
              updates.push({
                pickup_station_day: Number(stationId),
                bread: breadId,
                capacity: null,
              });
            } else {
              updates.push({
                pickup_station_day: Number(stationId),
                bread: breadId,
                capacity: Number(value),
              });
            }
          }
        });
      });

      if (updates.length > 0) {
        await bakeryApi.bakeryBreadCapacityPickupStationBulkUpdateCreate({
          body: {
            year,
            week,
            updates,
          } as any,
        });
      }

      onClose();
    } catch (error) {
      console.error('Failed to save capacities:', error);
      alert('Fehler beim Speichern der Mengen');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

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
        <div className="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
          <div className="modal-content">
            <div
              className="modal-header"
              style={{ backgroundColor: '#D4A574', color: 'white' }}
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
                  <div className="spinner-border" style={{ color: '#D4A574' }} />
                  <p className="mt-2 text-muted">Lade Daten...</p>
                </div>
              ) : (
                <>
                  {breads.length === 0 ? (
                    <div className="alert alert-info d-flex align-items-center" role="alert">
                      <InfoCircle size={20} className="me-2" />
                      Keine Brote für diesen Tag verfügbar. Aktiviere zuerst Brote im Wochenplan.
                    </div>
                  ) : pickupStations.length === 0 ? (
                    <div className="alert alert-warning d-flex align-items-center" role="alert">
                      <ExclamationTriangle size={20} className="me-2" />
                      Keine Abholorte für {dayLabel} konfiguriert.
                    </div>
                  ) : (
                    <div className="card">
                      <div className="card-body p-0">
                        <div className="table-responsive">
                          <table className="table table-bordered table-hover mb-0">
                            <thead style={{ backgroundColor: '#F5E6D3', position: 'sticky', top: 0, zIndex: 10 }}>
                              <tr>
                                <th style={{ minWidth: '150px' }}>Abholort</th>
                                {breads.map(bread => (
                                  <th key={bread.id} className="text-center" style={{ minWidth: '120px' }}>
                                    {bread.name}
                                  </th>
                                ))}
                                <th className="text-center" style={{ minWidth: '80px', backgroundColor: '#EDE0D0' }}>
                                  Σ
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              {pickupStations.map(station => {
                                const rowSum = breads.reduce((sum, bread) => {
                                  const val = allocations[station.id]?.[bread.id!] || '';
                                  if (val === 'x') return Infinity;
                                  if (val === '' || isNaN(Number(val))) return sum;
                                  return sum + Number(val);
                                }, 0);

                                return (
                                  <tr key={station.id}>
                                    <td className="fw-bold align-middle">
                                      {station.name}
                                    </td>
                                    {breads.map(bread => (
                                      <td key={bread.id} className="p-1">
                                        <input
                                          type="text"
                                          className="form-control form-control-sm text-center"
                                          value={allocations[station.id]?.[bread.id!] || ''}
                                          onChange={(e) => handleCellChange(String(station.id), bread.id!, e.target.value)}
                                          placeholder="-"
                                          style={{
                                            minWidth: '60px',
                                            fontFamily: 'monospace',
                                            fontSize: '14px',
                                          }}
                                        />
                                      </td>
                                    ))}
                                    <td
                                      className="text-center align-middle fw-bold"
                                      style={{ backgroundColor: '#F5E6D3', fontFamily: 'monospace', fontSize: '14px' }}
                                    >
                                      {rowSum === Infinity ? '∞' : rowSum === 0 ? '-' : rowSum}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                            <tfoot>
                              <tr style={{ backgroundColor: '#EDE0D0' }}>
                                <td className="fw-bold" style={{ backgroundColor: '#EDE0D0' }}>Σ Gesamt</td>
                                {breads.map(bread => {
                                  const colSum = pickupStations.reduce((sum, station) => {
                                    const val = allocations[station.id]?.[bread.id!] || '';
                                    if (val === 'x') return Infinity;
                                    if (val === '' || isNaN(Number(val))) return sum;
                                    return sum + Number(val);
                                  }, 0);

                                  return (
                                    <td
                                      key={bread.id}
                                      className="text-center fw-bold align-middle"
                                      style={{ fontFamily: 'monospace', fontSize: '14px', backgroundColor: '#EDE0D0' }}
                                    >
                                      {colSum === Infinity ? '∞' : colSum === 0 ? '-' : colSum}
                                    </td>
                                  );
                                })}
                                <td
                                  className="text-center fw-bold align-middle"
                                  style={{ backgroundColor: '#D4A574', color: 'white', fontFamily: 'monospace', fontSize: '14px' }}
                                >
                                  {(() => {
                                    const totalSum = pickupStations.reduce((total, station) => {
                                      return breads.reduce((sum, bread) => {
                                        const val = allocations[station.id]?.[bread.id!] || '';
                                        if (val === 'x') return Infinity;
                                        if (val === '' || isNaN(Number(val))) return sum;
                                        return sum + Number(val);
                                      }, total);
                                    }, 0);
                                    return totalSum === Infinity ? '∞' : totalSum === 0 ? '-' : totalSum;
                                  })()}
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
                <XLg size={14} />
                Abbrechen
              </button>
              <button
                type="button"
                className="btn d-inline-flex align-items-center gap-1"
                style={{ backgroundColor: '#8B6F47', color: 'white' }}
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
                    <Save size={14} />
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