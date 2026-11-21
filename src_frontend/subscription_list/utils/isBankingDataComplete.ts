import { AdminSubscriptionChangePrerequisitesStatus } from "../../api-client";
import { isIbanValid } from "../../bestell_wizard/utils/isIbanValid.ts";
import { SubscriptionPrerequisitesFormData } from "../types/SubscriptionPrerequisitesFormData.ts";

export function isBankingDataComplete(
  status: AdminSubscriptionChangePrerequisitesStatus,
  formData: SubscriptionPrerequisitesFormData,
): boolean {
  return (
    status.hasBankingData ||
    (formData.accountOwner.trim().length > 0 &&
      isIbanValid(formData.iban) &&
      formData.sepaMandateConfirmed)
  );
}
