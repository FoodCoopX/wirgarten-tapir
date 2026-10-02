import "dayjs/locale/de";
import React, { useEffect, useState } from "react";
import { Form, Modal, Spinner } from "react-bootstrap";
import { v4 as uuidv4 } from "uuid";
import { CoopApi } from "../../api-client";
import { isPersonalDataValidShort } from "../../bestell_wizard_mobile/utils/isPersonalDataValidShort.ts";
import TapirButton from "../../components/TapirButton.tsx";
import TapirHelpButton from "../../components/TapirHelpButton.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { addToast } from "../../utils/addToast.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { isEmailValid } from "../../bestell_wizard/utils/isEmailValid.ts";
import {
  emailsMatch,
  shouldShowEmailMismatchWarning,
} from "../../bestell_wizard/utils/emailsMatch.ts";

interface MemberPersonalDataModalProps {
  memberId: string;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  show: boolean;
  onHide: () => void;
}

const MemberPersonalDataModal: React.FC<MemberPersonalDataModalProps> = ({
  memberId,
  csrfToken,
  setToastDatas,
  show,
  onHide,
}) => {
  const api = useApi(CoopApi, csrfToken);
  const [showValidation, setShowValidation] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [email, setEmail] = useState("");
  const [emailConfirmation, setEmailConfirmation] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);

  const emailHelpText = isAdmin ? (
    <>
      Änderst du die E-Mail-Adresse hier direkt als Admin, hängt das Verhalten
      vom Verifizierungsstatus der aktuellen Adresse ab:
      <br />
      <br />
      <strong>Adresse bereits verifiziert:</strong> Die neue Adresse wird beim
      Speichern nicht sofort übernommen. Stattdessen wird ein Bestätigungslink
      an die <strong>alte</strong> Adresse verschickt – erst ein Klick darauf
      setzt die neue Adresse. Damit das funktioniert, muss die transaktionale
      Mail "Email-Änderung: Bestätigung anfordern" im Mailmodul veröffentlicht
      sein und den Token{" "}
      <code>
        {"{{Email-Änderung: Bestätigung anfordern.Bestätigungslink}}"}
      </code>{" "}
      enthalten.
      <br />
      <br />
      <strong>Adresse noch nicht verifiziert</strong> (z. B. bei einem neuen
      Mitglied, das sein Konto noch nicht bestätigt hat): Die neue Adresse wird
      sofort übernommen, und es wird automatisch eine neue Verifizierungsmail an
      die neue Adresse verschickt. Ein manuelles erneutes Versenden ist nicht
      nötig – das Mitglied muss nur noch auf den Link in dieser Mail klicken.
    </>
  ) : (
    <>
      Die Änderung deiner E-Mail-Adresse muss durch dich selbst bestätigt
      werden. Folge den Anweisungen, die du an deine alte E-Mail-Adresse
      erhältst. Wenn du keine Mail erhältst, dann wende dich an deinen Betrieb (
      <a href={`mailto:${contactEmail}`}>{contactEmail}</a>).
    </>
  );

  useEffect(() => {
    if (!show) return;

    setLoading(true);

    api
      .coopApiMemberEmailRetrieve({ memberId: memberId })
      .then((response) => {
        setEmail(response.email);
        setEmailConfirmation(response.email);
        setContactEmail(response.contactEmail);
        setIsAdmin(response.isAdmin);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der persönlichen Daten",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, [show]);

  function onSave() {
    if (
      !isPersonalDataValidShort(
        {
          email: email,
          emailConfirm: emailConfirmation,
          firstName: "unused",
          lastName: "unused",
          street: "unused",
          street2: "unused",
          postcode: "unused",
          city: "unused",
          country: "unused",
          iban: "unused",
          accountOwner: "unused",
          paymentRhythm: "unused",
          phoneNumber: "",
        },
        false,
      )
    ) {
      setShowValidation(true);
      return;
    }

    setSaving(true);

    api
      .coopApiMemberEmailCreate({
        memberEmailRequestRequest: {
          memberId: memberId,
          email: email,
        },
      })
      .then((response) => {
        if (response.orderConfirmed) {
          onHide();
          globalThis.location.reload();
        } else {
          addToast(
            {
              id: uuidv4(),
              variant: "danger",
              title: "Fehler",
              message: response.error ?? undefined,
            },
            setToastDatas,
          );
        }
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Speichern der E-Mail-Adresse",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  return (
    <Modal show={show} onHide={onHide} centered>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>E-Mail-Adresse ändern</h5>
      </Modal.Header>
      <Modal.Body>
        {loading ? (
          <Spinner />
        ) : (
          <Form>
            <Form.Group className="mb-2">
              <Form.Label>
                <span className={"d-flex flex-row gap-2 align-items-center"}>
                  E-Mail
                  <TapirHelpButton buttonSize={"sm"} text={emailHelpText} />
                </span>
              </Form.Label>
              <Form.Control
                placeholder={"E-Mail"}
                type={"email"}
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                isValid={showValidation && isEmailValid(email)}
                isInvalid={showValidation && !isEmailValid(email)}
              />
            </Form.Group>
            <Form.Group className="mb-2">
              <Form.Label>E-Mail wiederholen</Form.Label>
              <Form.Control
                placeholder={"E-Mail wiederholen"}
                type={"email"}
                value={emailConfirmation}
                onChange={(event) => setEmailConfirmation(event.target.value)}
                isValid={
                  showValidation && emailsMatch(email, emailConfirmation)
                }
                isInvalid={
                  showValidation && !emailsMatch(email, emailConfirmation)
                }
              />
              {shouldShowEmailMismatchWarning(email, emailConfirmation) && (
                <Form.Text className={showValidation ? "text-danger" : ""}>
                  Die E-Mail-Adressen stimmen nicht überein
                </Form.Text>
              )}
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

export default MemberPersonalDataModal;
