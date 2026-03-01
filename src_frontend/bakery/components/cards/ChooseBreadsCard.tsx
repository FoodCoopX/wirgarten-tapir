import React, { useState, useEffect } from 'react';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import type { BreadList, BreadContent, BreadDelivery, BreadLabel } from '../../../api-client/models';
import { YearWeekSelectorCard } from './YearWeekSelectorCard';
import { BreadSelectionModal } from '../modals/BreadSelectionModal';
import PickupLocationChangeModal from '../../../member_profile/deliveries_and_jokers/PickupLocationChangeModal';
import { CompactBreadCard } from './CompactBreadCard';
import dayjs from 'dayjs';
import isoWeek from "dayjs/plugin/isoWeek";

dayjs.extend(isoWeek);

interface ChooseBreadsCardProps {
  memberId: string;
  csrfToken: string;
  chooseStationPerBread: boolean;
  membersCanChooseBreadSorts: boolean;
}

const currentWeek = dayjs().isoWeek();
const currentYear = dayjs().year();

export const ChooseBreadsCard: React.FC<ChooseBreadsCardProps> = ({
  chooseStationPerBread,
  membersCanChooseBreadSorts,
  memberId,
  csrfToken,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);

  const [breads, setBreads] = useState<BreadList[]>([]);
  const [contentsMap, setContentsMap] = useState<{ [breadId: string]: BreadContent[] }>({});
  const [deliveries, setDeliveries] = useState<BreadDelivery[]>([]);
  const [labelsMap, setLabelsMap] = useState<{ [labelId: string]: BreadLabel }>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [selectedWeek, setSelectedWeek] = useState(currentWeek);
  const [selectedYear, setSelectedYear] = useState(currentYear);
  const [modalOpen, setModalOpen] = useState<string | null>(null);
  const [editingLocation, setEditingLocation] = useState<string | null>(null);
  const [toastDatas, setToastDatas] = useState<any[]>([]);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line
  }, [memberId, selectedWeek, selectedYear]);

  const loadData = async () => {
    setLoading(true);
    try {
      const allBreads = await bakeryApi.bakeryBreadsListList({ isActive: true });
      setBreads(allBreads);

      // Load labels
      const labels = await bakeryApi.bakeryLabelsList();
      const labelMapping = labels.reduce((acc, label) => {
        if (label.id) {
          acc[label.id] = label;
        }
        return acc;
      }, {} as { [labelId: string]: BreadLabel });
      setLabelsMap(labelMapping);

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

  const handlePickupLocationChanged = async () => {
    setEditingLocation(null);
    await loadData();
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

      await loadData();
    } catch (error) {
      console.error('Failed to remove bread:', error);
      alert('Löschen des Brotes fehlgeschlagen');
    } finally {
      setSaving(null);
    }
  };

  const getBreadDetails = (breadId: string | null) => {
    if (!breadId) return null;
    return breads.find(b => b.id === breadId);
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
              Hier kannst du für jeden Anteil den Abholort ändern (falls gewünscht).
              {membersCanChooseBreadSorts && (
                <>
                  <br/>
                  Hier kannst du auch eine verfügbare Brotsorte direkt auswählen für diese Lieferung.
                </>
              )}
            </>
          ) : (
            <>
              Wähle den Abholort für alle deine Brote.
              {membersCanChooseBreadSorts && (
                <>
                  {' '}Anschließend kannst du die gewünschten Brotsorten wählen.
                </>
              )}
            </>
          )}
        </small>
      </div>

      {/* Bread Delivery Slots */}
      <div className="row g-3">
        {deliveries.map((delivery, index) => {
          const isFirstSlot = index === 0;
          const canChangeLocation = chooseStationPerBread || isFirstSlot;
          const selectedBread = getBreadDetails(delivery.bread || null);
          const breadLabels = selectedBread
            ? (selectedBread.labels || [])
                .map(labelId => labelsMap[labelId])
                .filter(Boolean)
            : [];
          const contents = selectedBread ? (contentsMap[selectedBread.id!] || []) : [];
          
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
                        <strong>Gewählter Abholort:</strong>{' '}
                        <span className="text-muted">
                          {delivery.pickupLocationName || 'Noch nicht gewählt'}
                        </span>
                        {!chooseStationPerBread && !isFirstSlot && (
                          <small className="text-muted ms-2">(wird mit Brotanteil 1 synchronisiert)</small>
                        )}
                      </div>
                      {canChangeLocation && (
                        <button
                          className="btn btn-sm btn-outline-secondary"
                          onClick={() => setEditingLocation(delivery.id!)}
                          disabled={saving === delivery.id}
                        >
                          {delivery.pickupLocation ? 'Ändern' : 'Auswählen'}
                        </button>
                      )}
                      {saving === delivery.id && (
                        <span className="spinner-border spinner-border-sm ms-2" />
                      )}
                    </div>
                  </div>

                  <hr />

                  {/* Bread Selection Section */}
                  {membersCanChooseBreadSorts && (
                  <div>
                    <strong className="mb-2 d-block">Gewählte Brotsorte:</strong>

                    {!delivery.pickupLocation ? (
                      <div className="alert alert-warning mt-2 mb-0 py-2">
                        <small>
                          {isFirstSlot || chooseStationPerBread 
                            ? '⚠️ Bitte zuerst eine Abholstation auswählen' 
                            : '⚠️ Bitte eine Station bei Brotanteil 1 auswählen'}
                        </small>
                      </div>
                    ) : selectedBread ? (
                      <CompactBreadCard
                        bread={selectedBread}
                        contents={contents}
                        labels={breadLabels}
                        onEdit={() => setModalOpen(delivery.id!)}
                        onRemove={() => handleRemoveBread(delivery.id!)}
                        disabled={saving === delivery.id}
                      />
                    ) : (
                      <div className="d-flex align-items-center justify-content-between p-3 border rounded" style={{ backgroundColor: '#F8F9FA' }}>
                        <span className="text-muted">Noch nicht gewählt</span>
                        <button
                          className="btn btn-sm"
                          style={{ backgroundColor: '#8B4513', color: 'white' }}
                          onClick={() => setModalOpen(delivery.id!)}
                          disabled={!delivery.pickupLocation || saving === delivery.id}
                        >
                          Auswählen
                        </button>
                      </div>
                    )}
                  </div>)}
                </div>
              </div>

              {/* Bread Selection Modal */}
              {modalOpen === delivery.id && delivery.pickupLocation && (
                <BreadSelectionModal
                  breads={breads}
                  contentsMap={contentsMap}
                  pickupLocationId={delivery.pickupLocation}
                  pickupLocationName={delivery.pickupLocationName || ''}
                  selectedWeek={selectedWeek}
                  selectedYear={selectedYear}
                  currentBreadId={delivery.bread || null}
                  onSelect={(breadId) => handleBreadSelected(delivery.id!, breadId)}
                  onClose={() => setModalOpen(null)}
                  csrfToken={csrfToken}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Pickup Location Change Modal */}
      <PickupLocationChangeModal
        show={editingLocation !== null}
        onHide={() => setEditingLocation(null)}
        csrfToken={csrfToken}
        memberId={memberId}
        reloadDeliveries={handlePickupLocationChanged}
        setToastDatas={setToastDatas}
      />
    </div>
  );
};