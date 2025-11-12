import React, { useEffect, useState } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { PublicProduct, PublicProductType } from "../../api-client";
import { shouldShowWarningProductNotAvailable } from "../../utils/shouldShowWarningNotAvailable.ts";
import { Carousel, Form } from "react-bootstrap";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import Step4BProductDetailModal from "../components/Step4BProductDetailModal.tsx";
import { isProductTypeOrdered } from "../../bestell_wizard/utils/isProductTypeOrdered.ts";
import { formatShoppingCart } from "../../bestell_wizard/utils/formatShoppingCart.ts";
import { doesProductBelongsToProductType } from "../../bestell_wizard/utils/doesProductBelongToProductType.ts";

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
  const [productForDetailModal, setProductForDetailModal] =
    useState<PublicProduct>();
  const [activeProductIndex, setActiveProductIndex] = useState(0);

  useEffect(() => {
    if (productType.products.length > 1) {
      setActiveProductIndex(1);
    } else {
      setActiveProductIndex(0);
    }
  }, [productType]);

  function handleSelect(index: number) {
    setActiveProductIndex(index);
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

  return (
    <>
      <div
        style={{ height: "100%", overflowY: "hidden" }}
        className={
          "d-flex align-items-center justify-content-center gap-4 flex-column"
        }
      >
        <Carousel
          activeIndex={activeProductIndex}
          onSelect={handleSelect}
          indicators={false}
          controls={productType.products.length > 1}
          interval={null}
          touch={false}
          style={{ width: "100%" }}
          variant={"dark"}
        >
          {productType.products
            .sort((a, b) => a.price - b.price)
            .map((product) => (
              <Carousel.Item key={product.id}>
                <div className={"d-flex justify-content-center"}>
                  {product.urlOfImageInBestellwizard !== "" && (
                    <img
                      src={product.urlOfImageInBestellwizard}
                      style={{
                        maxHeight: "40dvh",
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
                <div className={"d-flex flex-row gap-2 justify-content-center"}>
                  <strong>{product.name}</strong>
                </div>
                <div
                  className={
                    "mt-1 d-flex flex-row gap-2 justify-content-center"
                  }
                >
                  {productType.singleSubscriptionOnly ? (
                    <Form.Check
                      checked={shoppingCart[product.id!] > 0}
                      onChange={(event) => {
                        shoppingCart[product.id!] = event.target.checked
                          ? 1
                          : 0;
                        setShoppingCart(Object.assign({}, shoppingCart));
                      }}
                    />
                  ) : (
                    <>
                      <TapirButton
                        variant={"outline-secondary"}
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
                        variant={"outline-secondary"}
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
                    Basisbeitrag: {formatCurrency(product.price)} pro Monat
                    inkl. MwSt.
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

        <div
          className={"px-2 d-flex flex-row justify-content-center"}
          style={{ width: "100%" }}
        >
          <TapirButton
            variant={"outline-secondary"}
            text={getNextButtonText()}
            onClick={goToNextStep}
            size={"sm"}
            icon={"keyboard_arrow_down"}
          />
        </div>
      </div>

      {productForDetailModal && (
        <Step4BProductDetailModal
          productType={productType}
          product={productForDetailModal}
          show={true}
          onHide={() => setProductForDetailModal(undefined)}
          settings={settings}
        />
      )}
    </>
  );
};

export default Step4BProductTypeOrder;
