import React, { RefObject } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { PublicProduct, PublicProductType } from "../../api-client";
import { showCapacityWarning } from "../utils/showCapacityWarning.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import TapirCheckbox from "./TapirCheckbox.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { isProductTypeOrdered } from "../../bestell_wizard/utils/isProductTypeOrdered.ts";
import { Button, Form } from "react-bootstrap";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { CarouselRef } from "react-bootstrap/Carousel";

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
  carouselRef,
}) => {
  function buildImageAtIndex(index: number, isBeforeButton: boolean) {
    if (index < 0 || index >= productType.products.length) return;

    const product = productType.products[index];

    return (
      <div
        style={{
          position: "absolute",
          left: isBeforeButton ? "2dvw" : undefined,
          right: isBeforeButton ? undefined : "2dvw",
          top: "47%",
          transform: "translate(0, -50%)",
          cursor: "pointer",
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
      </div>
    );
  }

  return (
    <>
      <div
        className={"d-flex flex-row align-items-center justify-content-center"}
      >
        {showCarouselArrows && buildImageAtIndex(index - 1, true)}
        {product.urlOfImageInBestellwizard ? (
          <img
            src={product.urlOfImageInBestellwizard}
            style={{
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
        {showCarouselArrows && buildImageAtIndex(index + 1, false)}
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
          />
        ) : (
          <>
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
            <span
              className={
                showValidation &&
                !isProductTypeOrdered(productType, shoppingCart) &&
                productType.mustBeSubscribedTo
                  ? "text-danger"
                  : ""
              }
            >
              {shoppingCart[product.id!]}
            </span>
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
          </>
        )}
      </div>
      <div>
        <Form.Text className={"text-center mb-0"} as={"p"}>
          Basisbeitrag: {formatCurrency(product.price)} pro Monat inkl. MwSt.
          {product.descriptionInBestellwizard && (
            <>
              <br />
              {product.descriptionInBestellwizard}
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
