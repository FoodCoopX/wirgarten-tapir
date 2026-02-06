import React, { useEffect, useRef, useState } from "react";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { Accordion } from "react-bootstrap";
import NextStepButton from "../components/NextStepButton.tsx";
import { scrollIntoView } from "../utils/scrollIntoView.ts";
import TapirCheckbox from "../components/TapirCheckbox.tsx";
import { isAtLeastOneProductOrdered } from "../../bestell_wizard/utils/isAtLeastOneProductOrdered.ts";
import { buildFilteredShoppingCart } from "../../bestell_wizard/utils/buildFilteredShoppingCart.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { PublicProductType } from "../../api-client";

interface Step11LegalProps {
  settings: BestellWizardSettings;
  cancellationPolicyRead: boolean;
  setCancellationPolicyRead: (read: boolean) => void;
  privacyPolicyRead: boolean;
  setPrivacyPolicyRead: (read: boolean) => void;
  active: boolean;
  goToNextStep: () => void;
  shoppingCart: ShoppingCart;
  productTypesInWaitingList: Set<PublicProductType>;
  solidarityContribution: number;
}

const Step11Legal: React.FC<Step11LegalProps> = ({
  settings,
  cancellationPolicyRead,
  setCancellationPolicyRead,
  privacyPolicyRead,
  setPrivacyPolicyRead,
  active,
  goToNextStep,
  shoppingCart,
  productTypesInWaitingList,
  solidarityContribution,
}) => {
  const scrollDiv = useRef<HTMLDivElement>(null);
  const [showValidation, setShowValidation] = useState(false);

  useEffect(() => {
    if (!active) {
      setTimeout(() => setShowValidation(false), 200);
    }
  }, [active]);

  useEffect(() => {
    if (!active || !scrollDiv.current) {
      return;
    }

    scrollDiv.current.scrollTop = 0;
  }, [active]);

  function validate() {
    setShowValidation(true);

    if (showCheckboxCancellationPolicy() && !cancellationPolicyRead) {
      return;
    }

    if (!privacyPolicyRead) {
      return;
    }

    goToNextStep();
  }

  function showCheckboxCancellationPolicy() {
    if (
      isAtLeastOneProductOrdered(
        buildFilteredShoppingCart(
          shoppingCart,
          false,
          productTypesInWaitingList,
        ),
      )
    ) {
      return true;
    }

    return solidarityContribution > 0;
  }

  return (
    <>
      {showCheckboxCancellationPolicy() && (
        <Accordion style={{ width: "100%" }}>
          <Accordion.Item eventKey={"cancellation"} onClick={scrollIntoView}>
            <Accordion.Header>
              <TapirCheckbox
                controlId={"legal_cancellation"}
                checked={cancellationPolicyRead}
                onChange={setCancellationPolicyRead}
                label={settings.strings.step11RevocationLabel}
                showError={showValidation && !cancellationPolicyRead}
              />
            </Accordion.Header>
            <Accordion.Body>
              <span
                dangerouslySetInnerHTML={{
                  __html: settings.strings.step11RevocationText,
                }}
              />
            </Accordion.Body>
          </Accordion.Item>
        </Accordion>
      )}
      <Accordion style={{ width: "100%" }}>
        <Accordion.Item eventKey={"privacy"} onClick={scrollIntoView}>
          <Accordion.Header>
            <TapirCheckbox
              controlId={"legal_privacy"}
              checked={privacyPolicyRead}
              onChange={setPrivacyPolicyRead}
              label={settings.strings.step11PrivacyPolicyLabel}
              showError={showValidation && !privacyPolicyRead}
            />
          </Accordion.Header>
          <Accordion.Body>
            <span
              dangerouslySetInnerHTML={{
                __html: settings.strings.step11PrivacyPolicyText.replace(
                  "{link_zu_datenschutzerklärung}",
                  settings.strings.privacyPolicyUrl,
                ),
              }}
            />
          </Accordion.Body>
        </Accordion.Item>
      </Accordion>

      <NextStepButton onClick={validate} />
    </>
  );
};

export default Step11Legal;
