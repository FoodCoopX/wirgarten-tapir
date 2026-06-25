import React, { useEffect, useRef, useState } from "react";
import { Form, Modal } from "react-bootstrap";
import { AssociationMembershipType, AssociationsApi } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface AssociationMembershipTypeEditModalProps {
  csrfToken: string;
  show: boolean;
  onHide: () => void;
  onEdited: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  membershipType: AssociationMembershipType;
}

const AssociationMembershipTypeEditModal: React.FC<
  AssociationMembershipTypeEditModalProps
> = ({ csrfToken, onEdited, onHide, show, setToastDatas, membershipType }) => {
  const api = useApi(AssociationsApi, csrfToken);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [order, setOrder] = useState(1);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    setName(membershipType.name);
    setOrder(membershipType.orderInBestellWizard);
    setDescription(membershipType.descriptionInBestellWizard);
  }, [membershipType]);

  function onSave() {
    if (!formRef.current) {
      return;
    }

    if (!formRef.current.reportValidity()) {
      return;
    }

    setSaving(true);

    api
      .associationsAssociationMembershipTypesUpdate({
        id: membershipType.id!,
        associationMembershipTypeRequest: {
          name: name,
          descriptionInBestellWizard: description,
          orderInBestellWizard: order,
        },
      })
      .then(onEdited)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim editieren einen bestehenden Mitgliedschafttyp",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  return (
    <Modal show={show} onHide={onHide} centered={true}>
      <Modal.Header closeButton={true}>
        <Modal.Title>Mitgliedschafttyp anpassen</Modal.Title>
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
          text={"Speichern"}
          icon={"save"}
          loading={saving}
          onClick={onSave}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default AssociationMembershipTypeEditModal;
