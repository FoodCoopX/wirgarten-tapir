import React, { useEffect, useState } from "react";
import {
  ButtonGroup,
  Form,
  Modal,
  Spinner,
  ToggleButton,
} from "react-bootstrap";
import { v4 as uuidv4 } from "uuid";
import {
  DeliveryAddressRequest,
  PickupLocationsApi,
  PublicPickupLocation,
  type PublicSubscription,
  SubscriptionsApi,
  WaitingListApi,
} from "../../api-client";
import PickupLocationSelector from "../../bestell_wizard/components/PickupLocationSelector.tsx";
import PickupLocationWaitingListSelector from "../../bestell_wizard/components/PickupLocationWaitingListSelector.tsx";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { checkPickupLocationCapacities } from "../../bestell_wizard/utils/checkPickupLocationCapacities.ts";
import { DeliveryMode } from "../../bestell_wizard_mobile/types/DeliveryMode.ts";
import { getPickupLocationsForDeliveryMode } from "../../bestell_wizard_mobile/utils/getPickupLocationsForDeliveryMode.ts";
import { isDeliveryAddressValid } from "../../bestell_wizard_mobile/utils/isDeliveryAddressValid.ts";
import ConfirmModal from "../../components/ConfirmModal.tsx";
import DeliveryAddressFields from "../../components/DeliveryAddressFields.tsx";
import DeliveryDayTabs from "../../components/DeliveryDayTabs.tsx";
import TapirButton from "../../components/TapirButton.tsx";
import TapirHelpButton from "../../components/TapirHelpButton.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { addToast } from "../../utils/addToast.ts";
import { getUniqueDeliveryDays } from "../../utils/getUniqueDeliveryDays.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

interface PickupLocationChangeModalProps {
  show: boolean;
  onHide: () => void;
  csrfToken: string;
  memberId: string;
  reloadDeliveries: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  membersCanChangePickupLocationThemselves: boolean;
  pickupLocationLabel?: string;
}

