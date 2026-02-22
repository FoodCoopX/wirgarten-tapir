import React, { useState, useEffect } from 'react';
import { EggFried, Plus, Dash, CheckCircleFill } from 'react-bootstrap-icons';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import { BrownCircleButton } from '../BrownCircleButton';
import type { BreadList, BreadContent, Subscription, BreadDelivery, PickupLocation } from '../../../api-client/models';
import { YearWeekSelectorCard } from './YearWeekSelectorCard';
import dayjs from 'dayjs';
import isoWeek from "dayjs/plugin/isoWeek";

dayjs.extend(isoWeek);

interface ChooseBreadsCardProps {
  memberId: string;
  csrfToken: string;
}

interface BreadSelection {
  id: string; // unique ID for this selection slot
  breadId: string | null;
  pickupLocationId: string | null;
  deliveryId?: string; // ID of existing BreadDelivery object
}

const currentWeek = dayjs().isoWeek();
const currentYear = dayjs().year();

export const ChooseBreadsCard: React.FC<ChooseBreadsCardProps> = ({
  memberId,
  csrfToken,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);

  const [breads, setBreads] = useState<BreadList[]>([]);
  const [contentsMap, setContentsMap] = useState<{ [breadId: string]: BreadContent[] }>({});
  const [pickupLocations, setPickupLocations] = useState<PickupLocation[]>([]);
  const [selections, setSelections] = useState<BreadSelection[]>([]);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null); // ID of slot being saved
  const [selectedWeek, setSelectedWeek] = useState(currentWeek);
  const [selectedYear, setSelectedYear] = useState(currentYear);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line
  }, [memberId, selectedWeek, selectedYear]);

  const loadData = async () => {
    setLoading(true);
    try {
      // Load breads
      const allBreads = await bakeryApi.bakeryBreadsListList({ isActive: true });
      setBreads(allBreads);

      // Load bread contents
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

      // Load pickup locations
      const locations = await bakeryApi.pickupLocationsApiDeliveryDaysRetrieve();
      // TODO: Adjust this once you have proper API endpoint for pickup locations
      setPickupLocations([]); // Replace with actual pickup locations from API

      // Load current week's deliveries
      const deliveries = await bakeryApi.bakeryBreadDeliveriesList({
        memberId,
        year: selectedYear,
        deliveryWeek: selectedWeek,
      });

      if (deliveries.length > 0) {
        // Load from current week
        setSubscription(deliveries[0].subscription as Subscription);
        const loaded: BreadSelection[] = deliveries.map((d, idx) => ({
          id: `slot-${idx}`,
          breadId: d.bread || null,
          pickupLocationId: d.pickupLocation || null,
          deliveryId: d.id,
        }));
        setSelections(loaded);
      } else {
        // Try to load from previous week for pre-selection
        const prevWeek = selectedWeek === 1 ? 52 : selectedWeek - 1;
        const prevYear = selectedWeek === 1 ? selectedYear - 1 : selectedYear;
        
        const prevDeliveries = await bakeryApi.bakeryBreadDeliveriesList({
          memberId,
          year: prevYear,
          deliveryWeek: prevWeek,
        });

        if (prevDeliveries.length > 0) {
          // Pre-fill from previous week
          setSubscription(prevDeliveries[0].subscription as Subscription);
          const quantity = (prevDeliveries[0].subscription as Subscription).quantity || 0;
          const preselected: BreadSelection[] = Array.from({ length: quantity }, (_, idx) => {
            const prev = prevDeliveries[idx];
            return {
              id: `slot-${idx}`,
              breadId: prev ? prev.bread : null,
              pickupLocationId: prev ? prev.pickupLocation : (prevDeliveries[0].subscription as Subscription).pickupLocation || null,
            };
          });
          setSelections(preselected);
        } else {
          // Load subscription without deliveries
          // TODO: Load subscription from API
          // For now, create empty slots
          const quantity = 3; // Default, replace with actual subscription.quantity
          const empty: BreadSelection[] = Array.from({ length: quantity }, (_, idx) => ({
            id: `slot-${idx}`,
            breadId: null,
            pickupLocationId: null, // Pre-fill from subscription.pickup_location if available
          }));
          setSelections(empty);
        }
      }

      setLoading(false);
    } catch (error) {
      console.error('Failed to load data:', error);
      setLoading(false);
    }
  };

  const maxBreads = subscription?.quantity || selections.length;

  const handleBreadChange = async (slotId: string, breadId: string | null) => {
    const slot = selections.find(s => s.id === slotId);
    if (!slot) return;

    // Update locally
    const updated = selections.map(s => 
      s.id === slotId ? { ...s, breadId } : s
    );
    setSelections(updated);

    // Auto-save
    await saveSlot(slotId, breadId, slot.pickupLocationId);
  };

  const handlePickupLocationChange = async (slotId: string, pickupLocationId: string | null) => {
    const slot = selections.find(s => s.id === slotId);
    if (!slot) return;

    // Update locally
    const updated = selections.map(s => 
      s.id === slotId ? { ...s, pickupLocationId } : s
    );
    setSelections(updated);

    // Auto-save
    await saveSlot(slotId, slot.breadId, pickupLocationId);
  };

  const saveSlot = async (slotId: string, breadId: string | null, pickupLocationId: string | null) => {
    const slot = selections.find(s => s.id === slotId);
    if (!slot || !subscription) return;

    // Only save if both bread and pickup location are selected
    if (!breadId || !pickupLocationId) return;

    setSaving(slotId);
    try {
      if (slot.deliveryId) {
        // Update existing delivery
        await bakeryApi.bakeryBreadDeliveriesPartialUpdate({
          id: slot.deliveryId,
          patchedBreadDeliveryRequest: {
            bread: breadId,
            pickupLocation: pickupLocationId,
          },
        });
      } else {
        // Create new delivery
        const created = await bakeryApi.bakeryBreadDeliveriesCreate({
          breadDeliveryRequest: {
            subscription: subscription.id!,
            bread: breadId,
            pickupLocation: pickupLocationId,
            year: selectedYear,
            deliveryWeek: selectedWeek,
            slotNumber: selections.indexOf(slot) + 1,
          },
        });

        // Update slot with deliveryId
        const updated = selections.map(s => 
          s.id === slotId ? { ...s, deliveryId: created.id } : s
        );
        setSelections(updated);
      }
    } catch (error) {
      console.error('Failed to save slot:', error);
      alert('Speichern fehlgeschlagen');
    } finally {
      setSaving(null);
    }
  };

  const handleAddBread = (breadId: string) => {
    // Find first empty slot
    const emptySlot = selections.find(s => !s.breadId);
    if (emptySlot) {
      handleBreadChange(emptySlot.id, breadId);
    }
  };

  const handleRemoveBread = async (breadId: string) => {
    // Find first slot with this bread
    const slot = selections.find(s => s.breadId === breadId);
    if (!slot) return;

    setSaving(slot.id);
    try {
      // Delete from backend if it exists
      if (slot.deliveryId) {
        await bakeryApi.bakeryBreadDeliveriesDestroy({ id: slot.deliveryId });
      }

      // Clear locally
      const updated = selections.map(s => 
        s.id === slot.id ? { ...s, breadId: null, deliveryId: undefined } : s
      );
      setSelections(updated);
    } catch (error) {
      console.error('Failed to remove bread:', error);
      alert('Löschen fehlgeschlagen');
    } finally {
      setSaving(null);
    }
  };

  const getQuantityForBread = (breadId: string) => {
    return selections.filter(s => s.breadId === breadId).length;
  };

  const getFilledSlots = () => {
    return selections.filter(s => s.breadId && s.pickupLocationId).length;
  };

  if (loading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border" style={{ color: '#D4A574' }} />
        <p className="mt-2 text-muted">Lade Daten...</p>
      </div>
    );
  }

  return (
    <div>
      <YearWeekSelectorCard
        selectedYear={selectedYear}
        selectedWeek={selectedWeek}
        onYearChange={setSelectedYear}
        onWeekChange={setSelectedWeek}
      />

      {/* Instructions */}
      <div className="alert alert-info mb-3">
        <strong>Du darfst {maxBreads} Brote auswählen.</strong>
        <br />
        <small>
          Aktuell ausgewählt: {getFilledSlots()} / {maxBreads}
        </small>
      </div>

      {/* Selection Slots */}
      <div className="card mb-4">
        <div className="card-header" style={{ backgroundColor: '#D4A574', color: 'white' }}>
          <h6 className="mb-0">Deine Brot-Auswahl</h6>
        </div>
        <div className="card-body">
          {selections.map((slot, index) => (
            <div key={slot.id} className="row mb-3 align-items-center">
              <div className="col-auto">
                <strong style={{ color: '#8B4513' }}>#{index + 1}</strong>
              </div>
              <div className="col">
                <label className="form-label small mb-1">Brotsorte</label>
                <select
                  className="form-select form-select-sm"
                  value={slot.breadId || ''}
                  onChange={(e) => handleBreadChange(slot.id, e.target.value || null)}
                  disabled={saving === slot.id}
                >
                  <option value="">-- Brotsorte wählen --</option>
                  {breads.map(bread => (
                    <option key={bread.id} value={bread.id}>
                      {bread.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="col">
                <label className="form-label small mb-1">Abholstation</label>
                <select
                  className="form-select form-select-sm"
                  value={slot.pickupLocationId || ''}
                  onChange={(e) => handlePickupLocationChange(slot.id, e.target.value || null)}
                  disabled={saving === slot.id || !slot.breadId}
                >
                  <option value="">-- Station wählen --</option>
                  {pickupLocations.map(location => (
                    <option key={location.id} value={location.id}>
                      {location.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="col-auto">
                {saving === slot.id ? (
                  <span className="spinner-border spinner-border-sm" style={{ color: '#8B4513' }} />
                ) : slot.breadId && slot.pickupLocationId ? (
                  <CheckCircleFill size={20} style={{ color: '#28a745' }} />
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Bread Cards for Quick Selection */}
      <div className="d-flex flex-wrap gap-3">
        {breads.map(bread => {
          const qty = getQuantityForBread(bread.id!);
          const contents = contentsMap[bread.id!] || [];
          const hasEmptySlot = selections.some(s => !s.breadId);

          return (
            <div key={bread.id} style={{ width: '280px', flex: '0 0 280px' }}>
              <div
                className="card h-100 shadow-sm"
                style={{
                  border: qty > 0 ? '2px solid #8B4513' : '1px solid #dee2e6',
                  opacity: !hasEmptySlot && qty === 0 ? 0.6 : 1,
                }}
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

                  <div className="d-flex align-items-center justify-content-center gap-2 mt-auto">
                    <BrownCircleButton
                      active={qty > 0}
                      onClick={() => handleRemoveBread(bread.id!)}
                      disabled={qty === 0 || saving !== null}
                    >
                      <Dash size={18} />
                    </BrownCircleButton>

                    <span
                      className="fw-bold text-center"
                      style={{ minWidth: '32px', fontSize: '1.1rem', color: qty > 0 ? '#8B4513' : '#adb5bd' }}
                    >
                      {qty}
                    </span>

                    <button
                      className="btn btn-sm rounded-circle"
                      style={{
                        width: '32px',
                        height: '32px',
                        backgroundColor: '#8B4513',
                        color: 'white',
                      }}
                      onClick={() => handleAddBread(bread.id!)}
                      disabled={!hasEmptySlot || saving !== null}
                    >
                      <Plus size={18} />
                    </button>
                  </div>
                </div>

                {qty > 0 && (
                  <div
                    className="card-footer text-center py-1"
                    style={{ backgroundColor: '#8B4513', color: 'white', fontSize: '0.8rem' }}
                  >
                    {qty}× ausgewählt
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};