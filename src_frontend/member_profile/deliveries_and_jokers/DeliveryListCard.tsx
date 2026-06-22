import dayjs from "dayjs";
import "dayjs/locale/de";
import RelativeTime from "dayjs/plugin/relativeTime";
import WeekOfYear from "dayjs/plugin/weekOfYear";
import React, { useEffect, useState } from "react";
import { Card, Spinner } from "react-bootstrap";
import {
  DeliveriesApi,
  Delivery,
  PickupLocation,
  PickupLocationOpeningTime,
} from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import DeliveriesTable from "./DeliveriesTable.tsx";
import ManageJokersAndDonationsModal from "./ManageJokersAndDonationsModal.tsx";
import PickupLocationChangeModal from "./PickupLocationChangeModal.tsx";
import PickupLocationDeliveryDetailsModal from "./PickupLocationDeliveryDetailsModal.tsx";

interface DeliveryListCardProps {
  memberId: string;
  areJokersEnabled: boolean;
  areDonationsEnabled: boolean;
  csrfToken: string;
}

const DeliveryListCard: React.FC<DeliveryListCardProps> = ({
  memberId,
  areJokersEnabled,
  areDonationsEnabled,
  csrfToken,
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
  const [showManageJokersModal, setShowManageJokersModal] = useState(false);
  const [showPickupLocationChangeModal, setShowPickupLocationChangeModal] =
    useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  dayjs.extend(RelativeTime);
  dayjs.extend(WeekOfYear);
  dayjs.locale("de");

  useEffect(() => {
    loadDeliveries();
  }, []);

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

  function getJokerButtonText() {
    if (areJokersEnabled && areDonationsEnabled) {
      return "Joker & Spende";
    }

    if (areJokersEnabled) {
      return "Joker";
    }

    if (areDonationsEnabled) {
      return "Spenden";
    }

    return "Feature disabled";
  }

  function getHeaderButtons() {
    if (deliveriesLoading) {
      return <Spinner />;
    }

    if (deliveries.length === 0) {
      return null;
    }

    return (
      <span className={"d-flex gap-2"}>
        {(areJokersEnabled || areDonationsEnabled) && (
          <TapirButton
            text={getJokerButtonText()}
            icon={"free_cancellation"}
            variant={"outline-primary"}
            onClick={() => {
              setShowManageJokersModal(true);
            }}
          />
        )}
        <TapirButton
          text={"Verteilstation ändern"}
          icon={"edit"}
          variant={"outline-primary"}
          onClick={() => setShowPickupLocationChangeModal(true)}
        />
      </span>
    );
  }

  return (
    <>
      <Card style={{ marginBottom: "1rem" }}>
        <Card.Header>
          <div
            className={"d-flex justify-content-between align-items-center mb-0"}
          >
            <h5 className={"mb-0"}>Abholung</h5>
            {getHeaderButtons()}
          </div>
        </Card.Header>
        <Card.Body className={deliveries.length > 0 ? "p-0" : ""}>
          <DeliveriesTable
            deliveries={deliveries}
            deliveriesLoading={deliveriesLoading}
            setSelectedPickupLocation={setSelectedPickupLocation}
            setSelectedPickupLocationOpeningTimes={
              setSelectedPickupLocationOpeningTimes
            }
          />
        </Card.Body>
      </Card>
      {selectedPickupLocation && (
        <PickupLocationDeliveryDetailsModal
          pickupLocation={selectedPickupLocation}
          openingTimes={selectedPickupLocationOpeningTimes}
          onHide={() => setSelectedPickupLocation(undefined)}
        />
      )}
      {(areJokersEnabled || areDonationsEnabled) && (
        <ManageJokersAndDonationsModal
          show={showManageJokersModal}
          onHide={() => setShowManageJokersModal(false)}
          memberId={memberId}
          deliveries={deliveries}
          loadDeliveries={loadDeliveries}
          deliveriesLoading={deliveriesLoading}
          csrfToken={csrfToken}
          setToastDatas={setToastDatas}
          areDonationsEnabled={areDonationsEnabled}
          areJokersEnabled={areJokersEnabled}
        />
      )}
      <PickupLocationChangeModal
        onHide={() => setShowPickupLocationChangeModal(false)}
        show={showPickupLocationChangeModal}
        csrfToken={csrfToken}
        memberId={memberId}
        reloadDeliveries={loadDeliveries}
        setToastDatas={setToastDatas}
      />
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default DeliveryListCard;
