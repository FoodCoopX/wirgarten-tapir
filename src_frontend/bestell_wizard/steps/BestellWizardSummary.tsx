import React, { Fragment } from "react";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { PersonalData } from "../types/PersonalData.ts";
import BestellWizardCardTitle from "../components/BestellWizardCardTitle.tsx";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import BestellWizardCardSubtitle from "../components/BestellWizardCardSubtitle.tsx";
import { Col, Form, Row, Table } from "react-bootstrap";
import { PublicPickupLocation, PublicProductType } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import formatAddress from "../../utils/formatAddress.ts";
import { formatOpeningTimes } from "../utils/formatOpeningTimes.ts";
import { isProductTypeOrdered } from "../utils/isProductTypeOrdered.ts";
import { formatDateText } from "../../utils/formatDateText.ts";

interface BestellWizardSummaryProps {
  theme: TapirTheme;
  personalData: PersonalData;
  shoppingCart: ShoppingCart;
  selectedNumberOfCoopShares: number;
  productTypes: PublicProductType[];
  selectedPickupLocations: PublicPickupLocation[];
  priceOfAShare: number;
  firstDeliveryDatesByProductType: { [key: string]: Date };
  updateOrderFromSummary: (productType: PublicProductType) => void;
  waitingListModeEnabled: boolean;
  cancellationPolicyRead: boolean;
  setCancellationPolicyRead: (read: boolean) => void;
  privacyPolicyRead: boolean;
  setPrivacyPolicyRead: (read: boolean) => void;
}

const BestellWizardSummary: React.FC<BestellWizardSummaryProps> = ({
  theme,
  personalData,
  shoppingCart,
  selectedNumberOfCoopShares,
  productTypes,
  selectedPickupLocations,
  priceOfAShare,
  firstDeliveryDatesByProductType,
  updateOrderFromSummary,
  waitingListModeEnabled,
  cancellationPolicyRead,
  setCancellationPolicyRead,
  privacyPolicyRead,
  setPrivacyPolicyRead,
}) => {
  function getProductIdsOfProductType(productType: PublicProductType) {
    return productType.products.map((product) => product.id);
  }

  function getProductById(productType: PublicProductType, productId: string) {
    return productType.products.find((product) => product.id === productId);
  }

  function buildProductTypeTable(productType: PublicProductType) {
    return (
      <Table bordered={true}>
        <tbody>
          {!waitingListModeEnabled && (
            <tr>
              <td>Erste Lieferung</td>
              <td>
                {formatDateText(
                  firstDeliveryDatesByProductType[productType.id!],
                )}
              </td>
            </tr>
          )}
          {Object.entries(shoppingCart)
            .filter(
              ([productId, quantity]) =>
                getProductIdsOfProductType(productType).includes(productId) &&
                quantity > 0,
            )
            .map(([productId, quantity]) => (
              <tr key={productId}>
                <td>{getProductById(productType, productId)?.name}</td>
                <td>
                  {quantity} x{" "}
                  {formatCurrency(
                    getProductById(productType, productId)!.price,
                  )}
                </td>
              </tr>
            ))}
        </tbody>
      </Table>
    );
  }

  return (
    <>
      <Row>
        <Col>
          <BestellWizardCardTitle text={"Übersicht"} />
          <BestellWizardCardSubtitle
            text={"Deine Mitgliedschaft in der Genossenschaft"}
          />
          <Table bordered={true}>
            <tbody>
              <tr>
                <td>Deine Genossenschaftsanteile</td>
                <td>
                  {selectedNumberOfCoopShares} * {formatCurrency(priceOfAShare)}{" "}
                  = {formatCurrency(priceOfAShare * selectedNumberOfCoopShares)}
                </td>
              </tr>
              {!waitingListModeEnabled && (
                <tr>
                  <td>Abbuchung</td>
                  <td>TODO Abbuchung</td>
                </tr>
              )}
            </tbody>
          </Table>
          {productTypes.map((productType) => (
            <div className={"mt-4"} key={productType.id}>
              <BestellWizardCardSubtitle text={productType.name} />
              {isProductTypeOrdered(productType, shoppingCart) ? (
                buildProductTypeTable(productType)
              ) : (
                <span>Dieses Produkt ist nicht bestellt worden</span>
              )}
              <TapirButton
                icon={"edit"}
                text={"Bestellung anpassen"}
                variant={"outline-primary"}
                size={"sm"}
                onClick={() => updateOrderFromSummary(productType)}
              />
            </div>
          ))}
          {selectedPickupLocations.length > 0 && (
            <div className={"mt-4"}>
              {waitingListModeEnabled ? (
                <BestellWizardCardSubtitle
                  text={"Deine Verteilstationswünsche"}
                />
              ) : (
                <BestellWizardCardSubtitle text={"Deine Verteilstation"} />
              )}
              <Table bordered={true}>
                <tbody>
                  {selectedPickupLocations.map((pickupLocation, index) => (
                    <Fragment key={pickupLocation.id!}>
                      {waitingListModeEnabled && (
                        <tr>
                          <th colSpan={2}>{index + 1}. Wunsch</th>
                        </tr>
                      )}
                      <tr>
                        <td>Adresse</td>
                        <td>
                          {pickupLocation.name} <br />
                          {formatAddress(
                            pickupLocation.street,
                            pickupLocation.street2,
                            pickupLocation.postcode,
                            pickupLocation.city,
                          )}
                        </td>
                      </tr>
                      <tr>
                        <td>Öffnungszeiten</td>
                        <td>{formatOpeningTimes(pickupLocation)}</td>
                      </tr>
                    </Fragment>
                  ))}
                </tbody>
              </Table>
            </div>
          )}
        </Col>
      </Row>
      <Row>
        <Col>
          {!waitingListModeEnabled && (
            <Form.Group controlId={"cancellation_policy"}>
              <Form.Check
                label={
                  "Ja, ich habe die Widerrufsbelehrung zur Kenntnis genommen."
                }
                checked={cancellationPolicyRead}
                onChange={(event) =>
                  setCancellationPolicyRead(event.target.checked)
                }
              />
              <Form.Text>
                Du kannst deine Verträge und Beitrittserklärung innerhalb von
                zwei Wochen in Textform (z.B. Brief, E-Mail) widerrufen. Die
                Frist beginnt spätestens mit Erhalt dieser Belehrung. Zur
                Wahrung der Widerrufsfrist genügt die rechtzeitige Absendung
                eines formlosen Widerrufsschreibens an
                verwaltung@biotop-oberland.de.
              </Form.Text>
            </Form.Group>
          )}
          <Form.Group controlId={"privacy_policy"}>
            <Form.Check
              label={
                "Ja, ich habe die Datenschutzerklärung zur Kenntnis genommen."
              }
              checked={privacyPolicyRead}
              onChange={(event) => setPrivacyPolicyRead(event.target.checked)}
            />
            <Form.Text>
              Wir behandeln deine Daten vertraulich, verwenden diese nur im
              Rahmen der Mitgliederverwaltung und geben sie nicht an Dritte
              weiter. Unsere Datenschutzerklärung kannst du hier einsehen:{" "}
              <a href={"https://biotop-oberland.de/datenschutz/"}>
                Datenschutzerklärung
              </a>
            </Form.Text>
          </Form.Group>
        </Col>
      </Row>
    </>
  );
};

export default BestellWizardSummary;
