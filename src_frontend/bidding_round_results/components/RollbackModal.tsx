import React from "react";
import { Alert, Button, Form, Modal, Spinner, Table } from "react-bootstrap";

import type { RollbackConflict, RollbackTarget } from "../types.ts";

interface RollbackModalProps {
  show: boolean;
  onHide: () => void;
  target: RollbackTarget | null;
  reason: string;
  onReasonChange: (value: string) => void;
  force: boolean;
  onForceChange: (value: boolean) => void;
  conflicts: RollbackConflict[];
  error: string | null;
  loading: boolean;
  onRun: () => void;
}

function conflictKey(conflict: RollbackConflict): string {
  return [
    conflict.kind ?? "",
    conflict.member_name ?? conflict.memberName ?? "",
    conflict.round_name ?? conflict.roundName ?? "",
  ].join(":");
}

const RollbackModal: React.FC<RollbackModalProps> = ({
  show,
  onHide,
  target,
  reason,
  onReasonChange,
  force,
  onForceChange,
  conflicts,
  error,
  loading,
  onRun,
}) => {
  return (
    <Modal show={show} onHide={onHide} centered={true} size="lg">
      <Modal.Header closeButton>
        <h5 className="mb-0">{"Verträge zurücknehmen"}</h5>
      </Modal.Header>
      <Modal.Body>
        <p className="mb-2">
          {target?.memberIds === null
            ? "Alle von dieser Beitragsrunde erzeugten Verträge und Beitragsanpassungen werden zurückgenommen."
            : "Der Vertrag und die Beitragsanpassungen dieses Mitglieds werden zurückgenommen."}
        </p>
        {target && target.memberNames.length > 0 && (
          <p className="mb-2">
            <strong>{target.memberNames.join(", ")}</strong>
          </p>
        )}
        {error && (
          <Alert variant="danger" className="py-2">
            {error}
          </Alert>
        )}
        {conflicts.length > 0 && (
          <Table size="sm" responsive>
            <thead>
              <tr>
                <th>{"Mitglied"}</th>
                <th>{"Runde"}</th>
                <th>{"Grund"}</th>
              </tr>
            </thead>
            <tbody>
              {conflicts.map((conflict) => (
                <tr key={conflictKey(conflict)}>
                  <td>{conflict.member_name ?? conflict.memberName}</td>
                  <td>{conflict.round_name ?? conflict.roundName ?? "–"}</td>
                  <td>{conflict.detail ?? "–"}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
        {conflicts.some((conflict) => (conflict.kind ?? "") === "diverged") && (
          <Form.Check
            type="checkbox"
            id="rollback-force"
            label={"Trotz nachträglicher Änderungen zurücknehmen (force)"}
            checked={force}
            onChange={(event) => onForceChange(event.target.checked)}
          />
        )}
        <Form.Group className="mt-3">
          <Form.Label>
            {"Begründung"}
            {force ? " (Pflicht)" : ""}
          </Form.Label>
          <Form.Control
            as="textarea"
            rows={2}
            value={reason}
            onChange={(event) => onReasonChange(event.target.value)}
          />
        </Form.Group>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide} disabled={loading}>
          {"Abbrechen"}
        </Button>
        <Button variant="danger" onClick={onRun} disabled={loading}>
          {loading ? <Spinner animation="border" size="sm" /> : "Zurücknehmen"}
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default RollbackModal;
