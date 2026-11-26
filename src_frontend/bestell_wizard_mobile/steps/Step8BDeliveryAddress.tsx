import React, { useEffect, useState } from "react";
import { FloatingLabel, Form } from "react-bootstrap";
import { DeliveryAddressRequest } from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import TapirCheckbox from "../components/TapirCheckbox.tsx";
import { isDeliveryAddressValid } from "../utils/isDeliveryAddressValid.ts";

interface Step8BDeliveryAddressProps {
  settings: BestellWizardSettings;
  goToNextStep: () => void;
  deliveryAddress: DeliveryAddressRequest;
  setDeliveryAddress: (deliveryAddress: DeliveryAddressRequest) => void;
  stepActive: boolean;
}

type AddressField = "street" | "street2" | "postcode" | "city";

const FIELDS: { field: AddressField; label: string; required: boolean }[] = [
  { field: "street", label: "Straße & Hausnummer", required: true },
  { field: "street2", label: "Adresszusatz (optional)", required: false },
  { field: "postcode", label: "Postleitzahl", required: true },
  { field: "city", label: "Stadt", required: true },
];

const Step8BDeliveryAddress: React.FC<Step8BDeliveryAddressProps> = ({
  settings,
  goToNextStep,
  deliveryAddress,
  setDeliveryAddress,
  stepActive,
}) => {
  const [showValidation, setShowValidation] = useState(false);

  useEffect(() => {
    if (!stepActive) {
      setTimeout(() => setShowValidation(false), 200);
    }
  }, [stepActive]);

  function validate() {
    setShowValidation(true);

    if (isDeliveryAddressValid(deliveryAddress)) {
      goToNextStep();
    }
  }

  function isFieldValid(field: AddressField, required: boolean) {
    return !required || (deliveryAddress[field] ?? "").trim().length > 0;
  }

  return (
    <div className={"d-flex flex-column gap-2 align-items-center"}>
      <div
        className={"text-center"}
        dangerouslySetInnerHTML={{
          __html: settings.strings.homeDeliveryChoiceText,
        }}
      />
      <TapirCheckbox
        checked={deliveryAddress.sameAsBillingAddress}
        onChange={(checked) =>
          setDeliveryAddress({
            ...deliveryAddress,
            sameAsBillingAddress: checked,
          })
        }
        label={"Lieferadresse entspricht der Rechnungsadresse"}
        controlId={"delivery_same_as_billing_address"}
      />
      {!deliveryAddress.sameAsBillingAddress && (
        <div
          className={"d-flex gap-2 flex-wrap align-items-start"}
          style={{ maxWidth: "540px" }}
        >
          {FIELDS.map(({ field, label, required }) => (
            <FloatingLabel
              key={field}
              label={label}
              controlId={"delivery_" + field}
              style={{ width: "264px" }}
            >
              <Form.Control
                placeholder={label}
                value={deliveryAddress[field] ?? ""}
                onChange={(event) =>
                  setDeliveryAddress({
                    ...deliveryAddress,
                    [field]: event.target.value,
                  })
                }
                size={"sm"}
                isValid={showValidation && isFieldValid(field, required)}
                isInvalid={showValidation && !isFieldValid(field, required)}
              />
            </FloatingLabel>
          ))}
        </div>
      )}
      <NextStepButton onClick={validate} stepActive={stepActive} />
    </div>
  );
};

export default Step8BDeliveryAddress;
