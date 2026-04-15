import "dayjs/locale/de";
import React, { useState } from "react";
import { Card } from "react-bootstrap";
import TapirButton from "../../components/TapirButton.tsx";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { ToastData } from "../../types/ToastData.ts";
import SubscriptionCancellationModal from "./SubscriptionCancellationModal.tsx";

interface SubscriptionCancellationCardProps {
  memberId: string;
  csrfToken: string;
}

const SubscriptionCancellationCard: React.FC<
  SubscriptionCancellationCardProps
> = ({ memberId, csrfToken }) => {
  const [showModal, setShowModal] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  return (
    <>
      <Card style={{ marginBottom: "1rem" }}>
        <Card.Header>
          <h5 className={"mb-0"}>Verträge kündigen</h5>
        </Card.Header>
        <Card.Body>Einzelne oder alle Verträge kündigen</Card.Body>
        <Card.Footer>
          <div className={"d-flex justify-content-end"}>
            <TapirButton
              text={"Kündigen"}
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
        setToastDatas={setToastDatas}
      />
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default SubscriptionCancellationCard;
