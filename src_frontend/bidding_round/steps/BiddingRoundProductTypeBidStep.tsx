import React, { useEffect, useRef, useState } from "react";
import { Carousel, Form } from "react-bootstrap";
import { PublicProductType } from "../../api-client";
import NextStepButton from "../../bestell_wizard_mobile/components/NextStepButton.tsx";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { getHtmlDescription } from "../../utils/getHtmlDescription.ts";
import { interpolate } from "../../utils/interpolate.ts";
import {
  BiddingRoundBidItem,
  BiddingRoundBidOptions,
  BiddingRoundProductType,
  BiddingRoundRound,
  BiddingRoundTexts,
} from "../types/BiddingRoundTypes.ts";
import {
  BiddingRoundAmountKey,
  buildStandardAmounts,
  formatEuroNumber,
  getBidAmountKey,
  getBidLevelLabel,
  getBidLevels,
  parseEuroAmount,
  sanitizeEuroAmountInput,
} from "../utils/bidLevels.ts";
import {
  TRAFFIC_LIGHT_LEVELS,
  TrafficLightLevel,
  getTrafficLightLabel,
} from "../utils/trafficLightLevels.ts";

interface BiddingRoundProductTypeBidStepProps {
  productType: PublicProductType;
  biddingRoundProductType: BiddingRoundProductType;
  round: BiddingRoundRound;
  bidOptions: BiddingRoundBidOptions;
  texts: BiddingRoundTexts;
  item: BiddingRoundBidItem;
  onChange: (patch: Partial<BiddingRoundBidItem>) => void;
  checkCapacity: () => Promise<{ sufficient: boolean; message: string }>;
  onCapacityCheckError: (error: unknown) => void;
  goToNextStep: () => void;
  stepActive: boolean;
}

const BiddingRoundProductTypeBidStep: React.FC<
  BiddingRoundProductTypeBidStepProps
