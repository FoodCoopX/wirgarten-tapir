import React, { useEffect, useState } from "react";
import "dayjs/locale/de";
import {
  PublicProductType,
  PublicSubscription,
  SubscriptionsApi,
} from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import SubscriptionCard from "./SubscriptionCard.tsx";
import { Spinner } from "react-bootstrap";

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
  const [productTypes, setProductTypes] = useState<PublicProductType[]>([]);
  const [subscriptionsLoading, setSubscriptionsLoading] = useState(true);

  useEffect(() => {
    setSubscriptionsLoading(true);
    api
      .subscriptionsApiMemberSubscriptionsList({ memberId: memberId })
      .then((subscriptions) => {
        setSubscriptions(subscriptions);
        setProductTypes([
          ...new Set(
            subscriptions.map((subscription) => subscription.productType),
          ),
        ]);
      })
      .catch(handleRequestError)
      .finally(() => setSubscriptionsLoading(false));
  }, []);

  return (
    <>
      {subscriptionsLoading ? (
        <Spinner />
      ) : (
        productTypes.map((productType) => (
          <SubscriptionCard
            key={productType.id}
            subscriptions={subscriptions.filter(
              (subscription) => subscription.productType === productType,
            )}
            productType={productType}
          />
        ))
      )}
    </>
  );
};

export default SubscriptionCards;
