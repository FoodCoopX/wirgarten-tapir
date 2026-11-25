import React, { useEffect, useState } from "react";
import { Form, Modal } from "react-bootstrap";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { isIbanValid } from "../../bestell_wizard/utils/isIbanValid.ts";
import CheckboxWithExplanation from "../../bestell_wizard_mobile/components/CheckboxWithExplanation.tsx";
import NextStepButton from "../../components/mobile_wizard/NextStepButton.tsx";
import { BUTTON_VARIANT } from "../../components/mobile_wizard/utils/BUTTON_VARIANT.ts";
import TapirButton from "../../components/TapirButton.tsx";

interface BiddingRoundSepaStepProps {
  settings: BestellWizardSettings;
  accountOwner: string;
  setAccountOwner: (value: string) => void;
  iban: string;
  setIban: (value: string) => void;
  paymentRhythm: string;
  setPaymentRhythm: (value: string) => void;
  sepaAllowed: boolean;
  setSepaAllowed: (value: boolean) => void;
  goToNextStep: () => void;
  stepActive: boolean;
}

const BiddingRoundSepaStep: React.FC<BiddingRoundSepaStepProps> = ({
  settings,
  accountOwner,
  setAccountOwner,
  iban,
  setIban,
  paymentRhythm,
  setPaymentRhythm,
  sepaAllowed,
  setSepaAllowed,
  goToNextStep,
  stepActive,
}) => {
  const [showValidation, setShowValidation] = useState(false);
  const [paymentRhythmModalOpen, setPaymentRhythmModalOpen] = useState(false);

  useEffect(() => {
    if (!stepActive) {
      setTimeout(() => setShowValidation(false), 200);
    }
  }, [stepActive]);

  function validate() {
    setShowValidation(true);

    if (accountOwner.trim().length === 0) {
      return;
    }

    if (!isIbanValid(iban)) {
      return;
    }

    if (!sepaAllowed) {
      return;
    }

    goToNextStep();
  }

  return (
    <>
      <div className={"d-flex flex-column gap-2"} style={{ width: "100%" }}>
        <Form.FloatingLabel label={"Kontoinhaber"}>
          <Form.Control
            placeholder={"Kontoinhaber"}
            value={accountOwner}
            onChange={(event) => setAccountOwner(event.target.value)}
            isInvalid={showValidation && accountOwner.trim().length === 0}
            isValid={showValidation && accountOwner.trim().length > 0}
          />
        </Form.FloatingLabel>
        <Form.FloatingLabel label={"IBAN"}>
          <Form.Control
            placeholder={"IBAN"}
            value={iban}
            onChange={(event) => setIban(event.target.value)}
            isInvalid={showValidation && !isIbanValid(iban)}
            isValid={showValidation && isIbanValid(iban)}
          />
          {showValidation && !isIbanValid(iban) && (
            <Form.Text className={"text-danger"}>Ungültige IBAN</Form.Text>
          )}
        </Form.FloatingLabel>
        {Object.entries(settings.paymentRhythmChoices).length > 1 && (
          <div className={"d-flex flex-row gap-2"}>
            <Form.FloatingLabel
              label={"Zahlungsintervall"}
              style={{ flexGrow: 1 }}
            >
              <Form.Select
                value={paymentRhythm}
                onChange={(event) => setPaymentRhythm(event.target.value)}
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
        <CheckboxWithExplanation
          onChange={setSepaAllowed}
          checked={sepaAllowed}
          label={settings.labelCheckboxSepaMandat}
          explanation={settings.explanationCheckboxSepaMandat}
          controlId={"sepa"}
          showError={showValidation && !sepaAllowed}
        />
      </div>
      <NextStepButton onClick={validate} stepActive={stepActive} />
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
          />
        </Modal.Body>
      </Modal>
    </>
  );
};

export default BiddingRoundSepaStep;
