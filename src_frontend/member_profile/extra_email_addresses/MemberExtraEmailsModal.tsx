import React, { useEffect, useState } from "react";
import "dayjs/locale/de";
import { CoreApi, MemberExtraEmail } from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { Form, ListGroup, Modal, Spinner, Table } from "react-bootstrap";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import TapirButton from "../../components/TapirButton.tsx";

interface MemberExtraEmailsModalProps {
  memberId: string;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  show: boolean;
  onHide: () => void;
}

const MemberExtraEmailsModal: React.FC<MemberExtraEmailsModalProps> = ({
  memberId,
  csrfToken,
  setToastDatas,
  show,
  onHide,
}) => {
  const api = useApi(CoreApi, csrfToken);
  const [extraEmails, setExtraEmails] = useState<MemberExtraEmail[]>([]);
  const [explanationText, setExplanationText] = useState("");
  const [newAddress, setNewAddress] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!show) return;

    setNewAddress("");
    loadData();
  }, [show]);

  function loadData() {
    setLoading(true);

    api
      .coreApiMemberExtraEmailsRetrieve({ memberId: memberId })
      .then((response) => {
        setExtraEmails(response.extraMails);
        setExplanationText(response.explanationText);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der zusätzliche Adressen",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }

  function onSave() {
    setSaving(true);

    api
      .coreApiMemberExtraEmailsCreate({
        memberId: memberId,
        extraEmail: newAddress,
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Speichern eine zusätzliche Adresse",
          setToastDatas,
        ),
      )
      .finally(() => {
        loadData();
        setSaving(false);
      });
  }

  function onDelete(id: string) {
    setDeleting(true);

    api
      .coreApiMemberExtraEmailsDestroy({ extraEmailId: id })
      .then(loadData)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Speichern eine zusätzliche Adresse",
          setToastDatas,
        ),
      )
      .finally(() => setDeleting(false));
  }

  function getTable() {
    if (loading) {
      return <Spinner />;
    }

    if (extraEmails.length === 0) {
      return <p>Keine zusätzliche Adresse eingetragen</p>;
    }

    return (
      <Table striped hover responsive>
        <thead style={{ textAlign: "center" }}>
          <tr>
            <th>E-Mail</th>
            <th>Bestätigt am</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {extraEmails.map((extraEmail) => (
            <tr key={extraEmail.id}>
              <td>{extraEmail.email}</td>
              <td>
                {extraEmail.confirmedOn
                  ? formatDateNumeric(extraEmail.confirmedOn)
                  : "Nicht bestätigt"}
              </td>
              <td>
                <TapirButton
                  variant={"outline-danger"}
                  icon={"delete"}
                  size={"sm"}
                  onClick={() => onDelete(extraEmail.id!)}
                  loading={deleting}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    );
  }

  return (
    <Modal show={show} onHide={onHide} centered>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Zusätzliche Mail-Adressen verwalten</h5>
      </Modal.Header>
      <ListGroup>
        <>
          <ListGroup.Item>
            <div dangerouslySetInnerHTML={{ __html: explanationText }}></div>
          </ListGroup.Item>
          <ListGroup.Item>{getTable()}</ListGroup.Item>
          <ListGroup.Item>
            <Form>
              <h5>Zusätzliche Adresse hinzufügen</h5>
              <div className={"d-flex flex-row gap-2"}>
                <Form.Group controlId={"new_extra"}>
                  <Form.Control
                    type={"email"}
                    value={newAddress}
                    onChange={(event) => setNewAddress(event.target.value)}
                  />
                </Form.Group>
                <TapirButton
                  variant={"primary"}
                  icon={"add_circle"}
                  onClick={onSave}
                  loading={saving}
                />
              </div>
            </Form>
          </ListGroup.Item>
        </>
      </ListGroup>
    </Modal>
  );
};

export default MemberExtraEmailsModal;
