import React, { useEffect, useState } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { Form, Modal } from "react-bootstrap";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { PublicProductType } from "../../api-client";
import { sortProductTypes } from "../../bestell_wizard/utils/sortProductTypes.ts";
import { getHtmlDescription } from "../../utils/getHtmlDescription.ts";
import { buildEmptyShoppingCart } from "../../bestell_wizard/utils/buildEmptyShoppingCart.ts";
import { selectAllRequiredProductTypes } from "../../bestell_wizard/utils/selectAllRequiredProductTypes.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { replaceTokens } from "../utils/replaceTokens.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";

interface Step3ProductTypeChoiceProps {
  settings: BestellWizardSettings;
  goToNextStep: () => void;
  firstName: string;
  selectedProductTypes: PublicProductType[];
  setSelectedProductTypes: (types: PublicProductType[]) => void;
  investingMembership: boolean;
  setInvestingMembership: (investing: boolean) => void;
  setShoppingCart: (cart: ShoppingCart) => void;
}

const Step3ProductTypesChoice: React.FC<Step3ProductTypeChoiceProps> = ({
  settings,
  goToNextStep,
  firstName,
  selectedProductTypes,
  setSelectedProductTypes,
  investingMembership,
  setInvestingMembership,
  setShoppingCart,
}) => {
  const [productTypeForModal, setProductTypeForModal] =
    useState<PublicProductType>();

  useEffect(() => {
    if (investingMembership) {
      setSelectedProductTypes([]);
      setShoppingCart(buildEmptyShoppingCart(settings.productTypes));
    } else {
      selectAllRequiredProductTypes(
        settings.productTypes,
        selectedProductTypes,
        setSelectedProductTypes,
      );
    }
  }, [investingMembership]);

  useEffect(() => {
    if (selectedProductTypes.length > 0) {
      setInvestingMembership(false);
    }
  }, [selectedProductTypes]);

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

  function updateSelection(productType: PublicProductType, selected: boolean) {
    let selection;
    if (selected) {
      if (selectedProductTypes.includes(productType)) {
        return;
      }
      selection = [...selectedProductTypes, productType];
    } else {
      selection = selectedProductTypes.filter((pt) => productType.id !== pt.id);
    }
    setSelectedProductTypes(sortProductTypes(selection));
  }

  return (
    <>
      {settings.strings.step3Text && (
        <p className={"text-center"}>
          {replaceTokens(settings.strings.step3Text, firstName)}
        </p>
      )}
      <div>
        {settings.productTypes.map((productType) => (
          <Form.Group
            key={"checkbox_" + productType.id}
            controlId={"control_" + productType.id}
          >
            <div className={"d-flex flex-row gap-2 align-items-center"}>
              <Form.Check
                label={productType.name}
                checked={selectedProductTypes.includes(productType)}
                onChange={(event) =>
                  updateSelection(productType, event.target.checked)
                }
                disabled={productType.mustBeSubscribedTo}
              />
              <TapirButton
                icon={"help"}
                variant={BUTTON_VARIANT}
                size={"sm"}
                onClick={() => setProductTypeForModal(productType)}
              />
            </div>
          </Form.Group>
        ))}
        <Form.Group controlId={"investing"}>
          <Form.Check
            label={"Fördermitgliedschaft"}
            checked={investingMembership}
            onChange={(event) => setInvestingMembership(event.target.checked)}
          />
        </Form.Group>
      </div>
      <NextStepButton onClick={goToNextStep} />
      <Modal
        show={productTypeForModal !== undefined}
        fullscreen={"md-down"}
        centered={true}
        onHide={() => setProductTypeForModal(undefined)}
      >
        <Modal.Header closeButton={true}>
          {productTypeForModal?.name}
        </Modal.Header>
        <Modal.Body>{getModalText()}</Modal.Body>
      </Modal>
    </>
  );
};

export default Step3ProductTypesChoice;
