import React from "react";
import { Col, ListGroup, Modal, Row } from "react-bootstrap";
import { MemberDataToConfirm } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";

interface ConfirmRevokeModalProps {
  open: boolean;
  onRevoke: () => void;
  onWaitingList: () => void;
  onCancel: () => void;
  loading?: boolean;
  selectedChanges: Set<MemberDataToConfirm>;
}

const ConfirmRevokeModal: React.FC<ConfirmRevokeModalProps> = ({
  open,
  onRevoke,
  onWaitingList,
  onCancel,
  loading,
  selectedChanges,
}) => {
  const hasCoopShares = Array.from(selectedChanges).some(
    (change) => change.sharePurchases.length > 0,
  );
  const revokedItems = hasCoopShares
    ? "Die ausgewählten Zeichnungen werden gelöscht."
    : "Die ausgewählten Verträge werden gelöscht.";

  function buildRevokeConfirmationModalText() {
    return (
      <>
        <p>Möchtest du die Änderungen für folgende Mitglieder widerrufen?</p>
        <ul>
          {Array.from(selectedChanges).map((change) => (
            <li key={change.member.id}>
              <a href={change.memberProfileUrl}>
                {change.member.firstName} {change.member.lastName} #
                {change.member.memberNo}
              </a>
            </li>
          ))}
        </ul>
      </>
    );
  }

  return (
    <Modal show={open} onHide={onCancel} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <Modal.Title>
          <h5>Änderungen widerrufen</h5>
        </Modal.Title>
      </Modal.Header>
      <ListGroup>
        <ListGroup.Item>{buildRevokeConfirmationModalText()}</ListGroup.Item>
        <ListGroup.Item>
          <Row>
            <Col>
              <h4 className={"card-subtitle"}>Widerrufen</h4>
              <p>
                {revokedItems} Die betroffenen Mitglieder erhalten automatisch
                eine E-Mail.
              </p>
              <div className={"d-flex justify-content-end"}>
                <TapirButton
                  variant={"danger"}
                  text={"Widerrufen"}
                  icon={"contract_delete"}
                  loading={loading}
                  onClick={onRevoke}
                />
              </div>
            </Col>
            <Col>
              <h4 className={"card-subtitle"}>Auf Warteliste verschieben</h4>
              <p>
                {revokedItems} Tapir legt einen Wartelisteneintrag an und sendet
                keine automatische E-Mail.
              </p>
              <div className={"d-flex justify-content-end"}>
                <TapirButton
                  variant={"warning"}
                  text={"Auf Warteliste verschieben"}
                  icon={"pending_actions"}
                  loading={loading}
                  onClick={onWaitingList}
                />
              </div>
            </Col>
          </Row>
        </ListGroup.Item>
      </ListGroup>
    </Modal>
  );
};

export default ConfirmRevokeModal;
