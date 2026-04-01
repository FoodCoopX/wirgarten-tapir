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
  function buildRevokeConfirmationModalText() {
    return (
      <>
        <p>Bist du sicher das du folgende Änderungen widerrufen willst?</p>
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
                Wenn die Zeichnungen widerrufen werden bekommt das Mitglied eine
                automatisiert Mail. Alle Verträge und Genossenschaftsanteile
                werden aus der Datenbank gelöscht.
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
                Wenn die Zeichnungen auf der Warteliste verschoben werden,
                bekommt das Mitglied keine automatisiert Mail. Alle Verträge und
                Genossenschaftsanteile werden aus der Datenbank gelöscht, aber
                einen Warteliste-Eintrag wird erzeugt der genau die Zeichnungen
                entspricht.
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
