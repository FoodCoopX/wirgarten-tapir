import { PublicProductType } from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";

export function getBiddingRoundProductTypeFromStep(
  step: string,
  settings: BestellWizardSettings,
): [PublicProductType | undefined, string] {
  const separatorIndex = step.lastIndexOf("_");
  if (separatorIndex === -1) {
    return [undefined, ""];
  }
  const productTypeId = step.slice(0, separatorIndex);
  const subStep = step.slice(separatorIndex + 1);
  const productType = settings.productTypes.find(
    (candidate) => candidate.id === productTypeId,
  );
  return [productType, subStep];
}
