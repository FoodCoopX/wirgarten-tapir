import React from "react";
import { Form, Modal } from "react-bootstrap";
import { ExportSegment } from "../api-client";

interface CsvExportCreateModalProps {
  show: boolean;
  onHide: () => void;
  segments: ExportSegment[];
}

const CsvExportCreateModal: React.FC<CsvExportCreateModalProps> = ({
  show,
  onHide,
  segments,
}) => {
  return (
    <Modal show={show} onHide={onHide} centered={true}>
      <Modal.Header closeButton>Neues Export erzeugen</Modal.Header>
      <Modal.Body>
        <Form>
          <Form.Group>
            <Form.Label>Name</Form.Label>
            <Form.Control type={"text"} placeholder={"Name"} />
          </Form.Group>
          <Form.Group>
            <Form.Label>Datensegment</Form.Label>
            <Form.Select>
              {segments.map((segment) => {
                return (
                  <option key={segment.id} value={segment.id}>
                    {segment.displayName}
                  </option>
                );
              })}
            </Form.Select>
          </Form.Group>
          <Form.Group>
            <Form.Label>Beschreibung</Form.Label>
            <Form.Control
              type={"text"}
              placeholder={"Beschreibung"}
              as={"textarea"}
            />
          </Form.Group>
          <Form.Group>
            <Form.Label>Trennzeichen</Form.Label>
            <Form.Control type={"text"} placeholder={"Trennzeichen"} />
          </Form.Group>
        </Form>
      </Modal.Body>
    </Modal>
  );
};

export default CsvExportCreateModal;
