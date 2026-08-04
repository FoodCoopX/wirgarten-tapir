import React, { useEffect, useState } from "react";
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

  useEffect(() => {
    if (show) {
      setListName("");
    }
  }, [show]);

  function onSave() {
    setSaving(true);

    api
      .coreApiMailingListCreateCreate({
        mailingListCreateRequest: { name: listName },
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
    <Modal show={show} onHide={onHide}>
      <Modal.Header closeButton={true}>
        <Modal.Title className={"mb-0"}>Mailing-List erzeugen</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Form
          onSubmit={(event) => {
            event.preventDefault();
            onSave();
          }}
        >
          <Form.Group>
            <Form.Label>Name</Form.Label>
            <Form.Control
              value={listName}
              onChange={(event) => setListName(event.target.value)}
              placeholder={"Name"}
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
