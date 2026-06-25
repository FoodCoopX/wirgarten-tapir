import React, { useEffect, useState } from "react";
import { Form, Modal } from "react-bootstrap";
import { AssociationsApi } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface AssociationMembershipTypeCreateModalProps {
  csrfToken: string;
  show: boolean;
  onHide: () => void;
  onCreated: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const AssociationMembershipTypeCreateModal: React.FC<
  AssociationMembershipTypeCreateModalProps
> = ({ csrfToken, onCreated, onHide, show, setToastDatas }) => {
  const api = useApi(AssociationsApi, csrfToken);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");

  useEffect(() => {
    setName("");
  }, [show]);

  function onSave() {
    setSaving(true);

    api
      .associationsAssociationMembershipTypesCreate({
        associationMembershipTypeRequest: { name: name },
      })
      .then(onCreated)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Speichern ein neues Mitgliedschafttyp",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  return (
    <Modal show={show} onHide={onHide} centered={true}>
      <Modal.Header closeButton={true}>
        <Modal.Title>Mitgliedschafttyp erzeugen</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Form>
          <Form.Group>
            <Form.Label>Name</Form.Label>
            <Form.Control
              placeholder={"Name"}
              value={name}
              onChange={(event) => setName(event.target.value)}
              onKeyUp={(event) => {
                event.preventDefault();
                if (event.key === "Enter") onSave();
              }}
            />
          </Form.Group>
        </Form>
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          variant={"outline-secondary"}
          text={"Abbrechen"}
          icon={"cancel"}
          onClick={onHide}
        />
        <TapirButton
          variant={"primary"}
          text={"Erzeugen"}
          icon={"save"}
          loading={saving}
          onClick={onSave}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default AssociationMembershipTypeCreateModal;
