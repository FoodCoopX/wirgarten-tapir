import React, { useState, useEffect } from 'react';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import type { BreadList, BreadContent, BreadDelivery, PickupLocation } from '../../../api-client/models';
import { YearWeekSelectorCard } from './YearWeekSelectorCard';
import { BreadSelectionModal } from '../modals/BreadSelectionModal';
import dayjs from 'dayjs';
import isoWeek from "dayjs/plugin/isoWeek";

dayjs.extend(isoWeek);

interface ChooseBreadsCardProps {
  memberId: string;
  csrfToken: string;
  chooseStationPerBread: boolean;
}

const currentWeek = dayjs().isoWeek();
const currentYear = dayjs().year();

export const ChooseBreadsCard: React.FC<ChooseBreadsCardProps> = ({
  chooseStationPerBread,
  memberId,
  csrfToken,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);

  const [breads, setBreads] = useState<BreadList[]>([]);
  const [contentsMap, setContentsMap] = useState<{ [breadId: string]: BreadContent[] }>({});
  const [pickupLocations, setPickupLocations] = useState<PickupLocation[]>([]);
  const [deliveries, setDeliveries] = useState<BreadDelivery[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [selectedWeek, setSelectedWeek] = useState(currentWeek);
  const [selectedYear, setSelectedYear] = useState(currentYear);
  const [modalOpen, setModalOpen] = useState<string | null>(null);
  const [editingLocation, setEditingLocation] = useState<string | null>(null);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line
  }, [memberId, selectedWeek, selectedYear]);

  const loadData = async () => {
    setLoading(true);
    try {
      const allBreads = await bakeryApi.bakeryBreadsListList({ isActive: true });
      setBreads(allBreads);

      const contentsResults = await Promise.all(
        allBreads.map(async (bread) => {
          try {
            const contents = await bakeryApi.bakeryBreadsListContentsList({ id: bread.id! });
            return { breadId: bread.id, contents };
          } catch {
            return { breadId: bread.id, contents: [] };
          }
        })
      );

      const map: { [breadId: string]: BreadContent[] } = {};
      contentsResults.forEach(({ breadId, contents }) => {
        map[breadId!] = [...contents].sort((a, b) => Number(b.amount) - Number(a.amount));
      });
      setContentsMap(map);

      // const locations = await bakeryApi.pickupLocationsApiListList();
      const locations = [];
      setPickupLocations(locations);

      const breadDeliveries = await bakeryApi.bakeryBreadDeliveriesList({
        memberId,
        year: selectedYear,
        deliveryWeek: selectedWeek,
      });

      const sortedDeliveries = [...breadDeliveries].sort((a, b) => 
        (a.slotNumber || 0) - (b.slotNumber || 0)
      );

      setDeliveries(sortedDeliveries);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load data:', error);
      setLoading(false);
    }
  };

  const handlePickupLocationChange = async (deliveryId: string, pickupLocationId: string | null) => {
    if (!pickupLocationId) return;

    setSaving(deliveryId);
    try {
      if (chooseStationPerBread) {
        await bakeryApi.bakeryBreadDeliveriesPartialUpdate({
          id: deliveryId,
          patchedBreadDeliveryRequest: {
            pickupLocation: pickupLocationId,
          },
        });

        setDeliveries(deliveries.map(d => 
          d.id === deliveryId ? { ...d, pickupLocation: pickupLocationId } : d
        ));
      } else {
        await Promise.all(
          deliveries.map(delivery =>
            bakeryApi.bakeryBreadDeliveriesPartialUpdate({
              id: delivery.id!,
              patchedBreadDeliveryRequest: {
                pickupLocation: pickupLocationId,
              },
            })
          )
        );

        setDeliveries(deliveries.map(d => ({ ...d, pickupLocation: pickupLocationId })));
      }
      setEditingLocation(null);
    } catch (error) {
      console.error('Failed to save pickup location:', error);
      alert('Speichern der Abholstation fehlgeschlagen');
    } finally {
      setSaving(null);
    }
  };

  const handleBreadSelected = async (deliveryId: string, breadId: string) => {
    const delivery = deliveries.find(d => d.id === deliveryId);
    if (!delivery || !delivery.pickupLocation) return;

    setSaving(deliveryId);
    try {
      await bakeryApi.bakeryBreadDeliveriesPartialUpdate({
        id: deliveryId,
        patchedBreadDeliveryRequest: {
          bread: breadId,
        },
      });

      setModalOpen(null);
      await loadData();
    } catch (error) {
      console.error('Failed to save bread selection:', error);
      alert('Speichern des Brotes fehlgeschlagen');
    } finally {
      setSaving(null);
    }
  };

  const handleRemoveBread = async (deliveryId: string) => {
    setSaving(deliveryId);
    try {
      await bakeryApi.bakeryBreadDeliveriesPartialUpdate({
        id: deliveryId,
        patchedBreadDeliveryRequest: {
          bread: null,
        },
      });

      setDeliveries(deliveries.map(d => 
        d.id === deliveryId ? { ...d, bread: null, breadName: undefined } : d
      ));
    } catch (error) {
      console.error('Failed to remove bread:', error);
      alert('Löschen des Brotes fehlgeschlagen');
    } finally {
      setSaving(null);
    }
  };



  const maxBreads = deliveries.length;

  return (
    <div>
      <YearWeekSelectorCard
        selectedYear={selectedYear}
        selectedWeek={selectedWeek}
        onYearChange={setSelectedYear}
        onWeekChange={setSelectedWeek}
      />

      {/* Instructions */}
      <div className="alert alert-info mb-3 mt-3">
          <strong>Du hast {maxBreads} Brot-Anteil{maxBreads !== 1 ? 'e' : ''} für diese Woche.</strong>
        <br />
        <small>
          {chooseStationPerBread ? (
            <>
              Hier kannst du für jeden Anteil den Abholort ändern (falls gewünscht) und eine verfügbare Brotsorte auswählen.
            </>
          ) : (
            <>
              Wähle den Abholort für alle deine Brote und anschließend die gewünschten Brotsorten.
            </>
          )}
        </small>
      </div>

      {/* Bread Delivery Slots */}
      <div className="row g-3">
        {deliveries.map((delivery, index) => {
          const selectedLocation = pickupLocations.find(l => l.id === delivery.pickupLocation);
          const isFirstSlot = index === 0;
          const canChangeLocation = chooseStationPerBread || isFirstSlot;
          const isEditingThisLocation = editingLocation === delivery.id;
          
          return (
            <div key={delivery.id} className="col-12">
              <div className="card">
                <div 
                  className="card-header"
                  style={{ backgroundColor: '#D4A574', color: 'white' }}
                >
                  <h6 className="mb-0">Brotanteil {index + 1}</h6>
                </div>
                <div className="card-body">
                  {/* Pickup Location Row */}
                  <div className="mb-3">
                    <div className="d-flex align-items-center justify-content-between">
                      <div className="flex-grow-1">
                        <strong>Abholort:</strong>{' '}
                        {isEditingThisLocation ? (
                        <select
                          className="form-select form-select-sm d-inline-block w-auto ms-2"
                          value={delivery.pickupLocation || ''}
                          onChange={(e) => handlePickupLocationChange(delivery.id!, e.target.value || null)}
                          disabled={saving === delivery.id}
                          autoFocus
                        >
                          <option value="">-- Station wählen --</option>
                          {pickupLocations.map(location => (
                            <option key={location.id} value={location.id}>
                              {location.name}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className="text-muted">
                          {delivery.pickupLocationName || selectedLocation?.name || 'Noch nicht gewählt'}
                        </span>
                      )}
                        {!chooseStationPerBread && !isFirstSlot && (
                          <small className="text-muted ms-2">(wird mit Brotanteil 1 synchronisiert)</small>
                        )}
                      </div>
                      {canChangeLocation && !isEditingThisLocation && (
                        <button
                          className="btn btn-sm btn-outline-secondary"
                          onClick={() => setEditingLocation(delivery.id!)}
                          disabled={saving === delivery.id}
                        >
                          {delivery.pickupLocation ? 'Ändern' : 'Auswählen'}
                        </button>
                      )}
                      {isEditingThisLocation && (
                        <button
                          className="btn btn-sm btn-outline-secondary ms-2"
                          onClick={() => setEditingLocation(null)}
                        >
                          Abbrechen
                        </button>
                      )}
                      {saving === delivery.id && (
                        <span className="spinner-border spinner-border-sm ms-2" />
                      )}
                    </div>
                  </div>

                  <hr />

                  {/* Bread Selection Row */}
                  <div>
                    <div className="d-flex align-items-center justify-content-between">
                      <div className="flex-grow-1">
                        <strong>Brotsorte:</strong>{' '}
                        <span className="text-muted">
                          {delivery.breadName || 'Noch nicht gewählt'}
                        </span>
                      </div>
                      <div className="d-flex gap-2">
                        <button
                          className="btn btn-sm"
                          style={{ backgroundColor: '#8B4513', color: 'white' }}
                          onClick={() => setModalOpen(delivery.id!)}
                          disabled={!delivery.pickupLocation || saving === delivery.id}
                        >
                          {delivery.bread ? 'Ändern' : 'Auswählen'}
                        </button>
                        {delivery.bread && (
                          <button
                            className="btn btn-sm btn-outline-danger"
                            onClick={() => handleRemoveBread(delivery.id!)}
                            disabled={saving === delivery.id}
                          >
                            Entfernen
                          </button>
                        )}
                      </div>
                    </div>
                    {!delivery.pickupLocation && (
                      <div className="alert alert-warning mt-2 mb-0 py-2">
                        <small>
                          {isFirstSlot || chooseStationPerBread 
                            ? '⚠️ Bitte zuerst eine Abholstation auswählen' 
                            : '⚠️ Bitte eine Station bei Brotanteil 1 auswählen'}
                        </small>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Bread Selection Modal */}
              {modalOpen === delivery.id && delivery.pickupLocation && (
                <BreadSelectionModal
                  breads={breads}
                  contentsMap={contentsMap}
                  pickupLocationId={delivery.pickupLocation}
                  pickupLocationName={delivery.pickupLocationName || selectedLocation?.name || ''}
                  selectedWeek={selectedWeek}
                  selectedYear={selectedYear}
                  onSelect={(breadId) => handleBreadSelected(delivery.id!, breadId)}
                  onClose={() => setModalOpen(null)}
                  csrfToken={csrfToken}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};