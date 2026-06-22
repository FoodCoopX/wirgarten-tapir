import React, { useEffect, useState } from "react";
import { Modal } from "react-bootstrap";
import {
  DeliveriesApi,
  Delivery,
  PickupLocation,
  PickupLocationOpeningTime,
} from "../api-client";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import DeliveriesTable from "../member_profile/deliveries_and_jokers/DeliveriesTable.tsx";
import PickupLocationDeliveryDetailsModal from "../member_profile/deliveries_and_jokers/PickupLocationDeliveryDetailsModal.tsx";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface DeliveryListModalProps {
  memberId: string;
  csrfToken: string;
  show: boolean;
  onHide: () => void;
}

const DeliveryListModal: React.FC<DeliveryListModalProps> = ({
  memberId,
  csrfToken,
  show,
  onHide,
}) => {
  const api = useApi(DeliveriesApi, csrfToken);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [deliveriesLoading, setDeliveriesLoading] = useState(false);
  const [selectedPickupLocation, setSelectedPickupLocation] =
    useState<PickupLocation>();
  const [
    selectedPickupLocationOpeningTimes,
    setSelectedPickupLocationOpeningTimes,
  ] = useState<PickupLocationOpeningTime[]>([]);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  useEffect(() => {
    loadDeliveries();
  }, [memberId]);

  function loadDeliveries() {
    setDeliveriesLoading(true);
    api
      .deliveriesApiMemberDeliveriesList({ memberId: memberId })
      .then(setDeliveries)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Lieferungen",
          setToastDatas,
        ),
      )
      .finally(() => setDeliveriesLoading(false));
  }

  return (
    <>
      <Modal
        style={{ marginBottom: "1rem" }}
        show={show && !selectedPickupLocation}
        size={"lg"}
        centered={true}
        onHide={onHide}
      >
        <Modal.Header closeButton={true}>
          <div
            className={"d-flex justify-content-between align-items-center mb-0"}
          >
            <h5 className={"mb-0"}>Abholung</h5>
          </div>
        </Modal.Header>
        <Modal.Body className={deliveries.length > 0 ? "p-0" : ""}>
          <DeliveriesTable
            deliveries={deliveries}
            deliveriesLoading={deliveriesLoading}
            setSelectedPickupLocation={setSelectedPickupLocation}
            setSelectedPickupLocationOpeningTimes={
              setSelectedPickupLocationOpeningTimes
            }
          />
        </Modal.Body>
      </Modal>
      {selectedPickupLocation && (
        <PickupLocationDeliveryDetailsModal
          pickupLocation={selectedPickupLocation}
          openingTimes={selectedPickupLocationOpeningTimes}
          onHide={() => setSelectedPickupLocation(undefined)}
        />
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default DeliveryListModal;
