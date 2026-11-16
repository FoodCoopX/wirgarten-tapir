import React from "react";
import { Card } from "react-bootstrap";

import { CurrentPickupLocation, RoundTexts } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import AmountRow from "../../components/mobile_wizard/AmountRow.tsx";
import PickupLocationRow from "../components/PickupLocationRow.tsx";
import {
  getMonthlyTotal,
  getYearlyAmount,
  parseEuroAmount,
} from "../utils/amounts.ts";
import { getLevelLabels } from "../utils/levelLabels.ts";

interface BiddingRoundSummaryStepProps {
  variantName: string;
  quantity: number;
  amounts: string[];
  requiredAmountLevels: number;
  isBidRange: boolean;
  texts: RoundTexts;
  currentPickupLocation: CurrentPickupLocation | null;
  submitting: boolean;
  onSubmit: () => void;
}

const BiddingRoundSummaryStep: React.FC<BiddingRoundSummaryStepProps> = ({
  variantName,
  quantity,
  amounts,
  requiredAmountLevels,
  isBidRange,
  texts,
  currentPickupLocation,
  submitting,
  onSubmit,
}) => {
  const levelLabels = getLevelLabels(isBidRange, requiredAmountLevels, texts);

  const levelRows = Array.from({ length: requiredAmountLevels }, (_, index) => {
    const amount = parseEuroAmount(amounts[index]);
    return {
      label: levelLabels[index] ?? "",
      amount,
      monthlyTotal: amount === null ? null : getMonthlyTotal(amount, quantity),
      yearlyTotal: amount === null ? null : getYearlyAmount(amount, quantity),
    };
  });

  return (
    <>
      <Card>
        <Card.Header>
          <strong>{texts.summaryTitle}</strong>
        </Card.Header>
        <Card.Body className={"d-flex flex-column gap-2"}>
          <div className={"d-flex justify-content-between"}>
            <span className={"text-muted"}>Produkt</span>
            <strong>{variantName}</strong>
          </div>
          <div className={"d-flex justify-content-between"}>
            <span className={"text-muted"}>Anteile</span>
            <strong>{quantity}</strong>
          </div>
          <PickupLocationRow
            currentPickupLocation={currentPickupLocation}
            texts={texts}
            variant={"inline"}
          />
          {levelRows.map((row) => (
            <div key={row.label} className={"border-top pt-2"}>
              <AmountRow
                label={row.label}
                amount={row.amount}
                unit={texts.bid.monthlyUnit}
                hint={quantity > 1 ? "pro Anteil" : undefined}
                strong
              />
              {row.monthlyTotal !== null && quantity > 1 && (
                <AmountRow
                  label={"Beitrag gesamt"}
                  amount={row.monthlyTotal}
                  unit={texts.bid.monthlyUnit}
                  strong
                />
              )}
              <AmountRow
                label={"Beitrag pro Jahr"}
                amount={row.yearlyTotal}
                unit={texts.bid.yearlyUnit}
                strong
              />
            </div>
          ))}
        </Card.Body>
      </Card>

      {texts.bid.confirmText && (
        <p
          className={"text-muted text-center"}
          dangerouslySetInnerHTML={{ __html: texts.bid.confirmText }}
        />
      )}

      <div className={"d-flex justify-content-center"}>
        <TapirButton
          variant={"dark"}
          text={texts.submitLabel}
          onClick={onSubmit}
          loading={submitting}
          disabled={submitting}
        />
      </div>
    </>
  );
};

export default BiddingRoundSummaryStep;
