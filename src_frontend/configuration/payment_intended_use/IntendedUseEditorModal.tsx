import React, { useEffect, useState } from "react";
import { Form, Modal, Row, Spinner } from "react-bootstrap";

interface IntendedUseEditorModalProps {
  show: boolean;
  onHide: () => void;
  parameterKey: string;
  currentPattern: string;
  setCurrentPattern: (newPattern: string) => void;
}

const IntendedUseEditorModal: React.FC<IntendedUseEditorModalProps> = ({
  show,
  onHide,
  parameterKey,
  currentPattern,
  setCurrentPattern,
}) => {
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState("");

  function onChange(event: React.ChangeEvent<HTMLInputElement>) {
    setCurrentPattern(event.target.value);
  }

  useEffect(() => {
    // TODO LOAD PREVIEW
  }, [currentPattern]);

  return (
    <Modal show={show} onHide={onHide} centered={true}>
      <Modal.Header closeButton={true}>
        Intended use editor: {parameterKey}
      </Modal.Header>
      <Modal.Body>
        <Row>Current: {currentPattern}</Row>
        <Row>
          <Form.Control value={currentPattern} onChange={onChange} />
        </Row>
        <Row>{loading ? <Spinner /> : <p>Preview: {preview}</p>}</Row>
      </Modal.Body>
    </Modal>
  );
};

export default IntendedUseEditorModal;
