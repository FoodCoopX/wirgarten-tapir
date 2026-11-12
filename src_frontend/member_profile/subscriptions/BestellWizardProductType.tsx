import React, { useEffect, useState } from "react";
import { Spinner } from "react-bootstrap";

import "../../../tapir/core/static/core/bootstrap/5.3.8/css/bootstrap.min.css";
import "../../../tapir/core/static/core/css/base.css";
import {
  BestellWizardApi,
  CoopApi,
  DeliveryAddressRequest,
  PaymentsApi,
  PickupLocationsApi,
  PublicGrowingPeriod,
  PublicPickupLocation,
  PublicProductType,
  SubscriptionsApi,
  WaitingListApi,
} from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { buildEmptySettings } from "../../bestell_wizard/utils/buildEmptySettings.ts";
import { buildEmptyShoppingCart } from "../../bestell_wizard/utils/buildEmptyShoppingCart.ts";
import { buildSettings } from "../../bestell_wizard/utils/buildSettings.ts";
import { checkPickupLocationCapacities } from "../../bestell_wizard/utils/checkPickupLocationCapacities.ts";
import { fetchFirstDeliveryDates } from "../../bestell_wizard/utils/fetchFirstDeliveryDates.ts";
import { formatShoppingCart } from "../../bestell_wizard/utils/formatShoppingCart.ts";
import { getEmptyPersonalData } from "../../bestell_wizard/utils/getEmptyPersonalData.ts";
import { isShoppingCartEmpty } from "../../bestell_wizard/utils/isShoppingCartEmpty.ts";
import { updateProductsAndProductTypesOverCapacity } from "../../bestell_wizard/utils/updateProductsAndProductTypesOverCapacity.ts";
import BestellWizardMobileBase from "../../bestell_wizard_mobile/components/BestellWizardMobileBase.tsx";
import Step10OrderSummary from "../../bestell_wizard_mobile/steps/Step10OrderSummary.tsx";
import Step11Legal from "../../bestell_wizard_mobile/steps/Step11Legal.tsx";
import Step3BGrowingPeriodChoice from "../../bestell_wizard_mobile/steps/Step3BGrowingPeriodChoice.tsx";
import Step4BProductTypeOrder from "../../bestell_wizard_mobile/steps/Step4BProductTypeOrder.tsx";
import Step5BDeliveryModeChoice from "../../bestell_wizard_mobile/steps/Step5BDeliveryModeChoice.tsx";
import Step5CPickupLocationChoice from "../../bestell_wizard_mobile/steps/Step5CPickupLocationChoice.tsx";
import Step5DHomeDeliveryChoice from "../../bestell_wizard_mobile/steps/Step5DHomeDeliveryChoice.tsx";
import Step8BDeliveryAddress from "../../bestell_wizard_mobile/steps/Step8BDeliveryAddress.tsx";
import Step9BankingData from "../../bestell_wizard_mobile/steps/Step9BankingData.tsx";
import StepGenericIntro from "../../bestell_wizard_mobile/steps/StepGenericIntro.tsx";
import { DeliveryMode } from "../../bestell_wizard_mobile/types/DeliveryMode.ts";
import { PickupLocationTab } from "../../bestell_wizard_mobile/types/PickupLocationTab.ts";
import { Step } from "../../bestell_wizard_mobile/types/Step.ts";
import { getFirstPickupLocationWithCapacity } from "../../bestell_wizard_mobile/utils/getFirstPickupLocationWithCapacity.ts";
import { getPickupLocationsForDeliveryMode } from "../../bestell_wizard_mobile/utils/getPickupLocationsForDeliveryMode.ts";
import { getProductTypeFromStep } from "../../bestell_wizard_mobile/utils/getProductTypeFromStep.ts";
import { shouldIncludeStepGrowingPeriodChoice } from "../../bestell_wizard_mobile/utils/shouldIncludeStepGrowingPeriodChoice.ts";
import { updateWaitingList } from "../../bestell_wizard_mobile/utils/updateWaitingList.ts";
import ConfirmModal from "../../components/ConfirmModal.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { isSubscriptionActive } from "../../utils/isSubscriptionActive.ts";

