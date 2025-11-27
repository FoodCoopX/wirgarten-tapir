import React, { useRef } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { PublicProductType } from "../../api-client";
import { shouldShowWarningProductNotAvailable } from "../../utils/shouldShowWarningNotAvailable.ts";
import { Button, Carousel, Form } from "react-bootstrap";
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

interface Step4BProductTypeOrderProps {
  settings: BestellWizardSettings;
  productType: PublicProductType;
  goToNextStep: () => void;
  shoppingCart: ShoppingCart;
  setShoppingCart: (cart: ShoppingCart) => void;
}

const Step4BProductTypeOrder: React.FC<Step4BProductTypeOrderProps> = ({
  settings,
  productType,
  goToNextStep,
  shoppingCart,
  setShoppingCart,
}) => {
  const carouselRef = useRef<CarouselRef>(null);

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
        <Button variant={"outline-dark"} style={{ padding: 0 }}>
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
                      disabled={shoppingCart[product.id!] === 0}
                    />
                    <span>{shoppingCart[product.id!]}</span>
                    <TapirButton
                      variant={BUTTON_VARIANT}
                      icon={"add"}
                      size={"sm"}
                      onClick={() => {
                        shoppingCart[product.id!] =
                          shoppingCart[product.id!] + 1;
                        setShoppingCart(Object.assign({}, shoppingCart));
                      }}
                    />
                  </>
                )}
              </div>
              <div>
                <Form.Text className={"text-center"} as={"p"}>
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
      <NextStepButton onClick={goToNextStep} text={getNextButtonText()} />
    </>
  );
};

export default Step4BProductTypeOrder;
