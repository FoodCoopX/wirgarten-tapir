import React, { useEffect, useState } from "react";
import { Spinner } from "react-bootstrap";

import "../../../tapir/core/static/core/bootstrap/5.3.8/css/bootstrap.min.css";
import "../../../tapir/core/static/core/css/base.css";
import { useApi } from "../../hooks/useApi.ts";
import {
  BestellWizardApi,
  PaymentsApi,
  PickupLocationsApi,
  PublicGrowingPeriod,
  PublicPickupLocation,
  PublicProductType,
  SubscriptionsApi,
  WaitingListApi,
} from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { buildEmptySettings } from "../../bestell_wizard/utils/buildEmptySettings.ts";
import { ToastData } from "../../types/ToastData.ts";
import { Step } from "../../bestell_wizard_mobile/types/Step.ts";
import { buildSettings } from "../../bestell_wizard/utils/buildSettings.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import StepGenericIntro from "../../bestell_wizard_mobile/steps/StepGenericIntro.tsx";
import Step9BankingData from "../../bestell_wizard_mobile/steps/Step9BankingData.tsx";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";
import { getEmptyPersonalData } from "../../bestell_wizard/utils/getEmptyPersonalData.ts";
import BestellWizardMobileBase from "../../bestell_wizard_mobile/components/BestellWizardMobileBase.tsx";
import { shouldIncludeStepGrowingPeriodChoice } from "../../bestell_wizard_mobile/utils/shouldIncludeStepGrowingPeriodChoice.ts";
import { formatShoppingCart } from "../../bestell_wizard/utils/formatShoppingCart.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import Step3BGrowingPeriodChoice from "../../bestell_wizard_mobile/steps/Step3BGrowingPeriodChoice.tsx";
import { getProductTypeFromStep } from "../../bestell_wizard_mobile/utils/getProductTypeFromStep.ts";
import Step4BProductTypeOrder from "../../bestell_wizard_mobile/steps/Step4BProductTypeOrder.tsx";
import { updateProductsAndProductTypesOverCapacity } from "../../bestell_wizard/utils/updateProductsAndProductTypesOverCapacity.ts";
import { updateWaitingList } from "../../bestell_wizard_mobile/utils/updateWaitingList.ts";
import { isShoppingCartEmpty } from "../../bestell_wizard/utils/isShoppingCartEmpty.ts";
import { checkPickupLocationCapacities } from "../../bestell_wizard/utils/checkPickupLocationCapacities.ts";
import Step5BPickupLocationChoice from "../../bestell_wizard_mobile/steps/Step5BPickupLocationChoice.tsx";
import { fetchFirstDeliveryDates } from "../../bestell_wizard/utils/fetchFirstDeliveryDates.ts";
import { PickupLocationTab } from "../../bestell_wizard_mobile/types/PickupLocationTab.ts";
import { buildEmptyShoppingCart } from "../../bestell_wizard/utils/buildEmptyShoppingCart.ts";
import { getFirstPickupLocationWithCapacity } from "../../bestell_wizard_mobile/utils/getFirstPickupLocationWithCapacity.ts";

interface BestellWizardProductTypeProps {
  csrfToken: string;
  memberId: string;
  firstName: string;
  lastName: string;
  needsBankingData: boolean;
  productTypeId: string;
}

