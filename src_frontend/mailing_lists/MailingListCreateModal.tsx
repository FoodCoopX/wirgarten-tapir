import React, { useEffect, useRef, useState } from "react";
import { Form, Modal } from "react-bootstrap";
import { CoreApi } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface MailingListCreateModalProps {
  show: boolean;
  onHide: () => void;
  loadData: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const MailingListCreateModal: React.FC<MailingListCreateModalProps> = ({
  show,
  onHide,
  loadData,
  setToastDatas,
}) => {
  const api = useApi(CoreApi, getCsrfToken());
  const [listName, setListName] = useState("");
  const [saving, setSaving] = useState(false);
  const [advertised, setAdvertised] = useState(false);
  const [description, setDescription] = useState("");
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (show) {
      setListName("");
      setDescription("");
      setAdvertised(false);
    }
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
      .coreApiMailingListCreateCreate({
        mailingListCreateRequest: {
          name: listName,
          advertised: advertised,
          description: description,
        },
      })
      .then(() => {
        loadData();
        onHide();
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Erzeugen der Mailing-List",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  return (
    <Modal show={show} onHide={onHide} centered={true}>
      <Modal.Header closeButton={true}>
        <Modal.Title className={"mb-0"}>Mailing-List erzeugen</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Form
          onSubmit={(event) => {
            event.preventDefault();
            onSave();
          }}
          ref={formRef}
        >
          <Form.Group>
            <Form.Label>Name</Form.Label>
            <Form.Control
              value={listName}
              onChange={(event) => setListName(event.target.value)}
              placeholder={"Name"}
              required={true}
            />
          </Form.Group>
          <Form.Group>
            <Form.Label>Beschreibung</Form.Label>
            <Form.Control
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder={"Beschreibung"}
              as={"textarea"}
              required={true}
            />
          </Form.Group>
          <Form.Group controlId={"advertised"} className={"mt-2"}>
            <Form.Check
              label={"Mitglieder können sich selber ein- und austragen."}
              checked={advertised}
              onChange={(event) => setAdvertised(event.target.checked)}
            />
          </Form.Group>
        </Form>
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          variant={"primary"}
          icon={"save"}
          text={"Erzeugen"}
          onClick={onSave}
          loading={saving}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default MailingListCreateModal;
