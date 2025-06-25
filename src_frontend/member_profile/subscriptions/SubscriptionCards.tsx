import React, { useEffect, useState } from "react";
import "dayjs/locale/de";
import { PublicSubscription, SubscriptionsApi } from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import SubscriptionCard from "./SubscriptionCard.tsx";

interface SubscriptionCardsProps {
  memberId: string;
  csrfToken: string;
}

const SubscriptionCards: React.FC<SubscriptionCardsProps> = ({
  memberId,
  csrfToken,
}) => {
  const api = useApi(SubscriptionsApi, csrfToken);
  const [subscriptions, setSubscriptions] = useState<PublicSubscription[]>([]);
  const [productTypes, setProductTypes] = useState<{ [id: string]: string }>(
    {},
  );
  const [subscriptionsLoading, setSubscriptionsLoading] = useState(true);

  useEffect(() => {
    setSubscriptionsLoading(true);
    api
      .subscriptionsApiMemberSubscriptionsList({ memberId: memberId })
      .then((subscriptions) => {
        setSubscriptions(subscriptions);
        setProductTypes(
          Object.fromEntries(
            subscriptions.map((subscription) => [
              subscription.productTypeId,
              subscription.productTypeName,
            ]),
          ),
        );
      })
      .catch(handleRequestError)
      .finally(() => setSubscriptionsLoading(false));
  }, []);

  return (
    <>
      {Object.entries(productTypes).map(([productTypeId, productTypeName]) => (
        <SubscriptionCard
          key={productTypeId}
          subscriptions={subscriptions.filter(
            (subscription) => subscription.productTypeId == productTypeId,
          )}
          productTypeName={productTypeName}
        />
      ))}
    </>
  );
};

export default SubscriptionCards;
