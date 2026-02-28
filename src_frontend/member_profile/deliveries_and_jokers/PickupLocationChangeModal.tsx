import React, { useEffect, useState } from "react";
import { Modal, Spinner, Nav } from "react-bootstrap";
import {
  PickupLocationsApi,
  PublicPickupLocation,
  type PublicSubscription,
  SubscriptionsApi,
  WaitingListApi,
} from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import PickupLocationWaitingListSelector from "../../bestell_wizard/components/PickupLocationWaitingListSelector.tsx";
import PickupLocationSelector from "../../bestell_wizard/components/PickupLocationSelector.tsx";
import { checkPickupLocationCapacities } from "../../bestell_wizard/utils/checkPickupLocationCapacities.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import TapirButton from "../../components/TapirButton.tsx";
import ConfirmModal from "../../components/ConfirmModal.tsx";
import { ToastData } from "../../types/ToastData.ts";
import { addToast } from "../../utils/addToast.ts";
import { v4 as uuidv4 } from "uuid";

interface PickupLocationChangeModalProps {
  show: boolean;
  onHide: () => void;
  csrfToken: string;
  memberId: string;
  reloadDeliveries: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const WEEKDAY_NAMES = [
  "Montag",
  "Dienstag",
  "Mittwoch",
  "Donnerstag",
  "Freitag",
  "Samstag",
  "Sonntag",
];

const PickupLocationChangeModal: React.FC<PickupLocationChangeModalProps> = ({
  show,
  onHide,
  csrfToken,
  memberId,
  reloadDeliveries,
  setToastDatas,
}) => {
  const pickupLocationsApi = useApi(PickupLocationsApi, csrfToken);
  const subscriptionsApi = useApi(SubscriptionsApi, csrfToken);
  const waitingListApi = useApi(WaitingListApi, csrfToken);

  const [pickupLocations, setPickupLocations] = useState<
    PublicPickupLocation[]
  >([]);
  const [selectedPickupLocations, setSelectedPickupLocations] = useState<
    PublicPickupLocation[]
  >([]);
  const [selectedDeliveryDay, setSelectedDeliveryDay] = useState<number | null>(null);
  const [
    pickupLocationsWithCapacityCheckLoading,
    setPickupLocationsWithCapacityCheckLoading,
  ] = useState<Set<PublicPickupLocation>>(new Set<PublicPickupLocation>());
  const [pickupLocationsWithCapacityFull, setPickupLocationsWithCapacityFull] =
    useState<Set<PublicPickupLocation>>(new Set<PublicPickupLocation>());
  const [subscriptions, setSubscriptions] = useState<PublicSubscription[]>([]);
  const [waitingListModeEnabled, setWaitingListModeEnabled] = useState(false);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [
    showWaitingListConfirmationModal,
    setShowWaitingListConfirmationModal,
  ] = useState(false);
  const [hasWaitingListEntry, setHasWaitingListEntry] = useState(false);

  // Get unique delivery days from pickup locations
  const availableDeliveryDays = React.useMemo(() => {
    const days = new Set(
      pickupLocations
        .map((loc) => loc.deliveryDay)
        .filter((day): day is number => day !== null && day !== undefined)
    );
    return Array.from(days).sort();
  }, [pickupLocations]);

  // Filter pickup locations by selected delivery day
  const filteredPickupLocations = React.useMemo(() => {
    if (selectedDeliveryDay === null) {
      return pickupLocations;
    }
    return pickupLocations.filter(
      (loc) => loc.deliveryDay === selectedDeliveryDay
    );
  }, [pickupLocations, selectedDeliveryDay]);

  useEffect(() => {
    pickupLocationsApi
      .pickupLocationsPublicPickupLocationsList()
      .then((responsePickupLocations) => {
        responsePickupLocations.sort((a, b) => {
          return a.name.localeCompare(b.name);
        });
        setPickupLocations(responsePickupLocations);
        if (responsePickupLocations.length === 1) {
          setSelectedPickupLocations([responsePickupLocations[0]]);
        }
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Verteilstationen",
          setToastDatas,
        ),
      );

    subscriptionsApi
      .subscriptionsApiMemberSubscriptionDataRetrieve({ memberId: memberId })
      .then((response) => setSubscriptions(response.subscriptions))
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Verträge",
          setToastDatas,
        ),
      );

    waitingListApi
      .waitingListApiMemberWaitingListEntryDetailsRetrieve({
        memberId: memberId,
      })
      .then((result) => setHasWaitingListEntry(result.entry !== undefined))
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Warteliste-Eintrag",
          setToastDatas,
        ),
      );
  }, []);

  useEffect(() => {
    if (filteredPickupLocations.length === 0 || !show) {
      return;
    }

    const shoppingCart: ShoppingCart = Object.fromEntries(
      subscriptions.map((subscription) => [
        subscription.productId,
        subscription.quantity,
      ]),
    );

    checkPickupLocationCapacities(
      filteredPickupLocations,
      shoppingCart,
      setPickupLocationsWithCapacityCheckLoading,
      setPickupLocationsWithCapacityFull,
      setToastDatas,
      undefined,
    );
  }, [filteredPickupLocations, subscriptions, show]);

  useEffect(() => {
    if (selectedPickupLocations.length === 0) {
      setWaitingListModeEnabled(false);
    }

    if (
      selectedPickupLocations.length === 1 &&
      !pickupLocationsWithCapacityFull.has(selectedPickupLocations[0]) &&
      pickupLocationsWithCapacityCheckLoading.size === 0
    ) {
      setWaitingListModeEnabled(false);
    }

    if (
      !waitingListModeEnabled &&
      selectedPickupLocations.length === 1 &&
      pickupLocationsWithCapacityFull.has(selectedPickupLocations[0]) &&
      !pickupLocationsWithCapacityCheckLoading.has(selectedPickupLocations[0])
    ) {
      if (hasWaitingListEntry) {
        alert(
          "Du stehst schon auf der Warteliste, deswegen kannst du kein ausgelastete Verteilstation auswählen.",
        );
        setSelectedPickupLocations([]);
      } else {
        setShowWaitingListConfirmationModal(true);
      }
    }
  }, [
    selectedPickupLocations,
    pickupLocationsWithCapacityFull,
    pickupLocationsWithCapacityCheckLoading,
  ]);

  function onConfirm() {
    setConfirmLoading(true);
    if (waitingListModeEnabled) {
      waitingListApi
        .waitingListApiWaitingListCreateEntryExistingMemberCreate({
          publicWaitingListEntryExistingMemberCreateRequest: {
            memberId: memberId,
            pickupLocationIds: selectedPickupLocations.map(
              (pickupLocations) => pickupLocations.id!,
            ),
            shoppingCart: {},
          },
        })
        .then((result) => {
          if (result.orderConfirmed) {
            const message = selectedPickupLocations
              .map((pickupLocation) => pickupLocation.name)
              .join(", ");

            addToast(
              {
                id: uuidv4(),
                variant: "success",
                message: message,
                title: "Warteliste-Eintrag erzeugt",
              },
              setToastDatas,
            );

            onHide();
          } else {
            addToast(
              {
                id: uuidv4(),
                variant: "danger",
                message:
                  "Es gibt schon einen Warteliste-Eintrag für dich, wenn du den ändern willst, wende dich bitte an dem Kontakt hier Oben Rechts",
                title: "Warteliste-Eintrag nicht erzeugt",
              },
              setToastDatas,
            );
          }
        })
        .catch((error) =>
          handleRequestError(
            error,
            "Fehler beim Erzeugen des Warteliste-Eintrags",
            setToastDatas,
          ),
        )
        .finally(() => {
          setConfirmLoading(false);
        });
    } else {
      pickupLocationsApi
        .pickupLocationsApiChangeMemberPickupLocationCreate({
          pickupLocationId: selectedPickupLocations[0].id!,
          memberId: memberId,
        })
        .then((response) => {
          if (response.orderConfirmed) {
            onHide();
            addToast(
              {
                id: uuidv4(),
                variant: "success",
                title: "Verteilstation-Weschel bestätig",
              },
              setToastDatas,
            );
          } else {
            addToast(
              {
                id: uuidv4(),
                variant: "danger",
                title: "Fehler",
                message: response.error ?? undefined,
              },
              setToastDatas,
            );
          }
        })
        .catch((error) =>
          handleRequestError(
            error,
            "Fehler beim Wechsel der Verteilstation",
            setToastDatas,
          ),
        )
        .finally(() => {
          setConfirmLoading(false);
          reloadDeliveries();
        });
    }
  }

  return (
    <>
      <Modal
        onHide={onHide}
        show={show && !showWaitingListConfirmationModal}
        centered={true}
        size={"lg"}
      >
        <Modal.Header closeButton>
          <Modal.Title>
            <h4>Verteilstation ändern</h4>
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {/* Delivery Day Filter Tabs */}
          {availableDeliveryDays.length > 1 && (
            <div className="mb-3">
              <Nav variant="pills" className="flex-row">
                <Nav.Item>
                  <Nav.Link
                    active={selectedDeliveryDay === null}
                    onClick={() => setSelectedDeliveryDay(null)}
                    style={{ cursor: "pointer" }}
                  >
                    Alle Tage
                  </Nav.Link>
                </Nav.Item>
                {availableDeliveryDays.map((day) => (
                  <Nav.Item key={day}>
                    <Nav.Link
                      active={selectedDeliveryDay === day}
                      onClick={() => setSelectedDeliveryDay(day)}
                      style={{ cursor: "pointer" }}
                    >
                      {WEEKDAY_NAMES[day]}
                    </Nav.Link>
                  </Nav.Item>
                ))}
              </Nav>
            </div>
          )}

          {waitingListModeEnabled && (
            <PickupLocationWaitingListSelector
              setSelectedPickupLocations={setSelectedPickupLocations}
              pickupLocations={filteredPickupLocations}
              selectedPickupLocations={selectedPickupLocations}
              pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
            />
          )}
          {pickupLocations.length === 0 ? (
            <Spinner />
          ) : (
            <PickupLocationSelector
              pickupLocations={filteredPickupLocations}
              selectedPickupLocations={selectedPickupLocations}
              setSelectedPickupLocations={setSelectedPickupLocations}
              waitingListModeEnabled={waitingListModeEnabled}
              pickupLocationsWithCapacityCheckLoading={
                pickupLocationsWithCapacityCheckLoading
              }
              pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
              waitingListLinkConfirmationModeEnabled={false}
            />
          )}

          {filteredPickupLocations.length === 0 && selectedDeliveryDay !== null && (
            <div className="alert alert-info">
              Keine Verteilstationen verfügbar für {WEEKDAY_NAMES[selectedDeliveryDay]}
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <TapirButton
            text={
              waitingListModeEnabled
                ? "Warteliste-Eintrag bestätigen"
                : "Wechsel bestätigen"
            }
            variant={"primary"}
            icon={waitingListModeEnabled ? "pending_actions" : "check"}
            disabled={selectedPickupLocations.length === 0}
            onClick={onConfirm}
            loading={confirmLoading}
          />
        </Modal.Footer>
      </Modal>
      <ConfirmModal
        message={
          "Die ausgewählte Verteilstation ist derzeit ausgelastet (" +
          (selectedPickupLocations.length > 0
            ? selectedPickupLocations[0].name
            : "") +
          "). Du kannst eine andere Station wählen, oder dich auf die Warteliste setzen lassen. " +
          "Du kannst dich auch auf die Warteliste von bis zu drei Verteilstationen setzen lassen."
        }
        title={"Verteilstation ausgelastet"}
        open={showWaitingListConfirmationModal}
        confirmButtonText={"Weiter mit Warteliste-Eintrag"}
        confirmButtonVariant={"outline-primary"}
        confirmButtonIcon={"pending_actions"}
        onConfirm={() => {
          setShowWaitingListConfirmationModal(false);
          setWaitingListModeEnabled(true);
        }}
        onCancel={() => {
          setShowWaitingListConfirmationModal(false);
          setSelectedPickupLocations([]);
        }}
      />
    </>
  );
};

export default PickupLocationChangeModal;