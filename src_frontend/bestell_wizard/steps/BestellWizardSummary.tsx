import React, { Fragment } from "react";
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
import { BestellWizardSettings } from "../types/BestellWizardSettings.ts";
import { formatShoppingCart } from "../utils/formatShoppingCart.ts";
import { doesProductBelongsToProductType } from "../utils/doesProductBelongToProductType.ts";

interface BestellWizardSummaryProps {
  shoppingCartOrder: ShoppingCart;
  shoppingCartWaitingList: ShoppingCart;
  selectedNumberOfCoopShares: number;
  selectedPickupLocations: PublicPickupLocation[];
  firstDeliveryDatesByProductType: { [key: string]: Date };
  updateOrderFromSummary: (productType: PublicProductType) => void;
  waitingListModeEnabled: boolean;
  cancellationPolicyRead: boolean;
  setCancellationPolicyRead: (read: boolean) => void;
  privacyPolicyRead: boolean;
  setPrivacyPolicyRead: (read: boolean) => void;
  waitingListEntryDetails: WaitingListEntryDetails | undefined;
  contractStartDate: Date;
  settings: BestellWizardSettings;
  becomeMemberNow: boolean | null;
}

const BestellWizardSummary: React.FC<BestellWizardSummaryProps> = ({
  shoppingCartOrder,
  shoppingCartWaitingList,
  selectedNumberOfCoopShares,
  selectedPickupLocations,
  firstDeliveryDatesByProductType,
  updateOrderFromSummary,
  waitingListModeEnabled,
  cancellationPolicyRead,
  setCancellationPolicyRead,
  privacyPolicyRead,
  setPrivacyPolicyRead,
  waitingListEntryDetails,
  contractStartDate,
  settings,
  becomeMemberNow,
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

  function buildProductTypeSummary(productType: PublicProductType) {
    if (isProductTypeOrdered(productType, shoppingCartOrder)) {
      return (
        <SummaryProductTypeTable
          productType={productType}
          firstDeliveryDatesByProductType={firstDeliveryDatesByProductType}
          shoppingCart={shoppingCartOrder}
          waitingListModeEnabled={waitingListModeEnabled}
          contractStartDate={contractStartDate}
        />
      );
    }

    if (isProductTypeOrdered(productType, shoppingCartWaitingList)) {
      return (
        <span>
          Du wirst auf der Warteliste eingetragen für:{" "}
          {formatShoppingCart(
            Object.fromEntries(
              Object.entries(shoppingCartWaitingList).filter(([productId, _]) =>
                doesProductBelongsToProductType(productId, productType),
              ),
            ),
            settings,
          )}
        </span>
      );
    }

    return <span>Dieses Produkt ist nicht bestellt worden</span>;
  }

  return (
    <>
      <Row>
        <Col>
          {shouldIncludeStepCoopShares(
            waitingListEntryDetails,
            waitingListModeEnabled,
            becomeMemberNow,
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
                      {formatCurrency(settings.priceOfAShare)} ={" "}
                      {formatCurrency(
                        settings.priceOfAShare * selectedNumberOfCoopShares,
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
          {settings.productTypes.map((productType) => {
            if (
              waitingListEntryDetails !== undefined &&
              !isProductTypeOrdered(productType, shoppingCartOrder)
            ) {
              return null;
            }
            return (
              <div className={"mt-4"} key={productType.id}>
                <BestellWizardCardSubtitle text={productType.name} />
                {buildProductTypeSummary(productType)}
                {waitingListEntryDetails !== undefined && (
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
      <Row className={"mt-2"}>
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
                <span
                  dangerouslySetInnerHTML={{
                    __html: settings.revocationRightsExplanation,
                  }}
                />
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
