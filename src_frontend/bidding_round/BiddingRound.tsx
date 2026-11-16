import React, { useEffect, useState } from "react";
import { Spinner } from "react-bootstrap";

import {
  BestellWizardApi,
  BiddingRoundsApi,
  PublicDataResponse,
  PublicEvaluationResponse,
  RoundTexts,
} from "../api-client";
import { BestellWizardSettings } from "../bestell_wizard/types/BestellWizardSettings.ts";
import { buildEmptySettings } from "../bestell_wizard/utils/buildEmptySettings.ts";
import { buildSettings } from "../bestell_wizard/utils/buildSettings.ts";
import StepGenericIntro from "../bestell_wizard_mobile/steps/StepGenericIntro.tsx";
import MobileWizardBase from "../components/mobile_wizard/MobileWizardBase.tsx";
import { MobileWizardStep } from "../components/mobile_wizard/types/MobileWizard.ts";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { addToast } from "../utils/addToast.ts";
import { formatCurrency } from "../utils/formatCurrency.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import BiddingRoundBidStep from "./steps/BiddingRoundBidStep.tsx";
import BiddingRoundConfirmationStep from "./steps/BiddingRoundConfirmationStep.tsx";
import BiddingRoundIntroStep from "./steps/BiddingRoundIntroStep.tsx";
import BiddingRoundSummaryStep from "./steps/BiddingRoundSummaryStep.tsx";
import { parseEuroAmount, toDotDecimal } from "./utils/amounts.ts";
import {
  buildBiddingRoundSteps,
  getBiddingRoundPhase,
  getBiddingRoundPhaseLabel,
  getBiddingRoundStepBackground,
  getBiddingRoundStepName,
  getBiddingRoundStepTitle,
  getProductTypeFromStep,
} from "./utils/biddingRoundSteps.ts";

interface BiddingRoundProps {
  csrfToken: string;
}

const BID_RANGE_PROCEDURE = "bid_range";

const EMPTY_TEXTS: RoundTexts = {
  introTitle: "",
  introText: "",
  endedText: "",
  loginTitle: "",
  loginText: "",
  summaryTitle: "",
  pickupLocationTitle: "",
  submitLabel: "",
  bid: {
    amountLabel: "",
    referenceValueHint: "",
    simpleExplanation: "",
    bidRangeExplanation: "",
    greenLabel: "",
    yellowLabel: "",
    redLabel: "",
    liveYearlyLabel: "",
    monthlyHint: "",
    monthlyUnit: "",
    yearlyUnit: "",
    confirmText: "",
    successText: "",
    errorText: "",
  },
};

