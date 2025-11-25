import React, { useEffect, useState } from "react";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import PersonalDataFormControl from "../components/PersonalDataFormControl.tsx";
import { Form, Modal } from "react-bootstrap";
import NextStepButton from "../components/NextStepButton.tsx";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { isAtLeastOneProductOrdered } from "../../bestell_wizard/utils/isAtLeastOneProductOrdered.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";

interface Step9BankingDataProps {
  goToNextStep: () => void;
  personalData: PersonalData;
  setPersonalData: (personalData: PersonalData) => void;
  sepaAllowed: boolean;
  setSepaAllowed: (sepaAllowed: boolean) => void;
  contractAccepted: boolean;
  setContractAccepted: (contractRead: boolean) => void;
  settings: BestellWizardSettings;
  shoppingCart: ShoppingCart;
  solidarityContribution: number;
}

const Step9BankingData: React.FC<Step9BankingDataProps> = ({
  goToNextStep,
  personalData,
  setPersonalData,
  sepaAllowed,
  setSepaAllowed,
  contractAccepted,
  setContractAccepted,
  settings,
  shoppingCart,
  solidarityContribution,
}) => {
  const [accountOwnerSetManually, setAccountOwnerSetManually] = useState(false);
  const [paymentRhythmModalOpen, setPaymentRhythmModalOpen] = useState(false);

  useEffect(() => {
    if (accountOwnerSetManually) {
      return;
    }

    const newAccountOwner =
      personalData.firstName + " " + personalData.lastName;
    if (personalData.accountOwner === newAccountOwner) {
      return;
    }

    personalData.accountOwner = newAccountOwner;
    setPersonalData(Object.assign({}, personalData));
  }, [personalData]);

  function getPlaceholder(key: keyof PersonalData) {
    switch (key) {
      case "accountOwner":
        return "Kontoinhaber";
      case "iban":
        return "IBAN";
      default:
        return key;
    }
  }

  return (
    <>
      <div className={"d-flex flex-column gap-2"} style={{ width: "100%" }}>
        <PersonalDataFormControl
          personalData={personalData}
          setPersonalData={(newData) => {
            setAccountOwnerSetManually(true);
            setPersonalData(newData);
          }}
          field={"accountOwner"}
          placeholder={getPlaceholder("accountOwner")}
          type={"text"}
        />
        <PersonalDataFormControl
          personalData={personalData}
          setPersonalData={setPersonalData}
          field={"iban"}
          placeholder={getPlaceholder("iban")}
          type={"text"}
        />
        {(isAtLeastOneProductOrdered(shoppingCart) ||
          solidarityContribution > 0) &&
          Object.entries(settings.paymentRhythmChoices).length > 1 && (
            <div className={"d-flex flex-row gap-2"}>
              <Form.FloatingLabel label={"Zahlungsintervall"}>
                <Form.Select
                  value={personalData.paymentRhythm}
                  onChange={(event) => {
                    personalData.paymentRhythm = event.target.value;
                    setPersonalData(Object.assign({}, personalData));
                  }}
                >
                  {Object.entries(settings.paymentRhythmChoices).map(
                    ([rhythm, displayName]) => (
                      <option key={rhythm} value={rhythm}>
                        {displayName}
                      </option>
                    ),
                  )}
                </Form.Select>
              </Form.FloatingLabel>
              <TapirButton
                icon={"help"}
                variant={BUTTON_VARIANT}
                onClick={() => setPaymentRhythmModalOpen(true)}
              />
            </div>
          )}
        <Form.Group controlId={"sepa"}>
          <Form.Check
            onChange={(event) => setSepaAllowed(event.target.checked)}
            required={true}
            checked={sepaAllowed}
            label={settings.labelCheckboxSepaMandat}
          />
        </Form.Group>
        <Form.Group controlId={"contract"}>
          <Form.Check
            onChange={(event) => setContractAccepted(event.target.checked)}
            required={true}
            checked={contractAccepted}
            label={<span>{settings.labelCheckboxContractPolicy}</span>}
          />
        </Form.Group>
      </div>
      <NextStepButton
        onClick={goToNextStep}
        disabled={!sepaAllowed || !contractAccepted}
      />
      <Modal
        show={paymentRhythmModalOpen}
        onHide={() => setPaymentRhythmModalOpen(false)}
        centered={true}
      >
        <Modal.Header closeButton={true}>Zahlungsintervalle</Modal.Header>
        <Modal.Body>
          <span
            dangerouslySetInnerHTML={{
              __html: settings.strings.step9PaymentRhythmModalText,
            }}
          ></span>
        </Modal.Body>
      </Modal>
    </>
  );
};

export default Step9BankingData;
