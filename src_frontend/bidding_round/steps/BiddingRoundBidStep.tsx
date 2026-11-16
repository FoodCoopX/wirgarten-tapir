import React, { useRef } from "react";
import { Button, Carousel, Form } from "react-bootstrap";
import { CarouselRef } from "react-bootstrap/Carousel";

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
  getMonthlyTotal,
  getYearlyAmount,
  parseEuroAmount,
  sanitizeEuroAmountInput,
} from "../utils/amounts.ts";
import { getLevelLabels } from "../utils/getLevelLabels.ts";

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
  sharesEnabled: boolean;
  carouselEnabled: boolean;
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
  sharesEnabled,
  carouselEnabled,
  goToNextStep,
  stepActive,
}) => {
  const selectedVariant = biddableProduct.products.find(
    (variant) => variant.id === selectedVariantId,
  );
  const selectedIndex = Math.max(
    0,
    biddableProduct.products.findIndex(
      (variant) => variant.id === selectedVariantId,
    ),
  );
  const carouselRef = useRef<CarouselRef>(null);

  const renderVariant = (
    variant: (typeof biddableProduct.products)[number],
  ) => (
    <div className={"d-flex flex-column align-items-center"}>
      <div
        className={"d-flex flex-row align-items-center justify-content-center"}
        style={{ width: "100%" }}
      >
        {variant.imageUrl ? (
          <img
            src={variant.imageUrl}
            style={{
              maxWidth: "40dvw",
              maxHeight: "30dvh",
              objectFit: "contain",
            }}
            alt={"Photo von " + variant.name}
          />
        ) : (
          <div style={{ height: "10dvh" }} />
        )}
      </div>
      <div className={"d-flex flex-row gap-2 justify-content-center"}>
        <strong>{variant.name}</strong>
      </div>
      {variant.referenceValue && (
        <div className={"text-center text-muted small"}>
          Richtwert {formatCurrency(Number(variant.referenceValue))}
        </div>
      )}
    </div>
  );

  function buildImageAtIndex(index: number, isBeforeButton: boolean) {
    const variant = biddableProduct.products[index];
    if (!variant) {
      return null;
    }

    return (
      <div
        style={{
          position: "absolute",
          left: isBeforeButton ? "2dvw" : undefined,
          right: isBeforeButton ? undefined : "2dvw",
          top: "47%",
          transform: "translate(0, -50%)",
          cursor: "pointer",
          zIndex: 10,
        }}
        className={"d-flex flex-column align-items-center"}
      >
        <Button
          variant={BUTTON_VARIANT}
          style={{ padding: 0 }}
          onClick={() =>
            isBeforeButton
              ? carouselRef.current?.prev()
              : carouselRef.current?.next()
          }
        >
          <div className={"d-flex flex-column align-items-center"}>
            <span className={"material-icons"}>
              {isBeforeButton ? "chevron_left" : "chevron_right"}
            </span>
            {variant.imageUrl && (
              <img
                src={variant.imageUrl}
                style={{
                  maxWidth: "8dvh",
                  objectFit: "contain",
                }}
                alt={"Photo von " + variant.name}
              />
            )}
          </div>
        </Button>
      </div>
    );
  }

  const levelLabels = getLevelLabels(
    texts,
    isBidRange,
    requiredAmountLevels,
  );

  return (
    <>
      <div className={"d-flex flex-column gap-2 w-100"}>
        {carouselEnabled ? (
          biddableProduct.products.length > 1 ? (
            <Carousel
              activeIndex={selectedIndex}
              onSelect={(index) =>
                onSelectVariant(biddableProduct.products[index].id)
              }
              controls={false}
              indicators={false}
              interval={null}
              touch={true}
              variant={"dark"}
              ref={carouselRef}
              wrap={false}
              style={{ width: "100%" }}
            >
              {biddableProduct.products.map((variant, index) => (
                <Carousel.Item key={variant.id}>
                  <div
                    className={
                      "d-flex flex-row align-items-center justify-content-center"
                    }
                  >
                    {buildImageAtIndex(index - 1, true)}
                    {renderVariant(variant)}
                    {buildImageAtIndex(index + 1, false)}
                  </div>
                </Carousel.Item>
              ))}
            </Carousel>
          ) : (
            biddableProduct.products.map((variant) => (
              <React.Fragment key={variant.id}>
                {renderVariant(variant)}
              </React.Fragment>
            ))
          )
        ) : (
          selectedVariant && renderVariant(selectedVariant)
        )}

        {sharesEnabled && (
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
        )}

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
          const parsedAmount = parseEuroAmount(amounts[levelIndex]);
          const yearlyAmount =
            parsedAmount === null
              ? null
              : getYearlyAmount(parsedAmount, quantity);
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
              {quantity > 1 && parsedAmount !== null && (
                <p className={"text-center mb-0 small text-muted"}>
                  Beitrag gesamt:{" "}
                  <strong>
                    {formatCurrency(getMonthlyTotal(parsedAmount, quantity))}{" "}
                    {texts.bid.monthlyUnit}
                  </strong>
                </p>
              )}
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
