import "dayjs/locale/de";
import React, { useEffect, useState } from "react";
import { Form, Modal, Spinner } from "react-bootstrap";
import { v4 as uuidv4 } from "uuid";
import { CoopApi } from "../../api-client";
import {
  emailsMatch,
  shouldShowEmailMismatchWarning,
} from "../../bestell_wizard/utils/emailsMatch.ts";
import { isEmailValid } from "../../bestell_wizard/utils/isEmailValid.ts";
import { isPhoneNumberValid } from "../../bestell_wizard/utils/isPhoneNumberValid.ts";
import { isPersonalDataValidShort } from "../../bestell_wizard_mobile/utils/isPersonalDataValidShort.ts";
import TapirButton from "../../components/TapirButton.tsx";
import TapirHelpButton from "../../components/TapirHelpButton.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { addToast } from "../../utils/addToast.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

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
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [emailConfirm, setEmailConfirm] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [street, setStreet] = useState("");
  const [street2, setStreet2] = useState("");
  const [postcode, setPostcode] = useState("");
  const [city, setCity] = useState("");
  const [isStudent, setIsStudent] = useState<boolean>();
  const [studentStatusEnabled, setStudentStatusEnabled] = useState(false);
  const [canEditStudent, setCanEditStudent] = useState(false);
  const [canEditName, setCanEditName] = useState(false);
  const [contactEmail, setContactEmail] = useState("");
  const [memberNumber, setMemberNumber] = useState("");

  const memberNumberHelpText =
    "Die Mitgliedsnummer kann nicht selbstständig verändert werden.";

  const nameHelpText = canEditName ? (
    <>
      Nur du als Admin kannst den Namen des Mitgliedes ändern. Das Mitglied kann
      dies nicht selbstständig. Ihm wird angezeigt, dass es den Betrieb
      kontaktieren muss, um den Namen zu verändern.
    </>
  ) : (
    <>
      Du kannst nicht selbstständig deinen Namen verändern. Bitte wende dich an
      deinen Betrieb (<a href={`mailto:${contactEmail}`}>{contactEmail}</a>
      ).
    </>
  );

  const emailHelpText = canEditName ? (
    <>
      Änderst du die Email hier direkt als Admin, hängt das Verhalten vom
      Verifizierungsstatus der aktuellen Adresse ab:
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
      Die Änderung deiner Email muss durch dich selbst bestätigt werden. Folge
      den Anweisungen, die du an deine alte Email erhältst. Wenn du keine Mail
      erhältst, dann wende dich an deinen Betrieb (
      <a href={`mailto:${contactEmail}`}>{contactEmail}</a>).
    </>
  );

  useEffect(() => {
    if (!show) return;

    setLoading(true);

    api
      .coopApiMemberPersonalDataRetrieve({ memberId: memberId })
      .then((response) => {
        setFirstName(response.firstName);
        setLastName(response.lastName);
        setEmail(response.email);
        setEmailConfirm(response.email);
        setPhoneNumber(response.phoneNumber);
        setStreet(response.street);
        setStreet2(response.street2);
        setPostcode(response.postcode);
        setCity(response.city);
        if (response.isStudent !== undefined) {
          setIsStudent(response.isStudent);
          setStudentStatusEnabled(true);
          setCanEditStudent(response.canEditStudent);
        }
        setCanEditName(response.canEditName);
        setContactEmail(response.contactEmail);
        setMemberNumber(response.memberNumber);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der persönliche Daten",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, [show]);

  function onSave() {
    if (
      !isPersonalDataValidShort(
        {
          firstName: firstName,
          lastName: lastName,
          email: email,
          emailConfirm: emailConfirm,
          phoneNumber: phoneNumber,
          street: street,
          street2: street2,
          postcode: postcode,
          city: city,
          country: "unused",
          iban: "unused",
          accountOwner: "unused",
          paymentRhythm: "unused",
        },
        false,
      )
    ) {
      setShowValidation(true);
      return;
    }

    setSaving(true);

    api
      .coopApiMemberPersonalDataPartialUpdate({
        patchedMemberProfilePersonalDataRequestRequest: {
          memberId: memberId,
          firstName: firstName,
          lastName: lastName,
          email: email,
          phoneNumber: phoneNumber,
          street: street,
          street2: street2,
          postcode: postcode,
          city: city,
          isStudent: isStudent,
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
          "Fehler beim Speichern der persönliche Daten",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  return (
    <Modal show={show} onHide={onHide} centered>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Persönliche Daten ändern</h5>
      </Modal.Header>
      <Modal.Body>
        {loading ? (
          <Spinner />
        ) : (
          <Form>
            <Form.Group className="mb-2">
              <Form.Label>
                <span className={"d-flex flex-row gap-2 align-items-center"}>
                  Mitgliedsnummer
                  <TapirHelpButton
                    buttonSize={"sm"}
                    text={memberNumberHelpText}
                  />
                </span>
              </Form.Label>
              <Form.Control
                placeholder={"Mitgliedsnummer"}
                value={memberNumber}
                disabled
              />
            </Form.Group>
            <Form.Group className="mb-2">
              <Form.Label>
                <span className={"d-flex flex-row gap-2 align-items-center"}>
                  Vorname
                  <TapirHelpButton buttonSize={"sm"} text={nameHelpText} />
                </span>
              </Form.Label>
              <Form.Control
                placeholder={"Vorname"}
                value={firstName}
                onChange={(event) => setFirstName(event.target.value)}
                isValid={showValidation && firstName.length > 0}
                isInvalid={showValidation && firstName.length === 0}
                disabled={!canEditName}
              />
            </Form.Group>
            <Form.Group className="mb-2">
              <Form.Label>
                <span className={"d-flex flex-row gap-2 align-items-center"}>
                  Nachname
                  <TapirHelpButton buttonSize={"sm"} text={nameHelpText} />
                </span>
              </Form.Label>
              <Form.Control
                placeholder={"Nachname"}
                value={lastName}
                onChange={(event) => setLastName(event.target.value)}
                isValid={showValidation && lastName.length > 0}
                isInvalid={showValidation && lastName.length === 0}
                disabled={!canEditName}
              />
            </Form.Group>
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
                value={emailConfirm}
                onChange={(event) => setEmailConfirm(event.target.value)}
                isValid={showValidation && emailsMatch(email, emailConfirm)}
                isInvalid={showValidation && !emailsMatch(email, emailConfirm)}
              />
              {shouldShowEmailMismatchWarning(email, emailConfirm) && (
                <Form.Text className={showValidation ? "text-danger" : ""}>
                  Die E-Mail-Adressen stimmen nicht überein
                </Form.Text>
              )}
            </Form.Group>
            <Form.Group className="mb-2">
              <Form.Label>Telefonnummer</Form.Label>
              <Form.Control
                placeholder={"Telefonnummer"}
                type={"tel"}
                value={phoneNumber}
                onChange={(event) => setPhoneNumber(event.target.value)}
                isValid={showValidation && isPhoneNumberValid(phoneNumber)}
                isInvalid={showValidation && !isPhoneNumberValid(phoneNumber)}
              />
            </Form.Group>
            <Form.Group className="mb-2">
              <Form.Label>Straße & Hausnummer</Form.Label>
              <Form.Control
                placeholder={"Straße & Hausnummer"}
                value={street}
                onChange={(event) => setStreet(event.target.value)}
                isValid={showValidation && street.length > 0}
                isInvalid={showValidation && street.length === 0}
              />
            </Form.Group>
            <Form.Group className="mb-2">
              <Form.Label>Adresszusatz</Form.Label>
              <Form.Control
                placeholder={"Adresszusatz"}
                value={street2}
                onChange={(event) => setStreet2(event.target.value)}
                isValid={showValidation}
              />
            </Form.Group>
            <Form.Group className="mb-2">
              <Form.Label>Postleitzahl</Form.Label>
              <Form.Control
                placeholder={"Postleitzahl"}
                value={postcode}
                onChange={(event) => setPostcode(event.target.value)}
                isValid={showValidation && postcode.length > 0}
                isInvalid={showValidation && postcode.length === 0}
              />
            </Form.Group>
            <Form.Group className="mb-2">
              <Form.Label>Stadt</Form.Label>
              <Form.Control
                placeholder={"Stadt"}
                value={city}
                onChange={(event) => setCity(event.target.value)}
                isValid={showValidation && city.length > 0}
                isInvalid={showValidation && city.length === 0}
              />
            </Form.Group>
            {studentStatusEnabled && (
              <Form.Group>
                <Form.Check
                  checked={isStudent}
                  onChange={(e) => setIsStudent(e.target.checked)}
                  id={"is_student"}
                  isValid={showValidation}
                  label={
                    "Ich bin Student*in und kann keine Genossenschaftsanteile zeichnen"
                  }
                  disabled={!canEditStudent}
                />
              </Form.Group>
            )}
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
