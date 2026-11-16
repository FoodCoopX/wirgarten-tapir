import React from "react";
import { Col, Form, Row } from "react-bootstrap";

import {
  BiddableProduct,
  CurrentPickupLocation,
  RoundTexts,
} from "../../api-client";
import NextStepButton from "../../components/mobile_wizard/NextStepButton.tsx";
import ProductCard from "../../components/mobile_wizard/ProductCard.tsx";
import { BUTTON_VARIANT } from "../../components/mobile_wizard/utils/BUTTON_VARIANT.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import PickupLocationRow from "../components/PickupLocationRow.tsx";
import {
  formatAmountNumber,
  getYearlyAmount,
  parseEuroAmount,
  sanitizeEuroAmountInput,
} from "../utils/amounts.ts";
import { getLevelLabels } from "../utils/levelLabels.ts";

interface BiddingRoundBidStepProps {
  biddableProduct: BiddableProduct;
  texts: RoundTexts;
  isBidRange: boolean;
  requiredAmountLevels: number;
  selectedVariantId: string | null;
  onSelectVariant: (variantId: string) => void;
  quantity: number;
  onQuantityChange: (quantity: number) => void;
  amounts: string[];
  onAmountChange: (levelIndex: number, value: string) => void;
  currentPickupLocation: CurrentPickupLocation | null;
  goToNextStep: () => void;
  stepActive: boolean;
}

const MIN_QUANTITY = 1;
const MAX_QUANTITY = 5;

const BiddingRoundBidStep: React.FC<BiddingRoundBidStepProps> = ({
  biddableProduct,
  texts,
  isBidRange,
  requiredAmountLevels,
  selectedVariantId,
  onSelectVariant,
  quantity,
  onQuantityChange,
  amounts,
  onAmountChange,
  currentPickupLocation,
  goToNextStep,
  stepActive,
}) => {
  const selectedVariant = biddableProduct.products.find(
    (variant) => variant.id === selectedVariantId,
  );

  const levelLabels = getLevelLabels(isBidRange, requiredAmountLevels, texts);

  function getLevelYearlyAmount(levelIndex: number): number | null {
    const parsedAmount = parseEuroAmount(amounts[levelIndex]);
    return parsedAmount === null
      ? null
      : getYearlyAmount(parsedAmount, quantity);
  }

  return (
    <>
      <div className={"d-flex flex-column gap-2"}>
        <Row xs={1} sm={2} className={"g-2"}>
          {biddableProduct.products.map((variant) => (
            <Col key={variant.id}>
              <ProductCard
                name={variant.name}
                referenceValue={variant.referenceValue}
                selected={variant.id === selectedVariantId}
                onSelect={() => onSelectVariant(variant.id)}
              />
            </Col>
          ))}
        </Row>

        <Form.Group>
          <Form.Label>
            <strong>Anteile</strong>
          </Form.Label>
          <div
            className={
              "d-flex flex-row gap-2 align-items-center justify-content-center"
            }
          >
            <TapirButton
              variant={BUTTON_VARIANT}
              icon={"remove"}
              size={"sm"}
              onClick={() =>
                onQuantityChange(Math.max(MIN_QUANTITY, quantity - 1))
              }
              disabled={quantity <= MIN_QUANTITY}
            />
            <span className={"fw-bold"}>{quantity}</span>
            <TapirButton
              variant={BUTTON_VARIANT}
              icon={"add"}
              size={"sm"}
              onClick={() =>
                onQuantityChange(Math.min(MAX_QUANTITY, quantity + 1))
              }
              disabled={quantity >= MAX_QUANTITY}
            />
          </div>
        </Form.Group>

        <PickupLocationRow
          currentPickupLocation={currentPickupLocation}
          texts={texts}
          variant={"stacked"}
        />

        {isBidRange && texts.bid.bidRangeExplanation && (
          <p
            className={"text-muted mb-0"}
            dangerouslySetInnerHTML={{
              __html: texts.bid.bidRangeExplanation,
            }}
          />
        )}

        {Array.from({ length: requiredAmountLevels }, (_, levelIndex) => {
          const yearlyAmount = getLevelYearlyAmount(levelIndex);
          return (
            <div key={levelLabels[levelIndex] ?? levelIndex}>
              <Form.Group>
                <Form.Label>
                  <strong>{levelLabels[levelIndex]}</strong>
                </Form.Label>
                <Form.Control
                  type={"text"}
                  inputMode={"decimal"}
                  placeholder={"0,00"}
                  value={amounts[levelIndex]}
                  onChange={(event) =>
                    onAmountChange(
                      levelIndex,
                      sanitizeEuroAmountInput(event.target.value),
                    )
                  }
                />
              </Form.Group>
              <p className={"text-center mb-0 small"}>
                {texts.bid.liveYearlyLabel}{" "}
                <strong>
                  {yearlyAmount === null ? "–" : formatCurrency(yearlyAmount)}
                </strong>
              </p>
            </div>
          );
        })}

        <Form.Text className={"text-muted"}>{texts.bid.monthlyHint}</Form.Text>

        {selectedVariant?.referenceValue && (
          <p className={"text-muted mb-0"}>
            {texts.bid.referenceValueHint.replace(
              "{reference_value}",
              formatAmountNumber(Number(selectedVariant.referenceValue)),
            )}
          </p>
        )}
      </div>

      <NextStepButton onClick={goToNextStep} stepActive={stepActive} />
    </>
  );
};

export default BiddingRoundBidStep;
