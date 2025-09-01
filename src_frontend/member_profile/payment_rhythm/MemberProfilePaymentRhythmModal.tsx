import React, { useEffect, useState } from "react";
import "dayjs/locale/de";
import { PaymentsApi } from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { Form, Modal, Spinner } from "react-bootstrap";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import TapirButton from "../../components/TapirButton.tsx";

interface MemberProfilePaymentRhythmModalProps {
  memberId: string;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  show: boolean;
  onHide: () => void;
}

const MemberProfilePaymentRhythmModal: React.FC<
  MemberProfilePaymentRhythmModalProps
> = ({ memberId, csrfToken, setToastDatas, show, onHide }) => {
  const api = useApi(PaymentsApi, csrfToken);
  const [dateOfNextChange, setDateOfNextChange] = useState<Date>();
  const [loading, setLoading] = useState(true);
  const [currentRhythm, setCurrentRhythm] = useState("monthly");
  const [newRhythm, setNewRhythm] = useState("monthly");
  const [allowedRhythms, setAllowedRhythms] = useState<{
    [key: string]: string;
  }>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!show) return;

    setLoading(true);

    api
      .paymentsApiMemberPaymentRhythmDataRetrieve({ memberId: memberId })
      .then((response) => {
        setDateOfNextChange(response.dateOfNextRhythmChange);
        setAllowedRhythms(response.allowedRhythms);
        setCurrentRhythm(response.currentRhythm);

        let found = false;
        for (const rhythm of Object.keys(response.allowedRhythms)) {
          if (rhythm === response.currentRhythm) {
            setNewRhythm(rhythm);
            found = true;
            break;
          }
        }
        if (!found) {
          setNewRhythm(Object.keys(response.allowedRhythms)[0]);
        }
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Zahlungsintervall-Datum",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, [show]);

  function getDisplayName(rhythm: string) {
    if (Object.keys(allowedRhythms).includes(rhythm)) {
      return allowedRhythms[rhythm];
    }
    return rhythm;
  }

  function onSave() {}

  return (
    <Modal show={show} onHide={onHide} centered>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Zahlungsintervall bearbeiten</h5>
      </Modal.Header>
      <Modal.Body>
        {loading ? (
          <Spinner />
        ) : (
          <div className={"d-flex flex-column gap-2"}>
            <div>
              Das aktuelles Intervall ist {getDisplayName(currentRhythm)}
            </div>
            <div>
              <Form.Group>
                <Form.Label>Intervall ändern</Form.Label>
                <Form.Select
                  value={newRhythm}
                  onChange={(event) => setNewRhythm(event.target.value)}
                >
                  {Object.entries(allowedRhythms).map(([rhythm, name]) => (
                    <option key={rhythm} value={rhythm}>
                      {name}
                    </option>
                  ))}
                </Form.Select>
                <Form.Text>
                  Das neue Intervall wird gültig ab dem{" "}
                  {formatDateNumeric(dateOfNextChange)}
                </Form.Text>
              </Form.Group>
            </div>
          </div>
        )}
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          variant={"primary"}
          icon={"save"}
          text={"Zahlungsintervall speichern"}
          loading={saving}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default MemberProfilePaymentRhythmModal;
