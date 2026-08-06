import React, { useEffect, useState } from "react";
import { Form, Modal } from "react-bootstrap";
import { CoreApi, MailingList } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import TapirHelpButton from "../components/TapirHelpButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface MailingListEditModalProps {
  show: boolean;
  onHide: () => void;
  loadData: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  mailingList: MailingList;
}

const MailingListEditModal: React.FC<MailingListEditModalProps> = ({
  show,
  onHide,
  loadData,
  setToastDatas,
  mailingList,
}) => {
  const api = useApi(CoreApi, getCsrfToken());
  const [listName, setListName] = useState("");
  const [saving, setSaving] = useState(false);
  const [advertised, setAdvertised] = useState(false);
  const [description, setDescription] = useState("");

  useEffect(() => {
    if (!show) {
      return;
    }

    setListName(mailingList.name);
    setDescription(mailingList.description);
    setAdvertised(mailingList.advertised);
  }, [show, mailingList]);

  function onSave() {
    setSaving(true);

    api
      .coreApiMailingListEditUpdate({
        mailingListCreateRequest: {
          name: mailingList.name,
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
          "Fehler beim Editieren der Mailing-List",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  return (
    <Modal show={show} onHide={onHide} centered={true}>
      <Modal.Header closeButton={true}>
        <Modal.Title className={"mb-0"}>Mailing-List editieren</Modal.Title>
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
            <Form.Control value={listName} disabled={true} />
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
              label={
                <span className={"d-flex gap-2"}>
                  <span>Mitglieder können sich selber ein- und austragen.</span>
                  <TapirHelpButton
                    text={
                      "Mitglieder die schon eingetragen sind werden werden nicht automatisch ausgetragen."
                    }
                    buttonSize={"sm"}
                  />
                </span>
              }
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

export default MailingListEditModal;
