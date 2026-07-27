import React from "react";
import { PublicPickupLocation } from "../../api-client";
import { formatCurrency } from "../../utils/formatCurrency.ts";

export function buildDeliveryChargeBadge(pickupLocation: PublicPickupLocation) {
  const amount = Number.parseFloat(pickupLocation.currentDeliveryCharge);
  if (!amount) {
    return null;
  }
  return <span>+ {formatCurrency(amount)} pro Lieferung</span>;
}
