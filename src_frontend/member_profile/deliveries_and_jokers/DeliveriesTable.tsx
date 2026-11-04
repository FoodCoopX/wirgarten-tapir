import dayjs from "dayjs";
import "dayjs/locale/de";
import RelativeTime from "dayjs/plugin/relativeTime";
import WeekOfYear from "dayjs/plugin/weekOfYear";
import React, { useState } from "react";
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
  pickupLocationLabel?: string;
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
            <div
              key={subscription.id}
              style={{
                textWrapMode: "wrap",
              }}
            >
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

const NB_DELIVERIES_SHOWN_BY_DEFAULT = 3;

const DeliveriesTable: React.FC<DeliveriesTableProps> = ({
  deliveries,
  deliveriesLoading,
  pickupLocationLabel = "Abholort",
  setSelectedPickupLocation,
  setSelectedPickupLocationOpeningTimes,
}) => {
  const [showAll, setShowAll] = useState(false);

  dayjs.extend(RelativeTime);
  dayjs.extend(WeekOfYear);
  dayjs.locale("de");

  const visibleDeliveries = showAll
    ? deliveries
    : deliveries.slice(0, NB_DELIVERIES_SHOWN_BY_DEFAULT);

  function pickupLocationCell(delivery: Delivery) {
    return (
      <div className={"d-flex flex-column align-items-center"}>
        <strong className={"text-break"}>{delivery.pickupLocation.name}</strong>
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
    <div>
      <div style={showAll ? { overflowY: "auto", maxHeight: "30em" } : {}}>
        {!deliveriesLoading && deliveries.length === 0 ? (
          <p className={"text-center mb-0"}>Keine Abholungen</p>
        ) : (
          <Table striped hover responsive size={"sm"} className={"text-center"}>
            <thead>
              <tr>
                <th>Datum</th>
                <th>Produkte</th>
                <th>{pickupLocationLabel}</th>
              </tr>
            </thead>
            <tbody>
              {deliveriesLoading ? (
                <PlaceholderTableRows nbColumns={3} nbRows={7} size={"lg"} />
              ) : (
                visibleDeliveries.map((delivery) => {
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
      {deliveries.length > NB_DELIVERIES_SHOWN_BY_DEFAULT && (
        <div className={"text-center p-2"}>
          <TapirButton
            variant={"outline-secondary"}
            size={"sm"}
            icon={showAll ? "expand_less" : "expand_more"}
            text={showAll ? "Weniger anzeigen" : `Alle anzeigen`}
            onClick={() => setShowAll(!showAll)}
          />
        </div>
      )}
    </div>
  );
};

export default DeliveriesTable;
