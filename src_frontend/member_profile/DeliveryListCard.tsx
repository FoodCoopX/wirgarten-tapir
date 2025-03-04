import React, { useEffect, useState } from "react";
import { Delivery, Joker, JokersApi } from "../api-client";
import { useApi } from "../hooks/useApi";
import { Card, Spinner, Table } from "react-bootstrap";
import TapirButton from "../components/TapirButton.tsx";
import { formatDateText } from "../utils/formatDateText.ts";
import RelativeTime from "dayjs/plugin/relativeTime";
import dayjs from "dayjs";
import "dayjs/locale/de";

interface DeliveryListCardProps {
  memberId: string;
}

const DeliveryListCard: React.FC<DeliveryListCardProps> = ({ memberId }) => {
  const api = useApi(JokersApi);
  const [jokers, setJokers] = useState<Joker[]>([]);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [deliveriesLoading, setDeliveriesLoading] = useState(false);

  dayjs.extend(RelativeTime);
  dayjs.locale("de");

  useEffect(() => {
    api
      .jokersApiMemberJokersList({ memberId: memberId })
      .then(setJokers)
      .catch((error) => alert(error));

    setDeliveriesLoading(true);
    api
      .jokersApiMemberDeliveriesList({ memberId: memberId })
      .then(setDeliveries)
      .catch((error) => alert(error))
      .finally(() => setDeliveriesLoading(false));
  }, []);

  return (
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
      <Card.Body>
        {deliveriesLoading ? (
          <Spinner />
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
              {deliveries.map((delivery, index) => {
                return (
                  <tr key={index}>
                    <td>
                      <div className={"d-flex flex-column"}>
                        <strong>{formatDateText(delivery.deliveryDate)}</strong>
                        <small>
                          {dayjs().to(dayjs(delivery.deliveryDate))}
                        </small>
                      </div>
                    </td>
                    <td></td>
                    <td></td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        )}
      </Card.Body>
    </Card>
  );
};

export default DeliveryListCard;
