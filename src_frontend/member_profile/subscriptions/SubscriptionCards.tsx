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
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { ToastData } from "../../types/ToastData.ts";

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
  const [productTypesLoading, setProductTypesLoading] = useState(true);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  useEffect(() => {
    setProductTypesLoading(true);
    api
      .subscriptionsPublicProductTypesList()
      .then(setProductTypes)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Produkte",
          setToastDatas,
        ),
      )
      .finally(() => setProductTypesLoading(false));

    loadSubscriptions();
  }, []);

  function loadSubscriptions() {
    setSubscriptionsLoading(true);
    api
      .subscriptionsApiMemberSubscriptionsList({ memberId: memberId })
      .then((subscriptions) => {
        setSubscriptions(subscriptions);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Verträge",
          setToastDatas,
        ),
      )
      .finally(() => setSubscriptionsLoading(false));
  }

  return (
    <>
      {subscriptionsLoading || productTypesLoading ? (
        <Spinner />
      ) : (
        productTypes.map((productType) => (
          <SubscriptionCard
            key={productType.id}
            subscriptions={subscriptions.filter(
              (subscription) => subscription.productType.id === productType.id,
            )}
            productType={productType}
            memberId={memberId}
            reloadSubscriptions={loadSubscriptions}
            setToastDatas={setToastDatas}
          />
        ))
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default SubscriptionCards;
