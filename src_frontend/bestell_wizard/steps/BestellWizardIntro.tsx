import React, { useEffect } from "react";
import { PublicProductType } from "../../api-client";
import { sortProductTypes } from "../utils/sortProductTypes.ts";
import { Form, Spinner } from "react-bootstrap";
import BestellWizardCardSubtitle from "../components/BestellWizardCardSubtitle.tsx";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { buildEmptyShoppingCart } from "../utils/buildEmptyShoppingCart.ts";
import { selectAllRequiredProductTypes } from "../utils/selectAllRequiredProductTypes.ts";
import { BestellWizardSettings } from "../types/BestellWizardSettings.ts";

interface BestellWizardIntroProps {
  selectedProductTypes: PublicProductType[];
  setSelectedProductTypes: (selectedProductTypes: PublicProductType[]) => void;
  investingMembership: boolean;
  setInvestingMembership: (investing: boolean) => void;
  setShoppingCart: (cart: ShoppingCart) => void;
  waitingListLinkConfirmationModeEnabled: boolean;
  settings: BestellWizardSettings;
}

const BestellWizardIntro: React.FC<BestellWizardIntroProps> = ({
  selectedProductTypes,
  setSelectedProductTypes,
  investingMembership,
  setInvestingMembership,
  setShoppingCart,
  waitingListLinkConfirmationModeEnabled,
  settings,
}) => {
  function getHtmlDescription(description: string) {
    return { __html: description };
  }

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

  function updateProductSelection(
    productType: PublicProductType,
    checked: boolean,
  ) {
    if (checked) {
      selectedProductTypes.push(productType);
    } else {
      selectedProductTypes = selectedProductTypes.filter(
        (existingType) => existingType.id !== productType.id,
      );
    }
    setSelectedProductTypes([...sortProductTypes(selectedProductTypes)]);
  }

  return (
    <>
      <span dangerouslySetInnerHTML={{ __html: settings.introStepText }} />
      <BestellWizardCardSubtitle
        text={"Welche Mitgliedschaft(en) möchtest du?"}
      />
      <div className={"d-flex flex-column gap-3"}>
        {settings.productTypes.length === 0 ? (
          <Spinner style={{ width: "10rem", height: "10rem" }} />
        ) : (
          settings.productTypes.map((publicProductType) => (
            <div
              key={publicProductType.id}
              className={"d-flex flex-column gap-2"}
            >
              <Form.Check
                id={publicProductType.id}
                label={publicProductType.name}
                onChange={(event) =>
                  updateProductSelection(
                    publicProductType,
                    event.target.checked,
                  )
                }
                checked={selectedProductTypes.includes(publicProductType)}
                disabled={
                  (publicProductType.mustBeSubscribedTo &&
                    selectedProductTypes.includes(publicProductType)) ||
                  waitingListLinkConfirmationModeEnabled
                }
              />
              <span>
                {!publicProductType.descriptionBestellwizardShort ? (
                  "No description"
                ) : (
                  <span
                    dangerouslySetInnerHTML={getHtmlDescription(
                      publicProductType.descriptionBestellwizardShort,
                    )}
                  ></span>
                )}
              </span>
              {publicProductType.forceWaitingList && (
                <Form.Text>
                  Derzeit nur Wartelisten-Eintragung möglich.
                </Form.Text>
              )}
            </div>
          ))
        )}
        {settings.allowInvestingMembership && settings.showCoopContent && (
          <div>
            <Form.Check
              id={"investingMembership"}
              label={"Fördermitgliedschaft in Genossenschaft"}
              onChange={(event) => setInvestingMembership(event.target.checked)}
              checked={investingMembership}
              disabled={waitingListLinkConfirmationModeEnabled}
            />
            <span>
              Werde Teil des Biotops und unterstütze die Genossenschaft als
              Fördermitglied der Genossenschaft ohne weiteren Vertrag.
            </span>
          </div>
        )}
      </div>
    </>
  );
};

export default BestellWizardIntro;
