import React, { ReactNode, useEffect, useRef, useState } from "react";
import { Spinner } from "react-bootstrap";

import {
  BestellWizardApi,
  BiddingRoundsApi,
  ResponseError,
} from "../api-client";
import { BestellWizardSettings } from "../bestell_wizard/types/BestellWizardSettings.ts";
import { PersonalData } from "../bestell_wizard/types/PersonalData.ts";
import { buildEmptySettings } from "../bestell_wizard/utils/buildEmptySettings.ts";
import { buildSettings } from "../bestell_wizard/utils/buildSettings.ts";
import { getEmptyPersonalData } from "../bestell_wizard/utils/getEmptyPersonalData.ts";
import { getTestPersonalData } from "../bestell_wizard/utils/getTestPersonalData.ts";
import StepGenericIntro from "../bestell_wizard_mobile/steps/StepGenericIntro.tsx";
import { Step } from "../bestell_wizard_mobile/types/Step.ts";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import { interpolate } from "../utils/interpolate.ts";
import BiddingRoundMobile from "./BiddingRoundMobile.tsx";
import BiddingRoundConfirmationStep from "./steps/BiddingRoundConfirmationStep.tsx";
import BiddingRoundIntroStep from "./steps/BiddingRoundIntroStep.tsx";
import BiddingRoundPickupLocationStep from "./steps/BiddingRoundPickupLocationStep.tsx";
import BiddingRoundProductTypeBidStep from "./steps/BiddingRoundProductTypeBidStep.tsx";
import BiddingRoundSummaryStep from "./steps/BiddingRoundSummaryStep.tsx";
import {
  BiddingRoundBidItem,
  BiddingRoundProductType,
  BiddingRoundPublicData,
  BiddingRoundPublicEvaluation,
  BiddingRoundTexts,
} from "./types/BiddingRoundTypes.ts";
import { applyDisplayName } from "./utils/applyDisplayName.ts";
import {
  buildStandardAmounts,
  getBidLevels,
  toDotDecimal,
} from "./utils/bidLevels.ts";
import { buildBiddingRoundSteps } from "./utils/buildBiddingRoundSteps.ts";
import { getBiddingRoundProductTypeFromStep } from "./utils/getBiddingRoundProductTypeFromStep.ts";

interface BiddingRoundProps {
  csrfToken: string;
  skipIntro: boolean;
}

/** Recursively replaces "Beitragsrunde" with the configured display name. */
function applyDisplayNameDeep<T>(value: T, displayName: string): T {
  if (typeof value === "string") {
    return applyDisplayName(value, displayName) as unknown as T;
  }
  if (Array.isArray(value)) {
    return value.map((entry) =>
      applyDisplayNameDeep(entry, displayName),
    ) as unknown as T;
  }
  if (value && typeof value === "object") {
    const result: Record<string, unknown> = {};
    for (const [key, entry] of Object.entries(value)) {
      result[key] = applyDisplayNameDeep(entry, displayName);
    }
    return result as T;
  }
  return value;
}

const EMPTY_TEXTS: BiddingRoundTexts = {
  introTitle: "",
  introText: "",
  endedText: "",
  loginTitle: "",
  loginText: "",
  statsTitle: "",
  statsText: "",
  statsExplanation: "",
  statsTrafficLightSliderHint: "",
  statsSimpleLevelsSliderHint: "",
  pickupLocationTitle: "",
  pickupLocationText: "",
  summaryTitle: "",
  submitLabel: "",
  bid: {
    productLabel: "",
    variantLabel: "",
    quantityLabel: "",
    amountLabel: "",
    referenceValueHint: "",
    simpleExplanation: "",
    trafficLightExplanation: "",
    simpleLevelsExplanation: "",
    level1Label: "",
    level2Label: "",
    level3Label: "",
    greenLabel: "",
    yellowLabel: "",
    redLabel: "",
    pickupLocationLabel: "",
    liveYearlyLabel: "",
    monthlyHint: "",
    monthlyUnit: "",
    confirmText: "",
    successText: "",
    errorText: "",
  },
};

