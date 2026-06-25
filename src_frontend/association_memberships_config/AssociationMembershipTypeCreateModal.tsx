import React, { useEffect, useRef, useState } from "react";
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
  const [description, setDescription] = useState("");
  const [order, setOrder] = useState(1);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    setName("");
    setDescription("");
    setOrder(1);
  }, [show]);

  function onSave() {
    if (!formRef.current) {
      return;
    }

    if (!formRef.current.reportValidity()) {
      return;
    }

    setSaving(true);

    api
      .associationsAssociationMembershipTypesCreate({
        associationMembershipTypeRequest: {
          name: name,
          orderInBestellWizard: order,
          descriptionInBestellWizard: description,
        },
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
        <Form ref={formRef}>
          <Form.Group>
            <Form.Label>Name</Form.Label>
            <Form.Control
              placeholder={"Name"}
              value={name}
              onChange={(event) => setName(event.target.value)}
              required={true}
            />
          </Form.Group>
          <Form.Group>
            <Form.Label>
              Reihenfolge im BestellWizard (kleiner ist früher)
            </Form.Label>
            <Form.Control
              placeholder={"Reihenfolge"}
              value={order}
              onChange={(event) =>
                setOrder(Number.parseInt(event.target.value))
              }
              type={"number"}
              step={1}
              min={1}
              required={true}
            />
          </Form.Group>
          <Form.Group>
            <Form.Label>Beschreibung im BestellWizard</Form.Label>
            <Form.Control
              placeholder={"Beschreibung"}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              as={"textarea"}
              required={true}
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
