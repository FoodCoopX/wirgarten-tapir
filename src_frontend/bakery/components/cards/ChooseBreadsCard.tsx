import React, { useState, useEffect, useRef } from "react";
import { BakeryApi, ResponseError } from "../../../api-client";
import { v4 as uuidv4 } from "uuid";
import { useApi } from "../../../hooks/useApi";
import { handleRequestError } from "../../../utils/handleRequestError";
import type {
  BreadList,
  BreadContent,
  BreadDelivery,
  BreadLabel,
} from "../../../api-client/models";
import { YearWeekSelectorCard } from "./YearWeekSelectorCard";
import { BreadSelectionModal } from "../modals/BreadSelectionModal";
import PickupLocationChangeModal from "../../../member_profile/deliveries_and_jokers/PickupLocationChangeModal";
import { CompactBreadCard } from "./CompactBreadCard";
import { CompactPickupLocationCard } from "./CompactPickupLocationCard";
import TapirButton from "../../../components/TapirButton";
import dayjs from "dayjs";
import isoWeek from "dayjs/plugin/isoWeek";
import "../../styles/bakery_styles.css";
import { currentIsoWeek, currentIsoYear } from "../../utils/weekdays";
import TapirToastContainer from "../../../components/TapirToastContainer";
import { ToastData } from "../../../types/ToastData";
import { addToast } from "../../../utils/addToast";
dayjs.extend(isoWeek);

interface ChooseBreadsCardProps {
  memberId: string;
  csrfToken: string;
  chooseStationPerBread: boolean;
  membersCanChooseBreadSorts: boolean;
}

const currentWeek = currentIsoWeek();
const currentYear = currentIsoYear();

