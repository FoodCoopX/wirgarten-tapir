import React, { useEffect, useRef, useState } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { PublicProductType } from "../../api-client";
import { shouldShowWarningProductNotAvailable } from "../../utils/shouldShowWarningNotAvailable.ts";
import { Alert, Button, Carousel, Form } from "react-bootstrap";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { isProductTypeOrdered } from "../../bestell_wizard/utils/isProductTypeOrdered.ts";
import { formatShoppingCart } from "../../bestell_wizard/utils/formatShoppingCart.ts";
import { doesProductBelongsToProductType } from "../../bestell_wizard/utils/doesProductBelongToProductType.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { CarouselRef } from "react-bootstrap/Carousel";
import TapirCheckbox from "../components/TapirCheckbox.tsx";
import { shouldShowWarningCurrentOrderIsOverCapacity } from "../utils/shouldShowWarningCurrentOrderIsOverCapacity.ts";
import ProductWaitingListModal from "../../bestell_wizard/components/ProductWaitingListModal.tsx";
import { shouldOpenProductWaitingListModal } from "../utils/shouldOpenProductWaitingListModal.ts";

interface Step4BProductTypeOrderProps {
  settings: BestellWizardSettings;
  productType: PublicProductType;
  goToNextStep: () => void;
  shoppingCart: ShoppingCart;
  setShoppingCart: (cart: ShoppingCart) => void;
  active: boolean;
  checkingCapacities: boolean;
  waitingListLinkConfirmationModeEnabled: boolean;
  productIdsOverCapacity: string[];
  productTypeIdsOverCapacity: string[];
  productTypesInWaitingList: Set<PublicProductType>;
  setProductTypesInWaitingList: (set: Set<PublicProductType>) => void;
}

