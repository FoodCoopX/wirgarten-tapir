import React, { useEffect, useState } from "react";
import "dayjs/locale/de";
import { CoopApi } from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { Form, Modal, Spinner } from "react-bootstrap";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { isPersonalDataValidShort } from "../../bestell_wizard_mobile/utils/isPersonalDataValidShort.ts";
import { isPhoneNumberValid } from "../../bestell_wizard/utils/isPhoneNumberValid.ts";
import { isEmailValid } from "../../bestell_wizard/utils/isEmailValid.ts";
import { addToast } from "../../utils/addToast.ts";
import { v4 as uuidv4 } from "uuid";

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
  const [phoneNumber, setPhoneNumber] = useState("");
  const [street, setStreet] = useState("");
  const [street2, setStreet2] = useState("");
  const [postcode, setPostcode] = useState("");
  const [city, setCity] = useState("");
  const [isStudent, setIsStudent] = useState<boolean>();
  const [studentStatusEnabled, setStudentStatusEnabled] = useState(false);
  const [canEditStudent, setCanEditStudent] = useState(false);

  useEffect(() => {
    if (!show) return;

    setLoading(true);

    api
      .coopApiMemberPersonalDataRetrieve({ memberId: memberId })
      .then((response) => {
        setFirstName(response.firstName);
        setLastName(response.lastName);
        setEmail(response.email);
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
        <h5 className={"mb-0"}>Bankverbindung ändern</h5>
      </Modal.Header>
      <Modal.Body>
        {loading ? (
          <Spinner />
        ) : (
          <Form>
            <Form.Group className="mb-2">
              <Form.Label>Vorname</Form.Label>
              <Form.Control
                placeholder={"Vorname"}
                value={firstName}
                onChange={(event) => setFirstName(event.target.value)}
                isValid={showValidation && firstName.length > 0}
                isInvalid={showValidation && firstName.length === 0}
              />
            </Form.Group>
            <Form.Group className="mb-2">
              <Form.Label>Nachname</Form.Label>
              <Form.Control
                placeholder={"Nachname"}
                value={lastName}
                onChange={(event) => setLastName(event.target.value)}
                isValid={showValidation && lastName.length > 0}
                isInvalid={showValidation && lastName.length === 0}
              />
            </Form.Group>
            <Form.Group className="mb-2">
              <Form.Label>E-Mail</Form.Label>
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
                value={street}
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
