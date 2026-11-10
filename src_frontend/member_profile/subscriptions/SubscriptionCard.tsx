import React from "react";
import { Card } from "react-bootstrap";
import "dayjs/locale/de";
import { PublicProductType, PublicSubscription } from "../../api-client";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import TapirButton from "../../components/TapirButton.tsx";
import TapirHelpButton from "../../components/TapirHelpButton.tsx";
import { isSubscriptionActive } from "../../utils/isSubscriptionActive.ts";

interface SubscriptionCardProps {
  subscriptions: PublicSubscription[];
  productType: PublicProductType;
  bestellWizardUrl: string;
  showContractEdit: boolean;
  contactEmail: string;
  adminVersion: boolean;
}

const SubscriptionCard: React.FC<SubscriptionCardProps> = ({
  subscriptions,
  productType,
  bestellWizardUrl,
  showContractEdit,
  contactEmail,
  adminVersion,
}) => {
  function buildHelpText() {
    if (adminVersion) {
      return (
        <p className={"mb-0"}>
          Beachte: Das Mitglied kann seine Vertragskonstellation ändern, solange
          sie insgesamt nicht kleiner wird als die bisherige. Nur du als Admin
          kannst die Anteile insgesamt reduzieren.
        </p>
      );
    }
    return (
      <p className={"mb-0"}>
        Beachte: Du kannst deine Vertragskonstellation ändern, solange sie
        insgesamt nicht kleiner wird als deine bisherige. Du kannst zum Beispiel
        einen größeren Anteil gegen mehrere kleinere tauschen, wenn sie zusammen
        mindestens gleich groß sind. Möchtest du deine Anteile insgesamt
        reduzieren, wende dich bitte an die Verwaltung (
        <a href={"mailto:" + contactEmail}>{contactEmail}</a>).
      </p>
    );
  }

  return (
    <Card>
      <Card.Body>
        <div className={"contract-tile-number"}>
          <strong>
            {subscriptions.reduce(
              (sum, subscription) =>
                isSubscriptionActive(subscription)
                  ? sum + subscription.quantity
                  : sum,
              0,
            )}
          </strong>
          {" ×"}
        </div>
        <strong>{productType.name}</strong>
        {subscriptions.length > 0 && (
          <>
            <hr />
            <small className={"d-flex flex-column"}>
              {subscriptions.map((subscription) => (
                <span
                  className={
                    "d-flex flex-column " +
                    (isSubscriptionActive(subscription)
                      ? ""
                      : "fw-light text-secondary")
                  }
                  key={subscription.productId}
                >
                  <span>
                    <strong>{subscription.quantity}</strong>
                    {" × "}
                    {subscription.productName}{" "}
                  </span>
                  <span>
                    {formatDateNumeric(subscription.startDate)}
                    {subscription.endDate && (
                      <>
                        {" - "}
                        {formatDateNumeric(subscription.endDate)}
                      </>
                    )}
                  </span>
                </span>
              ))}
            </small>
          </>
        )}
      </Card.Body>
      <Card.Footer>
        <div
          className={
            "d-flex flex-row justify-content-between align-items-center"
          }
        >
          <span>
            <strong>
              {formatCurrency(
                subscriptions.reduce(
                  (sum, subscription) =>
                    isSubscriptionActive(subscription)
                      ? sum + subscription.monthlyPrice
                      : sum,
                  0,
                ),
              )}
            </strong>
            <small>
              {" "}
              / {productType.pricePerDelivery ? "Lieferung" : "Monat"}
            </small>
          </span>
          {showContractEdit && (
            <div className={"d-flex flex-row gap-2"}>
              <TapirHelpButton text={buildHelpText()} />
              <TapirButton
                variant={"outline-primary"}
                icon={subscriptions.length == 0 ? "add" : "contract_edit"}
                onClick={() => {
                  location.assign(bestellWizardUrl);
                }}
              />
            </div>
          )}
        </div>
      </Card.Footer>
    </Card>
  );
};

export default SubscriptionCard;
