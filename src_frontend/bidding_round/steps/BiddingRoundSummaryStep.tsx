import React from "react";
import NextStepButton from "../../bestell_wizard_mobile/components/NextStepButton.tsx";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import {
  BiddingRoundBidItem,
  BiddingRoundPickupLocation,
  BiddingRoundProductType,
  BiddingRoundRound,
  BiddingRoundTexts,
} from "../types/BiddingRoundTypes.ts";
import {
  getBidAmountKey,
  getBidLevelLabel,
  getBidLevels,
  parseEuroAmount,
} from "../utils/bidLevels.ts";
import {
  TRAFFIC_LIGHT_LEVELS,
  getTrafficLightLabel,
} from "../utils/trafficLightLevels.ts";

interface BiddingRoundSummaryStepProps {
  round: BiddingRoundRound;
  items: BiddingRoundBidItem[];
  biddableProduct: BiddingRoundProductType | null;
  pickupLocations: BiddingRoundPickupLocation[];
  pickupLocationId: string;
  texts: BiddingRoundTexts;
  submitBid: () => void;
  submitLabel?: string;
  orderLoading: boolean;
  stepActive: boolean;
}

function formatLevelAmount(value: string | null | undefined): string {
  const amount = parseEuroAmount(value);
  return amount === null ? "–" : formatCurrency(amount);
}

const BiddingRoundSummaryStep: React.FC<BiddingRoundSummaryStepProps> = ({
  round,
  items,
  biddableProduct,
  pickupLocations,
  pickupLocationId,
  texts,
  submitBid,
  submitLabel,
  orderLoading,
  stepActive,
}) => {
  const trafficLight = round.biddingProcedure === "traffic_light";
  const bidLevels = getBidLevels(round);

  const yearlyAmountOf = (
    item: BiddingRoundBidItem,
    amountValue: string | null | undefined,
  ): number | null => {
    const amount = parseEuroAmount(amountValue);
    return amount === null ? null : amount * item.quantity * 12;
  };

  const deliveryChargePerYear =
    parseEuroAmount(
      pickupLocations.find((location) => location.id === pickupLocationId)
        ?.yearlyDeliveryCharge,
    ) ?? 0;

  const totalYearlyOf = (
    item: BiddingRoundBidItem,
    amountValue: string | null | undefined,
  ): number | null => {
    const yearly = yearlyAmountOf(item, amountValue);
    return yearly === null ? null : yearly + deliveryChargePerYear;
  };

  const renderYearlyBreakdown = (
    item: BiddingRoundBidItem,
    amountValue: string | null | undefined,
  ) => {
    const yearly = yearlyAmountOf(item, amountValue);
    const total = totalYearlyOf(item, amountValue);
    if (yearly === null || total === null) {
      return null;
    }
    return (
      <>
        <div className={"text-end text-muted small"}>
          {texts.bid.liveYearlyLabel} {formatCurrency(yearly)}
        </div>
        {deliveryChargePerYear > 0 && (
          <div className={"text-end text-muted small"}>
            + {"Lieferzuschlag pro Jahr"}:{" "}
            {formatCurrency(deliveryChargePerYear)}
          </div>
        )}
        <div className={"text-end small fw-semibold"}>
          {"Gesamt pro Jahr"}: {formatCurrency(total)}
        </div>
      </>
    );
  };

  const primaryLocation = pickupLocations.find(
    (location) => location.id === pickupLocationId,
  );

  return (
    <>
      <div
        className={"d-flex flex-column gap-3"}
        style={{ width: "100%", maxWidth: "540px" }}
      >
        {items.map((item, index) => {
          const product = biddableProduct?.products.find(
            (candidate) => candidate.id === item.productId,
          );
          return (
            <div key={index} className={"border rounded p-3"}>
              <div className={"d-flex justify-content-between gap-3"}>
                <strong>{biddableProduct?.productTypeName}</strong>
                <span>{product?.name}</span>
              </div>
              {texts.bid.monthlyHint && (
                <div className={"text-muted small"}>
                  {texts.bid.monthlyHint}
                </div>
              )}
              {item.quantity > 1 && (
                <div className={"d-flex justify-content-between gap-3"}>
                  <span>{texts.bid.quantityLabel}</span>
                  <span>{item.quantity}</span>
                </div>
              )}
              {trafficLight ? (
                <>
                  {TRAFFIC_LIGHT_LEVELS.map((level) => {
                    return (
                      <div key={level.key}>
                        <div className={"d-flex justify-content-between gap-3"}>
                          <span className={level.textClass}>
                            <span
                              className={
                                "d-inline-block rounded-circle me-2 " +
                                level.dotClass
                              }
                              style={{ width: "0.75rem", height: "0.75rem" }}
                            />
                            {getTrafficLightLabel(level, texts.bid)}
                          </span>
                          <span>{formatLevelAmount(item[level.key])}</span>
                        </div>
                        {renderYearlyBreakdown(item, item[level.key])}
                      </div>
                    );
                  })}
                </>
              ) : (
                Array.from({ length: bidLevels }, (_, levelIndex) => {
                  const level = levelIndex + 1;
                  const key = getBidAmountKey(level);
                  const label = getBidLevelLabel(level, bidLevels, texts);
                  return (
                    <div key={level}>
                      <div className={"d-flex justify-content-between gap-3"}>
                        <span>{label}</span>
                        <span>{formatLevelAmount(item[key])}</span>
                      </div>
                      {renderYearlyBreakdown(item, item[key])}
                    </div>
                  );
                })
              )}
            </div>
          );
        })}

        {primaryLocation && (
          <div className={"border rounded p-3"}>
            <div className={"d-flex justify-content-between gap-3"}>
              <span>{texts.bid.pickupLocationLabel}</span>
              <span>{primaryLocation.name}</span>
            </div>
          </div>
        )}

        <p className={"text-center"}>{texts.bid.confirmText}</p>
      </div>

      <NextStepButton
        onClick={submitBid}
        text={submitLabel || texts.submitLabel || "Gebot abgeben"}
        isOrderStep={true}
        loading={orderLoading}
        stepActive={stepActive}
      />
    </>
  );
};

export default BiddingRoundSummaryStep;
