import { AdminSubscriptionChangePrerequisitesStatus } from "../../api-client";
import { SubscriptionPrerequisitesFormData } from "../types/SubscriptionPrerequisitesFormData.ts";

export function isPickupLocationComplete(
  status: AdminSubscriptionChangePrerequisitesStatus,
  formData: SubscriptionPrerequisitesFormData,
): boolean {
  return status.pickupLocationName !== null || !!formData.pickupLocationId;
}
