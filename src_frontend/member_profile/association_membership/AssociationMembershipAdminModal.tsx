import "dayjs/locale/de";
import React, { useEffect, useState } from "react";
import { Form, Modal, Spinner } from "react-bootstrap";
import { AssociationMembershipType, AssociationsApi } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import TapirHelpButton from "../../components/TapirHelpButton.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

interface AssociationMembershipAdminModalProps {
  memberId: string;
  csrfToken: string;
  show: boolean;
  onHide: () => void;
  reloadData: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const AssociationMembershipAdminModal: React.FC<
  AssociationMembershipAdminModalProps
> = ({ memberId, csrfToken, show, onHide, reloadData, setToastDatas }) => {
  const api = useApi(AssociationsApi, csrfToken);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [membershipTypes, setMembershipTypes] = useState<
    AssociationMembershipType[]
  >([]);
  const [selectedMembershipTypeId, setSelectedMembershipTypeId] = useState("");
  const [startDateAsString, setStartDateAsString] = useState("");

  useEffect(() => {
    if (!show) {
      return;
    }

    setLoading(true);

    api
      .associationsAssociationMembershipTypesList()
      .then((types) => {
        setMembershipTypes(types);
        if (types.length > 0) {
          setSelectedMembershipTypeId(types[0].id!);
        }
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Mitdlieschafttypen",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, [show]);

  function onCreate() {
    if (selectedMembershipTypeId === "") {
      alert("Kein ausgewählter Mitgliedschafttyp");
      return;
    }

    const startDate = new Date(startDateAsString);
    if (Number.isNaN(startDate.valueOf())) {
      alert("Ungültiges Datum");
      return;
    }

    setSaving(true);
    api
      .associationsApiAdminCreateMembershipCreate({
        adminSetAssociationMembershipRequestRequest: {
          membershipTypeId: selectedMembershipTypeId,
          memberId: memberId,
          startDate: startDate,
        },
      })
      .then(() => {
        onHide();
        reloadData();
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Speichern der Mitgliedschaft",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  return (
    <Modal className={"mb-2"} show={show} onHide={onHide} centered={true}>
      <Modal.Header closeButton={true}>
        <Modal.Title>Vereinsmitgliedschaft als Admin erzeugen</Modal.Title>
        <TapirHelpButton
          text={
            <>
              <p>
                Bestehen Mitgliedschaften die nach dem ausgewähltem Start-Datum
                beginnen werden gelöscht.
              </p>
              <p>
                Bestehen Mitgliedschaften die aktiv am ausgewähltem Start-Datum
                sind werden geendet mit End-Datum am Tag vor dem Start-Datum.s
              </p>
            </>
          }
        />
      </Modal.Header>
      <Modal.Body>
        {loading ? (
          <Spinner />
        ) : (
          <>
            {membershipTypes.length === 0 ? (
              "Keine Mitgliedschafttypen"
            ) : (
              <div className={"d-flex flex-column gap-2"}>
                <Form.Group>
                  <Form.Label>Mitgliedschafttyp</Form.Label>
                  <Form.Select
                    onChange={(event) =>
                      setSelectedMembershipTypeId(event.target.value)
                    }
                  >
                    {membershipTypes.map((type) => {
                      return (
                        <option key={type.id} value={type.id}>
                          {type.name}
                        </option>
                      );
                    })}
                  </Form.Select>
                </Form.Group>
                <Form.Group>
                  <Form.Label>Start-Datum</Form.Label>
                  <Form.Control
                    type={"date"}
                    value={startDateAsString}
                    onChange={(event) =>
                      setStartDateAsString(event.target.value)
                    }
                  />
                </Form.Group>
              </div>
            )}
          </>
        )}
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          variant={"primary"}
          text={"Erzeugen"}
          icon={"save"}
          onClick={onCreate}
          loading={saving}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default AssociationMembershipAdminModal;
