import React, { useEffect, useState } from "react";
import { Joker, JokersApi } from "../api-client";
import { useApi } from "../hooks/useApi";
import { Card } from "react-bootstrap";
import TapirButton from "../components/TapirButton.tsx";

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
      <Card.Body>coucou</Card.Body>
    </Card>
  );
};

export default DeliveryListCard;
