import React, { useState } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { Form } from "react-bootstrap";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { PublicProductType } from "../../api-client";
import ConfirmModal from "../../components/ConfirmModal.tsx";

interface Step3ProductTypeChoiceProps {
  settings: BestellWizardSettings;
  goToNextStep: () => void;
  firstName: string;
}

const Step3ProductTypesChoice: React.FC<Step3ProductTypeChoiceProps> = ({
  settings,
  goToNextStep,
  firstName,
}) => {
  const [productTypeForModal, setProductTypeForModal] =
    useState<PublicProductType>();

  function insertFirstName(input: string) {
    return input.replace("{vorname}", firstName);
  }

  function getHtmlDescription(description: string) {
    return { __html: description };
  }

  function getModalText() {
    if (productTypeForModal === undefined) {
      return "Kein Produkt ausgewählt";
    }

    if (!productTypeForModal.descriptionBestellwizardShort) {
      return "Beschreibung fehlt";
    }

    return (
      <span
        dangerouslySetInnerHTML={getHtmlDescription(
          productTypeForModal.descriptionBestellwizardShort,
        )}
      />
    );
  }

  return (
    <>
      <div
        style={{ height: "100%" }}
        className={
          "d-flex align-items-center justify-content-center gap-2 flex-column"
        }
      >
        {settings.strings.step3Title && (
          <h1 className={"text-center"}>
            {insertFirstName(settings.strings.step3Title)}
          </h1>
        )}
        {settings.strings.step3Text && (
          <p className={"text-center"}>
            {insertFirstName(settings.strings.step3Text)}
          </p>
        )}
        <div>
          {settings.productTypes.map((productType) => (
            <Form.Group key={productType.id} controlId={productType.id}>
              <div className={"d-flex flex-row gap-2 align-items-center"}>
                <Form.Check label={productType.name} />
                <TapirButton
                  icon={"help"}
                  variant={"outline-secondary"}
                  size={"sm"}
                  onClick={() => setProductTypeForModal(productType)}
                />
              </div>
            </Form.Group>
          ))}
          <Form.Group controlId={"investing"}>
            <Form.Check label={"Fördermitgliedschaft"} />
          </Form.Group>
        </div>
        <TapirButton
          variant={"outline-secondary"}
          text={"Weiter"}
          onClick={goToNextStep}
        />
      </div>
      {productTypeForModal && (
        <ConfirmModal
          open={true}
          onConfirm={() => alert("WIP")}
          confirmButtonIcon={"select_check_box"}
          onCancel={() => setProductTypeForModal(undefined)}
          title={productTypeForModal.name}
          message={getModalText()}
          confirmButtonText={"Ich habe Interesse"}
          confirmButtonVariant={"outline-secondary"}
        />
      )}
    </>
  );
};

export default Step3ProductTypesChoice;
