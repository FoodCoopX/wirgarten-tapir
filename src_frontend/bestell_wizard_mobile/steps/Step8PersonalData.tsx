import React, { useEffect, useState } from "react";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";
import PersonalDataFormControl from "../components/PersonalDataFormControl.tsx";
import NextStepButton from "../components/NextStepButton.tsx";
import TapirCheckbox from "../components/TapirCheckbox.tsx";
import { isPersonalDataValidShort } from "../utils/isPersonalDataValidShort.ts";
import { isPhoneNumberValid } from "../../bestell_wizard/utils/isPhoneNumberValid.ts";
import { isEmailValid } from "../../bestell_wizard/utils/isEmailValid.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { useApi } from "../../hooks/useApi.ts";
import { BestellWizardApi } from "../../api-client";
import { getCsrfToken } from "../../utils/getCsrfToken.ts";
import { ToastData } from "../../types/ToastData.ts";
import "./Step8PersonalData.css";

interface Step8PersonalDataProps {
  goToNextStep: () => void;
  personalData: PersonalData;
  setPersonalData: (personalData: PersonalData) => void;
  active: boolean;
  emailAddressAlreadyInUse: boolean;
  setEmailAddressAlreadyInUse: (emailAddressAlreadyInUse: boolean) => void;
  emailAddressAlreadyInUseLoading: boolean;
  setEmailAddressAlreadyInUseLoading: (
    emailAddressAlreadyInUseLoading: boolean,
  ) => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
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
  active,
  emailAddressAlreadyInUse,
  setEmailAddressAlreadyInUse,
  emailAddressAlreadyInUseLoading,
  setEmailAddressAlreadyInUseLoading,
  setToastDatas,
}) => {
  const [isOver18, setIsOver18] = useState(false);
  const [showValidation, setShowValidation] = useState(false);
  const [controller, setController] = useState<AbortController>();
  const bestellWizardApi = useApi(BestellWizardApi, getCsrfToken());

  useEffect(() => {
    if (!active) {
      setTimeout(() => setShowValidation(false), 200);
    }
  }, [active]);

  useEffect(() => {
    if (controller) controller.abort();

    if (!isEmailValid(personalData.email)) {
      return;
    }

    setEmailAddressAlreadyInUseLoading(true);
    const localController = new AbortController();
    setController(localController);

    bestellWizardApi
      .bestellWizardApiIsEmailAddressValidRetrieve(
        { email: personalData.email },
        { signal: localController.signal },
      )
      .then((valid) => {
        setEmailAddressAlreadyInUse(!valid);
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
  }, [personalData.email]);

  function validate() {
    setShowValidation(true);

    if (
      isPersonalDataValidShort(personalData, emailAddressAlreadyInUse) &&
      isOver18
    ) {
      goToNextStep();
    }
  }

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
        return emailAddressAlreadyInUseLoading
          ? "Wird geprüft..."
          : "E-Mail-Adresse";
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

  function isValid(key: keyof PersonalData) {
    switch (key) {
      case "phoneNumber":
        return isPhoneNumberValid(personalData.phoneNumber);
      case "email":
        return (
          isEmailValid(personalData.email) &&
          !emailAddressAlreadyInUse &&
          !emailAddressAlreadyInUseLoading
        );
      case "street2":
        return true;
      default:
        return personalData[key].length > 0;
    }
  }

  return (
    <div className={"d-flex flex-column gap-2 align-items-center"}>
      <div
        id={"personal_data_flex"}
        className={"d-flex gap-2 flex-wrap align-items-start"}
        style={{ maxWidth: "540px" }}
      >
        {FIELDS.map((field) => (
          <PersonalDataFormControl
            personalData={personalData}
            setPersonalData={setPersonalData}
            key={field}
            field={field}
            placeholder={getPlaceholder(field)}
            type={getType(field)}
            showValidation={showValidation}
            isValid={isValid(field)}
            extraText={
              field === "email" &&
              emailAddressAlreadyInUse &&
              !emailAddressAlreadyInUseLoading
                ? "Diese Email-Adresse ist schon vergeben"
                : ""
            }
            style={{ width: "264px" }}
          />
        ))}
      </div>
      <TapirCheckbox
        onChange={setIsOver18}
        checked={isOver18}
        label={"Ich bin über 18 Jahre alt"}
        controlId={"over18"}
        showError={showValidation && !isOver18}
      />
      <NextStepButton onClick={validate} />
    </div>
  );
};

export default Step8PersonalData;