interface BestellWizardProductTypeProps {
  csrfToken: string;
  memberId: string;
  memberUrl: string;
  firstName: string;
  lastName: string;
  needsBankingData: boolean;
  productTypeId: string;
}

const BestellWizardProductType: React.FC<BestellWizardProductTypeProps> = ({
  csrfToken,
  memberId,
  memberUrl,
  firstName,
  lastName,
  needsBankingData,
  productTypeId,
}) => {
  const bestellWizardApi = useApi(BestellWizardApi, csrfToken);
  const pickupLocationApi = useApi(PickupLocationsApi, csrfToken);
  const waitingListApi = useApi(WaitingListApi, csrfToken);
  const subscriptionsApi = useApi(SubscriptionsApi, csrfToken);
  const paymentsApi = useApi(PaymentsApi, csrfToken);
  const coopApi = useApi(CoopApi, csrfToken);

  const [settings, setSettings] =
    useState<BestellWizardSettings>(buildEmptySettings());
  const [settingsLoaded, setSettingsLoaded] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [steps, setSteps] = useState<Step[]>(["loading"]);
  const [currentStep, setCurrentStep] = useState<Step>("loading");
  const [orderLoading, setOrderLoading] = useState(false);
  const [waitingListError, setWaitingListError] = useState<string>();
  const [productType, setProductType] = useState<PublicProductType>();
  const [checkingCapacities, setCheckingCapacities] = useState(false);
  const [productIdsOverCapacity, setProductIdsOverCapacity] = useState<
    string[]
  >([]);
  const [productTypeIdsOverCapacity, setProductTypeIdsOverCapacity] = useState<
    string[]
  >([]);
  const [checkingCapacitiesController, setCheckingCapacitiesController] =
    useState<AbortController>();
  const [productTypesInWaitingList, setProductTypesInWaitingList] = useState<
    Set<PublicProductType>
  >(new Set<PublicProductType>());
  const [pickupLocationsWithCapacityFull, setPickupLocationsWithCapacityFull] =
    useState<Set<PublicPickupLocation>>(new Set<PublicPickupLocation>());
  const [
    pickupLocationsCapacityCheckLoading,
    setPickupLocationsCapacityCheckLoading,
  ] = useState(false);
  const [
    firstDeliveryDatesByPickupLocationAndProductType,
    setFirstDeliveryDatesByPickupLocationAndProductType,
  ] = useState<{ [key: string]: { [key: string]: Date } }>({});
  const [currentPickupLocationTab, setCurrentPickupLocationTab] =
    useState<PickupLocationTab>("map");
  const [mustAddPickupLocation, setMustAddPickupLocation] = useState(false);
  const [canChangePaymentRhythm, setCanChangePaymentRhythm] = useState(false);
  const [
    memberAlreadyHasASubscriptionForThisProductType,
    setMemberAlreadyHasASubscriptionForThisProductType,
  ] = useState(false);

  const [contractAccepted, setContractAccepted] = useState(false);
  const [cancellationPolicyRead, setCancellationPolicyRead] = useState(false);
  const [privacyPolicyRead, setPrivacyPolicyRead] = useState(false);
  const [sepaAllowed, setSepaAllowed] = useState(false);
  const [personalData, setPersonalData] = useState<PersonalData>(
    getEmptyPersonalData(),
  );
  const [selectedPickupLocations, setSelectedPickupLocations] = useState<
    PublicPickupLocation[]
  >([]);
  const [selectedGrowingPeriod, setSelectedGrowingPeriod] =
    useState<PublicGrowingPeriod>();
  const [shoppingCart, setShoppingCart] = useState<ShoppingCart>({});
  const [deliveryMode, setDeliveryMode] = useState<DeliveryMode>("pickup");
  const [deliveryAddress, setDeliveryAddress] =
    useState<DeliveryAddressRequest>({ sameAsBillingAddress: true });

  useEffect(() => {
    setPersonalData({
      ...personalData,
      firstName: firstName,
      lastName: lastName,
    });

    Promise.all([
      bestellWizardApi.bestellWizardApiBestellWizardBaseDataRetrieve(),
      paymentsApi.paymentsApiCanLoggedInUserChangeTargetsPaymentRhythmRetrieve({
        memberId: memberId,
      }),
      subscriptionsApi.subscriptionsApiMemberSubscriptionDataRetrieve({
        memberId: memberId,
      }),
      coopApi.coopApiMemberBankingDataRetrieve({ memberId: memberId }),
      pickupLocationApi.pickupLocationsApiMemberDeliveryAddressRetrieve({
        memberId: memberId,
      }),
    ])
      .then(
        ([
          baseData,
          canChangePaymentRhythmResponse,
          subscriptionData,
          bankingData,
          memberDeliveryAddress,
        ]) => {
          const newSettings = buildSettings(baseData);
          for (const productType of newSettings.productTypes) {
            productType.mustBeSubscribedTo = true;
          }
          setSettings(newSettings);
          setSettingsLoaded(true);

          if (newSettings.growingPeriodChoices.length > 0) {
            setSelectedGrowingPeriod(newSettings.growingPeriodChoices[0]);
          }

          setShoppingCart(buildEmptyShoppingCart(newSettings.productTypes));

          setProductType(
            newSettings.productTypes.find(
              (productType) => productType.id === productTypeId,
            ),
          );

          setDeliveryAddress({
            sameAsBillingAddress: memberDeliveryAddress.sameAsBillingAddress,
            street: memberDeliveryAddress.street,
            street2: memberDeliveryAddress.street2,
            postcode: memberDeliveryAddress.postcode,
            city: memberDeliveryAddress.city,
            country: memberDeliveryAddress.country || "DE",
          });

          setCanChangePaymentRhythm(canChangePaymentRhythmResponse.canChange);
          setPersonalData({
            ...personalData,
            paymentRhythm: canChangePaymentRhythmResponse.currentRhythm,
            firstName: firstName,
            lastName: lastName,
            iban: bankingData.iban,
            accountOwner: bankingData.accountOwner,
          });

          for (const subscription of subscriptionData.subscriptions) {
            if (
              subscription.productType.id === productTypeId &&
              isSubscriptionActive(subscription)
            ) {
              setMemberAlreadyHasASubscriptionForThisProductType(true);
              break;
            }
          }
        },
      )
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden des BestellWizards",
          setToastDatas,
        ),
      );
  }, []);

  useEffect(() => {
    if (!settingsLoaded || !productType) {
      return;
    }

    pickupLocationApi
      .pickupLocationsApiGetMemberPickupLocationRetrieve({
        memberId: memberId,
        growingPeriodId: selectedGrowingPeriod?.id,
      })
      .then((pickupLocationData) => {
        setMustAddPickupLocation(
          !productType.noDelivery && !pickupLocationData.hasLocation,
        );
        if (pickupLocationData.hasLocation) {
          setSelectedPickupLocations([pickupLocationData.location!]);
        }
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Mitgliedsstation",
          setToastDatas,
        ),
      );
  }, [settingsLoaded, selectedGrowingPeriod, productType]);

  useEffect(() => {
    if (!settingsLoaded || !productType) {
      setSteps(["loading"]);
      return;
    }

    const newSteps = buildStepsFor(deliveryMode);
    setSteps(newSteps);
    setCurrentStep(newSteps[0]);
  }, [settingsLoaded, needsBankingData, productType, mustAddPickupLocation]);

  function getHomeDeliveryLocations() {
    return getPickupLocationsForDeliveryMode(
      settings.pickupLocations,
      "home_delivery",
    );
  }

  function buildStepsFor(deliveryMode: DeliveryMode) {
    const newSteps = [];
    if (
      !memberAlreadyHasASubscriptionForThisProductType &&
      shouldIncludeStepGrowingPeriodChoice(settings.growingPeriodChoices)
    ) {
      newSteps.push("3b_growing_period_choice");
    }

    newSteps.push(productTypeId + "_intro", productTypeId + "_order");

    if (mustAddPickupLocation) {
      newSteps.push("5a_pickup_location_intro");
      const homeDeliveryLocations = getHomeDeliveryLocations();
      if (homeDeliveryLocations.length > 0) {
        newSteps.push("5b_delivery_mode_choice");
      }
      if (deliveryMode === "pickup") {
        newSteps.push("5c_pickup_location_choice");
      } else {
        if (homeDeliveryLocations.length > 1) {
          newSteps.push("5d_home_delivery_choice");
        }
        newSteps.push("8b_delivery_address");
      }
    }

    newSteps.push("9_banking_data", "10_summary", "11_legal");
    return newSteps;
  }

  function onDeliveryModeChosen(newDeliveryMode: DeliveryMode) {
    let newSelection = selectedPickupLocations;
    if (newDeliveryMode !== deliveryMode) {
      const locations = getPickupLocationsForDeliveryMode(
        settings.pickupLocations,
        newDeliveryMode,
      );
      newSelection =
        newDeliveryMode === "home_delivery" && locations.length === 1
          ? locations
          : [];
    }
    setDeliveryMode(newDeliveryMode);
    setSelectedPickupLocations(newSelection);

    const newSteps = buildStepsFor(newDeliveryMode);
    setSteps(newSteps);
    setCurrentStep(newSteps[newSteps.indexOf("5b_delivery_mode_choice") + 1]);
  }

  function isHomeDeliverySelected() {
    return selectedPickupLocations.some(
      (pickupLocation) => pickupLocation.isHomeDelivery,
    );
  }

  useEffect(() => {
    updateProductsAndProductTypesOverCapacity(
      bestellWizardApi,
      shoppingCart,
      setProductIdsOverCapacity,
      setProductTypeIdsOverCapacity,
      setCheckingCapacities,
      setToastDatas,
      checkingCapacitiesController,
      setCheckingCapacitiesController,
      selectedGrowingPeriod,
    );
  }, [shoppingCart, selectedGrowingPeriod]);

  useEffect(() => {
    updateWaitingList(
      selectedPickupLocations,
      pickupLocationsWithCapacityFull,
      settings,
      shoppingCart,
      productTypeIdsOverCapacity,
      productIdsOverCapacity,
      setProductTypesInWaitingList,
    );
  }, [
    productTypeIdsOverCapacity,
    productIdsOverCapacity,
    pickupLocationsWithCapacityFull,
    selectedPickupLocations,
    shoppingCart,
  ]);

  useEffect(() => {
    if (
      settings.pickupLocations.length === 0 ||
      isShoppingCartEmpty(shoppingCart)
    ) {
      return;
    }

    checkPickupLocationCapacities(
      pickupLocationApi,
      settings.pickupLocations,
      shoppingCart,
      setPickupLocationsCapacityCheckLoading,
      setPickupLocationsWithCapacityFull,
      setToastDatas,
      selectedGrowingPeriod,
    );
  }, [settings, shoppingCart, selectedGrowingPeriod]);

  useEffect(() => {
    if (!selectedGrowingPeriod) {
      return;
    }

    fetchFirstDeliveryDates(
      bestellWizardApi,
      shoppingCart,
      selectedGrowingPeriod,
      setFirstDeliveryDatesByPickupLocationAndProductType,
      setToastDatas,
      undefined,
    );
  }, [shoppingCart, selectedGrowingPeriod]);

  useEffect(() => {
    setSepaAllowed(!needsBankingData);
  }, [needsBankingData]);

  function goToNextStep() {
    const currentIndex = steps.indexOf(currentStep);
    if (currentIndex + 1 >= steps.length) {
      onConfirm();
      return;
    }

    setCurrentStep(steps[steps.indexOf(currentStep) + 1]);
  }

  function onConfirm() {
    setOrderLoading(true);

    if (productTypesInWaitingList.size > 0) {
      waitingListApiCall();
    } else {
      orderApiCall();
    }
  }

  function orderApiCall() {
    subscriptionsApi
      .subscriptionsApiUpdateSubscriptionCreate({
        updateSubscriptionsRequestRequest: {
          memberId: memberId,
          shoppingCart: shoppingCart,
          sepaAllowed: sepaAllowed,
          cancellationPolicyRead: cancellationPolicyRead,
          productTypeId: productTypeId,
          pickupLocationId: getFirstPickupLocationWithCapacity(
            selectedPickupLocations,
            pickupLocationsWithCapacityFull,
          )!.id,
          growingPeriodId: selectedGrowingPeriod!.id!,
          iban: personalData.iban,
          accountOwner: personalData.accountOwner,
          paymentRhythm: personalData.paymentRhythm,
          deliveryAddress:
            mustAddPickupLocation && isHomeDeliverySelected()
              ? deliveryAddress
              : undefined,
        },
      })
      .then((response) => {
        if (response.orderConfirmed) {
          if (response.redirectUrl) {
            globalThis.location.assign(response.redirectUrl);
          }
        } else {
          alert(response.error);
          setOrderLoading(false);
        }
      })
      .catch(async (error) => {
        await handleRequestError(
          error,
          "Fehler beim Anpassen der Verträge",
          setToastDatas,
        );
        setOrderLoading(false);
      });
  }

  function waitingListApiCall() {
    waitingListApi
      .waitingListApiWaitingListCreateEntryExistingMemberCreate({
        publicWaitingListEntryExistingMemberCreateRequest: {
          shoppingCart: shoppingCart,
          pickupLocationIds: selectedPickupLocations.map(
            (pickupLocations) => pickupLocations.id,
          ),
          memberId: memberId,
        },
      })
      .then((response) => {
        if (response.orderConfirmed) {
          if (response.redirectUrl) {
            globalThis.location.assign(response.redirectUrl);
          }
        } else {
          setWaitingListError(
            response.error ??
              "Der Wartelisteneintrag konnte nicht erstellt werden.",
          );
          setOrderLoading(false);
        }
      })
      .catch(async (error) => {
        await handleRequestError(
          error,
          "Fehler beim Erzeugen des Wartelisteneintrags",
          setToastDatas,
        );
        setOrderLoading(false);
      });
  }

  function getConfirmButtonText() {
    return "Jetzt " + formatShoppingCart(shoppingCart, settings) + " bestellen";
  }

  function getStepComponent(step: Step) {
    switch (step) {
      case "3b_growing_period_choice":
        return (
          <Step3BGrowingPeriodChoice
            goToNextStep={goToNextStep}
            settings={settings}
            selectedGrowingPeriod={selectedGrowingPeriod}
            setSelectedGrowingPeriod={setSelectedGrowingPeriod}
            stepActive={step === currentStep}
          />
        );
      case "5a_pickup_location_intro":
        return (
          <StepGenericIntro
            content={{
              text: settings.strings.step5aText,
            }}
            goToNextStep={goToNextStep}
            stepActive={step === currentStep}
          />
        );
      case "5b_delivery_mode_choice":
        return (
          <Step5BDeliveryModeChoice
            settings={settings}
            onDeliveryModeChosen={onDeliveryModeChosen}
          />
        );
      case "5d_home_delivery_choice":
        return (
          <Step5DHomeDeliveryChoice
            settings={settings}
            selectedPickupLocations={selectedPickupLocations}
            setSelectedPickupLocations={setSelectedPickupLocations}
            pickupLocationsCapacityCheckLoading={
              pickupLocationsCapacityCheckLoading
            }
            pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
            goToNextStep={goToNextStep}
            firstDeliveryDatesByPickupLocationAndProductType={
              firstDeliveryDatesByPickupLocationAndProductType
            }
            stepActive={currentStep === step}
            productTypesInWaitingList={productTypesInWaitingList}
            shoppingCart={shoppingCart}
            productTypeIdsOverCapacity={productTypeIdsOverCapacity}
            productIdsOverCapacity={productIdsOverCapacity}
            changesDisabled={false}
          />
        );
      case "8b_delivery_address":
        return (
          <Step8BDeliveryAddress
            settings={settings}
            goToNextStep={goToNextStep}
            deliveryAddress={deliveryAddress}
            setDeliveryAddress={setDeliveryAddress}
            stepActive={currentStep === step}
          />
        );
      case "5c_pickup_location_choice":
        return (
          <Step5CPickupLocationChoice
            settings={settings}
            selectedPickupLocations={selectedPickupLocations}
            setSelectedPickupLocations={setSelectedPickupLocations}
            pickupLocationsCapacityCheckLoading={
              pickupLocationsCapacityCheckLoading
            }
            pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
            goToNextStep={goToNextStep}
            stepIsActive={step === "5c_pickup_location_choice"}
            firstDeliveryDatesByPickupLocationAndProductType={
              firstDeliveryDatesByPickupLocationAndProductType
            }
            stepActive={currentStep === step}
            productTypesInWaitingList={productTypesInWaitingList}
            shoppingCart={shoppingCart}
            currentTab={currentPickupLocationTab}
            setCurrentTab={setCurrentPickupLocationTab}
            productTypeIdsOverCapacity={productTypeIdsOverCapacity}
            productIdsOverCapacity={productIdsOverCapacity}
            isOrderStep={step === steps.at(-1)}
            orderLoading={orderLoading}
            nextButtonTextOverride={
              step === steps.at(-1) ? getConfirmButtonText() : undefined
            }
            changesDisabled={false}
          />
        );
      case "9_banking_data":
        return (
          <Step9BankingData
            goToNextStep={goToNextStep}
            personalData={personalData}
            setPersonalData={setPersonalData}
            sepaAllowed={sepaAllowed}
            setSepaAllowed={setSepaAllowed}
            contractAccepted={contractAccepted}
            setContractAccepted={setContractAccepted}
            autoFillAccountOwnerFromName={false}
            settings={settings}
            shoppingCart={shoppingCart}
            solidarityContribution={0}
            stepActive={currentStep === step}
            productTypesInWaitingList={new Set()}
            isOrderStep={step === steps.at(-1)}
            orderLoading={orderLoading}
            nextButtonText={
              step === steps.at(-1) ? getConfirmButtonText() : undefined
            }
            canChangePaymentRhythm={canChangePaymentRhythm}
          />
        );
      case "10_summary":
        return (
          <Step10OrderSummary
            isOrderStep={false}
            confirmOrderLoading={orderLoading}
            settings={settings}
            shoppingCart={shoppingCart}
            solidarityContribution={0}
            productTypesInWaitingList={productTypesInWaitingList}
            personalData={personalData}
            confirmOrder={onConfirm}
            goToNextStep={goToNextStep}
            goToProductTypeStep={() => {
              setCurrentStep(productTypeId + "_order");
            }}
            selectedPickupLocations={selectedPickupLocations}
            becomeMemberNow={false}
            firstDeliveryDatesByPickupLocationAndProductType={
              firstDeliveryDatesByPickupLocationAndProductType
            }
            numberOfCoopShares={0}
            pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
            studentStatusEnabled={false}
            waitingListEntryDetails={undefined}
            contractStartDate={selectedGrowingPeriod?.contractStartDate!}
            singleProductType={productType}
            selectedGrowingPeriod={selectedGrowingPeriod}
            hideTrialPeriod={memberAlreadyHasASubscriptionForThisProductType}
            stepActive={step === currentStep}
            setCurrentStep={setCurrentStep}
            deliveryAddress={
              mustAddPickupLocation && !deliveryAddress.sameAsBillingAddress
                ? deliveryAddress
                : undefined
            }
          />
        );
      case "11_legal":
        return (
          <Step11Legal
            goToNextStep={goToNextStep}
            settings={settings}
            shoppingCart={shoppingCart}
            solidarityContribution={0}
            productTypesInWaitingList={productTypesInWaitingList}
            cancellationPolicyRead={cancellationPolicyRead}
            setCancellationPolicyRead={setCancellationPolicyRead}
            privacyPolicyRead={privacyPolicyRead}
            setPrivacyPolicyRead={setPrivacyPolicyRead}
            stepActive={currentStep === step}
            isOrderStep={step === steps.at(-1)}
            confirmOrderLoading={orderLoading}
            confirmOrder={onConfirm}
          />
        );

      case "loading":
        return (
          <div
            style={{ width: "100%", height: "100%" }}
            className={"d-flex justify-content-center align-items-center"}
          >
            <Spinner />
          </div>
        );
      default: {
        const [productType, subStep] = getProductTypeFromStep(step, settings);
        if (productType === undefined) {
          return <div>Fehler: ungültiger Schritt {step}</div>;
        }
        switch (subStep) {
          case "intro":
            return (
              <StepGenericIntro
                content={{
                  text: productType.descriptionBestellwizardLong,
                  accordions: productType.accordions,
                }}
                goToNextStep={goToNextStep}
                stepActive={step === currentStep}
              />
            );
          case "order":
            return (
              <Step4BProductTypeOrder
                settings={settings}
                productType={productType}
                goToNextStep={goToNextStep}
                shoppingCart={shoppingCart}
                setShoppingCart={setShoppingCart}
                stepActive={step === currentStep}
                checkingCapacities={checkingCapacities}
                productTypeIdsOverCapacity={productTypeIdsOverCapacity}
                productIdsOverCapacity={productIdsOverCapacity}
                waitingListLinkConfirmationModeEnabled={false}
                waitingListEntryDetails={undefined}
                productTypesInWaitingList={productTypesInWaitingList}
                isOrderStep={step === steps.at(-1)}
                orderLoading={orderLoading}
                nextButtonTextOverride={
                  step === steps.at(-1) ? getConfirmButtonText() : undefined
                }
              />
            );
        }
      }
    }
  }

  return (
    <>
      <BestellWizardMobileBase
        settings={settings}
        steps={steps}
        currentStep={currentStep}
        setCurrentStep={setCurrentStep}
        shoppingCart={shoppingCart}
        phases={[]}
        selectedPickupLocations={selectedPickupLocations}
        solidarityContribution={0}
        productTypesInWaitingList={productTypesInWaitingList}
        personalData={personalData}
        getStepComponent={getStepComponent}
        setTestData={() => {}}
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
        showProgress={steps.length > 2}
        hideFooterButtonsOnLastStep={false}
        selectedNumberOfCoopShares={0}
        goToProductTypeStep={() => {
          setCurrentStep(productTypeId + "_order");
        }}
        contractStartDate={selectedGrowingPeriod?.contractStartDate!}
        selectedGrowingPeriod={selectedGrowingPeriod}
      />
      <ConfirmModal
        open={waitingListError !== undefined}
        title="Wartelisteneintrag nicht erstellt"
        message={waitingListError}
        confirmButtonText="Zum Mitgliederbereich"
        confirmButtonVariant="primary"
        confirmButtonIcon="arrow_back"
        onConfirm={() => globalThis.location.assign(memberUrl)}
        onCancel={() => setWaitingListError(undefined)}
      />
    </>
  );
};

export default BestellWizardProductType;
