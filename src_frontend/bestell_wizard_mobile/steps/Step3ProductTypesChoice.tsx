import React, { useEffect, useState } from "react";
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
import "./Step3ProductTypesChoice.css";

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
        <div id={"product_types_choice"} className={"d-flex gap-2"}>
          {settings.productTypes.map((productType) => (
            <div key={productType.id}>
              <input
                type="checkbox"
                className="btn-check"
                id={productType.id}
                autoComplete="off"
                onChange={(event) =>
                  updateSelection(productType, event.target.checked)
                }
                checked={selectedProductTypes.includes(productType)}
                disabled={productType.mustBeSubscribedTo}
              />
              <label
                className={"btn btn-" + BUTTON_VARIANT}
                htmlFor={productType.id}
              >
                <div className={"d-flex flex-row gap-2 align-items-center"}>
                  <Form.Check
                    checked={selectedProductTypes.includes(productType)}
                    readOnly={true}
                    style={{ pointerEvents: "none" }}
                  />
                  {productType.iconLink && (
                    <img
                      src={productType.iconLink}
                      alt={"Produkt-Icon"}
                      style={{ height: "1.5rem" }}
                    />
                  )}
                  <span>{productType.name}</span>
                </div>
              </label>
            </div>
          ))}
        </div>

        <hr />
        <div className={"d-flex justify-content-center"}>
          <input
            type="checkbox"
            className="btn-check"
            id={"investing"}
            autoComplete="off"
            onChange={(event) => setInvestingMembership(event.target.checked)}
            checked={investingMembership}
          />
          <label className={"btn btn-" + BUTTON_VARIANT} htmlFor={"investing"}>
            <div className={"d-flex flex-row gap-2 align-items-center"}>
              <Form.Check
                checked={investingMembership}
                style={{ pointerEvents: "none" }}
                readOnly={true}
              />
              <span>Fördermitgliedschaft</span>
            </div>
          </label>
        </div>
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
