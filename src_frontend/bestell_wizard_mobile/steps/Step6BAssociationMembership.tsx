import React, { useEffect, useState } from "react";
import { Accordion } from "react-bootstrap";
import { AssociationMembershipType } from "../../api-client";
import { getAssociationMembershipTypeCurrentPrice } from "../../association_memberships_config/getAssociationMembershipTypeCurrentPrice.ts";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import TapirCheckbox from "../components/TapirCheckbox.tsx";
import "../utils/flexColOnSmallScreen.css";
import { scrollIntoView } from "../utils/scrollIntoView.ts";

interface Step6BCoopSharesProps {
  goToNextStep: () => void;
  settings: BestellWizardSettings;
  selectedAssociationMembershipType: AssociationMembershipType | undefined;
  setSelectedAssociationMembershipType: React.Dispatch<
    React.SetStateAction<AssociationMembershipType | undefined>
  >;
}

function buildLabel(type: AssociationMembershipType) {
  const currentPrice = getAssociationMembershipTypeCurrentPrice(type);

  if (!currentPrice) {
    return type.name;
  }

  return type.name + " " + formatCurrency(currentPrice.priceAsFloat) + "/Monat";
}

const Step6BCoopShares: React.FC<Step6BCoopSharesProps> = ({
  goToNextStep,
  settings,
  selectedAssociationMembershipType,
  setSelectedAssociationMembershipType,
}) => {
  const [showError, setShowError] = useState(false);

  useEffect(() => {
    setShowError(false);
  }, [selectedAssociationMembershipType]);

  function onNextClicked() {
    if (selectedAssociationMembershipType === undefined) {
      setShowError(true);
      return;
    }

    goToNextStep();
  }

  return (
    <>
      <div style={{ width: "100%" }} className={"d-flex flex-column gap-2"}>
        {settings.associationMembershipTypes.map((type) => (
          <Accordion style={{ width: "100%" }} key={type.id}>
            <Accordion.Item eventKey={type.id!} onClick={scrollIntoView}>
              <Accordion.Header>
                <TapirCheckbox
                  controlId={type.id!}
                  checked={type === selectedAssociationMembershipType}
                  onChange={(checked) => {
                    if (checked) {
                      setSelectedAssociationMembershipType(type);
                    } else {
                      setSelectedAssociationMembershipType(undefined);
                    }
                  }}
                  label={buildLabel(type)}
                  showError={showError}
                />
              </Accordion.Header>
              <Accordion.Body>
                <span
                  dangerouslySetInnerHTML={{
                    __html: type.descriptionInBestellWizard,
                  }}
                />
              </Accordion.Body>
            </Accordion.Item>
          </Accordion>
        ))}
      </div>

      <NextStepButton onClick={onNextClicked} />
    </>
  );
};

export default Step6BCoopShares;
