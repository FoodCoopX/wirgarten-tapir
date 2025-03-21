import React, { useState } from "react";
import { Card } from "react-bootstrap";
import "dayjs/locale/de";
import TapirButton from "../../components/TapirButton.tsx";
import SubscriptionCancellationModal from "./SubscriptionCancellationModal.tsx";

interface SubscriptionCancellationCardProps {
  memberId: string;
  csrfToken: string;
}

const SubscriptionCancellationCard: React.FC<
  SubscriptionCancellationCardProps
> = ({ memberId, csrfToken }) => {
  const [showModal, setShowModal] = useState(false);

  return (
    <>
      <Card style={{ marginBottom: "1rem" }}>
        <Card.Header>
          <h5>Verträge kündigen</h5>
        </Card.Header>
        <Card.Body>Alle oder manche verträge kündigen</Card.Body>
        <Card.Footer>
          <div className={"d-flex justify-content-end"}>
            <TapirButton
              text={"kündigen"}
              icon={"contract_delete"}
              variant={"outline-primary"}
              onClick={() => {
                setShowModal(true);
              }}
            />
          </div>
        </Card.Footer>
      </Card>
      <SubscriptionCancellationModal
        csrfToken={csrfToken}
        show={showModal}
        memberId={memberId}
        onHide={() => setShowModal(false)}
      />
    </>
  );
};

export default SubscriptionCancellationCard;