export const ChooseBreadsCard: React.FC<ChooseBreadsCardProps> = ({
  chooseStationPerBread,
  membersCanChooseBreadSorts,
  memberId,
  csrfToken,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);

  const [breads, setBreads] = useState<BreadList[]>([]);
  const [contentsMap, setContentsMap] = useState<{
    [breadId: string]: BreadContent[];
  }>({});
  const [deliveries, setDeliveries] = useState<BreadDelivery[]>([]);
  const [labelsMap, setLabelsMap] = useState<{ [labelId: string]: BreadLabel }>(
    {},
  );
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [selectedWeek, setSelectedWeek] = useState(currentWeek);
  const [selectedYear, setSelectedYear] = useState(currentYear);
  const [modalOpen, setModalOpen] = useState<string | null>(null);
  const [modalRefreshKey, setModalRefreshKey] = useState(0);
  const [editingLocation, setEditingLocation] = useState<string | null>(null);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  // What the user is currently looking at. A response for an earlier
  // selection that arrives late is dropped, so the picker cannot PATCH one
  // week's slot ids while the header shows another.
  const selectionRef = useRef(`${memberId}/${selectedYear}/${selectedWeek}`);

  useEffect(() => {
    selectionRef.current = `${memberId}/${selectedYear}/${selectedWeek}`;
    loadData();
    // eslint-disable-next-line
  }, [memberId, selectedWeek, selectedYear]);

  // The deadline is the API's answer, not a second implementation of the
  // rule: the same service decides it here and rejects a late PATCH.
  const firstDelivery = deliveries[0];
  const choosingDeadline = firstDelivery?.choosingDeadline ?? null;
  const isAfterBreadDeadline = firstDelivery
    ? !firstDelivery.canStillChoose
    : false;
  const breadDeadlineMessage = choosingDeadline
    ? isAfterBreadDeadline
      ? `Frist zur Auswahl für diese Woche abgelaufen (${dayjs(choosingDeadline).format("DD.MM.YYYY")})`
      : `Auswahl für diese Woche möglich bis ${dayjs(choosingDeadline).format("DD.MM.YYYY")}`
    : "";

  // The pickup location may only be changed for next week or later. ISO year,
  // not calendar year: on 2027-01-01 the calendar year is 2027 while the ISO
  // week is 53 of 2026, and comparing the two would say next week is not in
  // the future.
  const canChangePickupLocation =
    selectedYear > currentIsoYear() ||
    (selectedYear === currentIsoYear() && selectedWeek > currentIsoWeek());

  const loadData = () => {
    const requestedFor = `${memberId}/${selectedYear}/${selectedWeek}`;
    // Drop the previous week's slots up front, so nothing on screen belongs
    // to a week other than the one in the header - including after a failed
    // load.
    setDeliveries([]);
    setLoading(true);
    bakeryApi
      .bakeryBreadsListList({ isActive: true })
      .then((allBreads) => {
        setBreads(allBreads);
        return Promise.all([
          bakeryApi.bakeryLabelsList(),
          bakeryApi.bakeryBreadDeliveriesList({
            memberId,
            year: selectedYear,
            deliveryWeek: selectedWeek,
          }),
          allBreads,
        ] as const);
      })
      .then(([labels, breadDeliveries, allBreads]) => {
        if (selectionRef.current !== requestedFor) return;

        // Contents ship with the bread list, so no request per bread.
        const contentsResults = allBreads.map((bread) => ({
          breadId: bread.id,
          contents: bread.contents ?? [],
        }));
        const labelMapping = labels.reduce(
          (acc, label) => {
            if (label.id) {
              acc[label.id] = label;
            }
            return acc;
          },
          {} as { [labelId: string]: BreadLabel },
        );
        setLabelsMap(labelMapping);

        const map: { [breadId: string]: BreadContent[] } = {};
        contentsResults.forEach(({ breadId, contents }) => {
          map[breadId!] = [...contents].sort(
            (a, b) => Number(b.amount) - Number(a.amount),
          );
        });
        setContentsMap(map);

        const sortedDeliveries = [...breadDeliveries].sort(
          (a, b) => (a.slotNumber || 0) - (b.slotNumber || 0),
        );
        setDeliveries(sortedDeliveries);
      })
      .catch((error) => {
        if (selectionRef.current !== requestedFor) return;
        handleRequestError(error, "Fehler beim Laden der Brotanteile");
      })
      .finally(() => {
        if (selectionRef.current !== requestedFor) return;
        setLoading(false);
      });
  };

  const handlePickupLocationChanged = () => {
    setEditingLocation(null);
    loadData();
  };

  const showChoiceRefused = (message?: string) => {
    addToast(
      {
        title: "Brot konnte nicht gespeichert werden",
        message:
          message ||
          "Dieses Brot ist leider nicht mehr verfügbar. Bitte wähle ein anderes Brot.",
        variant: "danger",
        id: uuidv4(),
      },
      setToastDatas,
    );
  };

  const handleBreadSelected = (deliveryId: string, breadId: string) => {
    const delivery = deliveries.find((d) => d.id === deliveryId);
    if (!delivery || !delivery.pickupLocation) return;

    setSaving(deliveryId);
    bakeryApi
      .bakeryBreadDeliveriesPartialUpdate({
        id: deliveryId,
        patchedBreadDeliveryRequest: {
          bread: breadId,
        },
      })
      .then(() => {
        setModalOpen(null);
        loadData();
      })
      .catch((error) => {
        // A 400 is the server refusing this bread - no capacity left, or the
        // choosing deadline has passed. Its message is written for the member,
        // so show it and reload the modal's availability.
        if (error instanceof ResponseError && error.response.status === 400) {
          error.response
            .json()
            .then((body: { error?: string }) => showChoiceRefused(body.error))
            .catch(() => showChoiceRefused());
          setModalRefreshKey((prev) => prev + 1);
        } else {
          handleRequestError(
            error,
            "Speichern des Brotes fehlgeschlagen",
            setToastDatas,
          );
        }
      })
      .finally(() => {
        setSaving(null);
      });
  };

  const handleRemoveBread = (deliveryId: string) => {
    setSaving(deliveryId);
    bakeryApi
      .bakeryBreadDeliveriesPartialUpdate({
        id: deliveryId,
        patchedBreadDeliveryRequest: {
          bread: null,
        },
      })
      .then(() => {
        loadData();
      })
      .catch((error) => {
        handleRequestError(error, "Löschen des Brotes fehlgeschlagen");
      })
      .finally(() => {
        setSaving(null);
      });
  };

  const getBreadDetails = (breadId: string | null) => {
    if (!breadId) return null;
    return breads.find((b) => b.id === breadId);
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

      {/* Bread Delivery Slots. `loading` was set and never read, so the card
          rendered an empty grid while the request was in flight and a member
          could not tell "still loading" from "you have no bread share". */}
      {loading ? (
        <div className="text-center py-4">
          <div className="spinner-border spinner-bakery-primary">
            <span className="visually-hidden">Lädt...</span>
          </div>
        </div>
      ) : deliveries.length === 0 ? (
        <p className="text-muted text-center py-4 mb-0">
          Für diese Woche sind keine Brotanteile eingetragen.
        </p>
      ) : (
        <div className="row g-3" style={{ marginTop: "0.5rem" }}>
          {deliveries.map((delivery, index) => {
            const isFirstSlot = index === 0;
            const hasBreadSelected = !!delivery.bread;

            const canEditThisLocation =
              (chooseStationPerBread || isFirstSlot) && canChangePickupLocation;
            const selectedBread = getBreadDetails(delivery.bread || null);
            const breadLabels = selectedBread
              ? (selectedBread.labels || [])
                  .map((labelId) => labelsMap[labelId])
                  .filter(Boolean)
              : [];
            const contents = selectedBread
              ? contentsMap[selectedBread.id!] || []
              : [];

            return (
              <div key={delivery.id} className="col-12 col-md-6 col-lg-4">
                <div className="card h-100">
                  <div className="card-header header-white-on-middle-brown">
                    <h6 className="mb-0">Brotanteil {index + 1}</h6>
                  </div>
                  <div className="card-body">
                    {delivery.jokerTaken ? (
                      <div className="d-flex align-items-center justify-content-center p-4">
                        <span className="badge bg-secondary fs-6">
                          Joker genommen
                        </span>
                      </div>
                    ) : (
                      <>
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
                            <TapirButton
                              variant=""
                              className="dark-brown-button"
                              size="sm"
                              text="Auswählen"
                              onClick={() => setEditingLocation(delivery.id!)}
                              disabled={saving === delivery.id || !canChangePickupLocation}
                            />
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
                            <strong className="mb-2 d-block">
                              Gewählte Brotsorte:
                            </strong>

                            {!delivery.pickupLocation ? (
                              <div className="alert alert-warning mt-2 mb-0 py-2">
                                <small>
                                  {isFirstSlot || chooseStationPerBread
                                    ? "⚠️ Bitte zuerst eine Abholstation auswählen"
                                    : "⚠️ Bitte eine Station bei Brotanteil 1 auswählen"}
                                </small>
                              </div>
                            ) : selectedBread ? (
                              <>
                                <CompactBreadCard
                                  bread={selectedBread}
                                  contents={contents}
                                  labels={breadLabels}
                                  onEdit={
                                    !isAfterBreadDeadline
                                      ? () => setModalOpen(delivery.id!)
                                      : undefined
                                  }
                                  onRemove={
                                    !isAfterBreadDeadline
                                      ? () => handleRemoveBread(delivery.id!)
                                      : undefined
                                  }
                                  disabled={
                                    saving === delivery.id ||
                                    isAfterBreadDeadline
                                  }
                                />
                                {isAfterBreadDeadline && (
                                  <div className="alert alert-danger mt-2 mb-0 py-1 px-2">
                                    <small>{breadDeadlineMessage}</small>
                                  </div>
                                )}
                                {!isAfterBreadDeadline &&
                                  breadDeadlineMessage && (
                                    <div className="alert alert-info mt-2 mb-0 py-1 px-2">
                                      <small>{breadDeadlineMessage}</small>
                                    </div>
                                  )}
                              </>
                            ) : (
                              <>
                                <div className="d-flex align-items-center justify-content-between p-3 border rounded bg-bakery-gray-light">
                                  <span className="text-muted">
                                    Noch nicht gewählt
                                  </span>
                                  <TapirButton
                                    variant=""
                                    className="dark-brown-button"
                                    size="sm"
                                    text="Auswählen"
                                    onClick={() => setModalOpen(delivery.id!)}
                                    disabled={
                                      !delivery.pickupLocation ||
                                      saving === delivery.id ||
                                      isAfterBreadDeadline
                                    }
                                  />
                                </div>
                                {isAfterBreadDeadline && (
                                  <div className="alert alert-danger mt-2 mb-0 py-1 px-2">
                                    <small>⚠️ {breadDeadlineMessage}</small>
                                  </div>
                                )}
                                {!isAfterBreadDeadline &&
                                  breadDeadlineMessage && (
                                    <div className="alert alert-info mt-2 mb-0 py-1 px-2">
                                      <small>ℹ️ {breadDeadlineMessage}</small>
                                    </div>
                                  )}
                              </>
                            )}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>

                {/* Bread Selection Modal */}
                {modalOpen === delivery.id &&
                  delivery.pickupLocation &&
                  !isAfterBreadDeadline && (
                    <BreadSelectionModal
                      key={modalRefreshKey}
                      contentsMap={contentsMap}
                      pickupLocationId={delivery.pickupLocation}
                      pickupLocationName={delivery.pickupLocationName || ""}
                      selectedWeek={selectedWeek}
                      selectedYear={selectedYear}
                      currentBreadId={delivery.bread || null}
                      onSelect={(breadId) =>
                        handleBreadSelected(delivery.id!, breadId)
                      }
                      onClose={() => setModalOpen(null)}
                      csrfToken={csrfToken}
                    />
                  )}
              </div>
            );
          })}
        </div>
      )}

      {/* Pickup Location Change Modal */}
      <PickupLocationChangeModal
        show={editingLocation !== null && canChangePickupLocation}
        onHide={() => setEditingLocation(null)}
        csrfToken={csrfToken}
        memberId={memberId}
        reloadDeliveries={handlePickupLocationChanged}
        setToastDatas={setToastDatas}
      />
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </div>
  );
};
