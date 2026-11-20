import { AdminSubscriptionChangePrerequisitesStatus } from "../../api-client";
import { SubscriptionPrerequisitesFormData } from "../types/SubscriptionPrerequisitesFormData.ts";
import { isBankingDataComplete } from "./isBankingDataComplete.ts";
import { isPickupLocationComplete } from "./isPickupLocationComplete.ts";

export function isSubscriptionPrerequisitesFormComplete(
  status: AdminSubscriptionChangePrerequisitesStatus,
  formData: SubscriptionPrerequisitesFormData,
): boolean {
  return (
    isPickupLocationComplete(status, formData) &&
    isBankingDataComplete(status, formData)
  );
}
