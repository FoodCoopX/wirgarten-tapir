import React, { useEffect, useState } from "react";
import { Joker, JokersApi } from "../api-client";
import { useApi } from "../hooks/useApi";
import { Card } from "react-bootstrap";

const DeliveryListCard: React.FC = () => {
  const api = useApi(JokersApi);
  const [jokers, setJokers] = useState<Joker[]>([]);

  useEffect(() => {
    api
      .jokersApiMemberJokersList({ memberId: "Hkl_XW7B9n" })
      .then(setJokers)
      .catch((error) => alert(error));
  }, []);

  return (
    <Card>
      <Card.Header>
        <h5>Abholung</h5>
      </Card.Header>
      <Card.Body>coucou</Card.Body>
    </Card>
  );
};

export default DeliveryListCard;
