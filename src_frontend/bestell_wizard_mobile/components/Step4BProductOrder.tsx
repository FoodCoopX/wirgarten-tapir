import React, { RefObject } from "react";
import { Button, Form } from "react-bootstrap";
import { CarouselRef } from "react-bootstrap/Carousel";
import { PublicProduct, PublicProductType } from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { isProductTypeOrdered } from "../../bestell_wizard/utils/isProductTypeOrdered.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { formatPercentage } from "../../utils/formatPercentage.ts";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { showCapacityWarning } from "../utils/showCapacityWarning.ts";
import TapirCheckbox from "./TapirCheckbox.tsx";

interface NextButtonProps {
  product: PublicProduct;
  productType: PublicProductType;
  settings: BestellWizardSettings;
  productTypeIdsOverCapacity: string[];
  productIdsOverCapacity: string[];
  shoppingCart: ShoppingCart;
  setShoppingCart: (cart: ShoppingCart) => void;
  waitingListLinkConfirmationModeEnabled: boolean;
  showValidation: boolean;
  setWaitingListInfoModalOpen: (open: boolean) => void;
  showCarouselArrows: boolean;
  index: number;
  carouselProducts: PublicProduct[];
  carouselRef: RefObject<CarouselRef | null>;
}

const Step4BProductOrder: React.FC<NextButtonProps> = ({
  product,
  productType,
  settings,
  productTypeIdsOverCapacity,
  productIdsOverCapacity,
  shoppingCart,
  setShoppingCart,
  waitingListLinkConfirmationModeEnabled,
  showValidation,
  setWaitingListInfoModalOpen,
  showCarouselArrows,
  index,
  carouselProducts,
  carouselRef,
}) => {
  function buildPreviewColumn(index: number, isBeforeButton: boolean) {
    const showPreview =
      showCarouselArrows && index >= 0 && index < carouselProducts.length;

    return (
      <div
        style={{
          justifySelf: isBeforeButton ? "start" : "end",
          marginLeft: isBeforeButton ? "2dvw" : undefined,
          marginRight: isBeforeButton ? undefined : "2dvw",
        }}
      >
        {showPreview && buildPreview(carouselProducts[index], isBeforeButton)}
      </div>
    );
  }

  function buildPreview(product: PublicProduct, isBeforeButton: boolean) {
    return (
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
          {product.urlOfImageInBestellwizard && (
            <img
              src={product.urlOfImageInBestellwizard}
              style={{
                maxWidth: "8dvh",
                objectFit: "contain",
                filter: showCapacityWarning(
                  product,
                  productType,
                  settings,
                  productTypeIdsOverCapacity,
                  productIdsOverCapacity,
                  shoppingCart,
                )
                  ? "grayscale(1)"
                  : "",
              }}
              alt={"Photo von " + productType.name + " " + product.name}
            />
          )}
        </div>
      </Button>
    );
  }

  return (
    <>
      <div
        className={"align-items-center"}
        style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr" }}
      >
        {buildPreviewColumn(index - 1, true)}
        {product.urlOfImageInBestellwizard ? (
          <img
            src={product.urlOfImageInBestellwizard}
            style={{
              maxWidth: "40dvw",
              maxHeight: "30dvh",
              objectFit: "contain",
              filter: showCapacityWarning(
                product,
                productType,
                settings,
                productTypeIdsOverCapacity,
                productIdsOverCapacity,
                shoppingCart,
              )
                ? "grayscale(1)"
                : "",
            }}
            alt={"Photo von " + productType.name + " " + product.name}
          />
        ) : (
          <div style={{ height: "10dvh" }}></div>
        )}
        {buildPreviewColumn(index + 1, false)}
      </div>
      <div className={"d-flex flex-row gap-2 justify-content-center"}>
        <strong>{product.name}</strong>
      </div>
      <div className={"mt-1 d-flex flex-row gap-2 justify-content-center"}>
        {productType.singleSubscriptionOnly ? (
          <TapirCheckbox
            controlId={"single_sub_" + product.id}
            checked={shoppingCart[product.id!] > 0}
            onChange={(checked) => {
              shoppingCart[product.id!] = checked ? 1 : 0;
              setShoppingCart({ ...shoppingCart });
            }}
            disabled={waitingListLinkConfirmationModeEnabled}
          />
        ) : (
          <>
            {!waitingListLinkConfirmationModeEnabled && (
              <TapirButton
                variant={BUTTON_VARIANT}
                icon={"remove"}
                size={"sm"}
                onClick={() => {
                  shoppingCart[product.id!] = Math.max(
                    0,
                    shoppingCart[product.id!] - 1,
                  );
                  setShoppingCart({ ...shoppingCart });
                }}
                disabled={
                  shoppingCart[product.id!] === 0 ||
                  waitingListLinkConfirmationModeEnabled
                }
              />
            )}
            <span
              className={
                showValidation &&
                !isProductTypeOrdered(productType, shoppingCart) &&
                productType.mustBeSubscribedTo
                  ? "text-danger"
                  : ""
              }
            >
              {shoppingCart[product.id!] ?? 0}
            </span>
            {!waitingListLinkConfirmationModeEnabled && (
              <TapirButton
                variant={BUTTON_VARIANT}
                icon={"add"}
                size={"sm"}
                onClick={() => {
                  shoppingCart[product.id!] = shoppingCart[product.id!] + 1;
                  setShoppingCart({ ...shoppingCart });
                }}
                disabled={waitingListLinkConfirmationModeEnabled}
              />
            )}
          </>
        )}
      </div>
      <div>
        <Form.Text className={"text-center mb-0"} as={"p"}>
          {settings.strings.step4bBasePriceLabel}:{" "}
          {formatCurrency(product.price)} pro{" "}
          {productType.pricePerDelivery ? "Lieferung" : "Monat"}
          {productType.taxRate > 0 &&
            " inkl. " + formatPercentage(productType.taxRate) + " MwSt"}
          .
          {product.descriptionInBestellwizard && (
            <>
              <br />
              <span
                dangerouslySetInnerHTML={{
                  __html: product.descriptionInBestellwizard,
                }}
              />
            </>
          )}
          <br />
          <span
            className={
              "d-flex flex-row gap-2 justify-content-center align-items-center"
            }
            style={
              showCapacityWarning(
                product,
                productType,
                settings,
                productTypeIdsOverCapacity,
                productIdsOverCapacity,
                shoppingCart,
              )
                ? {}
                : {
                    opacity: 0,
                    pointerEvents: "none",
                  }
            }
          >
            <span className={"text-danger"}>
              (nur Warteliste-Eintrag möglich)
            </span>
            <TapirButton
              icon={"help"}
              size={"sm"}
              variant={BUTTON_VARIANT}
              onClick={() => setWaitingListInfoModalOpen(true)}
            />
          </span>
        </Form.Text>
      </div>
    </>
  );
};

export default Step4BProductOrder;