const Step4BProductTypeOrder: React.FC<Step4BProductTypeOrderProps> = ({
  settings,
  productType,
  goToNextStep,
  shoppingCart,
  setShoppingCart,
  active,
  checkingCapacities,
  waitingListLinkConfirmationModeEnabled,
  productIdsOverCapacity,
  productTypeIdsOverCapacity,
  productTypesInWaitingList,
  setProductTypesInWaitingList,
}) => {
  const carouselRef = useRef<CarouselRef>(null);
  const [showValidation, setShowValidation] = useState(false);
  const [waitingListModalOpen, setWaitingListModalOpen] = useState(false);

  useEffect(() => {
    if (!active) {
      setTimeout(() => setShowValidation(false), 200);
    }
  }, [active]);

  function validate() {
    setShowValidation(true);
    if (
      productType.mustBeSubscribedTo &&
      !isProductTypeOrdered(productType, shoppingCart)
    ) {
      return;
    }

    if (
      shouldOpenProductWaitingListModal(
        settings,
        shoppingCart,
        productTypesInWaitingList,
        productTypeIdsOverCapacity,
        productIdsOverCapacity,
        productType,
      )
    ) {
      setWaitingListModalOpen(true);
      return;
    }

    goToNextStep();
  }

  function getNextButtonText() {
    if (!isProductTypeOrdered(productType, shoppingCart)) {
      return "Weiter ohne " + productType.name;
    }

    const filteredShoppingCart = Object.fromEntries(
      Object.entries(shoppingCart).filter(([productId, _]) =>
        doesProductBelongsToProductType(productId, productType),
      ),
    );
    return "Weiter mit " + formatShoppingCart(filteredShoppingCart, settings);
  }

  function confirmEnableProductWaitingListMode() {
    productTypesInWaitingList.add(productType);
    setProductTypesInWaitingList(new Set(productTypesInWaitingList));

    setWaitingListModalOpen(false);
    goToNextStep();
  }

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
        onClick={() =>
          isBeforeButton
            ? carouselRef.current?.prev()
            : carouselRef.current?.next()
        }
      >
        <Button variant={BUTTON_VARIANT} style={{ padding: 0 }}>
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
                  filter: shouldShowWarningProductNotAvailable(
                    product,
                    productType,
                    settings,
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
      <Carousel
        indicators={false}
        controls={false}
        interval={null}
        touch={true}
        style={{ width: "100%" }}
        variant={"dark"}
        ref={carouselRef}
        wrap={false}
        defaultActiveIndex={productType.products.length > 1 ? 1 : 0}
      >
        {productType.products
          .sort((a, b) => a.price - b.price)
          .map((product, index) => (
            <Carousel.Item key={product.id}>
              <div
                className={
                  "d-flex flex-row align-items-center justify-content-center"
                }
              >
                {productType.products.length > 1 &&
                  buildImageAtIndex(index - 1, true)}
                {product.urlOfImageInBestellwizard ? (
                  <img
                    src={product.urlOfImageInBestellwizard}
                    style={{
                      maxHeight: "30dvh",
                      objectFit: "contain",
                      filter: shouldShowWarningProductNotAvailable(
                        product,
                        productType,
                        settings,
                      )
                        ? "grayscale(1)"
                        : "",
                    }}
                    alt={"Photo von " + productType.name + " " + product.name}
                  />
                ) : (
                  <div style={{ height: "10dvh" }}></div>
                )}
                {productType.products.length > 1 &&
                  buildImageAtIndex(index + 1, false)}
              </div>
              <div className={"d-flex flex-row gap-2 justify-content-center"}>
                <strong>{product.name}</strong>
              </div>
              <div
                className={"mt-1 d-flex flex-row gap-2 justify-content-center"}
              >
                {productType.singleSubscriptionOnly ? (
                  <TapirCheckbox
                    controlId={"single_sub_" + product.id}
                    checked={shoppingCart[product.id!] > 0}
                    onChange={(checked) => {
                      shoppingCart[product.id!] = checked ? 1 : 0;
                      setShoppingCart(Object.assign({}, shoppingCart));
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
                        setShoppingCart(Object.assign({}, shoppingCart));
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
                        shoppingCart[product.id!] =
                          shoppingCart[product.id!] + 1;
                        setShoppingCart(Object.assign({}, shoppingCart));
                      }}
                      disabled={waitingListLinkConfirmationModeEnabled}
                    />
                  </>
                )}
              </div>
              <div>
                <Form.Text className={"text-center mb-0"} as={"p"}>
                  Basisbeitrag: {formatCurrency(product.price)} pro Monat inkl.
                  MwSt.
                  {product.descriptionInBestellwizard && (
                    <>
                      <br />
                      {product.descriptionInBestellwizard}
                    </>
                  )}
                  <br />
                  <span
                    className={"text-danger"}
                    style={{
                      opacity: shouldShowWarningProductNotAvailable(
                        product,
                        productType,
                        settings,
                      )
                        ? 1
                        : 0,
                    }}
                  >
                    (nur Warteliste-Eintrag möglich)
                  </span>
                </Form.Text>
              </div>
            </Carousel.Item>
          ))}
      </Carousel>
      {showValidation &&
        !isProductTypeOrdered(productType, shoppingCart) &&
        productType.mustBeSubscribedTo && (
          <Form.Control.Feedback
            type="invalid"
            style={{ display: "block" }}
            className={"text-center"}
          >
            Dieses Produkt muss bestellt werden.
          </Form.Control.Feedback>
        )}
      {shouldShowWarningCurrentOrderIsOverCapacity(
        productType,
        settings,
        productTypeIdsOverCapacity,
        productIdsOverCapacity,
        shoppingCart,
      ) && (
        <Alert variant={"warning"}>
          <small>
            Derzeit ist deine gewünschte {productType?.name}-Größe nicht
            verfügbar. Du kannst eine andere Größe wählen, oder dich auf die
            Warteliste setzen lassen.
          </small>
        </Alert>
      )}
      <NextStepButton
        onClick={validate}
        text={getNextButtonText()}
        loading={checkingCapacities}
      />
      <ProductWaitingListModal
        show={waitingListModalOpen}
        onHide={() => setWaitingListModalOpen(false)}
        confirmEnableWaitingListMode={confirmEnableProductWaitingListMode}
        productType={productType}
      />
    </>
  );
};

export default Step4BProductTypeOrder;
