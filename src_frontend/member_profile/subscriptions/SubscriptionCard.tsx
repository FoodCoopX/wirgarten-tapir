import React, { useState } from "react";
import { Card } from "react-bootstrap";
import "dayjs/locale/de";
import { PublicProductType, PublicSubscription } from "../../api-client";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import TapirButton from "../../components/TapirButton.tsx";
import SubscriptionEditModal from "./SubscriptionEditModal.tsx";

interface SubscriptionCardProps {
  subscriptions: PublicSubscription[];
  productType: PublicProductType;
  memberId: string;
}

const SubscriptionCard: React.FC<SubscriptionCardProps> = ({
  subscriptions,
  productType,
  memberId,
}) => {
  const [showEditModal, setShowEditModal] = useState(false);

  return (
    <>
      <Card>
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
          <strong>{productType.name}</strong>
          <hr />
          <small className={"d-flex flex-column"}>
            {subscriptions.map((subscription) => (
              <span
                className={"d-flex flex-column"}
                key={subscription.productId}
              >
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
          <div
            className={
              "d-flex flex-row justify-content-between align-items-center"
            }
          >
            <span>
              <strong>
                {formatCurrency(
                  subscriptions.reduce(
                    (sum, subscription) => sum + subscription.monthlyPrice,
                    0,
                  ),
                )}
              </strong>
              <small> / Monat</small>
            </span>
            <TapirButton
              variant={"outline-primary"}
              icon={"edit"}
              onClick={() => setShowEditModal(true)}
            />
          </div>
        </Card.Footer>
      </Card>
      <SubscriptionEditModal
        show={showEditModal}
        onHide={() => setShowEditModal(false)}
        subscriptions={subscriptions}
        productType={productType}
        memberId={memberId}
      />
    </>
  );
};

export default SubscriptionCard;
