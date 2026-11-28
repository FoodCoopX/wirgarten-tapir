import { PlusCircleIcon } from "@heroicons/react/24/outline";
import React, { useState } from "react";
import { Form, Modal } from "react-bootstrap";
import { TapirmailApi } from "tapir-api-client";
import { useAlert } from "../../contexts/alerts";
import { useApi } from "../../hooks/useApi";
import TapirButton from "../TapirButton";

interface StaticSegmentsCreateModalProps {
  open: boolean;
  onClose: () => void;
}

const StaticSegmentsCreateModal: React.FC<StaticSegmentsCreateModalProps> = ({
  open,
  onClose,
}) => {
  const [loading, setLoading] = useState(false);
  const staticSegmentApi = useApi(TapirmailApi);
  const showAlert = useAlert();
  const [segmentName, setSegmentName] = useState("");

  function onCreateClicked() {
    setLoading(true);

    staticSegmentApi
      .tapirmailApiStaticSegmentCreate({
        staticSegmentRequest: { name: segmentName },
      })
      .then(() => {
        onClose();
        setSegmentName("");
      })
      .catch((err) => {
        console.error(err);
        showAlert("Fehler beim erzeugen der Segment", "danger");
      })
      .finally(() => setLoading(false));
  }

  return (
    <Modal show={open} onHide={onClose} centered={true}>
      <Modal.Header closeButton>
        <Modal.Title>Statische Segment erzeugen</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Form.Group>
          <Form.Label column={"lg"}>Name</Form.Label>
          <Form.Control
            required={true}
            className={segmentName ? "" : "is-invalid"}
            type="text"
            value={segmentName}
            onChange={(e) => setSegmentName(e.target.value)}
          />
        </Form.Group>
      </Modal.Body>
      <Modal.Footer className="d-flex justify-content-end align-items-center">
        <TapirButton
          variant={"primary"}
          text={loading ? "Loading..." : "Erzeugen"}
          icon={PlusCircleIcon}
          disabled={loading}
          onClick={() => onCreateClicked()}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default StaticSegmentsCreateModal;
