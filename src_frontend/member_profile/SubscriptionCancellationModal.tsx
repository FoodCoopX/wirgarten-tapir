import React, { useEffect, useState } from "react";
import { Modal, Spinner } from "react-bootstrap";
import { SubscriptionsApi } from "../api-client";
import { useApi } from "../hooks/useApi.ts";
import "dayjs/locale/de";
import { formatDateText } from "../utils/formatDateText.ts";
import TapirButton from "../components/TapirButton.tsx";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import ConfirmModal from "../components/ConfirmModal.tsx";

interface SubscriptionCancellationModalProps {
  onHide: () => void;
  show: boolean;
  memberId: string;
  productTypeName: string;
  csrfToken: string;
}

const SubscriptionCancellationModal: React.FC<
  SubscriptionCancellationModalProps
> = ({ onHide, show, memberId, productTypeName, csrfToken }) => {
  const api = useApi(SubscriptionsApi, csrfToken);
  const [isInTrial, setIsInTrial] = useState(false);
  const [subscriptionEndDate, setSubscriptionEndDate] = useState<Date>();
  const [dataLoading, setDataLoading] = useState(true);
  const [showConfirmationModal, setShowConfirmationModal] = useState(false);

  useEffect(() => {
    setDataLoading(true);
    api
      .subscriptionsCancellationDataRetrieve({
        memberId: memberId,
        productTypeName: productTypeName,
      })
      .then((data) => {
        setIsInTrial(data.isInTrial);
        setSubscriptionEndDate(data.subscriptionEndDate);
      })
      .catch(alert)
      .finally(() => setDataLoading(false));
  }, []);

  function getModalBody() {
    if (dataLoading) return <Spinner />;

    if (isInTrial) {
      return (
        <p>
          Dieses Vertrag ist noch in der Probezeit. Um es zu kündigen, nutz
          bitte das dediziertes Knopf.
        </p>
      );
    }

    return (
      <>
        <p>
          Du kannst deine {productTypeName} zum{" "}
          {formatDateText(subscriptionEndDate)} kündigen.
        </p>
        <p>
          Möchtest du vor der Kündigungsfrist deinen Vertrag beenden,
          kontaktiere bitte unser Verwaltungsteam{" "}
          <a href={"mailto:verwaltung@biotop-oberland.de"}>
            verwaltung@biotop-oberland.de
          </a>{" "}
          (Mailadresse der Verwaltung)
        </p>
      </>
    );
  }
  return (
    <>
      <Modal
        onHide={onHide}
        show={show && !showConfirmationModal}
        centered={true}
      >
        <Modal.Header closeButton>
          <Modal.Title>
            <h4>Vertrag kündigen: {productTypeName}</h4>
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>{getModalBody()}</Modal.Body>
        {!dataLoading && !isInTrial && (
          <Modal.Footer>
            <TapirButton
              variant={"outline-danger"}
              icon={"contract_delete"}
              text={
                "Zum " + formatDateNumeric(subscriptionEndDate) + " kündigen"
              }
              onClick={() => setShowConfirmationModal(true)}
            />
          </Modal.Footer>
        )}
      </Modal>
      <ConfirmModal
        message={
          "Bist du zischer das du zum " +
          formatDateNumeric(subscriptionEndDate) +
          " kündigen willst?"
        }
        onCancel={() => setShowConfirmationModal(false)}
        confirmButtonIcon={"contract_delete"}
        confirmButtonText={
          "Zum " + formatDateNumeric(subscriptionEndDate) + " kündigen"
        }
        confirmButtonVariant={"danger"}
        open={showConfirmationModal}
        title={"Vertrag kündigen: " + productTypeName}
        onConfirm={() => {
          alert("YOYO");
          setShowConfirmationModal(false);
        }}
      ></ConfirmModal>
    </>
  );
};

export default SubscriptionCancellationModal;