> = ({
  productType,
  biddingRoundProductType,
  round,
  bidOptions,
  texts,
  item,
  onChange,
  checkCapacity,
  onCapacityCheckError,
  goToNextStep,
  stepActive,
}) => {
  const trafficLight = round.biddingProcedure === "traffic_light";
  const bidLevels = getBidLevels(round);
  const [errors, setErrors] = useState<Partial<Record<string, string>>>({});
  const [capacityMessage, setCapacityMessage] = useState("");

  const amountKeys: BiddingRoundAmountKey[] = trafficLight
    ? ["amount1", "amount2", "amount3"]
    : Array.from({ length: bidLevels }, (_, index) =>
        getBidAmountKey(index + 1),
      );

  const products = biddingRoundProductType.products.map(
    (biddingRoundProduct) => ({
      ...biddingRoundProduct,
      publicProduct: productType.products.find(
        (candidate) => candidate.id === biddingRoundProduct.id,
      ),
    }),
  );

  const selectedIndex = Math.max(
    0,
    products.findIndex((product) => product.id === item.productId),
  );
  const selectedProduct = products[selectedIndex];

  const itemRef = useRef(item);
  itemRef.current = item;
  // Ratio of a manually entered amount to the reference value, per field. Kept
  // so that custom amounts scale proportionally when the variant changes.
  const customRatio = useRef<Partial<Record<BiddingRoundAmountKey, number>>>(
    {},
  );
  // Value that was last written per field, used to tell an untouched standard
  // value (which follows the new variant) apart from a manual entry.
  const lastApplied = useRef<Partial<Record<BiddingRoundAmountKey, string>>>(
    {},
  );

  // Pre-fill the amount fields with the standard values of the selected variant
  // (reference value, +5 %, +10 %). Untouched fields follow the new standard on
  // a variant change; manually entered fields scale proportionally to it.
  useEffect(() => {
    if (!stepActive || !selectedProduct) {
      return;
    }
    const reference = parseEuroAmount(selectedProduct.referenceValue);
    if (reference === null || reference <= 0) {
      return;
    }
    const standard = buildStandardAmounts(
      selectedProduct.referenceValue,
      bidLevels,
    );
    const patch: Partial<BiddingRoundBidItem> = {};
    amountKeys.forEach((key, index) => {
      const current = itemRef.current[key] ?? "";
      const standardValue = standard[index] ?? "";
      let ratio = customRatio.current[key];
      const untouched =
        current === "" ||
        current === lastApplied.current[key] ||
        current === standardValue;
      if (ratio === undefined && !untouched) {
        const parsed = parseEuroAmount(current);
        if (parsed !== null) {
          ratio = parsed / reference;
          customRatio.current[key] = ratio;
        }
      }
      const next =
        ratio !== undefined
          ? formatEuroNumber(reference * ratio)
          : standardValue;
      lastApplied.current[key] = next;
      if (next !== current) {
        patch[key] = next;
      }
    });
    if (Object.keys(patch).length > 0) {
      onChange(patch);
    }
    // Only re-run when the selected variant or the step activation changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProduct?.id, stepActive]);

  // Check the available capacity as soon as the harvest share and the number of
  // shares are chosen, so that over-capacity bids are caught already here.
  // Amounts do not affect the capacity, so they do not trigger the check.
  useEffect(() => {
    if (!stepActive || !item.productId) {
      setCapacityMessage("");
      return;
    }
    let cancelled = false;
    const timeout = setTimeout(() => {
      checkCapacity()
        .then((result) => {
          if (!cancelled) {
            setCapacityMessage(result.sufficient ? "" : result.message);
          }
        })
        .catch((error) => {
          if (!cancelled) {
            // A failed check must not silently look like "enough capacity", so
            // report it instead of swallowing it.
            setCapacityMessage("");
            onCapacityCheckError(error);
          }
        });
    }, 400);
    return () => {
      cancelled = true;
      clearTimeout(timeout);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stepActive, item.productId, item.quantity]);

  if (products.length === 0) {
    return (
      <>
        <p className={"text-center"}>
          {"Für diesen Ernteanteil sind derzeit keine Varianten verfügbar."}
        </p>
        <NextStepButton onClick={goToNextStep} stepActive={stepActive} />
      </>
    );
  }

  function getMinimumAmount(): number | null {
    return selectedProduct?.minAmount
      ? parseEuroAmount(selectedProduct.minAmount)
      : null;
  }

  function computeErrors(): Partial<Record<string, string>> {
    const next: Partial<Record<string, string>> = {};
    const minimumAmount = getMinimumAmount();
    const provided: number[] = [];

    for (const key of amountKeys) {
      const value = parseEuroAmount(item[key]);
      if (value === null) {
        next[key] = "Bitte gib einen Betrag in € an.";
        continue;
      }
      if (minimumAmount !== null && value < minimumAmount) {
        next[key] = interpolate(
          "Der Betrag muss mindestens {amount} € betragen.",
          { amount: selectedProduct?.minAmount },
        );
        continue;
      }
      provided.push(value);
    }

    for (let index = 0; index + 1 < provided.length; index++) {
      if (provided[index] > provided[index + 1]) {
        next["amounts"] = "Die Beträge müssen aufsteigend sein.";
        break;
      }
    }

    return next;
  }

  function validateAndContinue() {
    const nextErrors = computeErrors();
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }
    // Run the capacity check again on the click so that a fast "next" cannot slip
    // past the debounced check above.
    checkCapacity()
      .then((result) => {
        if (result.sufficient) {
          setCapacityMessage("");
          goToNextStep();
        } else {
          setCapacityMessage(result.message);
        }
      })
      .catch((error) => {
        onCapacityCheckError(error);
        goToNextStep();
      });
  }

  function updateAmount(key: BiddingRoundAmountKey, raw: string) {
    const sanitized = sanitizeEuroAmountInput(raw);
    onChange({ [key]: sanitized } as Partial<BiddingRoundBidItem>);
    const reference = parseEuroAmount(selectedProduct?.referenceValue);
    const parsed = parseEuroAmount(sanitized);
    if (reference !== null && reference > 0 && parsed !== null) {
      customRatio.current[key] = parsed / reference;
    } else {
      delete customRatio.current[key];
    }
    setErrors({});
  }

  function selectProduct(index: number) {
    const product = products[index];
    if (product) {
      onChange({ productId: product.id });
    }
  }

  function renderAmountField(
    key: BiddingRoundAmountKey,
    label: string,
    trafficLightLevel?: TrafficLightLevel,
  ) {
    const error = errors[key];
    const amount = parseEuroAmount(item[key]);
    const yearlyAmount =
      amount === null ? null : amount * (item.quantity || 1) * 12;
    const inputClasses = trafficLightLevel
      ? `${trafficLightLevel.borderClass} border-2 ${trafficLightLevel.bgClass}`
      : "";
    return (
      <Form.Group className={"mt-3"} key={key}>
        <Form.Label className={trafficLightLevel?.textClass}>
          {trafficLightLevel && (
            <span
              className={
                "d-inline-block rounded-circle me-2 " +
                trafficLightLevel.dotClass
              }
              style={{ width: "0.85rem", height: "0.85rem" }}
            />
          )}
          {label}
        </Form.Label>
        <Form.Control
          type={"text"}
          inputMode={"decimal"}
          required={true}
          placeholder={`0.00 ${texts.bid.monthlyUnit}`}
          className={inputClasses + (error ? " is-invalid" : "")}
          value={item[key] ?? ""}
          onChange={(event) => updateAmount(key, event.target.value)}
        />
        {error && (
          <Form.Control.Feedback type={"invalid"}>
            {error}
          </Form.Control.Feedback>
        )}
        {yearlyAmount !== null && (
          <div className={"text-center small mt-1"}>
            <strong>
              {texts.bid.liveYearlyLabel} {formatCurrency(yearlyAmount)}
            </strong>
          </div>
        )}
      </Form.Group>
    );
  }

  function renderVariant(product: (typeof products)[number]) {
    return (
      <div
        className={
          "d-flex flex-column align-items-center gap-2 text-center py-2"
        }
      >
        {stepActive && product.publicProduct?.urlOfImageInBestellwizard && (
          <img
            src={product.publicProduct.urlOfImageInBestellwizard}
            alt={product.name}
            style={{
              maxHeight: "30dvh",
              maxWidth: "60dvw",
              objectFit: "contain",
            }}
          />
        )}
        <strong>{product.name}</strong>
        {product.publicProduct?.descriptionInBestellwizard && (
          <span
            className={"text-muted"}
            dangerouslySetInnerHTML={getHtmlDescription(
              product.publicProduct.descriptionInBestellwizard,
            )}
          />
        )}
      </div>
    );
  }

  const hasErrors = Object.keys(errors).length > 0 || capacityMessage !== "";

  return (
    <>
      <div
        className={"d-flex flex-column gap-3"}
        style={{ width: "100%", maxWidth: "540px" }}
      >
        <p
          className={"text-center"}
          dangerouslySetInnerHTML={{
            __html: trafficLight
              ? texts.bid.trafficLightExplanation
              : bidLevels > 1
                ? texts.bid.simpleLevelsExplanation
                : texts.bid.simpleExplanation,
          }}
        />

        <Carousel
          activeIndex={selectedIndex}
          onSelect={(index) => selectProduct(index)}
          indicators={false}
          controls={products.length > 2}
          interval={null}
          wrap={false}
        >
          {products.map((product) => (
            <Carousel.Item key={product.id}>
              {renderVariant(product)}
            </Carousel.Item>
          ))}
        </Carousel>

        {products.length > 1 && (
          <div className={"d-flex flex-wrap gap-2 justify-content-center"}>
            {products.map((product, index) => (
              <button
                key={product.id}
                type={"button"}
                className={
                  "btn btn-sm " +
                  (index === selectedIndex ? "btn-dark" : "btn-outline-dark")
                }
                onClick={() => selectProduct(index)}
              >
                {product.name}
              </button>
            ))}
          </div>
        )}

        <Form noValidate={true}>
          {selectedProduct && (
            <Form.Text className={"d-block text-center"}>
              {texts.bid.referenceValueHint.replace(
                "{reference_value}",
                selectedProduct.referenceValue ?? "–",
              )}
            </Form.Text>
          )}

          {texts.bid.monthlyHint && (
            <Form.Text className={"d-block text-center fw-semibold"}>
              {texts.bid.monthlyHint}
            </Form.Text>
          )}

          {bidOptions.quantityEnabled && (
            <Form.Group className={"mt-3"}>
              <Form.Label>{texts.bid.quantityLabel}</Form.Label>
              <Form.Control
                type={"number"}
                min={1}
                value={item.quantity}
                onChange={(event) =>
                  onChange({
                    quantity: Math.max(1, parseInt(event.target.value) || 1),
                  })
                }
              />
            </Form.Group>
          )}

          {trafficLight
            ? TRAFFIC_LIGHT_LEVELS.map((level) =>
                renderAmountField(
                  level.key,
                  getTrafficLightLabel(level, texts.bid),
                  level,
                ),
              )
            : amountKeys.map((key) => {
                const level = Number.parseInt(key.replace("amount", ""));
                return renderAmountField(
                  key,
                  getBidLevelLabel(level, bidLevels, texts),
                );
              })}

          {errors["amounts"] && (
            <div className={"text-danger small mt-2"}>{errors["amounts"]}</div>
          )}

          {capacityMessage && (
            <div className={"text-danger small mt-2"}>{capacityMessage}</div>
          )}
        </Form>
      </div>

      <NextStepButton
        onClick={validateAndContinue}
        showError={hasErrors}
        text={hasErrors ? "Bitte prüfe deine Beträge" : undefined}
        stepActive={stepActive}
      />
    </>
  );
};

export default BiddingRoundProductTypeBidStep;
