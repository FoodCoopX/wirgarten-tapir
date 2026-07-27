import React, { useEffect, useState } from "react";
import { Spinner } from "react-bootstrap";

import { v4 as uuidv4 } from "uuid";
import "../../../tapir/core/static/core/bootstrap/5.3.8/css/bootstrap.min.css";
import "../../../tapir/core/static/core/css/base.css";
import {
  AssociationMembershipType,
  AssociationsApi,
  BestellWizardApi,
} from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";
import { buildEmptySettings } from "../../bestell_wizard/utils/buildEmptySettings.ts";
import { buildSettings } from "../../bestell_wizard/utils/buildSettings.ts";
import { getEmptyPersonalData } from "../../bestell_wizard/utils/getEmptyPersonalData.ts";
import BestellWizardMobileBase from "../../bestell_wizard_mobile/components/BestellWizardMobileBase.tsx";
import Step6BAssociationMembership from "../../bestell_wizard_mobile/steps/Step6BAssociationMembership.tsx";
import Step9BankingData from "../../bestell_wizard_mobile/steps/Step9BankingData.tsx";
import StepGenericIntro from "../../bestell_wizard_mobile/steps/StepGenericIntro.tsx";
import { Step } from "../../bestell_wizard_mobile/types/Step.ts";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { addToast } from "../../utils/addToast.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

interface BestellWizardAssociationMembershipProps {
  csrfToken: string;
  memberId: string;
  firstName: string;
  lastName: string;
  needsBankingData: boolean;
}

const BestellWizardAssociationMembership: React.FC<
  BestellWizardAssociationMembershipProps
> = ({ csrfToken, memberId, firstName, lastName, needsBankingData }) => {
  const bestellWizardApi = useApi(BestellWizardApi, csrfToken);
  const associationApi = useApi(AssociationsApi, csrfToken);

  const [settings, setSettings] =
    useState<BestellWizardSettings>(buildEmptySettings());
  const [settingsLoaded, setSettingsLoaded] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [steps, setSteps] = useState<Step[]>(["loading"]);
  const [currentStep, setCurrentStep] = useState<Step>("loading");
  const [orderLoading, setOrderLoading] = useState(false);
  const [contractAccepted, setContractAccepted] = useState(false);
  const [sepaAllowed, setSepaAllowed] = useState(false);
  const [personalData, setPersonalData] = useState<PersonalData>(
    getEmptyPersonalData(),
  );
  const [
    selectedAssociationMembershipType,
    setSelectedAssociationMembershipType,
  ] = useState<AssociationMembershipType>();

  useEffect(() => {
    setPersonalData({
      ...personalData,
      firstName: firstName,
      lastName: lastName,
    });

    bestellWizardApi
      .bestellWizardApiBestellWizardBaseDataRetrieve()
      .then((baseData) => {
        const newSettings = buildSettings(baseData);
        newSettings.studentStatusAllowed = false;
        setSettings(newSettings);
        setSettingsLoaded(true);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der BestellWizard Basis-Daten",
          setToastDatas,
        ),
      );
  }, []);

  useEffect(() => {
    if (settingsLoaded) {
      const newSteps = ["6a_coop_intro", "6b_association_membership"];
      if (needsBankingData) {
        newSteps.push("9_banking_data");
      }
      setSteps(newSteps);
      setCurrentStep(newSteps[0]);
    } else {
      setSteps(["loading"]);
    }
  }, [settingsLoaded, needsBankingData]);

  function goToNextStep() {
    const currentIndex = steps.indexOf(currentStep);
    if (currentIndex + 1 >= steps.length) {
      onConfirm();
      return;
    }

    setCurrentStep(steps[steps.indexOf(currentStep) + 1]);
  }

  function onConfirm() {
    setOrderLoading(true);

    associationApi
      .associationsApiExistingMemberUpdatesMembershipCreate({
        existingMemberUpdatesAssociationMembershipRequestRequest: {
          associationMembershipTypeId: selectedAssociationMembershipType?.id!,
          memberId: memberId,
          iban: personalData.iban,
          accountOwner: personalData.accountOwner,
        },
      })
      .then((response) => {
        if (response.orderConfirmed) {
          if (response.redirectUrl) {
            location.assign(response.redirectUrl);
          }
        } else {
          addToast(
            {
              title: "Fehler beim Ändern der Vereinsmitgliedschaft",
              message: response.error ?? undefined,
              variant: "danger",
              id: uuidv4(),
            },
            setToastDatas,
          );
        }
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Ändern der Vereinsmitgliedschaft",
          setToastDatas,
        ),
      );
  }

  function getStepComponent(step: Step) {
    switch (step) {
      case "6a_coop_intro":
        return (
          <StepGenericIntro
            goToNextStep={goToNextStep}
            content={{
              text: settings.strings.step6aText,
            }}
          />
        );
      case "6b_association_membership":
        return (
          <Step6BAssociationMembership
            goToNextStep={goToNextStep}
            settings={settings}
            selectedAssociationMembershipType={
              selectedAssociationMembershipType
            }
            setSelectedAssociationMembershipType={
              setSelectedAssociationMembershipType
            }
            contractStartDate={
              settings.growingPeriodChoices.length > 0
                ? settings.growingPeriodChoices[0].contractStartDate
                : new Date()
            }
            active={currentStep === step}
            isOrderStep={step === steps.at(-1)}
          />
        );
      case "9_banking_data":
        return (
          <Step9BankingData
            goToNextStep={goToNextStep}
            personalData={personalData}
            setPersonalData={setPersonalData}
            sepaAllowed={sepaAllowed}
            setSepaAllowed={setSepaAllowed}
            contractAccepted={contractAccepted}
            setContractAccepted={setContractAccepted}
            settings={settings}
            shoppingCart={{}}
            solidarityContribution={0}
            active={currentStep === step}
            productTypesInWaitingList={new Set()}
            isOrderStep={step === steps.at(-1)}
            orderLoading={orderLoading}
            nextButtonText={
              step === steps.at(-1)
                ? "Vereinsmitgliedschaft bestätigen"
                : undefined
            }
            canChangePaymentRhythm={false}
            autoFillAccountOwnerFromName={false}
          />
        );
      case "loading":
        return (
          <div
            style={{ width: "100%", height: "100%" }}
            className={"d-flex justify-content-center align-items-center"}
          >
            <Spinner />
          </div>
        );
      default:
        return (
          <StepGenericIntro
            content={{
              text: "Invalid step: " + step,
            }}
            goToNextStep={goToNextStep}
          />
        );
    }
  }

  return (
    <BestellWizardMobileBase
      settings={settings}
      steps={steps}
      currentStep={currentStep}
      setCurrentStep={setCurrentStep}
      shoppingCart={{}}
      phases={[]}
      selectedPickupLocations={[]}
      solidarityContribution={0}
      productTypesInWaitingList={new Set()}
      personalData={personalData}
      getStepComponent={getStepComponent}
      setTestData={() => {}}
      toastDatas={toastDatas}
      setToastDatas={setToastDatas}
      showProgress={false}
      hideFooterButtonsOnLastStep={false}
      selectedNumberOfCoopShares={0}
      goToProductTypeStep={() => {}}
      contractStartDate={
        settings.growingPeriodChoices.length > 0
          ? settings.growingPeriodChoices[0].contractStartDate
          : new Date()
      }
      selectedGrowingPeriod={undefined}
    />
  );
};

export default BestellWizardAssociationMembership;
