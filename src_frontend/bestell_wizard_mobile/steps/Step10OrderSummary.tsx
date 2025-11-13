import React from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { Accordion, AccordionBody } from "react-bootstrap";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { PublicProductType } from "../../api-client";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { isProductTypeOrdered } from "../../bestell_wizard/utils/isProductTypeOrdered.ts";
import { doesProductBelongsToProductType } from "../../bestell_wizard/utils/doesProductBelongToProductType.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import { scrollIntoView } from "../utils/scrollIntoView.ts";
import NextStepButton from "../components/NextStepButton.tsx";

interface Step10OrderSummaryProps {
  settings: BestellWizardSettings;
  shoppingCart: ShoppingCart;
  numberOfCoopShares: number;
  studentStatusEnabled: boolean;
  goToNextStep: () => void;
  contractStartDate: Date;
  firstDeliveryDatesByProductType: { [key: string]: Date };
  goToProductTypeStep: (pt: PublicProductType) => void;
  active: boolean;
}

const Step10OrderSummary: React.FC<Step10OrderSummaryProps> = ({
  settings,
  shoppingCart,
  numberOfCoopShares,
  studentStatusEnabled,
  goToNextStep,
  contractStartDate,
  firstDeliveryDatesByProductType,
  goToProductTypeStep,
}) => {
  function getProductById(productType: PublicProductType, productId: string) {
    return productType.products.find((product) => product.id === productId);
  }

  function getTotalPriceForProductType(productType: PublicProductType) {
    let sum = 0;
    for (const [productId, quantity] of Object.entries(shoppingCart)) {
      const product = getProductById(productType, productId);
      if (!product) {
        continue;
      }
      sum += product.price * quantity;
    }
    return sum;
  }

  function getProductTypeTitle(productType: PublicProductType) {
    if (isProductTypeOrdered(productType, shoppingCart)) {
      return (
        productType.name +
        " " +
        formatCurrency(getTotalPriceForProductType(productType)) +
        " / Monat"
      );
    }

    return productType.name + " (nicht bestellt)";
  }

  function getCoopSharesTitle() {
    if (studentStatusEnabled) {
      return "Keine Mitgliedschaft in der Genossenschaft (student)";
    }

    return (
      "Mitgliedschaft in der Genossenschaft (" +
      formatCurrency(numberOfCoopShares * settings.priceOfAShare) +
      ")"
    );
  }

  function buildProductDetails(
    productId: string,
    quantity: number,
    productType: PublicProductType,
  ) {
    const product = getProductById(productType, productId);
    if (!product) {
      return;
    }

    return (
      <li key={productId}>
        {product.name}
        {" × "}
        {quantity}: {formatCurrency(product.price * quantity)} / Monat
      </li>
    );
  }

  return (
    <>
      <div>
        <div className={"d-flex flex-column gap-2"}>
          {settings.productTypes.map((productType) => (
            <Accordion key={productType.id}>
              <Accordion.Item
                eventKey={productType.id!.toString()}
                onClick={scrollIntoView}
              >
                <Accordion.Header>
                  {getProductTypeTitle(productType)}
                </Accordion.Header>

                <AccordionBody>
                  {isProductTypeOrdered(productType, shoppingCart) && (
                    <ul>
                      {Object.entries(shoppingCart)
                        .filter(
                          ([productId, quantity]) =>
                            doesProductBelongsToProductType(
                              productId,
                              productType,
                            ) && quantity > 0,
                        )
                        .map(([productId, quantity]) =>
                          buildProductDetails(productId, quantity, productType),
                        )}
                      <li>
                        Vertragsstart: {formatDateNumeric(contractStartDate)}
                      </li>
                      {!productType.noDelivery && (
                        <li>
                          Erste Lieferung:{" "}
                          {formatDateNumeric(
                            firstDeliveryDatesByProductType[productType.id!],
                          )}
                        </li>
                      )}
                    </ul>
                  )}
                  <TapirButton
                    icon={"edit"}
                    text={"Bestellung anpassen"}
                    variant={"outline-secondary"}
                    size={"sm"}
                    onClick={() => goToProductTypeStep(productType)}
                  />
                </AccordionBody>
              </Accordion.Item>
            </Accordion>
          ))}
          {settings.showCoopContent && (
            <Accordion>
              <Accordion.Item eventKey={"coop_shares"} onClick={scrollIntoView}>
                <Accordion.Header>{getCoopSharesTitle()}</Accordion.Header>
                <AccordionBody>
                  {studentStatusEnabled
                    ? "Keine Anteile gezeichnet da student."
                    : numberOfCoopShares +
                      " × " +
                      formatCurrency(settings.priceOfAShare) +
                      " = " +
                      formatCurrency(
                        numberOfCoopShares * settings.priceOfAShare,
                      )}
                </AccordionBody>
              </Accordion.Item>
            </Accordion>
          )}
        </div>
      </div>
      <NextStepButton onClick={goToNextStep} />
    </>
  );
};

export default Step10OrderSummary;
