import React from "react";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { Col, Form, Row } from "react-bootstrap";
import { PersonalData } from "../types/PersonalData.ts";
import dayjs from "dayjs";
import BestellWizardCardTitle from "../components/BestellWizardCardTitle.tsx";
import BestellWizardCardSubtitle from "../components/BestellWizardCardSubtitle.tsx";
import { isIbanValid } from "../utils/isIbanValid.ts";
import { isEmailValid } from "../utils/isEmailValid.ts";
import { isPhoneNumberValid } from "../utils/isPhoneNumberValid.ts";
import { isBirthdateValid } from "../utils/isBirthdateValid.ts";
import { getTextSepaCheckbox } from "../utils/getTextSepaCheckbox.ts";

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
}) => {
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
            <Form.Label>E-Mail-Adresse</Form.Label>
            <Form.Control
              value={personalData.email}
              onChange={(event) => {
                personalData.email = event.target.value;
                updatePersonalData();
              }}
              type="email"
              placeholder={"E-Mail-Adresse"}
              isInvalid={
                personalData.email !== "" && !isEmailValid(personalData.email)
              }
              disabled={waitingListLinkConfirmationModeEnabled}
            />
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
              <Form.Label>Geburtsdatum</Form.Label>
              <Form.Control
                onChange={(event) => {
                  personalData.birthdate = new Date(event.target.value);
                  updatePersonalData();
                }}
                value={dayjs(personalData.birthdate).format("YYYY-MM-DD")}
                placeholder={"Geburtsdatum"}
                type={"date"}
                isInvalid={
                  personalData.birthdate !== undefined &&
                  !isBirthdateValid(personalData.birthdate)
                }
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
