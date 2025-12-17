import React, { useEffect, useState } from "react";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import PersonalDataFormControl from "../components/PersonalDataFormControl.tsx";
import { Form, Modal } from "react-bootstrap";
import NextStepButton from "../components/NextStepButton.tsx";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import TapirCheckbox from "../components/TapirCheckbox.tsx";
import { isIbanValid } from "../../bestell_wizard/utils/isIbanValid.ts";
import { PublicProductType } from "../../api-client";
import { atLeastOneMonthlyPayment } from "../utils/atLeastOneMonthlyPayment.ts";

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
  active: boolean;
  productTypesInWaitingList: Set<PublicProductType>;
  isOrderStep: boolean;
  orderLoading: boolean;
  nextButtonText?: string;
  canChangePaymentRhythm: boolean;
}

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
  active,
  productTypesInWaitingList,
  isOrderStep,
  orderLoading,
  nextButtonText,
  canChangePaymentRhythm,
}) => {
  const [accountOwnerSetManually, setAccountOwnerSetManually] = useState(false);
  const [paymentRhythmModalOpen, setPaymentRhythmModalOpen] = useState(false);
  const [showValidation, setShowValidation] = useState(false);

  useEffect(() => {
    if (!active) {
      setTimeout(() => setShowValidation(false), 200);
    }
  }, [active]);

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
    setPersonalData({ ...personalData });
  }, [personalData]);

  function validate() {
    setShowValidation(true);
    if (personalData.accountOwner.length === 0) {
      return;
    }

    if (!isIbanValid(personalData.iban)) {
      return;
    }

    if (!contractAccepted || !sepaAllowed) {
      return;
    }

    goToNextStep();
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
          showValidation={showValidation}
          isValid={personalData.accountOwner.length > 0}
        />
        <PersonalDataFormControl
          personalData={personalData}
          setPersonalData={setPersonalData}
          field={"iban"}
          placeholder={getPlaceholder("iban")}
          type={"text"}
          showValidation={showValidation}
          isValid={isIbanValid(personalData.iban)}
          extraText={
            showValidation && !isIbanValid(personalData.iban)
              ? "Ungültige IBAN"
              : ""
          }
        />
        {atLeastOneMonthlyPayment(
          shoppingCart,
          productTypesInWaitingList,
          solidarityContribution,
        ) &&
          Object.entries(settings.paymentRhythmChoices).length > 1 && (
            <div className={"d-flex flex-row gap-2"}>
              <Form.FloatingLabel
                label={"Zahlungsintervall"}
                style={{ flexGrow: 1 }}
              >
                <Form.Select
                  value={personalData.paymentRhythm}
                  onChange={(event) => {
                    personalData.paymentRhythm = event.target.value;
                    setPersonalData({ ...personalData });
                  }}
                  disabled={!canChangePaymentRhythm}
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
        <div className={"d-flex flex-column gap-2 mx-2"}>
          <TapirCheckbox
            onChange={setSepaAllowed}
            checked={sepaAllowed}
            label={settings.labelCheckboxSepaMandat}
            controlId={"sepa"}
            showError={showValidation && !sepaAllowed}
          />
          <TapirCheckbox
            onChange={setContractAccepted}
            checked={contractAccepted}
            label={settings.labelCheckboxContractPolicy}
            controlId={"contract"}
            showError={showValidation && !contractAccepted}
          />
        </div>
      </div>
      <NextStepButton
        onClick={validate}
        loading={orderLoading}
        isOrderStep={isOrderStep}
        text={nextButtonText}
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
