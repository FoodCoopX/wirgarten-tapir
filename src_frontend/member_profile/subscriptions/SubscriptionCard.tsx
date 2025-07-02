import React, { useState } from "react";
import { Card } from "react-bootstrap";
import "dayjs/locale/de";
import { PublicProductType, PublicSubscription } from "../../api-client";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import TapirButton from "../../components/TapirButton.tsx";
import SubscriptionEditModal from "./SubscriptionEditModal.tsx";
import { isSubscriptionActive } from "../../utils/isSubscriptionActive.ts";

interface SubscriptionCardProps {
  subscriptions: PublicSubscription[];
  productType: PublicProductType;
  memberId: string;
  reloadSubscriptions: () => void;
}

const SubscriptionCard: React.FC<SubscriptionCardProps> = ({
  subscriptions,
  productType,
  memberId,
  reloadSubscriptions,
}) => {
  const [showEditModal, setShowEditModal] = useState(false);

  return (
    <>
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
                    (sum, subscription) =>
                      isSubscriptionActive(subscription)
                        ? sum + subscription.monthlyPrice
                        : sum,
                    0,
                  ),
                )}
              </strong>
              <small> / Monat</small>
            </span>
            <TapirButton
              variant={"outline-primary"}
              icon={subscriptions.length == 0 ? "add" : "contract_edit"}
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
        reloadSubscriptions={reloadSubscriptions}
      />
    </>
  );
};

export default SubscriptionCard;
