import React from "react";
import { Card } from "react-bootstrap";

import { RoundTexts } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import AmountRow from "../../components/mobile_wizard/AmountRow.tsx";
import { getMonthlyTotal, getYearlyAmount } from "../utils/amounts.ts";

interface BiddingRoundSummaryStepProps {
  variantName: string;
  quantity: number;
  amount: number;
  texts: RoundTexts;
  submitting: boolean;
  onSubmit: () => void;
}

const BiddingRoundSummaryStep: React.FC<BiddingRoundSummaryStepProps> = ({
  variantName,
  quantity,
  amount,
  texts,
  submitting,
  onSubmit,
}) => {
  const monthlyTotal = getMonthlyTotal(amount, quantity);
  const yearlyTotal = getYearlyAmount(amount, quantity);

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
          <AmountRow
            label={"Betrag je Anteil"}
            amount={amount}
            unit={texts.bid.monthlyUnit}
            strong
          />
          {quantity > 1 && (
            <AmountRow
              label={"Beitrag gesamt"}
              amount={monthlyTotal}
              unit={texts.bid.monthlyUnit}
              strong
            />
          )}
          <AmountRow
            label={"Beitrag pro Jahr"}
            amount={yearlyTotal}
            unit={texts.bid.yearlyUnit}
            strong
          />
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
