import React, { useEffect, useState } from "react";
import "dayjs/locale/de";
import { CoopApi } from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { Form, Modal, Spinner } from "react-bootstrap";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { isIbanValid } from "../../bestell_wizard/utils/isIbanValid.ts";

interface MemberBankingDataModalProps {
  memberId: string;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  show: boolean;
  onHide: () => void;
}

const MemberBankingDataModal: React.FC<MemberBankingDataModalProps> = ({
  memberId,
  csrfToken,
  setToastDatas,
  show,
  onHide,
}) => {
  const api = useApi(CoopApi, csrfToken);
  const [iban, setIban] = useState("");
  const [accountOwner, setAccountOwner] = useState("");
  const [sepaConsent, setSepaConsent] = useState(false);
  const [showValidation, setShowValidation] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [organisationName, setOrganisationName] = useState("");

  useEffect(() => {
    if (!show) return;

    setLoading(true);

    api
      .coopApiMemberBankingDataRetrieve({ memberId: memberId })
      .then((response) => {
        setIban(response.iban);
        setAccountOwner(response.accountOwner);
        setOrganisationName(response.organisationName);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Bank-Daten",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, [show]);

  function onSave() {
    if (!sepaConsent || accountOwner.length === 0 || !isIbanValid(iban)) {
      setShowValidation(true);
      return;
    }

    setSaving(true);

    api
      .coopApiMemberBankingDataPartialUpdate({
        patchedUpdateMemberBankDataRequestRequest: {
          memberId: memberId,
          iban: iban,
          accountOwner: accountOwner,
          sepaConsent: sepaConsent,
        },
      })
      .then(() => {
        onHide();
        globalThis.location.reload();
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Speichern der Bank-Daten",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  return (
    <Modal show={show} onHide={onHide} centered>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Bankverbindung ändern</h5>
      </Modal.Header>
      <Modal.Body>
        {loading ? (
          <Spinner />
        ) : (
          <Form>
            <Form.Group className={"mb-2"}>
              <Form.Label>Kontoinhaber*in</Form.Label>
              <Form.Control
                value={accountOwner}
                onChange={(event) => {
                  setAccountOwner(event.target.value);
                }}
                placeholder={"Kontoinhaber*in"}
                isInvalid={showValidation && accountOwner.length === 0}
                isValid={showValidation && accountOwner.length > 0}
              />
            </Form.Group>
            <Form.Group className={"mb-2"}>
              <Form.Label>IBAN</Form.Label>
              <Form.Control
                value={iban}
                onChange={(event) => {
                  setIban(event.target.value);
                }}
                placeholder={"IBAN"}
                isInvalid={showValidation && !isIbanValid(iban)}
                isValid={showValidation && isIbanValid(iban)}
              />
            </Form.Group>
            <Form.Group>
              <Form.Check
                checked={sepaConsent}
                onChange={(e) => setSepaConsent(e.target.checked)}
                id={"sepa_consent"}
                isInvalid={showValidation && !sepaConsent}
                isValid={showValidation && sepaConsent}
                label={
                  "Ich ermächtige die " +
                  organisationName +
                  " die gezeichneten Geschäftsanteile sowie die monatlichen Beträge für den Ernteanteil und ggf. weitere Produkte mittels Lastschrift von meinem Bankkonto einzuziehen. Zugleich weise ich mein Kreditinstitut an, die gezogene Lastschrift einzulösen."
                }
              />
            </Form.Group>
          </Form>
        )}
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          variant={"primary"}
          icon={"save"}
          text={"Speichern"}
          loading={saving}
          onClick={onSave}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default MemberBankingDataModal;
