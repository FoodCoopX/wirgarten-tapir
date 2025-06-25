import React from "react";
import { Card } from "react-bootstrap";
import "dayjs/locale/de";
import { PublicSubscription } from "../../api-client";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";

interface SubscriptionCardProps {
  subscriptions: PublicSubscription[];
  productTypeName: string;
}

const SubscriptionCard: React.FC<SubscriptionCardProps> = ({
  subscriptions,
  productTypeName,
}) => {
  return (
    <Card style={{ marginBottom: "1rem" }}>
      <Card.Body>
        <div className={"contract-tile-number"}>
          <strong>
            {subscriptions.reduce(
              (sum, subscription) => sum + subscription.quantity,
              0,
            )}
          </strong>
          {" ×"}
        </div>
        <strong>{productTypeName}</strong>
        <hr />
        <small className={"d-flex flex-column"}>
          {subscriptions.map((subscription) => (
            <span className={"d-flex flex-column"}>
              <span>
                <strong>{subscription.quantity}</strong>
                {" × "}
                {subscription.productName}{" "}
                {subscription.solidarityDisplay && (
                  <>({subscription.solidarityDisplay})</>
                )}
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
      </Card.Body>
      <Card.Footer>
        <strong>
          {formatCurrency(
            subscriptions.reduce(
              (sum, subscription) => sum + subscription.monthlyPrice,
              0,
            ),
          )}
        </strong>
        <small> / Monat</small>
      </Card.Footer>
    </Card>
  );
};

export default SubscriptionCard;
