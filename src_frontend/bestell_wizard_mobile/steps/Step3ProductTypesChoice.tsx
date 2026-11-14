import React, { useEffect, useState } from "react";
import { Form, Modal } from "react-bootstrap";
import { PublicGrowingPeriod, PublicProductType } from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { buildEmptyShoppingCart } from "../../bestell_wizard/utils/buildEmptyShoppingCart.ts";
import { isProductTypeOrdered } from "../../bestell_wizard/utils/isProductTypeOrdered.ts";
import { selectAllRequiredProductTypes } from "../../bestell_wizard/utils/selectAllRequiredProductTypes.ts";
import { sortProductTypes } from "../../bestell_wizard/utils/sortProductTypes.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { getHtmlDescription } from "../../utils/getHtmlDescription.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { replaceTokens } from "../utils/replaceTokens.ts";
import CombinedShareSelection from "./CombinedShareSelection.tsx";
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
  shoppingCart: ShoppingCart;
  combinedShareSelection: boolean;
  checkingCapacities: boolean;
  productTypesInWaitingList: Set<PublicProductType>;
  selectedGrowingPeriod: PublicGrowingPeriod | undefined;
  stepActive: boolean;
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
  shoppingCart,
  combinedShareSelection,
  checkingCapacities,
  productTypesInWaitingList,
  selectedGrowingPeriod,
  stepActive,
}) => {
  const [productTypeForModal, setProductTypeForModal] =
    useState<PublicProductType>();
  const [showError, setShowError] = useState(false);
  const productTypes =
    selectedGrowingPeriod?.productTypes ?? settings.productTypes;

  useEffect(() => {
    if (investingMembership) {
      setSelectedProductTypes([]);
      setShoppingCart(buildEmptyShoppingCart(settings.productTypes));
    } else if (!combinedShareSelection) {
      selectAllRequiredProductTypes(
        selectedGrowingPeriod?.productTypes ?? settings.productTypes,
        selectedProductTypes,
        setSelectedProductTypes,
      );
    }
  }, [investingMembership]);

  useEffect(() => {
    if (!combinedShareSelection && selectedProductTypes.length > 0) {
      setInvestingMembership(false);
    }
  }, [selectedProductTypes]);

  useEffect(() => {
    setShowError(false);
  }, [selectedProductTypes, investingMembership]);

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

  function chooseShare(productType: PublicProductType, productId: string) {
    const nextCart = { ...shoppingCart };
    for (const product of productType.products) {
      nextCart[product.id!] = product.id === productId ? 1 : 0;
    }
    setShoppingCart(nextCart);
    setShowError(false);
  }

  function validate() {
    const orderedTypes = combinedShareSelection
      ? productTypes.filter((type) => isProductTypeOrdered(type, shoppingCart))
      : selectedProductTypes;
    const missingRequiredShare =
      combinedShareSelection &&
      productTypes.some(
        (type) => type.mustBeSubscribedTo && !orderedTypes.includes(type),
      );

    if (
      !investingMembership &&
      (orderedTypes.length === 0 || missingRequiredShare)
    ) {
      setShowError(true);
      return;
    }
    goToNextStep();
  }

  function showInvestingMembership() {
    switch (settings.legalStatus) {
      case "association":
        return settings.associationsAllowInvestingMembership;
      case "coop":
        return settings.allowInvestingMembership;
      case "company":
        return false;
    }
  }

  const intro = (
    <>
      {settings.strings.step3Text && (
        <p
          className={"text-center"}
          dangerouslySetInnerHTML={{
            __html: replaceTokens(settings.strings.step3Text, firstName),
          }}
        />
      )}
    </>
  );

  if (combinedShareSelection) {
    return (
      <>
        {intro}
        <div className="d-flex flex-column gap-3">
          {!settings.forceWaitingList && showInvestingMembership() && (
            <fieldset>
              <legend className="visually-hidden">Teilnahme</legend>
              <Form.Check
                type="radio"
                name="share-participation"
                id="with-shares"
                label="Ich möchte Anteile beziehen"
                checked={!investingMembership}
                onChange={() => setInvestingMembership(false)}
                disabled={!stepActive}
              />
              <Form.Check
                type="radio"
                name="share-participation"
                id="investing"
                label={`${settings.strings.step3SupportingMembershipName} (ohne Anteile)`}
                checked={investingMembership}
                onChange={() => setInvestingMembership(true)}
                disabled={!stepActive}
              />
            </fieldset>
          )}
          {!investingMembership && (
            <CombinedShareSelection
              productTypes={productTypes}
              settings={settings}
              shoppingCart={shoppingCart}
              productTypesInWaitingList={productTypesInWaitingList}
              chooseShare={chooseShare}
              showError={showError}
              stepActive={stepActive}
            />
          )}
        </div>
        <NextStepButton
          onClick={validate}
          loading={checkingCapacities}
          stepActive={stepActive}
        />
      </>
    );
  }

  return (
    <>
      {intro}

      <div>
        <div
          id={"product_types_choice"}
          className={"d-flex gap-2 justify-content-center align-items-center"}
        >
          {sortProductTypes(
            selectedGrowingPeriod?.productTypes ?? settings.productTypes,
          ).map((productType) => (
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
                disabled={
                  productType.mustBeSubscribedTo && !investingMembership
                }
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
                  {productType.descriptionBestellwizardShort && (
                    <TapirButton
                      variant={"outline-secondary"}
                      icon={"help"}
                      size={"sm"}
                      onClick={() => {
                        setProductTypeForModal(productType);
                      }}
                      style={{ pointerEvents: "auto" }}
                    />
                  )}
                </div>
              </label>
            </div>
          ))}
        </div>
        {showInvestingMembership() && (
          <>
            <hr />
            <div className={"d-flex justify-content-center"}>
              <input
                type="checkbox"
                className="btn-check"
                id={"investing"}
                autoComplete="off"
                onChange={(event) =>
                  setInvestingMembership(event.target.checked)
                }
                checked={investingMembership}
              />
              <label
                className={"btn btn-" + BUTTON_VARIANT}
                htmlFor={"investing"}
              >
                <div className={"d-flex flex-row gap-2 align-items-center"}>
                  <Form.Check
                    checked={investingMembership}
                    style={{ pointerEvents: "none" }}
                    readOnly={true}
                  />
                  <span>{settings.strings.step3SupportingMembershipName}</span>
                </div>
              </label>
            </div>
          </>
        )}
        {showError && (
          <>
            <hr />
            <div className={"text-danger text-center"}>
              Wähle mindestens eine Option.
            </div>
          </>
        )}
      </div>
      <NextStepButton onClick={validate} stepActive={stepActive} />
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
