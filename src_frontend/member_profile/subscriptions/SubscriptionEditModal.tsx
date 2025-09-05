import React, { useEffect, useState } from "react";
import { ListGroup, Modal } from "react-bootstrap";
import "dayjs/locale/de";
import {
  BestellWizardApi,
  PickupLocationsApi,
  PublicPickupLocation,
  PublicProductType,
  PublicSubscription,
  SubscriptionsApi,
  WaitingListApi,
} from "../../api-client";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { getCsrfToken } from "../../utils/getCsrfToken.ts";
import { useApi } from "../../hooks/useApi.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { isShoppingCartEmpty } from "../../bestell_wizard/utils/isShoppingCartEmpty.ts";
import { checkPickupLocationCapacities } from "../../bestell_wizard/utils/checkPickupLocationCapacities.ts";
import SubscriptionEditStepPickupLocation from "./steps/SubscriptionEditStepPickupLocation.tsx";
import SubscriptionEditStepProductType from "./steps/SubscriptionEditStepProductType.tsx";
import PickupLocationWaitingListModal from "../../bestell_wizard/components/PickupLocationWaitingListModal.tsx";
import ProductWaitingListModal from "../../bestell_wizard/components/ProductWaitingListModal.tsx";
import SubscriptionEditStepSummary from "./steps/SubscriptionEditStepSummary.tsx";
import { fetchFirstDeliveryDates } from "../../bestell_wizard/utils/fetchFirstDeliveryDates.ts";
import SubscriptionEditStepConfirmation from "./steps/SubscriptionEditStepConfirmation.tsx";
import { isSubscriptionActive } from "../../utils/isSubscriptionActive.ts";
import { ToastData } from "../../types/ToastData.ts";

interface SubscriptionEditModalProps {
  show: boolean;
  onHide: () => void;
  subscriptions: PublicSubscription[];
  productType: PublicProductType;
  memberId: string;
  reloadSubscriptions: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

export type SubscriptionEditStep =
  | "product_type"
  | "pickup_location"
  | "summary"
  | "confirmation";

const SubscriptionEditModal: React.FC<SubscriptionEditModalProps> = ({
  show,
  onHide,
  subscriptions,
  productType,
  memberId,
  reloadSubscriptions,
  setToastDatas,
}) => {
  const subscriptionsApi = useApi(SubscriptionsApi, getCsrfToken());
  const bestellWizardApi = useApi(BestellWizardApi, getCsrfToken());
  const pickupLocationsApi = useApi(PickupLocationsApi, getCsrfToken());
  const waitingListApi = useApi(WaitingListApi, getCsrfToken());

  const [shoppingCart, setShoppingCart] = useState<ShoppingCart>({});
  const [sepaAllowed, setSepaAllowed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [orderConfirmed, setOrderConfirmed] = useState(false);
  const [orderError, setOrderError] = useState("");
  const [checkingCapacities, setCheckingCapacities] = useState(false);
  const [productIdsOverCapacity, setProductIdsOverCapacity] = useState<
    string[]
  >([]);
  const [productTypeIdsOverCapacity, setProductTypeIdsOverCapacity] = useState<
    string[]
  >([]);
  const [waitingListModeEnabled, setWaitingListModeEnabled] = useState(false);
  const [currentStep, setCurrentStep] =
    useState<SubscriptionEditStep>("product_type");
  const [memberHasPickupLocation, setMemberHasPickupLocation] = useState(false);
  const [pickupLocations, setPickupLocations] = useState<
    PublicPickupLocation[]
  >([]);
  const [needPickupLocation, setNeedPickupLocation] = useState(false);
  const [selectedPickupLocations, setSelectedPickupLocations] = useState<
    PublicPickupLocation[]
  >([]);
  const [
    pickupLocationsWithCapacityCheckLoading,
    setPickupLocationsWithCapacityCheckLoading,
  ] = useState<Set<PublicPickupLocation>>(new Set<PublicPickupLocation>());
  const [pickupLocationsWithCapacityFull, setPickupLocationsWithCapacityFull] =
    useState<Set<PublicPickupLocation>>(new Set<PublicPickupLocation>());
  const [forceWaitingList, setForceWaitingList] = useState(false);
  const [showWaitingListConfirmModal, setShowWaitingListConfirmModal] =
    useState(false);
  const [steps, setSteps] = useState<SubscriptionEditStep[]>([]);
  const [firstDeliveryDatesByProductType, setFirstDeliveryDatesByProductType] =
    useState<{ [key: string]: Date }>({});
  const [labelCheckboxSepaMandat, setLabelCheckboxSepaMandat] = useState("");
  const [contractStartDate, setContractStartDate] = useState(new Date());

  useEffect(() => {
    if (!show) return;

    setCurrentStep("product_type");

    pickupLocationsApi
      .pickupLocationsApiGetMemberPickupLocationRetrieve({ memberId: memberId })
      .then((response) => {
        setMemberHasPickupLocation(response.hasLocation);
        if (response.hasLocation) {
          setSelectedPickupLocations([response.location!]);
        }
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Verteilstation",
          setToastDatas,
        ),
      );

    bestellWizardApi
      .bestellWizardApiBestellWizardBaseDataRetrieve()
      .then((response) => {
        setForceWaitingList(response.forceWaitingList);
        setLabelCheckboxSepaMandat(response.labelCheckboxSepaMandat);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der BestellWizard-Daten",
          setToastDatas,
        ),
      );

    bestellWizardApi
      .bestellWizardApiNextContractStartDateRetrieve({
        waitingListEntryId: undefined,
      })
      .then((result) => setContractStartDate(new Date(result)))
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Vertragsstart-Datum",
          setToastDatas,
        ),
      );

    if (productType.forceWaitingList) {
      setShowWaitingListConfirmModal(true);
    }
  }, [show]);

