import React from "react";
import { Alert, Col, Form, Row } from "react-bootstrap";

import "../../../tapir/core/static/core/bootstrap/5.1.3/css/bootstrap.min.css";
import "../../../tapir/core/static/core/css/base.css";
import { type PublicProductType } from "../../api-client";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import BestellWizardCardSubtitle from "./BestellWizardCardSubtitle.tsx";

interface ProductFormProps {
  productType: PublicProductType;
  shoppingCart: ShoppingCart;
  setShoppingCart: (shoppingCart: ShoppingCart) => void;
  waitingListLinkConfirmationModeEnabled: boolean;
}

const ProductForm: React.FC<ProductFormProps> = ({
  productType,
  shoppingCart,
  setShoppingCart,
  waitingListLinkConfirmationModeEnabled,
}) => {
  function totalPriceForThisProductType() {
    let total = 0;
    for (const product of productType.products) {
      total += product.price * shoppingCart[product.id!];
    }
    return total;
  }

  return (
    <>
      <Row className={"justify-content-center"}>
        {productType.products
          .sort((a, b) => a.price - b.price)
          .map((product) => (
            <Col
              key={product.id}
              className={"d-flex align-items-center flex-column"}
            >
              <div className={"d-flex justify-content-center"}>
                {product.urlOfImageInBestellwizard !== "" && (
                  <img
                    src={product.urlOfImageInBestellwizard}
                    style={{ maxWidth: "75%" }}
                    alt={"Photo von " + productType.name + " " + product.name}
                  />
                )}
              </div>
              <div>
                <strong>{product.name}</strong>
              </div>
              <div>
                {productType.singleSubscriptionOnly ? (
                  <Form.Check
                    checked={shoppingCart[product.id!] > 0}
                    onChange={(event) => {
                      shoppingCart[product.id!] = event.target.checked ? 1 : 0;
                      setShoppingCart(Object.assign({}, shoppingCart));
                    }}
                    disabled={waitingListLinkConfirmationModeEnabled}
                  />
                ) : (
                  <Form.Control
                    type={"number"}
                    min={0}
                    value={shoppingCart[product.id!]}
                    onChange={(event) => {
                      let newValue = parseInt(event.target.value);
                      if (Number.isNaN(newValue)) {
                        newValue = 0;
                      }
                      shoppingCart[product.id!] = newValue;
                      setShoppingCart(Object.assign({}, shoppingCart));
                    }}
                    disabled={waitingListLinkConfirmationModeEnabled}
                  />
                )}
              </div>
              <div>
                <Form.Text className={"text-center"} as={"p"}>
                  Basisbeitrag: {formatCurrency(product.price)} pro Monat inkl.
                  MwSt.
                </Form.Text>
              </div>
              <div>
                <Form.Text className={"text-center"} as={"p"}>
                  {product.descriptionInBestellwizard}
                </Form.Text>
              </div>
            </Col>
          ))}
      </Row>
      {productType.forceWaitingList && (
        <Row className={"mt-4"}>
          <Col>
            <Alert variant={"warning"}>
              Derzeit ausgebucht. Nur Wartelisteneintrag möglich
            </Alert>
          </Col>
        </Row>
      )}
      <Row className={"mt-4"}>
        <Col>
          <BestellWizardCardSubtitle
            text={
              "Dein Basisbeitrag: " +
              formatCurrency(totalPriceForThisProductType())
            }
          />
          <p>
            Ein Beitrag für einen Ernteanteil im Biotop besteht aus dem{" "}
            <strong>Basisbeitrag</strong> und einem{" "}
            <strong>Solidarbeitrag</strong>.
          </p>
          <p>
            Dein monatlicher Gesamt-Beitrag = Basisbeitrag + individueller
            Solidarbeitrag <br />
            Unsere Beitragsstruktur im Detail erklärt:{" "}
            <a href={"https://biotop-oberland.de/beitrag/"}>
              https://biotop-oberland.de/beitrag/
            </a>
          </p>
          <p>
            <strong>Solidarisch finanzierter Ernteanteil:</strong> Du kannst dir
            den Basisbeitrag nicht leisten? Für Auszubildende, Studenten,
            Arbeitssuchende etc. gibt die Möglichkeit einen geringeren
            Basisbeitrag zu zahlen. Für den genauen Ablauf und die aktuelle
            Beitragshöhe kontaktiere uns bitte unter
            verwaltung@biotop-oberland.de.
          </p>
        </Col>
      </Row>
    </>
  );
};

export default ProductForm;