const PickupLocationChangeModal: React.FC<PickupLocationChangeModalProps> = ({
  show,
  onHide,
  csrfToken,
  memberId,
  reloadDeliveries,
  setToastDatas,
  membersCanChangePickupLocationThemselves,
  pickupLocationLabel = "Abholort",
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
  const [selectedDeliveryDay, setSelectedDeliveryDay] = useState<number | null>(
    null,
  );
  const [
    pickupLocationsCapacityCheckLoading,
    setPickupLocationsCapacityCheckLoading,
  ] = useState(false);
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
  const [currentPickupLocationId, setCurrentPickupLocationId] = useState("");
  const [deliveryMode, setDeliveryMode] = useState<DeliveryMode>("pickup");
  const [deliveryAddress, setDeliveryAddress] =
    useState<DeliveryAddressRequest>({ sameAsBillingAddress: true });

  const homeDeliveryAvailable = pickupLocations.some(
    (pickupLocation) => pickupLocation.isHomeDelivery,
  );

  const pickupLocationsForDeliveryMode = React.useMemo(
    () => getPickupLocationsForDeliveryMode(pickupLocations, deliveryMode),
    [pickupLocations, deliveryMode],
  );

  const availableDeliveryDays = React.useMemo(
    () => getUniqueDeliveryDays(pickupLocationsForDeliveryMode),
    [pickupLocationsForDeliveryMode],
  );

  const filteredPickupLocations = React.useMemo(() => {
    if (selectedDeliveryDay === null) {
      return pickupLocationsForDeliveryMode;
    }
    return pickupLocationsForDeliveryMode.filter(
      (loc) => loc.deliveryDay === selectedDeliveryDay,
    );
  }, [pickupLocationsForDeliveryMode, selectedDeliveryDay]);

  const homeDeliverySelected =
    selectedPickupLocations.length === 1 &&
    selectedPickupLocations[0].isHomeDelivery &&
    !waitingListModeEnabled;

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

    pickupLocationsApi
      .pickupLocationsApiGetMemberPickupLocationRetrieve({ memberId: memberId })
      .then((result) => {
        setCurrentPickupLocationId(result.location?.id ?? "");
        if (result.location?.isHomeDelivery) {
          setDeliveryMode("home_delivery");
        }
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der aktuellen Verteilstation",
          setToastDatas,
        ),
      );

    pickupLocationsApi
      .pickupLocationsApiMemberDeliveryAddressRetrieve({ memberId: memberId })
      .then((result) =>
        setDeliveryAddress({
          sameAsBillingAddress: result.sameAsBillingAddress,
          street: result.street,
          street2: result.street2,
          postcode: result.postcode,
          city: result.city,
          country: result.country || "DE",
        }),
      )
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Lieferadresse",
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
          "Fehler beim Laden des Wartelisteneintrags",
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
      pickupLocationsApi,
      filteredPickupLocations,
      shoppingCart,
      setPickupLocationsCapacityCheckLoading,
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
      !pickupLocationsCapacityCheckLoading
    ) {
      setWaitingListModeEnabled(false);
    }

    if (
      !waitingListModeEnabled &&
      selectedPickupLocations.length === 1 &&
      pickupLocationsWithCapacityFull.has(selectedPickupLocations[0]) &&
      !pickupLocationsCapacityCheckLoading
    ) {
      if (hasWaitingListEntry) {
        alert(
          "Du stehst schon auf der Warteliste, deswegen kannst du keine ausgelastete Verteilstation auswählen.",
        );
        setSelectedPickupLocations([]);
      } else {
        setShowWaitingListConfirmationModal(true);
      }
    }
  }, [
    selectedPickupLocations,
    pickupLocationsWithCapacityFull,
    pickupLocationsCapacityCheckLoading,
  ]);

  function onDeliveryModeChange(newDeliveryMode: DeliveryMode) {
    setDeliveryMode(newDeliveryMode);
    setSelectedDeliveryDay(null);
    setSelectedPickupLocations([]);
  }

  function onConfirm() {
    setConfirmLoading(true);
    if (waitingListModeEnabled) {
      waitingListApi
        .waitingListApiWaitingListCreateEntryExistingMemberCreate({
          publicWaitingListEntryExistingMemberCreateRequest: {
            memberId: memberId,
            pickupLocationIds: selectedPickupLocations.map(
              (pickupLocations) => pickupLocations.id,
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
                title: "Wartelisteneintrag erzeugt",
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
                  "Es gibt schon einen Wartelisteneintrag für dich. Wenn du ihn ändern willst, wende dich bitte an die Verwaltung.",
                title: "Wartelisteneintrag nicht erzeugt",
              },
              setToastDatas,
            );
          }
        })
        .catch((error) =>
          handleRequestError(
            error,
            "Fehler beim Erzeugen des Wartelisteneintrags",
            setToastDatas,
          ),
        )
        .finally(() => {
          setConfirmLoading(false);
        });
    } else {
      pickupLocationsApi
        .pickupLocationsApiChangeMemberPickupLocationCreate({
          changeMemberPickupLocationRequestRequest: {
            memberId: memberId,
            pickupLocationId: selectedPickupLocations[0].id,
            deliveryAddress: homeDeliverySelected ? deliveryAddress : undefined,
          },
        })
        .then((response) => {
          if (response.orderConfirmed) {
            onHide();
            addToast(
              {
                id: uuidv4(),
                variant: "success",
                title: "Verteilstation-Wechsel bestätigt",
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
          <div className={"d-flex gap-2 align-items-center"}>
            <Modal.Title>
              <h4 className={"mb-0"}>{pickupLocationLabel} ändern</h4>
            </Modal.Title>
            {!membersCanChangePickupLocationThemselves && (
              <TapirHelpButton
                text={
                  <>
                    Mitglieder können nicht selbstständig ihren Abholort ändern.
                    Sie müssen sich dazu an die Verwaltung wenden. Wenn Sie es
                    selbstständig ändern können sollen, muss die Checkbox
                    "Mitglieder können deren Abholort selber ändern" in der
                    allgemeinen Konfiguration aktiviert werden.
                  </>
                }
              />
            )}
          </div>
        </Modal.Header>
        <Modal.Body>
          {homeDeliveryAvailable && (
            <ButtonGroup className={"mb-3 w-100"}>
              {(["pickup", "home_delivery"] as DeliveryMode[]).map((mode) => (
                <ToggleButton
                  key={mode}
                  id={"delivery_mode_" + mode}
                  value={mode}
                  type={"radio"}
                  variant={"outline-primary"}
                  name={"delivery_mode"}
                  checked={deliveryMode === mode}
                  onChange={() => onDeliveryModeChange(mode)}
                >
                  {mode === "pickup"
                    ? "Abholung an einer Verteilstation"
                    : "Hauslieferung"}
                </ToggleButton>
              ))}
            </ButtonGroup>
          )}
          <DeliveryDayTabs
            availableDays={availableDeliveryDays}
            selectedDay={selectedDeliveryDay}
            onSelectDay={(day) => {
              setSelectedDeliveryDay(day);
              setSelectedPickupLocations([]);
            }}
          />

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
              pickupLocationsCapacityCheckLoading={
                pickupLocationsCapacityCheckLoading
              }
              pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
              waitingListLinkConfirmationModeEnabled={false}
              disabledLocationIds={[currentPickupLocationId]}
            />
          )}
          {homeDeliverySelected && (
            <Form className={"d-flex flex-column gap-2 mt-3"}>
              <h5 className={"mb-0"}>Lieferadresse</h5>
              <DeliveryAddressFields
                deliveryAddress={deliveryAddress}
                setDeliveryAddress={setDeliveryAddress}
              />
            </Form>
          )}
        </Modal.Body>
        <Modal.Footer>
          <TapirButton
            text={
              waitingListModeEnabled
                ? "Wartelisteneintrag bestätigen"
                : "Wechsel bestätigen"
            }
            variant={"primary"}
            icon={waitingListModeEnabled ? "pending_actions" : "check"}
            disabled={
              selectedPickupLocations.length === 0 ||
              (homeDeliverySelected && !isDeliveryAddressValid(deliveryAddress))
            }
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
          "). Du kannst eine andere Station wählen oder dich auf die Warteliste setzen lassen. " +
          "Du kannst dich auch auf die Warteliste von bis zu drei Verteilstationen setzen lassen."
        }
        title={"Verteilstation ausgelastet"}
        open={showWaitingListConfirmationModal}
        confirmButtonText={"Weiter mit Wartelisteneintrag"}
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
