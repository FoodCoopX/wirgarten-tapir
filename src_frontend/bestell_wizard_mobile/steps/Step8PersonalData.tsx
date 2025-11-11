import React, { useState } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import PersonalDataFormControl from "../Components/PersonalDataFormControl.tsx";
import { Form } from "react-bootstrap";
import { replaceTokens } from "../utils/replaceTokens.ts";

interface Step8PersonalDataProps {
  goToNextStep: () => void;
  personalData: PersonalData;
  setPersonalData: (personalData: PersonalData) => void;
  settings: BestellWizardSettings;
}

const FIELDS: (keyof PersonalData)[] = [
  "firstName",
  "lastName",
  "email",
  "street",
  "street2",
  "postcode",
  "city",
  "phoneNumber",
];

const Step8PersonalData: React.FC<Step8PersonalDataProps> = ({
  goToNextStep,
  personalData,
  setPersonalData,
  settings,
}) => {
  const [isOver18, setIsOver18] = useState(false);

  function getPlaceholder(key: keyof PersonalData) {
    switch (key) {
      case "firstName":
        return "Vorname";
      case "lastName":
        return "Nachname";
      case "street":
        return "Straße & Hausnummer";
      case "street2":
        return "Adresszusatz";
      case "postcode":
        return "Postleitzahl";
      case "city":
        return "Stadt";
      case "email":
        return "E-Mail-Adresse";
      case "phoneNumber":
        return "Telefon-Nr";
      default:
        return key;
    }
  }

  function getType(key: keyof PersonalData) {
    switch (key) {
      case "phoneNumber":
        return "tel";
      case "email":
        return "email";
      default:
        return "text";
    }
  }

  return (
    <div
      style={{ height: "80dvh", display: "flex", flexDirection: "column" }}
      className={"d-flex flex-column gap-2 mx-4"}
    >
      <div
        style={{
          maxHeight: "70dvh",
          overflowY: "scroll",
        }}
      >
        {settings.strings.step8Title && (
          <h3 className={"text-center"}>
            {replaceTokens(settings.strings.step8Title, personalData.firstName)}
          </h3>
        )}
        <div className={"d-flex flex-column gap-2"}>
          {FIELDS.map((field) => (
            <PersonalDataFormControl
              personalData={personalData}
              setPersonalData={setPersonalData}
              key={field}
              field={field}
              placeholder={getPlaceholder(field)}
              type={getType(field)}
            />
          ))}
          <Form.Group controlId={"over18"}>
            <Form.Check
              onChange={(event) => setIsOver18(event.target.checked)}
              required={true}
              checked={isOver18}
              label={"Ich bin über 18 Jahre alt"}
            />
          </Form.Group>
        </div>
      </div>
      <div className={"d-flex flex-row justify-content-center"}>
        <TapirButton
          variant={"outline-secondary"}
          text={"Weiter"}
          onClick={goToNextStep}
          disabled={!isOver18}
          icon={"keyboard_arrow_down"}
          size={"sm"}
        />
      </div>
    </div>
  );
};

export default Step8PersonalData;
