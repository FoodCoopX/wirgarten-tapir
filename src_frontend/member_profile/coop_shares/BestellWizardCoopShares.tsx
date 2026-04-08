import React, { useEffect, useState } from "react";
import { Spinner } from "react-bootstrap";

import "../../../tapir/core/static/core/bootstrap/5.3.8/css/bootstrap.min.css";
import "../../../tapir/core/static/core/css/base.css";
import { useApi } from "../../hooks/useApi.ts";
import { BestellWizardApi, CoopApi } from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { buildEmptySettings } from "../../bestell_wizard/utils/buildEmptySettings.ts";
import { ToastData } from "../../types/ToastData.ts";
import { Step } from "../../bestell_wizard_mobile/types/Step.ts";
import { buildSettings } from "../../bestell_wizard/utils/buildSettings.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import StepGenericIntro from "../../bestell_wizard_mobile/steps/StepGenericIntro.tsx";
import Step6BCoopShares from "../../bestell_wizard_mobile/steps/Step6BCoopShares.tsx";
import Step9BankingData from "../../bestell_wizard_mobile/steps/Step9BankingData.tsx";
import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";
import { getEmptyPersonalData } from "../../bestell_wizard/utils/getEmptyPersonalData.ts";
import BestellWizardMobileBase from "../../bestell_wizard_mobile/components/BestellWizardMobileBase.tsx";
import { addToast } from "../../utils/addToast.ts";
import { v4 as uuidv4 } from "uuid";

interface BestellWizardCoopSharesProps {
  csrfToken: string;
  memberId: string;
  firstName: string;
  lastName: string;
  needsBankingData: boolean;
}

const BestellWizardCoopShares: React.FC<BestellWizardCoopSharesProps> = ({
  csrfToken,
  memberId,
  firstName,
  lastName,
  needsBankingData,
}) => {
  const bestellWizardApi = useApi(BestellWizardApi, csrfToken);
  const coopApi = useApi(CoopApi, csrfToken);

  const [settings, setSettings] =
    useState<BestellWizardSettings>(buildEmptySettings());
  const [settingsLoaded, setSettingsLoaded] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [steps, setSteps] = useState<Step[]>(["loading"]);
  const [currentStep, setCurrentStep] = useState<Step>("loading");
  const [orderLoading, setOrderLoading] = useState(false);

  const [statuteAccepted, setStatuteAccepted] = useState(false);
  const [selectedNumberOfCoopShares, setSelectedNumberOfCoopShares] =
    useState(0);
  const [contractAccepted, setContractAccepted] = useState(false);
  const [sepaAllowed, setSepaAllowed] = useState(false);
  const [personalData, setPersonalData] = useState<PersonalData>(
    getEmptyPersonalData(),
  );

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
          "Fehler beim Laden der BestellWizard",
          setToastDatas,
        ),
      );
  }, []);

  useEffect(() => {
    if (settingsLoaded) {
      const newSteps = ["6a_coop_intro", "6b_coop_shares"];
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

    coopApi
      .coopApiExistingMemberPurchasesSharesCreate({
        existingMemberPurchasesSharesRequestRequest: {
          memberId: memberId,
          numberOfSharesToAdd: selectedNumberOfCoopShares,
          iban: personalData.iban,
          accountOwner: personalData.accountOwner,
          asAdmin: false,
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
              title: "Fehler beim Bestellen der Geno-Anteile",
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
          "Fehler beim Bestellen der Geno-Anteile",
          setToastDatas,
        ),
      );
  }

  function getConfirmButtonText() {
    let share = " zusätzliche Anteile";
    if (selectedNumberOfCoopShares === 1) {
      share = " zusätzlicher Anteil";
    }

    return "Jetzt " + selectedNumberOfCoopShares + share + " zeichnen";
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
      case "6b_coop_shares":
        return (
          <Step6BCoopShares
            goToNextStep={goToNextStep}
            settings={settings}
            selectedNumberOfCoopShares={selectedNumberOfCoopShares}
            setSelectedNumberOfCoopShares={setSelectedNumberOfCoopShares}
            minimumNumberOfShares={1}
            studentStatusEnabled={false}
            setStudentStatusEnabled={() => {}}
            statuteAccepted={statuteAccepted}
            setStatuteAccepted={setStatuteAccepted}
            active={currentStep === step}
            isOrderStep={step === steps.at(-1)}
            orderLoading={orderLoading}
            nextButtonText={
              step === steps.at(-1) ? getConfirmButtonText() : undefined
            }
            canChangeNumberOfShares={true}
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
              step === steps.at(-1) ? getConfirmButtonText() : undefined
            }
            canChangePaymentRhythm={false}
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
      selectedNumberOfCoopShares={selectedNumberOfCoopShares}
    />
  );
};

export default BestellWizardCoopShares;
