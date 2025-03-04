import React, { useEffect, useState } from "react";
import { Delivery, Joker, JokersApi } from "../api-client";
import { useApi } from "../hooks/useApi";
import { Card } from "react-bootstrap";
import TapirButton from "../components/TapirButton.tsx";
import { formatDate } from "../utils/formatDate.ts";

interface DeliveryListCardProps {
  memberId: string;
}

const DeliveryListCard: React.FC<DeliveryListCardProps> = ({ memberId }) => {
  const api = useApi(JokersApi);
  const [jokers, setJokers] = useState<Joker[]>([]);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);

  useEffect(() => {
    api
      .jokersApiMemberJokersList({ memberId: memberId })
      .then(setJokers)
      .catch((error) => alert(error));

    api
      .jokersApiMemberDeliveriesList({ memberId: memberId })
      .then(setDeliveries)
      .catch((error) => alert(error));
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
        <div>
          <h2>Jokers</h2>
          <ul>
            {jokers.map((joker, index) => {
              return (
                <li key={index}>
                  Joker {index}: {formatDate(joker.date)}
                </li>
              );
            })}
          </ul>
          <h2>Deliveries</h2>
          <ul>
            {deliveries.map((delivery, index) => {
              return (
                <li key={index}>
                  <div>Delivery {index}: </div>
                  <ul>
                    <li>{formatDate(delivery.deliveryDate)}</li>
                    <li>
                      Subscriptions:{" "}
                      <ul>
                        {delivery.subscriptions.map((subscription) => {
                          return (
                            <li>
                              {subscription.product} x {subscription.quantity}
                            </li>
                          );
                        })}
                      </ul>
                    </li>
                    <li>Pickup location: {delivery.pickupLocation.name}</li>
                    <li>
                      Opening times:{" "}
                      <ul>
                        {delivery.pickupLocationOpeningTimes.map(
                          (openingTimes) => {
                            return (
                              <li>
                                {openingTimes.dayOfWeek}:{" "}
                                {openingTimes.openTime}:{openingTimes.closeTime}
                              </li>
                            );
                          },
                        )}
                      </ul>
                    </li>
                  </ul>
                </li>
              );
            })}
          </ul>
        </div>
      </Card.Body>
    </Card>
  );
};

export default DeliveryListCard;
