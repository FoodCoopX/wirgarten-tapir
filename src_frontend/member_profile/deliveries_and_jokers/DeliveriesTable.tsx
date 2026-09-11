import dayjs from "dayjs";
import "dayjs/locale/de";
import RelativeTime from "dayjs/plugin/relativeTime";
import WeekOfYear from "dayjs/plugin/weekOfYear";
import React from "react";
import { Table } from "react-bootstrap";
import {
  Delivery,
  PickupLocation,
  PickupLocationOpeningTime,
} from "../../api-client";
import PlaceholderTableRows from "../../components/PlaceholderTableRows.tsx";
import TapirButton from "../../components/TapirButton.tsx";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import { formatDateText } from "../../utils/formatDateText.ts";

interface DeliveriesTableProps {
  deliveriesLoading: boolean;
  deliveries: Delivery[];
  setSelectedPickupLocation: React.Dispatch<
    React.SetStateAction<PickupLocation | undefined>
  >;
  setSelectedPickupLocationOpeningTimes: React.Dispatch<
    React.SetStateAction<PickupLocationOpeningTime[]>
  >;
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
  let content;
  if (delivery.isDeliveryCancelledThisWeek) {
    content = <>Keine Lieferung</>;
  } else if (delivery.jokerUsed) {
    content = <>Joker eingesetzt</>;
  } else if (delivery.donationUsed) {
    content = <>Lieferung gespendet</>;
  } else {
    content = (
      <>
        {delivery.subscriptions.map((subscription) => {
          return (
            <div key={subscription.id}>
              {subscription.quantity}
              {" × "}
              {subscription.product.name}
            </div>
          );
        })}
      </>
    );
  }

  return <div className={"d-flex flex-column"}>{content}</div>;
}

const DeliveriesTable: React.FC<DeliveriesTableProps> = ({
  deliveries,
  deliveriesLoading,
  setSelectedPickupLocation,
  setSelectedPickupLocationOpeningTimes,
}) => {
  dayjs.extend(RelativeTime);
  dayjs.extend(WeekOfYear);
  dayjs.locale("de");

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
    <div style={{ overflowY: "scroll", maxHeight: "30em" }}>
      {!deliveriesLoading && deliveries.length === 0 ? (
        <p className={"text-center mb-0"}>Keine Abholungen</p>
      ) : (
        <Table striped hover responsive className={"text-center"}>
          <thead>
            <tr>
              <th>Datum</th>
              <th>Produkte</th>
              <th>Abholort</th>
            </tr>
          </thead>
          <tbody>
            {deliveriesLoading ? (
              <PlaceholderTableRows nbColumns={3} nbRows={7} size={"lg"} />
            ) : (
              deliveries.map((delivery) => {
                return (
                  <tr key={formatDateNumeric(delivery.deliveryDate)}>
                    <td>{dateCell(delivery)}</td>
                    <td>{productCell(delivery)}</td>
                    <td>{pickupLocationCell(delivery)}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </Table>
      )}
    </div>
  );
};

export default DeliveriesTable;
