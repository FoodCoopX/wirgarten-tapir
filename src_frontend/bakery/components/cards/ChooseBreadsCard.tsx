import React, { useState, useEffect } from 'react';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import type { BreadList, BreadContent, BreadDelivery, BreadLabel } from '../../../api-client/models';
import { YearWeekSelectorCard } from './YearWeekSelectorCard';
import { BreadSelectionModal } from '../modals/BreadSelectionModal';
import PickupLocationChangeModal from '../../../member_profile/deliveries_and_jokers/PickupLocationChangeModal';
import { CompactBreadCard } from './CompactBreadCard';
import { CompactPickupLocationCard } from './CompactPickupLocationCard';
import dayjs from 'dayjs';
import isoWeek from "dayjs/plugin/isoWeek";
import '../../styles/bakery_styles.css';
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
  const [modalRefreshKey, setModalRefreshKey] = useState(0);
  const [editingLocation, setEditingLocation] = useState<string | null>(null);
  const [toastDatas, setToastDatas] = useState<any[]>([]);
  
  // Parameters for deadline calculation
  const [lastChoosingDayBeforeBaking, setLastChoosingDayBeforeBaking] = useState<number>(0);
  const [bakingDayBeforeDelivery, setBakingDayBeforeDelivery] = useState<number>(0);
  const [isAfterBreadDeadline, setIsAfterBreadDeadline] = useState(false);
  const [breadDeadlineMessage, setBreadDeadlineMessage] = useState<string>('');
  const [canChangePickupLocation, setCanChangePickupLocation] = useState(false);

  useEffect(() => {
    loadParameters();
    // eslint-disable-next-line
  }, []);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line
  }, [memberId, selectedWeek, selectedYear]);

  useEffect(() => {
    calculateDeadlines();
    // eslint-disable-next-line
  }, [selectedWeek, selectedYear, deliveries, lastChoosingDayBeforeBaking, bakingDayBeforeDelivery]);

  const loadParameters = () => {
    bakeryApi.bakeryApiConfigurationParametersRetrieve()
      .then((params) => {
        const lastChoosingParam = params.find(
          p => p.key === 'wirgarten.bakery.last_choosing_day_before_baking_day'
        );
        const bakingDayParam = params.find(
          p => p.key === 'wirgarten.bakery.baking_day_before_delivery_day'
        );

        setLastChoosingDayBeforeBaking(Number(lastChoosingParam?.value || 0));
        setBakingDayBeforeDelivery(Number(bakingDayParam?.value || 0));
      })
      .catch((error) => {
        console.error('Failed to load parameters:', error);
      });
  };

  const calculateDeadlines = () => {
    const now = dayjs();
    const nowWeek = now.isoWeek();
    const nowYear = now.year();

    // 1. Check if pickup location can be changed (only for next week or later)
    const isNextWeekOrLater = 
      selectedYear > nowYear || 
      (selectedYear === nowYear && selectedWeek > nowWeek);
    
    setCanChangePickupLocation(isNextWeekOrLater);

    // 2. Calculate bread selection deadline
    if (deliveries.length === 0) {
      setIsAfterBreadDeadline(false);
      setBreadDeadlineMessage('');
      return;
    }

    const firstDelivery = deliveries[0];
    if (!firstDelivery.deliveryDay) {
      setIsAfterBreadDeadline(false);
      setBreadDeadlineMessage('');
      return;
    }

    // Calculate the delivery date for the selected ISO week
    const deliveryDate = dayjs()
      .year(selectedYear)
      .isoWeek(selectedWeek)
      .isoWeekday(firstDelivery.deliveryDay); // 1 = Monday, 7 = Sunday
    
    console.log('Delivery Date:', deliveryDate.format('YYYY-MM-DD'));

    // Calculate deadline: delivery_date - baking_day_offset - last_choosing_day_offset
    const totalDaysBeforeDelivery = bakingDayBeforeDelivery + lastChoosingDayBeforeBaking;
    const deadline = deliveryDate.subtract(totalDaysBeforeDelivery, 'day');
    
    const isPastDeadline = now.isAfter(deadline.endOf('day'));
    
    setIsAfterBreadDeadline(isPastDeadline);
    
    if (isPastDeadline) {
      setBreadDeadlineMessage(
        `Frist zur Auswahl für diese Woche abgelaufen (${deadline.format('DD.MM.YYYY')})`
      );
    } else {
      setBreadDeadlineMessage(
        `Auswahl für diese Woche möglich bis ${deadline.format('DD.MM.YYYY')}`
      );
    }
  };

  const loadData = () => {
    setLoading(true);
    bakeryApi.bakeryBreadsListList({ isActive: true })
      .then((allBreads) => {
        setBreads(allBreads);
        return Promise.all([
          bakeryApi.bakeryLabelsList(),
          Promise.all(
            allBreads.map((bread) =>
              bakeryApi.bakeryBreadsListContentsList({ id: bread.id! })
                .then((contents) => ({ breadId: bread.id, contents }))
                .catch(() => ({ breadId: bread.id, contents: [] as BreadContent[] }))
            )
          ),
          bakeryApi.bakeryBreadDeliveriesList({
            memberId,
            year: selectedYear,
            deliveryWeek: selectedWeek,
          }),
        ] as const);
      })
      .then(([labels, contentsResults, breadDeliveries]) => {
        const labelMapping = labels.reduce((acc, label) => {
          if (label.id) {
            acc[label.id] = label;
          }
          return acc;
        }, {} as { [labelId: string]: BreadLabel });
        setLabelsMap(labelMapping);

        const map: { [breadId: string]: BreadContent[] } = {};
        contentsResults.forEach(({ breadId, contents }) => {
          map[breadId!] = [...contents].sort((a, b) => Number(b.amount) - Number(a.amount));
        });
        setContentsMap(map);

        const sortedDeliveries = [...breadDeliveries].sort((a, b) => 
          (a.slotNumber || 0) - (b.slotNumber || 0)
        );
        setDeliveries(sortedDeliveries);
      })
      .catch((error) => {
        console.error('Failed to load data:', error);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const handlePickupLocationChanged = () => {
    setEditingLocation(null);
    loadData();
  };

  const handleBreadSelected = (deliveryId: string, breadId: string) => {
    const delivery = deliveries.find(d => d.id === deliveryId);
    if (!delivery || !delivery.pickupLocation) return;

    setSaving(deliveryId);
    bakeryApi.bakeryBreadDeliveriesPartialUpdate({
      id: deliveryId,
      patchedBreadDeliveryRequest: {
        bread: breadId,
      },
    })
      .then(() => {
        setModalOpen(null);
        loadData();
      })
      .catch((error: any) => {
        console.error('Failed to save bread selection:', error);
        // Handle capacity error (400 response)
        if (error?.response?.status === 400) {
          error.response.json()
            .then((errorData: any) => {
              alert(errorData.error || 'Dieses Brot ist leider nicht mehr verfügbar. Bitte wähle ein anderes Brot.');
            })
            .catch(() => {
              alert('Dieses Brot ist leider nicht mehr verfügbar. Bitte wähle ein anderes Brot.');
            });
          // Refresh the modal to show updated availability
          setModalRefreshKey(prev => prev + 1);
        } else {
          alert('Speichern des Brotes fehlgeschlagen');
        }
      })
      .finally(() => {
        setSaving(null);
      });
  };

  const handleRemoveBread = (deliveryId: string) => {
    setSaving(deliveryId);
    bakeryApi.bakeryBreadDeliveriesPartialUpdate({
      id: deliveryId,
      patchedBreadDeliveryRequest: {
        bread: null,
      },
    })
      .then(() => {
        loadData();
      })
      .catch((error) => {
        console.error('Failed to remove bread:', error);
        alert('L\u00f6schen des Brotes fehlgeschlagen');
      })
      .finally(() => {
        setSaving(null);
      });
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
      {/* <div className="alert alert-info white-on-green mb-3 mt-3">
        <strong>Du hast {maxBreads} Brot-Anteil{maxBreads !== 1 ? 'e' : ''} für diese Woche.</strong>
        <br />
       <small>
          {chooseStationPerBread ? (
            <>
              Hier kannst du für jeden Anteil den Abholort ändern (falls gewünscht).
              {membersCanChooseBreadSorts && (
                <>
                  <br/>
                  Du kannst auch eine verfügbare Brotsorte direkt auswählen für diese Lieferung.
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
      </div> */}

      {/* Bread Delivery Slots */}
      <div className="row g-3" style={{ marginTop: '0.5rem' }}>
        {deliveries.map((delivery, index) => {
          const isFirstSlot = index === 0;
          const hasBreadSelected = !!delivery.bread;

          const canEditThisLocation = (chooseStationPerBread || isFirstSlot) && canChangePickupLocation;
          const selectedBread = getBreadDetails(delivery.bread || null);
          const breadLabels = selectedBread
            ? (selectedBread.labels || [])
                .map(labelId => labelsMap[labelId])
                .filter(Boolean)
            : [];
          const contents = selectedBread ? (contentsMap[selectedBread.id!] || []) : [];
          
          return (
            <div key={delivery.id} className="col-12 col-md-6 col-lg-4">
              <div className="card h-100">
                <div 
                  className="card-header header-white-on-middle-brown"
                >
                  <h6 className="mb-0">Brotanteil {index + 1}</h6>
                </div>
                <div className="card-body">
                  {delivery.jokerTaken ? (
                    <div className="d-flex align-items-center justify-content-center p-4">
                      <span className="badge bg-secondary fs-6">
                        Joker genommen
                      </span>
                    </div>
                  ) : (<>
                  {/* Pickup Location Row */}
                  {/* <div className="mb-3">
                    <strong className="mb-2 d-block">Gewählter Abholort:</strong>
                    
                    {!chooseStationPerBread && !isFirstSlot && (
                      <div className="alert alert-info mb-2 py-2">
                        <small>Wird mit den anderen Brotanteilen synchronisiert</small>
                      </div>
                    )}

                    {delivery.pickupLocation ? (
                      <>
                        <CompactPickupLocationCard
                          name={delivery.pickupLocationName || 'Unbekannt'}
                          street={delivery.pickupLocationStreet || 'Unbekannt'}
                          city={delivery.pickupLocationCity || 'Unbekannt'}
                          deliveryDay={delivery.deliveryDay}
                          onEdit={canEditThisLocation ? () => setEditingLocation(delivery.id!) : undefined}
                          disabled={saving === delivery.id || !canChangePickupLocation || hasBreadSelected}
                          year = {selectedYear}
                          week = {selectedWeek}
                        />
                        {hasBreadSelected  && !isAfterBreadDeadline &&(
                            <div className="alert alert-warning mt-2 mb-0 py-1 px-2">
                              <small className="text-muted">Zum Ändern des Abholorts, bitte zuerst Brotauswahl entfernen. (Es sind nicht alle Brote an allen Abholorten verfügbar.)</small>
                            </div>
                                                  )}
                        {!hasBreadSelected && !canChangePickupLocation && canEditThisLocation && (
                          <div className="alert alert-warning mt-2 mb-0 py-1 px-2">
                            <small>⚠️ Nur ab nächster Woche änderbar</small>
                          </div>
                        )}
                      </>
                    ) : (
                      <>
                        <div className="d-flex align-items-center justify-content-between p-3 border rounded bg-bakery-gray-light">
                          <span className="text-muted">Noch nicht gewählt</span>
                          {canEditThisLocation && (
                            <button
                              className="btn btn-sm btn-outline-secondary dark-brown-button"
                              onClick={() => setEditingLocation(delivery.id!)}
                              disabled={saving === delivery.id || !canChangePickupLocation}
                            >
                              Auswählen
                            </button>
                          )}
                        </div>
                        {!canChangePickupLocation && canEditThisLocation && (
                          <div className="alert alert-warning mt-2 mb-0 py-1 px-2">
                            <small>⚠️ Nur ab nächster Woche wählbar</small>
                          </div>
                        )}
                      </>
                    )}
                  </div> */}

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
                      <>
                        <CompactBreadCard
                          bread={selectedBread}
                          contents={contents}
                          labels={breadLabels}
                          onEdit={!isAfterBreadDeadline ? () => setModalOpen(delivery.id!) : undefined}
                          onRemove={!isAfterBreadDeadline ? () => handleRemoveBread(delivery.id!) : undefined}
                          disabled={saving === delivery.id || isAfterBreadDeadline}
                        />
                        {isAfterBreadDeadline && (
                          <div className="alert alert-danger mt-2 mb-0 py-1 px-2">
                            <small>{breadDeadlineMessage}</small>
                          </div>
                        )}
                        {!isAfterBreadDeadline && breadDeadlineMessage && (
                          <div className="alert alert-info mt-2 mb-0 py-1 px-2">
                            <small>{breadDeadlineMessage}</small>
                          </div>
                        )}
                      </>
                    ) : (
                      <>
                        <div className="d-flex align-items-center justify-content-between p-3 border rounded bg-bakery-gray-light">
                          <span className="text-muted">Noch nicht gewählt</span>
                          <button
                            className="btn btn-sm btn-outline-secondary dark-brown-button"
                            onClick={() => setModalOpen(delivery.id!)}
                            disabled={!delivery.pickupLocation || saving === delivery.id || isAfterBreadDeadline}
                          >
                            Auswählen
                          </button>
                        </div>
                        {isAfterBreadDeadline && (
                          <div className="alert alert-danger mt-2 mb-0 py-1 px-2">
                            <small>⚠️ {breadDeadlineMessage}</small>
                          </div>
                        )}
                        {!isAfterBreadDeadline && breadDeadlineMessage && (
                          <div className="alert alert-info mt-2 mb-0 py-1 px-2">
                            <small>ℹ️ {breadDeadlineMessage}</small>
                          </div>
                        )}
                      </>
                    )}
                  </div>)}
                  </>)}
                </div>
              </div>

              {/* Bread Selection Modal */}
              {modalOpen === delivery.id && delivery.pickupLocation && !isAfterBreadDeadline && (
                <BreadSelectionModal
                  key={modalRefreshKey}
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
        show={editingLocation !== null && canChangePickupLocation}
        onHide={() => setEditingLocation(null)}
        csrfToken={csrfToken}
        memberId={memberId}
        reloadDeliveries={handlePickupLocationChanged}
        setToastDatas={setToastDatas}
      />
    </div>
  );
};