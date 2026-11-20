import React from "react";
import { Accordion, AccordionBody } from "react-bootstrap";

import {
  CurrentPickupLocation,
  PublicAssociationMembership,
  RoundTexts,
} from "../../api-client";
import { scrollIntoView } from "../../bestell_wizard_mobile/utils/scrollIntoView.ts";
import TapirButton from "../../components/TapirButton.tsx";
import AmountRow from "../../components/mobile_wizard/AmountRow.tsx";
import { BUTTON_VARIANT } from "../../components/mobile_wizard/utils/BUTTON_VARIANT.ts";
import { formatAmountNumber } from "../../utils/formatAmountNumber.ts";
import PickupLocationRow from "../components/PickupLocationRow.tsx";
import {
  BidLevelCost,
  getBidLevelCost,
  getBidTotalRange,
  parseEuroAmount,
} from "../utils/amounts.ts";
import {
  getAmountLevelLabels,
  getBidRangeLabels,
} from "../utils/getLevelLabels.ts";

interface BiddingRoundSummaryStepProps {
  productName: string;
  variantName: string;
  quantity: number;
  amounts: string[];
  requiredAmountLevels: number;
  isBidRange: boolean;
  texts: RoundTexts;
  currentPickupLocation: CurrentPickupLocation | null;
  associationMembership: PublicAssociationMembership | null;
  sharesEnabled: boolean;
  submitting: boolean;
  onSubmit: () => void;
  onAdjustBid: () => void;
}

type LevelRow = BidLevelCost & { label: string };

function buildHeaderText(
  productName: string,
  variantName: string,
  texts: RoundTexts,
  totalRange: ReturnType<typeof getBidTotalRange>,
): string {
  const title = `${productName} ${variantName}`;
  if (totalRange === null) {
    return title;
  }
  if (totalRange.min === totalRange.max) {
    return `${title} ${formatAmountNumber(totalRange.min)} ${texts.bid.monthlyUnit}`;
  }
  return `${title} ${formatAmountNumber(totalRange.min)}-${formatAmountNumber(totalRange.max)} ${texts.bid.monthlyUnit}`;
}

const BiddingRoundSummaryStep: React.FC<BiddingRoundSummaryStepProps> = ({
  productName,
  variantName,
  quantity,
  amounts,
  requiredAmountLevels,
  isBidRange,
  texts,
  currentPickupLocation,
  associationMembership,
  sharesEnabled,
  submitting,
  onSubmit,
  onAdjustBid,
}) => {
  const levelLabels = isBidRange
    ? getBidRangeLabels(texts)
    : getAmountLevelLabels(texts, requiredAmountLevels);
  const membershipPrice = associationMembership
    ? Number(associationMembership.price)
    : null;
  const deliveryCharge = currentPickupLocation
    ? Number(currentPickupLocation.yearlyDeliveryCharge)
    : null;

  const levelRows: LevelRow[] = levelLabels.map((label, index) => ({
    label,
    ...getBidLevelCost(
      parseEuroAmount(amounts[index]),
      quantity,
      membershipPrice,
      deliveryCharge,
    ),
  }));

  const totalRange = getBidTotalRange(
    amounts,
    requiredAmountLevels,
    quantity,
    membershipPrice,
    deliveryCharge,
  );

  const headerText = buildHeaderText(
    productName,
    variantName,
    texts,
    totalRange,
  );

  const [selectedRow, ...otherRows] = levelRows;

  function renderLevelRow(row: LevelRow, key: string) {
    return (
      <div key={key} className={"mb-2"}>
        <AmountRow
          label={row.label}
          amount={row.bidMonthly}
          unit={texts.bid.monthlyUnit}
          strong
          labelStrong
        />
        {row.membershipMonthly !== null && (
          <AmountRow
            label={"Vereinsmitgliedschaft"}
            amount={row.membershipMonthly}
            unit={texts.bid.monthlyUnit}
          />
        )}
        {row.deliveryMonthly !== null && (
          <AmountRow
            label={"Lieferkosten"}
            amount={row.deliveryMonthly}
            unit={texts.bid.monthlyUnit}
          />
        )}
        <AmountRow
          label={"Gesamt"}
          amount={row.totalMonthly}
          unit={texts.bid.monthlyUnit}
          strong
        />
        <AmountRow
          label={"Gebot pro Jahr"}
          amount={row.bidYearly}
          unit={texts.bid.yearlyUnit}
        />
        {row.deliveryYearly !== null && (
          <AmountRow
            label={"Lieferkosten"}
            amount={row.deliveryYearly}
            unit={texts.bid.yearlyUnit}
          />
        )}
        <AmountRow
          label={"Gesamt pro Jahr"}
          amount={row.totalYearly}
          unit={texts.bid.yearlyUnit}
          strong
        />
      </div>
    );
  }

  return (
    <>
      <Accordion style={{ width: "100%" }}>
        <Accordion.Item eventKey={"product"} onClick={scrollIntoView}>
          <Accordion.Header>{headerText}</Accordion.Header>
          <AccordionBody>
            {sharesEnabled && (
              <div className={"d-flex justify-content-between"}>
                <span className={"text-muted"}>Anteile</span>
                <strong>{quantity}</strong>
              </div>
            )}
            <PickupLocationRow
              currentPickupLocation={currentPickupLocation}
              texts={texts}
              variant={"inline"}
              showDeliveryCharge={false}
            />
            <hr />
            {selectedRow && renderLevelRow(selectedRow, "selected")}
            {otherRows.length > 0 && (
              <>
                <hr />
                {otherRows.map((row, index) => (
                  <React.Fragment key={row.label}>
                    {renderLevelRow(row, row.label)}
                    {index < otherRows.length - 1 && <hr />}
                  </React.Fragment>
                ))}
              </>
            )}
            <hr />
            <TapirButton
              variant={BUTTON_VARIANT}
              icon={"edit"}
              text={"Gebot anpassen"}
              onClick={onAdjustBid}
            />
          </AccordionBody>
        </Accordion.Item>
      </Accordion>

      {texts.bid.confirmText && (
        <p
          className={"text-muted"}
          dangerouslySetInnerHTML={{ __html: texts.bid.confirmText }}
        />
      )}

      <div className={"d-flex justify-content-center"}>
        <TapirButton
          variant={"dark"}
          text={texts.finalSubmitLabel}
          onClick={onSubmit}
          loading={submitting}
        />
      </div>
    </>
  );
};

export default BiddingRoundSummaryStep;
