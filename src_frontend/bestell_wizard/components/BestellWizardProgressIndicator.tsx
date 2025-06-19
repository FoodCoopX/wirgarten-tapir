import React from "react";
import { PublicProductType } from "../../api-client";
import { BestellWizardStep } from "../types/BestellWizardStep.ts";

interface BestellWizardProgressIndicatorProps {
  currentStep: string | BestellWizardStep;
  steps: (string | BestellWizardStep)[];
  productTypes: PublicProductType[];
}

const BestellWizardProgressIndicator: React.FC<
  BestellWizardProgressIndicatorProps
> = ({ currentStep, steps, productTypes }) => {
  function getColor(step: string) {
    const indexOfCurrentStep = steps.indexOf(currentStep);
    const indexOfColoredStep = steps.indexOf(step);
    if (indexOfColoredStep > indexOfCurrentStep) {
      return "info";
    }

    return "primary";
  }

  function getText(step: string | BestellWizardStep) {
    switch (step) {
      case "intro":
        return "Intro";
      case "pickup_location":
        return "Verteilstation";
      case "coop_shares":
        return "Genossenschaft";
      case "personal_data":
        return "Persönliche Daten";
      case "summary":
        return "Zusammenfassung";
      case "end":
        return "Debug";
      default:
        const productType = productTypes.find(
          (productType) => productType.id === step,
        );
        if (productType === undefined) return step;
        return productType.name;
    }
  }

  return (
    <div
      className={"d-flex flex-column align-items-start justify-content-center"}
      style={{ height: "100%" }}
    >
      {steps.map((step, index) => (
        <>
          {index > 0 && (
            <div
              className={"d-flex flex-row justify-content-center"}
              style={{ width: "50px" }}
            >
              <div
                className={"bg-" + getColor(step)}
                style={{ width: "5px", height: "25px" }}
              ></div>
            </div>
          )}
          <div className={"d-flex flex-row align-items-center"}>
            <div
              className={
                "bg-" +
                getColor(step) +
                " d-flex align-items-center justify-content-center"
              }
              style={{ width: "50px", height: "50px", borderRadius: "50%" }}
            >
              <span className={"text-bg-" + getColor(step)}>{index + 1}</span>
            </div>
            <span style={{ marginLeft: "10px", textWrap: "nowrap" }}>
              {getText(step)}
            </span>
          </div>
        </>
      ))}
    </div>
  );
};

export default BestellWizardProgressIndicator;
