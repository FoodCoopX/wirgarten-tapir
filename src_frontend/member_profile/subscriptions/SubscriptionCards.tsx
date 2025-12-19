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
import { sortProductTypes } from "../../bestell_wizard/utils/sortProductTypes.ts";

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
  const [loading, setLoading] = useState(true);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [bestellWizardUrlTemplate, setBestellWizardUrlTemplate] = useState("");

  useEffect(() => {
    loadSubscriptions();
  }, []);

  function loadSubscriptions() {
    setLoading(true);
    api
      .subscriptionsApiMemberSubscriptionDataRetrieve({ memberId: memberId })
      .then((response) => {
        setProductTypes(sortProductTypes(response.productTypes));
        setSubscriptions(response.subscriptions);
        setBestellWizardUrlTemplate(response.bestellWizardUrlTemplate);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Verträge",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }

  return (
    <>
      {loading ? (
        <Spinner />
      ) : (
        productTypes.map((productType) => (
          <SubscriptionCard
            key={productType.id}
            subscriptions={subscriptions.filter(
              (subscription) => subscription.productType.id === productType.id,
            )}
            productType={productType}
            bestellWizardUrl={bestellWizardUrlTemplate.replace(
              "product_type_id",
              productType.id!,
            )}
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
