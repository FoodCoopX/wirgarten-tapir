import React, { useEffect, useState } from "react";
import {
  Delivery,
  JokersApi,
  PickupLocation,
  PickupLocationOpeningTime,
} from "../api-client";
import { useApi } from "../hooks/useApi";
import { Card, Placeholder, Table } from "react-bootstrap";
import TapirButton from "../components/TapirButton.tsx";
import { formatDateText } from "../utils/formatDateText.ts";
import RelativeTime from "dayjs/plugin/relativeTime";
import dayjs from "dayjs";
import "dayjs/locale/de";
import PickupLocationModal from "./PickupLocationModal.tsx";

interface DeliveryListCardProps {
  memberId: string;
}

const DeliveryListCard: React.FC<DeliveryListCardProps> = ({ memberId }) => {
  const api = useApi(JokersApi);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [deliveriesLoading, setDeliveriesLoading] = useState(false);
  const [selectedPickupLocation, setSelectedPickupLocation] =
    useState<PickupLocation>();
  const [
    selectedPickupLocationOpeningTimes,
    setSelectedPickupLocationOpeningTimes,
  ] = useState<PickupLocationOpeningTime[]>([]);

  dayjs.extend(RelativeTime);
  dayjs.locale("de");

  useEffect(() => {
    setDeliveriesLoading(true);
    api
      .jokersApiMemberDeliveriesList({ memberId: memberId })
      .then(setDeliveries)
      .catch((error) => alert(error))
      .finally(() => setDeliveriesLoading(false));
  }, []);

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
        <small>{dayjs().to(dayjs(delivery.deliveryDate))}</small>
      </div>
    );
  }

  function productCell(delivery: Delivery) {
    return (
      <div className={"d-flex flex-column"}>
        {delivery.jokerUsed
          ? "Joker eingesetzt"
          : delivery.subscriptions.map((subscription) => {
              return (
                <div key={subscription.id}>
                  {subscription.quantity}
                  {" × "}
                  {subscription.product.name} {subscription.product.type.name}
                </div>
              );
            })}
      </div>
    );
  }

  function pickupLocationCell(delivery: Delivery) {
    return (
      <div className={"d-flex flex-column align-items-center"}>
        <strong>{delivery.pickupLocation.name}</strong>
        <div style={{ width: "32px" }}>
          <TapirButton
            variant={"outline-secondary"}
            icon={"schedule"}
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
      <Card>
        <Card.Header>
          <div
            className={"d-flex justify-content-between align-items-center mb-0"}
          >
            <h5 className={"mb-0"}>Abholung</h5>
            <TapirButton
              text={"Bearbeiten"}
              icon={"edit"}
              variant={"outline-primary"}
            />
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
                  : deliveries.map((delivery, index) => {
                      return (
                        <tr key={index}>
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
    </>
  );
};

export default DeliveryListCard;
