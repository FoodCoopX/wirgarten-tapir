import React, { useEffect, useState } from "react";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { Col, Form, Row, Spinner } from "react-bootstrap";
import { PersonalData } from "../types/PersonalData.ts";
import BestellWizardCardTitle from "../components/BestellWizardCardTitle.tsx";
import BestellWizardCardSubtitle from "../components/BestellWizardCardSubtitle.tsx";
import { isIbanValid } from "../utils/isIbanValid.ts";
import { isEmailValid } from "../utils/isEmailValid.ts";
import { isPhoneNumberValid } from "../utils/isPhoneNumberValid.ts";
import { isBirthdateValid } from "../utils/isBirthdateValid.ts";
import { getTextSepaCheckbox } from "../utils/getTextSepaCheckbox.ts";
import { useApi } from "../../hooks/useApi.ts";
import { SubscriptionsApi, WaitingListEntryDetails } from "../../api-client";
import { getCsrfToken } from "../../utils/getCsrfToken.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { ToastData } from "../../types/ToastData.ts";
import Datetime from "react-datetime";
import "react-datetime/css/react-datetime.css";
import moment from "moment";
import "moment/dist/locale/de";

moment.locale("de");

interface BestellWizardPersonalDataProps {
  theme: TapirTheme;
  personalData: PersonalData;
  setPersonalData: (personalData: PersonalData) => void;
  sepaAllowed: boolean;
  setSepaAllowed: (sepaAllowed: boolean) => void;
  contractAccepted: boolean;
  setContractAccepted: (contractRead: boolean) => void;
  waitingListModeEnabled: boolean;
  waitingListLinkConfirmationModeEnabled: boolean;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  emailAddressAlreadyInUse: boolean;
  setEmailAddressAlreadyInUse: (emailAddressAlreadyInUse: boolean) => void;
  emailAdresseAlreadyInUseIsKnown: boolean;
  setEmailAdresseAlreadyInUseIsKnown: (
    emailAdresseAlreadyInUseIsKnown: boolean,
  ) => void;
  emailAddressAlreadyInUseLoading: boolean;
  setEmailAddressAlreadyInUseLoading: (
    emailAddressAlreadyInUseLoading: boolean,
  ) => void;
  waitingListEntryDetails?: WaitingListEntryDetails;
}

