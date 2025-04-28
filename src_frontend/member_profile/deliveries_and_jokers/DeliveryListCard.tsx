import React, { useEffect, useState } from "react";
import {
  DeliveriesApi,
  Delivery,
  PickupLocation,
  PickupLocationOpeningTime,
} from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import { Card, Placeholder, Table } from "react-bootstrap";
import TapirButton from "../../components/TapirButton.tsx";
import { formatDateText } from "../../utils/formatDateText.ts";
import RelativeTime from "dayjs/plugin/relativeTime";
import dayjs from "dayjs";
import "dayjs/locale/de";
import PickupLocationModal from "./PickupLocationModal.tsx";
import ManageJokersModal from "./ManageJokersModal.tsx";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

declare let FormModal: { load: (url: string, title: string) => void };

interface DeliveryListCardProps {
  memberId: string;
  areJokersEnabled: boolean;
  csrfToken: string;
  pickupLocationModalUrl: string;
}

const DeliveryListCard: React.FC<DeliveryListCardProps> = ({
  memberId,
  areJokersEnabled,
  csrfToken,
  pickupLocationModalUrl,
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

  dayjs.extend(RelativeTime);
  dayjs.locale("de");

  useEffect(() => {
    loadDeliveries();
  }, []);

  function loadDeliveries() {
    setDeliveriesLoading(true);
    api
      .deliveriesApiMemberDeliveriesList({ memberId: memberId })
      .then(setDeliveries)
      .catch(handleRequestError)
      .finally(() => setDeliveriesLoading(false));
  }

  function loadingPlaceholder() {
    return Array.from(Array(7).keys()).map((index) => {
      return (
        <tr key={index}>
          {Array.from(Array(3).keys()).map((index) => {
            return (
              <td key={index}>
                <Placeholder lg={10} />
              </td>
            );
          })}
        </tr>
      );
    });
  }

  function dateCell(delivery: Delivery) {
    return (
      <div className={"d-flex flex-column"}>
        <strong>{formatDateText(delivery.deliveryDate)}</strong>
        <small>
          KW{dayjs(delivery.deliveryDate).week()},{" "}
          {dayjs().to(dayjs(delivery.deliveryDate))}
        </small>
      </div>
    );
  }

  function productCell(delivery: Delivery) {
    let content = <></>;
    if (delivery.isDeliveryCancelledThisWeek) {
      content = <>Keine Lieferung</>;
    } else if (delivery.jokerUsed) {
      content = <>Joker eingesetzt</>;
    } else {
      content = (
        <>
          {delivery.subscriptions.map((subscription) => {
            return (
              <div key={subscription.id}>
                {subscription.quantity}
                {" × "}
                {subscription.product.name} {subscription.product.type.name}
              </div>
            );
          })}
        </>
      );
    }

    return <div className={"d-flex flex-column"}>{content}</div>;
  }

  function pickupLocationCell(delivery: Delivery) {
    return (
      <div className={"d-flex flex-column align-items-center"}>
        <strong>{delivery.pickupLocation.name}</strong>
        <div style={{ width: "32px" }}>
          <TapirButton
            variant={"outline-secondary"}
            icon={"info"}
            size={"sm"}
            onClick={() => {
              setSelectedPickupLocation(delivery.pickupLocation);
              setSelectedPickupLocationOpeningTimes(
                delivery.pickupLocationOpeningTimes,
              );
            }}
          />
        </div>
      </div>
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
            <span className={"d-flex gap-2"}>
              {areJokersEnabled && (
                <TapirButton
                  text={"Joker verwalten"}
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
                onClick={() =>
                  FormModal.load(
                    pickupLocationModalUrl,
                    "Verteilstation ändern",
                  )
                }
              />
            </span>
          </div>
        </Card.Header>
        <Card.Body className={"p-0"}>
          <div style={{ overflowY: "scroll", maxHeight: "30em" }}>
            <Table striped hover responsive className={"text-center"}>
              <thead>
                <tr>
                  <th>Datum</th>
                  <th>Produkte</th>
                  <th>Abholort</th>
                </tr>
              </thead>
              <tbody>
                {deliveriesLoading
                  ? loadingPlaceholder()
                  : deliveries.map((delivery) => {
                      return (
                        <tr key={formatDateNumeric(delivery.deliveryDate)}>
                          <td>{dateCell(delivery)}</td>
                          <td>{productCell(delivery)}</td>
                          <td>{pickupLocationCell(delivery)}</td>
                        </tr>
                      );
                    })}
              </tbody>
            </Table>
          </div>
        </Card.Body>
      </Card>
      {selectedPickupLocation && (
        <PickupLocationModal
          pickupLocation={selectedPickupLocation}
          openingTimes={selectedPickupLocationOpeningTimes}
          onHide={() => setSelectedPickupLocation(undefined)}
        />
      )}
      {areJokersEnabled && (
        <ManageJokersModal
          show={showManageJokersModal}
          onHide={() => setShowManageJokersModal(false)}
          memberId={memberId}
          deliveries={deliveries}
          loadDeliveries={loadDeliveries}
          deliveriesLoading={deliveriesLoading}
          csrfToken={csrfToken}
        />
      )}
    </>
  );
};

export default DeliveryListCard;