  useEffect(() => {
    if (!show) return;

    const shoppingCart: ShoppingCart = Object.fromEntries(
      productType.products.map((product) => [product.id, 0]),
    );
    for (const subscription of subscriptions) {
      if (isSubscriptionActive(subscription)) {
        shoppingCart[subscription.productId] = subscription.quantity;
      }
    }
    setShoppingCart(shoppingCart);
  }, [subscriptions, show]);

  useEffect(() => {
    if (!show) return;

    setCheckingCapacities(true);

    subscriptionsApi
      .subscriptionsApiMemberProfileCapacityCheckCreate({
        memberProfileCapacityCheckRequestRequest: {
          shoppingCart: shoppingCart,
          memberId: memberId,
        },
      })
      .then((response) => {
        setProductIdsOverCapacity(response.idsOfProductsOverCapacity);
        setProductTypeIdsOverCapacity(response.idsOfProductTypesOverCapacity);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Prüfen der Kapazitäten",
          setToastDatas,
        ),
      )
      .finally(() => setCheckingCapacities(false));
  }, [shoppingCart, show]);

  useEffect(() => {
    setNeedPickupLocation(!memberHasPickupLocation && !productType.noDelivery);
  }, [productType, memberHasPickupLocation, show]);

  useEffect(() => {
    if (!show) return;

    pickupLocationsApi
      .pickupLocationsPublicPickupLocationsList()
      .then(setPickupLocations)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Verteilstationen",
          setToastDatas,
        ),
      );

