import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { PublicProductType } from "../../api-client";

export function getProductTypeFromStep(
  step: string,
  settings: BestellWizardSettings,
): [PublicProductType | undefined, string] {
  const separatorIndex = step.lastIndexOf("_");
  const productId = step.slice(0, separatorIndex);
  const subStep = step.slice(separatorIndex + 1);
  const productType = settings.productTypes.find(
    (productType) => productType.id === productId,
  );
  return [productType, subStep];
}
