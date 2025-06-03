import React from "react";
import { Col, Form, Row } from "react-bootstrap";

import "../../tapir/core/static/core/bootstrap/5.1.3/css/bootstrap.min.css";
import "../../tapir/core/static/core/css/base.css";
import { type PublicProductType } from "../api-client";
import { formatCurrency } from "../utils/formatCurrency.ts";

interface ProductFormProps {
  productType: PublicProductType;
}

const ProductForm: React.FC<ProductFormProps> = ({ productType }) => {
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
              <div>
                <img
                  src={
                    "https://upload.wikimedia.org/wikipedia/commons/8/8a/Vegetables_for_sale_in_a_market_in_France.jpg"
                  }
                  style={{ maxWidth: "80%" }}
                  alt={"Photo von " + productType.name + " " + product.name}
                />
                <Form.Text>
                  Temporary pictures, later they should come from the DB
                </Form.Text>
              </div>
              <div>
                <strong>{product.name}</strong>
              </div>
              <div>
                <Form.Control type={"number"} min={0}></Form.Control>
              </div>
              <div>
                <Form.Text className={"text-center"} as={"p"}>
                  Basisbeitrag: {formatCurrency(product.price)} pro Monat inkl.
                  MwSt.
                </Form.Text>
              </div>
              <div>
                <Form.Text>{product.descriptionInBestellwizard}</Form.Text>
              </div>
            </Col>
          ))}
      </Row>
      <Row className={"mt-4"}>
        <Col>
          <h4>Dein Basisbeitrag: XX.YY€</h4>
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
