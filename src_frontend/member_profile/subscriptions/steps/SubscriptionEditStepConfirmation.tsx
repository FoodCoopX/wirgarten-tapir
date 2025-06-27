import React from "react";
import { Modal } from "react-bootstrap";
import TapirButton from "../../../components/TapirButton.tsx";

interface SubscriptionEditStepConfirmationProps {
  orderConfirmed: boolean;
  error: string;
  onBackClicked: () => void;
  onFinishedClicked: () => void;
  waitingListModeEnabled: boolean;
}

const SubscriptionEditStepConfirmation: React.FC<
  SubscriptionEditStepConfirmationProps
> = ({
  orderConfirmed,
  error,
  onBackClicked,
  onFinishedClicked,
  waitingListModeEnabled,
}) => {
  return (
    <>
      <Modal.Body>
        {orderConfirmed ? (
          <p>
            {waitingListModeEnabled
              ? "Warteliste-Eintrag bestätigt!"
              : "Bestellung bestätigt!"}
          </p>
        ) : (
          <>
            <p>Die Bestellung könnte nicht bestätigt werden</p>
            <p>{error}</p>
          </>
        )}
      </Modal.Body>
      <Modal.Footer>
        {!orderConfirmed ? (
          <div style={{ width: "100%" }}>
            <TapirButton
              variant={"outline-secondary"}
              onClick={onBackClicked}
              icon={"chevron_left"}
              text={"Zurück"}
            />
          </div>
        ) : (
          <TapirButton
            variant={"outline-success"}
            onClick={onFinishedClicked}
            icon={"close"}
            text={"Schließen"}
            iconPosition={"right"}
          />
        )}
      </Modal.Footer>
    </>
  );
};

export default SubscriptionEditStepConfirmation;
