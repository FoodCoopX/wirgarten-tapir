import React, { useState } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { PublicProduct, PublicProductType } from "../../api-client";
import { shouldShowWarningProductNotAvailable } from "../../utils/shouldShowWarningNotAvailable.ts";
import { Form } from "react-bootstrap";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import Step4BProductDetailModal from "../Components/Step4BProductDetailModal.tsx";

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

  return (
    <>
      <div
        style={{ height: "100%", overflowY: "hidden" }}
        className={
          "d-flex align-items-center justify-content-center gap-2 flex-column"
        }
      >
        <div
          className={
            "d-flex flex-row align-items-center  justify-content-center flex-wrap"
          }
          style={{ gap: "0 .5rem" }}
        >
          {productType.products
            .sort((a, b) => a.price - b.price)
            .map((product) => (
              <div
                key={product.id}
                className={"d-flex align-items-center  flex-column"}
                style={{ width: "40%" }}
              >
                <div className={"d-flex justify-content-center"}>
                  {product.urlOfImageInBestellwizard !== "" && (
                    <img
                      src={product.urlOfImageInBestellwizard}
                      style={{
                        maxWidth: "80%",
                        maxHeight: "23vh",
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
                <div className={"d-flex flex-row gap-2"}>
                  <strong>{product.name}</strong>
                  <TapirButton
                    size={"sm"}
                    icon={"help"}
                    variant={"outline-secondary"}
                    onClick={() => setProductForDetailModal(product)}
                  />
                </div>
                <div className={"mt-1"}>
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
                    <div className={"d-flex flex-row gap-2"}>
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
                      />
                      <Form.Control
                        type={"number"}
                        min={0}
                        onChange={(event) => {
                          let newValue = parseInt(event.target.value);
                          if (Number.isNaN(newValue)) {
                            newValue = 0;
                          }
                          shoppingCart[product.id!] = newValue;
                          setShoppingCart(Object.assign({}, shoppingCart));
                        }}
                        value={shoppingCart[product.id!]}
                        size={"sm"}
                      />
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
                    </div>
                  )}
                </div>
                <div>
                  <Form.Text className={"text-center"} as={"p"}>
                    Basisbeitrag: {formatCurrency(product.price)} pro Monat
                    {shouldShowWarningProductNotAvailable(
                      product,
                      productType,
                      settings,
                    ) && (
                      <>
                        <br />
                        <span className={"text-danger"}>
                          (nur Warteliste-Eintrag möglich)
                        </span>
                      </>
                    )}
                  </Form.Text>
                </div>
              </div>
            ))}
        </div>
        <TapirButton
          variant={"outline-secondary"}
          text={"Weiter"}
          onClick={goToNextStep}
        />
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