    let steps: SubscriptionEditStep[] = [
      "product_type",
      "pickup_location",
      "summary",
      "confirmation",
    ];
    if (!needPickupLocation) {
      steps = steps.filter((step) => step !== "pickup_location");
    }
    setSteps(steps);
  }, [show, needPickupLocation]);

  useEffect(() => {
    if (isShoppingCartEmpty(shoppingCart) || !show || !needPickupLocation) {
      return;
    }

    checkPickupLocationCapacities(
      pickupLocations,
      shoppingCart,
      setPickupLocationsWithCapacityCheckLoading,
      setPickupLocationsWithCapacityFull,
      setToastDatas,
    );
  }, [pickupLocations, show, needPickupLocation, shoppingCart]);

  useEffect(() => {
    if (forceWaitingList) {
      setWaitingListModeEnabled(true);
      return;
    }

    if (
      productIdsOverCapacity.length === 0 &&
      productTypeIdsOverCapacity.length === 0 &&
      selectedPickupLocations.length > 0 &&
      pickupLocationsWithCapacityCheckLoading.size === 0 &&
      !pickupLocationsWithCapacityFull.has(selectedPickupLocations[0])
    ) {
      setWaitingListModeEnabled(false);
    }
  }, [
    forceWaitingList,
    productIdsOverCapacity,
    productTypeIdsOverCapacity,
    selectedPickupLocations,
    pickupLocationsWithCapacityCheckLoading,
    pickupLocationsWithCapacityFull,
  ]);

  useEffect(() => {
    fetchFirstDeliveryDates(
      selectedPickupLocations,
      shoppingCart,
      setFirstDeliveryDatesByProductType,
      setToastDatas,
      undefined,
    );
  }, [selectedPickupLocations, shoppingCart]);

  function onConfirmOrder() {
    setLoading(true);

    if (waitingListModeEnabled) {
      waitingListApi
        .waitingListApiWaitingListCreateEntryExistingMemberCreate({
          publicWaitingListEntryExistingMemberCreateRequest: {
            productIds: Object.keys(shoppingCart),
            productQuantities: Object.values(shoppingCart),
            pickupLocationIds: selectedPickupLocations.map(
              (pickupLocations) => pickupLocations.id!,
            ),
            memberId: memberId,
          },
        })
        .then((response) => {
          setOrderConfirmed(response.orderConfirmed);
          if (!response.orderConfirmed) {
            setOrderError(response.error!);
          }
          setCurrentStep("confirmation");
        })
        .catch((error) =>
          handleRequestError(
            error,
            "Fehler beim Erzeugen des Warteliste-Eintrags",
            setToastDatas,
          ),
        )
        .finally(() => setLoading(false));
    } else {
      subscriptionsApi
        .subscriptionsApiUpdateSubscriptionCreate({
          updateSubscriptionsRequestRequest: {
            memberId: memberId,
            shoppingCart: shoppingCart,
            sepaAllowed: sepaAllowed,
            productTypeId: productType.id!,
            pickupLocationId:
              selectedPickupLocations.length > 0
                ? selectedPickupLocations[0].id
                : undefined,
          },
        })
        .then((response) => {
          setOrderConfirmed(response.orderConfirmed);
          if (!response.orderConfirmed) {
            setOrderError(response.error!);
          }
          setCurrentStep("confirmation");
        })
        .catch(async (error) => {
          await handleRequestError(
            error,
            "Fehler beim Anpassen der Verträge",
            setToastDatas,
          );
          setOrderConfirmed(false);
          setOrderError(
            "Fehler beim Anpassen der Verträge, bitte versuche es später nochmal oder kontaktiere die Verwaltung",
          );
          setCurrentStep("confirmation");
        })
        .finally(() => setLoading(false));
    }
  }

  function goToNextStep() {
    setCurrentStep(steps[steps.indexOf(currentStep) + 1]);
  }

  function goToPreviousStep() {
    setCurrentStep(steps[steps.indexOf(currentStep) - 1]);
  }

  function onNextClicked() {
    if (waitingListModeEnabled) {
      goToNextStep();
      return;
    }

    if (
      productIdsOverCapacity.length > 0 ||
      productTypeIdsOverCapacity.length > 0
    ) {
      setShowWaitingListConfirmModal(true);
      return;
    }

    if (
      selectedPickupLocations.length > 0 &&
      pickupLocationsWithCapacityFull.has(selectedPickupLocations[0])
    ) {
      setShowWaitingListConfirmModal(true);
      return;
    }

    goToNextStep();
  }

  return (
    <>
      <Modal
        show={show && !showWaitingListConfirmModal}
        onHide={onHide}
        centered={true}
        size={"lg"}
      >
        <Modal.Header closeButton>
          <h5 className={"mb-0"}>Neuen {productType.name} bestellen</h5>
        </Modal.Header>
        <ListGroup variant={"flush"}>
          {waitingListModeEnabled && (
            <ListGroup.Item className={"list-group-item-warning"}>
              <div className={"text-center"}>Warteliste-Eintrag</div>
            </ListGroup.Item>
          )}
          {currentStep == "product_type" && (
            <SubscriptionEditStepProductType
              productType={productType}
              shoppingCart={shoppingCart}
              setShoppingCart={setShoppingCart}
              checkingCapacities={checkingCapacities}
              loading={loading}
              sepaAllowed={sepaAllowed}
              setSepaAllowed={setSepaAllowed}
              onCancelClicked={onHide}
              onNextClicked={onNextClicked}
              labelCheckboxSepaMandat={labelCheckboxSepaMandat}
            />
          )}
          {currentStep == "pickup_location" && (
            <SubscriptionEditStepPickupLocation
              pickupLocations={pickupLocations}
              setSelectedPickupLocations={setSelectedPickupLocations}
              selectedPickupLocations={selectedPickupLocations}
              pickupLocationsWithCapacityCheckLoading={
                pickupLocationsWithCapacityCheckLoading
              }
              pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
              waitingListModeEnabled={waitingListModeEnabled}
              onBackClicked={goToPreviousStep}
              onNextClicked={onNextClicked}
            />
          )}
          {currentStep === "summary" && (
            <SubscriptionEditStepSummary
              waitingListModeEnabled={waitingListModeEnabled}
              selectedPickupLocations={selectedPickupLocations}
              shoppingCart={shoppingCart}
              productType={productType}
              firstDeliveryDatesByProductType={firstDeliveryDatesByProductType}
              onBackClicked={goToPreviousStep}
              onConfirmClicked={onConfirmOrder}
              loading={loading}
              contractStartDate={contractStartDate}
            />
          )}
          {currentStep === "confirmation" && (
            <SubscriptionEditStepConfirmation
              orderConfirmed={orderConfirmed}
              error={orderError}
              onBackClicked={() => setCurrentStep("product_type")}
              onFinishedClicked={() => {
                reloadSubscriptions();
                onHide();
              }}
              waitingListModeEnabled={waitingListModeEnabled}
            />
          )}
        </ListGroup>
      </Modal>
      <PickupLocationWaitingListModal
        show={showWaitingListConfirmModal && currentStep === "pickup_location"}
        onHide={() => setShowWaitingListConfirmModal(false)}
        confirmEnableWaitingListMode={() => {
          setWaitingListModeEnabled(true);
          setShowWaitingListConfirmModal(false);
        }}
      />
      <ProductWaitingListModal
        show={showWaitingListConfirmModal && currentStep === "product_type"}
        onHide={() => setShowWaitingListConfirmModal(false)}
        confirmEnableWaitingListMode={() => {
          setWaitingListModeEnabled(true);
          setShowWaitingListConfirmModal(false);
        }}
        productType={productType}
      />
    </>
  );
};

export default SubscriptionEditModal;
