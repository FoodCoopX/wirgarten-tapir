import React, { Fragment } from "react";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { PersonalData } from "../types/PersonalData.ts";
import BestellWizardCardTitle from "../components/BestellWizardCardTitle.tsx";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import BestellWizardCardSubtitle from "../components/BestellWizardCardSubtitle.tsx";
import { Col, Form, Row, Table } from "react-bootstrap";
import {
  PublicPickupLocation,
  PublicProductType,
  WaitingListEntryDetails,
} from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { isProductTypeOrdered } from "../utils/isProductTypeOrdered.ts";
import SummaryProductTypeTable from "../components/SummaryProductTypeTable.tsx";
import SummaryPickupLocations from "../components/SummaryPickupLocations.tsx";
import { shouldIncludeStepCoopShares } from "../utils/shouldIncludeStep.ts";

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
  waitingListLinkConfirmationModeEnabled: boolean;
  waitingListEntryDetails: WaitingListEntryDetails | undefined;
  showCoopContent: boolean;
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
  waitingListLinkConfirmationModeEnabled,
  waitingListEntryDetails,
  showCoopContent,
}) => {
  function shouldShowPickupLocationSummary() {
    if (selectedPickupLocations.length === 0) {
      return false;
    }

    return (
      waitingListEntryDetails === undefined ||
      (waitingListEntryDetails.pickupLocationWishes ?? []).length > 0
    );
  }

  return (
    <>
      <Row>
        <Col>
          {shouldIncludeStepCoopShares(
            waitingListEntryDetails,
            waitingListModeEnabled,
            showCoopContent,
          ) && (
            <>
              <BestellWizardCardTitle text={"Übersicht"} />
              <BestellWizardCardSubtitle
                text={"Deine Mitgliedschaft in der Genossenschaft"}
              />
              <Table bordered={true}>
                <tbody>
                  <tr>
                    <td>Deine Genossenschaftsanteile</td>
                    <td>
                      {selectedNumberOfCoopShares} *{" "}
                      {formatCurrency(priceOfAShare)} ={" "}
                      {formatCurrency(
                        priceOfAShare * selectedNumberOfCoopShares,
                      )}
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
            </>
          )}
          {productTypes.map((productType) => {
            if (
              waitingListLinkConfirmationModeEnabled &&
              !isProductTypeOrdered(productType, shoppingCart)
            ) {
              return null;
            }
            return (
              <div className={"mt-4"} key={productType.id}>
                <BestellWizardCardSubtitle text={productType.name} />
                {isProductTypeOrdered(productType, shoppingCart) ? (
                  <SummaryProductTypeTable
                    productType={productType}
                    firstDeliveryDatesByProductType={
                      firstDeliveryDatesByProductType
                    }
                    shoppingCart={shoppingCart}
                    waitingListModeEnabled={waitingListModeEnabled}
                  />
                ) : (
                  <span>Dieses Produkt ist nicht bestellt worden</span>
                )}
                {!waitingListLinkConfirmationModeEnabled && (
                  <TapirButton
                    icon={"edit"}
                    text={"Bestellung anpassen"}
                    variant={"outline-primary"}
                    size={"sm"}
                    onClick={() => updateOrderFromSummary(productType)}
                  />
                )}
              </div>
            );
          })}
          {shouldShowPickupLocationSummary() && (
            <SummaryPickupLocations
              selectedPickupLocations={selectedPickupLocations}
              waitingListModeEnabled={waitingListModeEnabled}
            />
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