const BiddingRound: React.FC<BiddingRoundProps> = ({
  csrfToken,
  skipIntro,
}) => {
  const biddingRoundsApi = useApi(BiddingRoundsApi, csrfToken);
  const bestellWizardApi = useApi(BestellWizardApi, csrfToken);

  const [data, setData] = useState<BiddingRoundPublicData | null>(null);
  const displayNameRef = useRef("Beitragsrunde");
  const skipIntroApplied = useRef(false);
  const [settings, setSettings] =
    useState<BestellWizardSettings>(buildEmptySettings());
  const [settingsLoaded, setSettingsLoaded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [personalData, setPersonalData] = useState<PersonalData>(
    getEmptyPersonalData(),
  );

  const [steps, setSteps] = useState<Step[]>(["loading"]);
  const [currentStep, setCurrentStep] = useState<Step>("loading");

  const [orderLoading, setOrderLoading] = useState(false);
  const [confirmationText, setConfirmationText] = useState("");
  const [confirmationShowsLogin, setConfirmationShowsLogin] = useState(false);

  const [evaluation, setEvaluation] =
    useState<BiddingRoundPublicEvaluation | null>(null);

  const [bidItems, setBidItems] = useState<BiddingRoundBidItem[]>([]);
  const [pickupLocationId, setPickupLocationId] = useState("");

  const bidItemsRef = useRef<BiddingRoundBidItem[]>([]);
  bidItemsRef.current = bidItems;
  const pickupLocationIdRef = useRef("");
  pickupLocationIdRef.current = pickupLocationId;

  useEffect(() => {
    Promise.all([
      biddingRoundsApi.biddingRoundsApiPublicDataRetrieve(),
      bestellWizardApi.bestellWizardApiBestellWizardBaseDataRetrieve(),
    ])
      .then(([publicData, baseData]) => {
        const newSettings = buildSettings(baseData);
        setSettings(newSettings);
        setSettingsLoaded(true);

        const typedData = publicData as unknown as BiddingRoundPublicData;
        const displayName = typedData.displayName ?? "Beitragsrunde";
        displayNameRef.current = displayName;
        setData({
          ...typedData,
          texts: applyDisplayNameDeep(typedData.texts, displayName),
          pickupLocations: typedData.pickupLocations ?? [],
        });

        if (typedData?.bid?.items && typedData.bid.items.length > 0) {
          setBidItems(typedData.bid.items);
          setPickupLocationId(typedData.bid.pickupLocationId ?? "");
        } else if (typedData.currentPickupLocationId) {
          setPickupLocationId(typedData.currentPickupLocationId);
        }
      })
      .catch((error) =>
        handleRequestError(
          error,
          applyDisplayName(
            "Die Beitragsrunden-Daten konnten nicht geladen werden.",
            displayNameRef.current,
          ),
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!settingsLoaded || !data) {
      return;
    }

    if (!data.enabled || !data.round) {
      setSteps(["bidding_round_intro"]);
      setCurrentStep("bidding_round_intro");
      return;
    }

    const newSteps = buildBiddingRoundSteps({
      isAuthenticated: data.isAuthenticated,
      activeProductTypeId: data.biddableProduct?.productTypeId,
      pickupLocationsEnabled: data.pickupLocations.length > 0,
    });
    setSteps(newSteps);
    setCurrentStep((current) => {
      if (skipIntro && !skipIntroApplied.current && newSteps.length > 1) {
        skipIntroApplied.current = true;
        return newSteps[1];
      }
      return newSteps.includes(current) ? current : newSteps[0];
    });
  }, [settingsLoaded, data, settings]);

  useEffect(() => {
    const biddingRoundProductType = data?.biddableProduct;
    if (!data?.round || !biddingRoundProductType) {
      return;
    }

    setBidItems((previous) => {
      const existing = previous.find(
        (item) => item.roundProductId === biddingRoundProductType.id,
      );
      return [
        existing ?? buildDefaultBidItem(biddingRoundProductType, data.round!),
      ];
    });
  }, [data]);

  useEffect(() => {
    if (!data?.round) {
      return;
    }

    biddingRoundsApi
      .biddingRoundsApiPublicResultsRetrieve({ roundId: data.round.id })
      .then((result) =>
        setEvaluation(result as unknown as BiddingRoundPublicEvaluation),
      )
      .catch(() => setEvaluation(null));
  }, [data]);

  function goToNextStep() {
    const currentIndex = steps.indexOf(currentStep);
    if (currentIndex + 1 >= steps.length) {
      return;
    }
    setCurrentStep(steps[currentIndex + 1]);
  }

  function checkCapacity(): Promise<{ sufficient: boolean; message: string }> {
    if (!data?.round) {
      return Promise.resolve({ sufficient: true, message: "" });
    }
    return biddingRoundsApi
      .biddingRoundsApiCapacityCheckCreate({
        roundId: data.round.id,
        biddingRoundCapacityCheckRequestRequest: {
          items: bidItemsRef.current.map((item) => ({
            productId: item.productId,
            quantity: item.quantity,
          })),
          pickupLocationId: pickupLocationIdRef.current || null,
        },
      })
      .then((response) => ({
        sufficient: response.sufficient,
        message: response.message ?? "",
      }));
  }

  function submitBid() {
    if (!data?.round) {
      return;
    }

    setOrderLoading(true);

    biddingRoundsApi
      .biddingRoundsApiBidCreate({
        roundId: data.round.id,
        bidSubmitRequest: {
          items: bidItems.map((item) => ({
            round_product_id: item.roundProductId,
            product_id: item.productId,
            quantity: item.quantity,
            amount_1: toDotDecimal(item.amount1),
            amount_2: toDotDecimal(item.amount2),
            amount_3: toDotDecimal(item.amount3),
          })),
          pickupLocationId: pickupLocationId || null,
        },
      })
      .then(() => {
        setConfirmationText(data.texts.bid.successText);
        setConfirmationShowsLogin(false);
        setCurrentStep("bidding_round_confirmation");
      })
      .catch(async (error) => {
        let message = "Dein Gebot konnte nicht gespeichert werden.";
        if (error instanceof ResponseError) {
          const body = await error.response.json().catch(() => null);
          if (body?.error) {
            message = body.error;
          }
        }
        await handleRequestError(error, message, setToastDatas);
      })
      .finally(() => setOrderLoading(false));
  }

  function setTestData() {
    setPersonalData(getTestPersonalData());

    if (!data?.round) {
      return;
    }

    const biddingRoundProductType = data.biddableProduct;
    if (biddingRoundProductType) {
      const item = buildDefaultBidItem(biddingRoundProductType, data.round);
      const standard = buildStandardAmounts(
        biddingRoundProductType.products[0]?.referenceValue ?? null,
        getBidLevels(data.round),
      );
      setBidItems([
        {
          ...item,
          amount1: standard[0] ?? "",
          ...(item.amount2 !== undefined ? { amount2: standard[1] ?? "" } : {}),
          ...(item.amount3 !== undefined ? { amount3: standard[2] ?? "" } : {}),
        },
      ]);
    }

    if (data.pickupLocations.length > 0) {
      setPickupLocationId(data.pickupLocations[0].id!);
    }
  }

  function updateBidItem(
    roundProductId: string,
    patch: Partial<BiddingRoundBidItem>,
  ) {
    setBidItems((previous) =>
      previous.map((item) =>
        item.roundProductId === roundProductId ? { ...item, ...patch } : item,
      ),
    );
  }

  function getProductTypeStepContent(step: Step): ReactNode {
    if (!data?.round) {
      return null;
    }

    const [productType, subStep] = getBiddingRoundProductTypeFromStep(
      step,
      settings,
    );
    if (!productType) {
      return (
        <div>
          {interpolate("Fehler: ungültiger Ernteanteil {step}", {
            step,
          })}
        </div>
      );
    }

    const biddingRoundProductType = data.biddableProduct;
    if (
      !biddingRoundProductType ||
      biddingRoundProductType.productTypeId !== productType.id
    ) {
      return (
        <div>
          {interpolate("Fehler: ungültiger Ernteanteil {step}", {
            step,
          })}
        </div>
      );
    }

    if (subStep === "intro") {
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
    }

    const item = bidItems.find(
      (candidate) => candidate.roundProductId === biddingRoundProductType.id,
    );
    if (!item) {
      return null;
    }

    return (
      <BiddingRoundProductTypeBidStep
        productType={productType}
        biddingRoundProductType={biddingRoundProductType}
        round={data.round}
        bidOptions={data.bidOptions}
        texts={data.texts}
        item={item}
        onChange={(patch) => updateBidItem(biddingRoundProductType.id, patch)}
        checkCapacity={checkCapacity}
        onCapacityCheckError={(error) =>
          handleRequestError(
            error,
            "Die Kapazität konnte nicht geprüft werden.",
            setToastDatas,
          )
        }
        goToNextStep={goToNextStep}
        stepActive={step === currentStep}
      />
    );
  }

  function getStepComponent(step: Step): ReactNode {
    switch (step) {
      case "loading":
        return (
          <div
            style={{ width: "100%", height: "100%" }}
            className={"d-flex justify-content-center align-items-center"}
          >
            <Spinner />
          </div>
        );
      case "bidding_round_intro":
        if (!data) {
          return null;
        }
        if (!data.enabled) {
          return (
            <p className={"text-center"}>
              {applyDisplayName(
                "Die Beitragsrunde ist derzeit nicht verfügbar.",
                data.displayName,
              )}
            </p>
          );
        }
        if (!data.round) {
          return (
            <div
              className={"text-center"}
              dangerouslySetInnerHTML={{ __html: data.texts.endedText }}
            />
          );
        }
        return (
          <BiddingRoundIntroStep
            texts={data.texts}
            round={data.round}
            evaluation={evaluation}
            isAuthenticated={data.isAuthenticated}
            goToNextStep={goToNextStep}
            stepActive={step === currentStep}
          />
        );
      case "bidding_round_pickup_location":
        if (!data?.round) {
          return null;
        }
        return (
          <BiddingRoundPickupLocationStep
            pickupLocations={data.pickupLocations}
            pickupLocationId={pickupLocationId}
            setPickupLocationId={setPickupLocationId}
            texts={data.texts}
            goToNextStep={goToNextStep}
            stepActive={step === currentStep}
          />
        );
      case "bidding_round_summary":
        if (!data?.round) {
          return null;
        }
        return (
          <BiddingRoundSummaryStep
            round={data.round}
            items={bidItems}
            biddableProduct={data.biddableProduct}
            pickupLocations={data.pickupLocations}
            pickupLocationId={pickupLocationId}
            texts={data.texts}
            submitBid={submitBid}
            orderLoading={orderLoading}
            stepActive={step === currentStep}
          />
        );
      case "bidding_round_confirmation":
        return (
          <BiddingRoundConfirmationStep
            contentHtml={confirmationText}
            showLoginButton={confirmationShowsLogin}
          />
        );
      default:
        return getProductTypeStepContent(step);
    }
  }

  const texts = data?.texts ?? EMPTY_TEXTS;

  if (loading) {
    return (
      <BiddingRoundMobile
        settings={settings}
        texts={texts}
        steps={["loading"]}
        currentStep={"loading"}
        setCurrentStep={setCurrentStep}
        personalData={personalData}
        getStepComponent={getStepComponent}
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
        showProgress={false}
        hideFooterButtonsOnLastStep={true}
        setTestData={setTestData}
      />
    );
  }

  return (
    <BiddingRoundMobile
      settings={settings}
      texts={texts}
      steps={steps}
      currentStep={currentStep}
      setCurrentStep={setCurrentStep}
      personalData={personalData}
      getStepComponent={getStepComponent}
      toastDatas={toastDatas}
      setToastDatas={setToastDatas}
      showProgress={!!data?.round}
      hideFooterButtonsOnLastStep={true}
      setTestData={setTestData}
    />
  );
};

export default BiddingRound;

function buildDefaultBidItem(
  biddingRoundProductType: BiddingRoundProductType,
  round: BiddingRoundPublicData["round"],
): BiddingRoundBidItem {
  const product = biddingRoundProductType.products[0];
  const bidLevels = getBidLevels(round ?? undefined);
  const item: BiddingRoundBidItem = {
    roundProductId: biddingRoundProductType.id,
    productId: product?.id ?? "",
    quantity: 1,
    amount1: "",
  };
  if (bidLevels >= 2) {
    item.amount2 = "";
  }
  if (bidLevels >= 3) {
    item.amount3 = "";
  }
  return item;
}