const BestellWizardPersonalData: React.FC<BestellWizardPersonalDataProps> = ({
  theme,
  personalData,
  setPersonalData,
  sepaAllowed,
  setSepaAllowed,
  contractAccepted,
  setContractAccepted,
  waitingListModeEnabled,
  waitingListLinkConfirmationModeEnabled,
  setToastDatas,
  emailAddressAlreadyInUse,
  setEmailAddressAlreadyInUse,
  emailAdresseAlreadyInUseIsKnown,
  setEmailAdresseAlreadyInUseIsKnown,
  emailAddressAlreadyInUseLoading,
  setEmailAddressAlreadyInUseLoading,
  waitingListEntryDetails,
}) => {
  const [emailAddress, setEmailAddress] = useState("");
  const [controller, setController] = useState<AbortController>();
  const [innerDate, setInnerDate] = useState("");
  const api = useApi(SubscriptionsApi, getCsrfToken());

  useEffect(() => {
    setInnerDate(moment(personalData.birthdate).format("DD.MM.YYYY"));
  }, [personalData]);

  useEffect(() => {
    setEmailAddress(personalData.email);
  }, [personalData]);

  useEffect(() => {
    if (controller) controller.abort();

    if (waitingListLinkConfirmationModeEnabled) {
      setEmailAddressAlreadyInUse(false);
      setEmailAdresseAlreadyInUseIsKnown(false);
      setEmailAddressAlreadyInUseLoading(false);
      return;
    }

    setEmailAdresseAlreadyInUseIsKnown(false);

    if (!isEmailValid(emailAddress)) {
      return;
    }

    setEmailAddressAlreadyInUseLoading(true);
    const localController = new AbortController();
    setController(localController);

    api
      .subscriptionsApiIsEmailAddressValidRetrieve(
        { email: emailAddress },
        { signal: localController.signal },
      )
      .then((valid) => {
        setEmailAddressAlreadyInUse(!valid);
        setEmailAdresseAlreadyInUseIsKnown(true);
      })
      .catch(async (error) => {
        if (error.cause && error.cause.name === "AbortError") return;
        await handleRequestError(
          error,
          "Fehler beim Prüfen der Mail-Gültigkeit",
          setToastDatas,
        );
      })
      .finally(() => setEmailAddressAlreadyInUseLoading(false));
  }, [emailAddress, waitingListLinkConfirmationModeEnabled]);

  function updatePersonalData() {
    setPersonalData(Object.assign({}, personalData));
  }

  return (
    <>
      <Row>
        <Col className={""}>
          <BestellWizardCardTitle text={"Deine persönliche Daten"} />
        </Col>
      </Row>
      <Row>
        <Col>
          <Form.Group>
            <Form.Label>Vorname</Form.Label>
            <Form.Control
              value={personalData.firstName}
              onChange={(event) => {
                personalData.firstName = event.target.value;
                updatePersonalData();
              }}
              placeholder={"Vorname"}
              disabled={waitingListLinkConfirmationModeEnabled}
            />
          </Form.Group>
        </Col>
        <Col>
          <Form.Group>
            <Form.Label>Nachname</Form.Label>
            <Form.Control
              value={personalData.lastName}
              onChange={(event) => {
                personalData.lastName = event.target.value;
                updatePersonalData();
              }}
              placeholder={"Nachname"}
              disabled={waitingListLinkConfirmationModeEnabled}
            />
          </Form.Group>
        </Col>
      </Row>
      <Row className={"mt-2"}>
        <Col>
          <Form.Group>
            <Form.Label>
              E-Mail-Adresse{" "}
              {emailAddressAlreadyInUseLoading && <Spinner size={"sm"} />}
            </Form.Label>
            <Form.Control
              value={personalData.email}
              onChange={(event) => {
                personalData.email = event.target.value;
                updatePersonalData();
              }}
              type="email"
              placeholder={"E-Mail-Adresse"}
              isInvalid={
                personalData.email !== "" &&
                (!isEmailValid(personalData.email) ||
                  (emailAdresseAlreadyInUseIsKnown && emailAddressAlreadyInUse))
              }
              disabled={waitingListLinkConfirmationModeEnabled}
            />
            {emailAdresseAlreadyInUseIsKnown && emailAddressAlreadyInUse && (
              <Form.Control.Feedback type="invalid">
                Diese Email-Adresse ist schon vergeben
              </Form.Control.Feedback>
            )}
          </Form.Group>
        </Col>
        <Col>
          <Form.Group>
            <Form.Label>Telefon-Nr</Form.Label>
            <Form.Control
              value={personalData.phoneNumber}
              onChange={(event) => {
                personalData.phoneNumber = event.target.value;
                updatePersonalData();
              }}
              placeholder={"Telefon-Nr"}
              type={"tel"}
              isInvalid={
                personalData.phoneNumber !== "" &&
                !isPhoneNumberValid(personalData.phoneNumber)
              }
              disabled={waitingListLinkConfirmationModeEnabled}
            />
          </Form.Group>
        </Col>
      </Row>
      <Row className={"mt-2"}>
        <Col>
          <Form.Group>
            <Form.Label>Straße & Hausnummer</Form.Label>
            <Form.Control
              value={personalData.street}
              onChange={(event) => {
                personalData.street = event.target.value;
                updatePersonalData();
              }}
              placeholder={"Straße & Hausnummer"}
              disabled={waitingListLinkConfirmationModeEnabled}
            />
          </Form.Group>
        </Col>
        <Col>
          <Form.Group>
            <Form.Label>Adresszusatz</Form.Label>
            <Form.Control
              value={personalData.street2}
              onChange={(event) => {
                personalData.street2 = event.target.value;
                updatePersonalData();
              }}
              placeholder={"Adresszusatz"}
              disabled={waitingListLinkConfirmationModeEnabled}
            />
          </Form.Group>
        </Col>
      </Row>
      <Row className={"mt-2"}>
        <Col>
          <Form.Group>
            <Form.Label>Postleitzahl</Form.Label>
            <Form.Control
              value={personalData.postcode}
              onChange={(event) => {
                personalData.postcode = event.target.value;
                updatePersonalData();
              }}
              placeholder={"Postleitzahl"}
              disabled={waitingListLinkConfirmationModeEnabled}
            />
          </Form.Group>
        </Col>
        <Col>
          <Form.Group>
            <Form.Label>Stadt</Form.Label>
            <Form.Control
              value={personalData.city}
              onChange={(event) => {
                personalData.city = event.target.value;
                updatePersonalData();
              }}
              placeholder={"Stadt"}
              disabled={waitingListLinkConfirmationModeEnabled}
            />
          </Form.Group>
        </Col>
      </Row>
      <Row className={"mt-2"}>
        <Col>
          <Form.Group>
            <Form.Label>Land</Form.Label>
            <Form.Control value={"Deutschland"} disabled={true} />
          </Form.Group>
        </Col>
        <Col>
          {!waitingListModeEnabled && (
            <Form.Group>
              <Form.Label>
                <span
                  className={
                    personalData.birthdate !== undefined &&
                    !isBirthdateValid(personalData.birthdate)
                      ? "text-danger"
                      : ""
                  }
                >
                  Geburtsdatum
                </span>
              </Form.Label>
              <Datetime
                value={innerDate}
                timeFormat={false}
                dateFormat={true}
                onChange={(changedValue) => {
                  if (moment.isMoment(changedValue)) {
                    setInnerDate(changedValue.format("DD.MM.YYYY"));
                    personalData.birthdate = changedValue.toDate();
                    updatePersonalData();
                  } else {
                    setInnerDate(changedValue);
                  }
                }}
                inputProps={{
                  disabled: waitingListEntryDetails?.memberAlreadyExists,
                }}
              />
            </Form.Group>
          )}
        </Col>
      </Row>

      {!waitingListModeEnabled && (
        <>
          {" "}
          <Row className={"mt-2"}>
            <Col>
              <Form.Label>Kontoinhaber*in</Form.Label>
              <Form.Control
                value={personalData.accountOwner}
                onChange={(event) => {
                  personalData.accountOwner = event.target.value;
                  updatePersonalData();
                }}
                placeholder={"Kontoinhaber*in"}
              />
            </Col>
            <Col>
              <Form.Group>
                <Form.Label>IBAN</Form.Label>
                <Form.Control
                  value={personalData.iban}
                  onChange={(event) => {
                    personalData.iban = event.target.value;
                    updatePersonalData();
                  }}
                  placeholder={"IBAN"}
                  isInvalid={
                    personalData.iban !== "" && !isIbanValid(personalData.iban)
                  }
                />
              </Form.Group>
            </Col>
          </Row>
          <Row className={"mt-4"}>
            <Col>
              <Row>
                <Col>
                  <BestellWizardCardSubtitle text={"Erteilung SEPA-Mandat"} />
                </Col>
              </Row>
              <Row className={"mt-2"}>
                <Col>
                  <Form.Check
                    id={"sepa-mandat"}
                    label={getTextSepaCheckbox()}
                    checked={sepaAllowed}
                    onChange={(event) => setSepaAllowed(event.target.checked)}
                  />
                </Col>
                <Col>
                  <Form.Check
                    id={"contract"}
                    label={
                      "Ich habe die Vertragsgrundsätze/Gebührenordnung gelesen und akzeptiere diese."
                    }
                    checked={contractAccepted}
                    onChange={(event) =>
                      setContractAccepted(event.target.checked)
                    }
                  />
                  <Form.Text>
                    <a href="https://biotop-oberland.de/gebuehrenordnung">
                      https://biotop-oberland.de/gebuehrenordnung
                    </a>
                  </Form.Text>
                </Col>
              </Row>
            </Col>
          </Row>
        </>
      )}
    </>
  );
};

export default BestellWizardPersonalData;