const BiddingRound: React.FC<BiddingRoundProps> = ({ csrfToken }) => {
  const api = useApi(BiddingRoundsApi, csrfToken);
  const bestellWizardApi = useApi(BestellWizardApi, csrfToken);

  const [data, setData] = useState<PublicDataResponse | null>(null);
  const [liveEvaluation, setLiveEvaluation] =
    useState<PublicEvaluationResponse | null>(null);
  const [settings, setSettings] =
    useState<BestellWizardSettings>(buildEmptySettings());
  const [loading, setLoading] = useState(true);
  const [steps, setSteps] = useState<MobileWizardStep[]>(["loading"]);
  const [currentStep, setCurrentStep] = useState<MobileWizardStep>("loading");
  const [selectedVariantId, setSelectedVariantId] = useState<string | null>(
    null,
  );
  const [quantity, setQuantity] = useState(1);
  const [amounts, setAmounts] = useState<string[]>(["", "", ""]);
  const [submitting, setSubmitting] = useState(false);
  const [confirmationHtml, setConfirmationHtml] = useState("");
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  const texts = data?.texts ?? EMPTY_TEXTS;
  const isAuthenticated = Boolean(data?.isAuthenticated);
  const hasActiveRound = Boolean(data?.round) && data?.roundStatus === "active";
  const biddingProcedure = data?.round?.biddingProcedure ?? "simple";
  const isBidRange = biddingProcedure === BID_RANGE_PROCEDURE;
  const configuredLevels = Math.min(
    Math.max(data?.round?.bidLevels ?? 1, 1),
    3,
  );
  const requiredAmountLevels = isBidRange ? 2 : configuredLevels;

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    let publicData: PublicDataResponse | null = null;
    try {
      publicData = await api.biddingRoundsApiPublicDataRetrieve();
    } catch (error) {
      await handleRequestError(
        error,
        "Die Beitragsrunde konnte nicht geladen werden.",
        setToastDatas,
      );
    }

    if (publicData?.round && publicData.roundStatus === "active") {
      try {
        setLiveEvaluation(
          await api.biddingRoundsApiPublicResultsRetrieve({
            roundId: publicData.round.id,
          }),
        );
      } catch {
        setLiveEvaluation(null);
      }
    }

    let wizardSettings = buildEmptySettings();
    try {
      wizardSettings = buildSettings(
        await bestellWizardApi.bestellWizardApiBestellWizardBaseDataRetrieve(),
      );
    } catch {
      // The bidding round stays usable without logo, backgrounds and product texts.
    }

    setSettings(wizardSettings);
    setData(publicData);
    applyDefaultBid(publicData);
    setLoading(false);
  }

  function applyDefaultBid(publicData: PublicDataResponse | null) {
    const variants = publicData?.biddableProduct?.products ?? [];
    const existingItem = publicData?.bid?.items?.[0];
    const variant = existingItem
      ? variants.find((candidate) => candidate.id === existingItem.productId)
      : (variants.find((candidate) => candidate.currentQuantity !== null) ??
        variants[0]);

    setSelectedVariantId(variant?.id ?? null);
    setQuantity(existingItem?.quantity ?? variant?.currentQuantity ?? 1);
    setAmounts([
      existingItem?.amount1 ?? "",
      existingItem?.amount2 ?? "",
      isBidRange ? "" : (existingItem?.amount3 ?? ""),
    ]);
  }

  useEffect(() => {
    if (loading) {
      return;
    }

    const productTypeId = data?.biddableProduct?.productTypeId;
    const productType = productTypeId
      ? settings.productTypes.find(
          (candidate) => candidate.id === productTypeId,
        )
      : undefined;
    const hasProductIntro = Boolean(
      productType &&
      (productType.descriptionBestellwizardLong ||
        productType.accordions?.length),
    );

    const newSteps = buildBiddingRoundSteps({
      hasActiveRound,
      isAuthenticated,
      productTypeId,
      hasProductIntro,
    });
    setSteps(newSteps);
    setCurrentStep((current) =>
      newSteps.includes(current) ? current : newSteps[0],
    );
  }, [loading, data, settings, hasActiveRound, isAuthenticated]);

  function goToNextStep() {
    const currentIndex = steps.indexOf(currentStep);
    if (currentIndex + 1 >= steps.length) {
      return;
    }
    setCurrentStep(steps[currentIndex + 1]);
  }

  function getSelectedVariant() {
    return data?.biddableProduct?.products.find(
      (variant) => variant.id === selectedVariantId,
    );
  }

  function updateAmount(levelIndex: number, value: string) {
    setAmounts((current) => {
      const next = [...current];
      next[levelIndex] = value;
      return next;
    });
  }

  function getProvidedAmounts(levels: number): number[] {
    return amounts
      .slice(0, levels)
      .map((value) => parseEuroAmount(value))
      .filter((value): value is number => value !== null);
  }

  function goToSummary() {
    const variant = getSelectedVariant();
    if (!variant) {
      addToast(
        {
          title: "Bitte prüfe dein Gebot.",
          message: "Wähle eine Variante.",
          variant: "danger",
          id: crypto.randomUUID(),
        },
        setToastDatas,
      );
      return;
    }

    if (isBidRange) {
      if (
        parseEuroAmount(amounts[0]) === null ||
        parseEuroAmount(amounts[1]) === null
      ) {
        addToast(
          {
            title: "Bitte prüfe dein Gebot.",
            message: "Bitte gib den Grün- und den Rot-Betrag an.",
            variant: "danger",
            id: crypto.randomUUID(),
          },
          setToastDatas,
        );
        return;
      }
    } else if (
      Array.from(
        { length: requiredAmountLevels },
        (_, index) => amounts[index],
      ).some((value) => parseEuroAmount(value) === null)
    ) {
      addToast(
        {
          title: "Bitte prüfe dein Gebot.",
          message:
            requiredAmountLevels === 1
              ? "Bitte gib einen Betrag an."
              : "Bitte gib alle Gebote an.",
          variant: "danger",
          id: crypto.randomUUID(),
        },
        setToastDatas,
      );
      return;
    }

    const providedAmounts = getProvidedAmounts(requiredAmountLevels);
    const minAmount = Number(variant.minAmount ?? 0);
    if (providedAmounts.some((amount) => amount < minAmount)) {
      addToast(
        {
          title: "Bitte prüfe dein Gebot.",
          message: `Der Mindestbetrag liegt bei ${formatCurrency(minAmount)}.`,
          variant: "danger",
          id: crypto.randomUUID(),
        },
        setToastDatas,
      );
      return;
    }

    const ascending = providedAmounts.every(
      (amount, index) => index === 0 || providedAmounts[index - 1] <= amount,
    );
    if (!ascending) {
      addToast(
        {
          title: "Bitte prüfe dein Gebot.",
          message: "Die Gebote müssen aufsteigend sein.",
          variant: "danger",
          id: crypto.randomUUID(),
        },
        setToastDatas,
      );
      return;
    }

    setCurrentStep("bidding_round_summary");
  }

  async function submitBid() {
    const variant = getSelectedVariant();
    if (!data?.biddableProduct || !data.round || !variant) {
      return;
    }
    setSubmitting(true);
    try {
      await api.biddingRoundsApiBidCreate({
        roundId: data.round.id,
        bidSubmitRequest: {
          items: [
            {
              roundProductTypeId: data.biddableProduct.id,
              productId: variant.id,
              quantity: quantity,
              amount1: toDotDecimal(amounts[0]),
              amount2: toDotDecimal(amounts[1]),
              amount3: isBidRange ? null : toDotDecimal(amounts[2]),
            },
          ],
        },
      });
      setConfirmationHtml(texts.bid.successText);
      setCurrentStep("bidding_round_confirmation");
    } catch (error) {
      await handleRequestError(
        error,
        texts.bid.errorText || "Das Gebot konnte nicht gespeichert werden.",
        setToastDatas,
      );
    } finally {
      setSubmitting(false);
    }
  }

  function setTestData() {
    const variant =
      getSelectedVariant() ?? data?.biddableProduct?.products[0] ?? undefined;
    if (!variant) {
      return;
    }
    setSelectedVariantId(variant.id);
    setQuantity(variant.currentQuantity ?? 1);
    const reference = Number(variant.referenceValue ?? 0);
    if (reference > 0) {
      const next = ["", "", ""];
      for (let index = 0; index < requiredAmountLevels; index++) {
        next[index] = String(
          Number((reference * (1 + index * 0.1)).toFixed(2)),
        );
      }
      setAmounts(next);
    }
  }

  function getStepComponent(step: MobileWizardStep) {
    if (step === "loading") {
      return (
        <div
          style={{ width: "100%", height: "100%" }}
          className={"d-flex justify-content-center align-items-center"}
        >
          <Spinner />
        </div>
      );
    }

    if (!data) {
      return (
        <p className={"text-center"}>
          Die Beitragsrunde ist derzeit nicht verfügbar.
        </p>
      );
    }

    if (step === "bidding_round_intro") {
      return (
        <BiddingRoundIntroStep
          texts={texts}
          isAuthenticated={isAuthenticated}
          hasActiveRound={hasActiveRound}
          liveEvaluation={liveEvaluation}
          goToNextStep={goToNextStep}
          stepActive={step === currentStep}
        />
      );
    }

    if (step === "bidding_round_summary") {
      const variant = getSelectedVariant();
      if (!variant) {
        return null;
      }
      return (
        <BiddingRoundSummaryStep
          variantName={variant.name}
          quantity={quantity}
          amounts={amounts}
          requiredAmountLevels={requiredAmountLevels}
          isBidRange={isBidRange}
          texts={texts}
          currentPickupLocation={data.currentPickupLocation ?? null}
          submitting={submitting}
          onSubmit={submitBid}
        />
      );
    }

    if (step === "bidding_round_confirmation") {
      return (
        <BiddingRoundConfirmationStep
          contentHtml={confirmationHtml}
          onEdit={() => setCurrentStep(steps[Math.max(steps.length - 2, 0)])}
        />
      );
    }

    const productType = getProductTypeFromStep(step, settings);
    if (!productType || !data.biddableProduct) {
      return null;
    }

    if (step.endsWith("_intro")) {
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

    return (
      <BiddingRoundBidStep
        biddableProduct={data.biddableProduct}
        texts={texts}
        isBidRange={isBidRange}
        requiredAmountLevels={requiredAmountLevels}
        selectedVariantId={selectedVariantId}
        onSelectVariant={setSelectedVariantId}
        quantity={quantity}
        onQuantityChange={setQuantity}
        amounts={amounts}
        onAmountChange={updateAmount}
        currentPickupLocation={data.currentPickupLocation ?? null}
        goToNextStep={goToSummary}
        stepActive={step === currentStep}
      />
    );
  }

  return (
    <MobileWizardBase
      steps={steps}
      currentStep={currentStep}
      setCurrentStep={setCurrentStep}
      getStepComponent={getStepComponent}
      getStepTitle={(step) => getBiddingRoundStepTitle(step, settings, texts)}
      getStepBackground={(step) =>
        getBiddingRoundStepBackground(step, settings)
      }
      getPhase={(step) => getBiddingRoundPhase(step)}
      getPhaseLabel={(phase) => getBiddingRoundPhaseLabel(phase)}
      getStepName={(step) => getBiddingRoundStepName(step, settings)}
      logoUrl={settings.logoUrl}
      firstName={""}
      showProgress={hasActiveRound && isAuthenticated && steps.length > 1}
      hideFooterButtonsOnLastStep={true}
      showTestMenu={settings.debug}
      onTestData={setTestData}
      toastDatas={toastDatas}
      setToastDatas={setToastDatas}
    />
  );
};

export default BiddingRound;