const BestellWizardProductType: React.FC<BestellWizardProductTypeProps> = ({
  csrfToken,
  memberId,
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

  const [settings, setSettings] =
    useState<BestellWizardSettings>(buildEmptySettings());
  const [settingsLoaded, setSettingsLoaded] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [steps, setSteps] = useState<Step[]>(["loading"]);
  const [currentStep, setCurrentStep] = useState<Step>("loading");
  const [orderLoading, setOrderLoading] = useState(false);
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
    pickupLocationsWithCapacityCheckLoading,
    setPickupLocationsWithCapacityCheckLoading,
  ] = useState<Set<PublicPickupLocation>>(new Set<PublicPickupLocation>());
  const [
    firstDeliveryDatesByPickupLocationAndProductType,
    setFirstDeliveryDatesByPickupLocationAndProductType,
  ] = useState<{ [key: string]: { [key: string]: Date } }>({});
  const [currentPickupLocationTab, setCurrentPickupLocationTab] =
    useState<PickupLocationTab>("map");
  const [mustAddPickupLocation, setMustAddPickupLocation] = useState(false);
  const [canChangePaymentRhythm, setCanChangePaymentRhythm] = useState(false);

  const [contractAccepted, setContractAccepted] = useState(false);
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
    ])
      .then(([baseData, canChangePaymentRhythmResponse]) => {
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

        setCanChangePaymentRhythm(canChangePaymentRhythmResponse.canChange);
        setPersonalData({
          ...personalData,
          paymentRhythm: canChangePaymentRhythmResponse.currentRhythm,
        });
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der BestellWizard",
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

    const newSteps = [];
    if (
      shouldIncludeStepGrowingPeriodChoice(
        [productType],
        settings.growingPeriodChoices,
      )
    ) {
      newSteps.push("3b_growing_period_choice");
    }

    newSteps.push(productTypeId + "_intro", productTypeId + "_order");

    if (mustAddPickupLocation) {
      newSteps.push("5a_pickup_location_intro", "5b_pickup_location_choice");
    }

    if (needsBankingData) {
      newSteps.push("9_banking_data");
    }

    setSteps(newSteps);
    setCurrentStep(newSteps[0]);
  }, [settingsLoaded, needsBankingData, productType, mustAddPickupLocation]);

  useEffect(() => {
    updateProductsAndProductTypesOverCapacity(
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
      settings.pickupLocations,
      shoppingCart,
      setPickupLocationsWithCapacityCheckLoading,
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
          productTypeId: productTypeId,
          pickupLocationId: getFirstPickupLocationWithCapacity(
            selectedPickupLocations,
            pickupLocationsWithCapacityFull,
          )!.id,
          growingPeriodId: selectedGrowingPeriod!.id!,
          iban: personalData.iban,
          accountOwner: personalData.accountOwner,
          paymentRhythm: personalData.paymentRhythm,
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
            (pickupLocations) => pickupLocations.id!,
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
          alert(response.error);
          setOrderLoading(false);
        }
      })
      .catch(async (error) => {
        await handleRequestError(
          error,
          "Fehler beim Erzeugen des Warteliste-Eintrags",
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
          />
        );
      case "5a_pickup_location_intro":
        return (
          <StepGenericIntro
            content={{
              text: settings.strings.step5aText,
            }}
            goToNextStep={goToNextStep}
          />
        );
      case "5b_pickup_location_choice":
        return (
          <Step5BPickupLocationChoice
            settings={settings}
            selectedPickupLocations={selectedPickupLocations}
            setSelectedPickupLocations={setSelectedPickupLocations}
            pickupLocationsWithCapacityCheckLoading={
              pickupLocationsWithCapacityCheckLoading
            }
            pickupLocationsWithCapacityFull={pickupLocationsWithCapacityFull}
            goToNextStep={goToNextStep}
            stepIsActive={step === "5b_pickup_location_choice"}
            firstDeliveryDatesByPickupLocationAndProductType={
              firstDeliveryDatesByPickupLocationAndProductType
            }
            active={currentStep === step}
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
            settings={settings}
            shoppingCart={shoppingCart}
            solidarityContribution={0}
            active={currentStep === step}
            productTypesInWaitingList={new Set()}
            isOrderStep={step === steps.at(-1)}
            orderLoading={orderLoading}
            nextButtonText={
              step === steps.at(-1) ? getConfirmButtonText() : undefined
            }
            canChangePaymentRhythm={canChangePaymentRhythm}
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
          return <div>Fehler: ungültiges Schritt {step}</div>;
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
                active={step === currentStep}
                checkingCapacities={checkingCapacities}
                productTypeIdsOverCapacity={productTypeIdsOverCapacity}
                productIdsOverCapacity={productIdsOverCapacity}
                waitingListLinkConfirmationModeEnabled={false}
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
    />
  );
};

export default BestellWizardProductType;
