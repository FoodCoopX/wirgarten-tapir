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

interface Step6BAssociationMembershipsProps {
  goToNextStep: () => void;
  settings: BestellWizardSettings;
  selectedAssociationMembershipType: AssociationMembershipType | undefined;
  setSelectedAssociationMembershipType: React.Dispatch<
    React.SetStateAction<AssociationMembershipType | undefined>
  >;
  contractStartDate: Date;
  active: boolean;
}

function buildLabel(type: AssociationMembershipType, contractStartDate: Date) {
  const currentPrice = getAssociationMembershipTypeCurrentPrice(
    type,
    contractStartDate,
  );

  if (!currentPrice) {
    return type.name;
  }

  return type.name + " " + formatCurrency(currentPrice.priceAsFloat) + "/Monat";
}

const Step6BAssociationMemberships: React.FC<
  Step6BAssociationMembershipsProps
> = ({
  goToNextStep,
  settings,
  selectedAssociationMembershipType,
  setSelectedAssociationMembershipType,
  contractStartDate,
  active,
}) => {
  const [showError, setShowError] = useState(false);

  useEffect(() => {
    setShowError(false);
  }, [selectedAssociationMembershipType]);

  useEffect(() => {
    if (!active) return;

    if (
      selectedAssociationMembershipType === undefined &&
      settings.associationMembershipTypes.length > 0
    ) {
      setSelectedAssociationMembershipType(
        settings.associationMembershipTypes[0],
      );
    }
  }, [active]);

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
                    }
                  }}
                  label={buildLabel(type, contractStartDate)}
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

export default Step6BAssociationMemberships;
